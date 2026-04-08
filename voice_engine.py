import os
import queue
import threading
import subprocess
import sys
import sounddevice as sd
import vosk
import json
import time


class VoiceEngine:
    def __init__(self, model_path=None):
        # ── 1. TTS Subprocess State ──────────────────────────────────
        self._tts_proc   = None
        self._tts_lock   = threading.Lock()
        self._tts_ready  = False
        
        # ── 2. Sequential Speech Queue ────────────────────────────────
        self._speech_queue = queue.Queue()
        self._is_speaking_event = threading.Event()
        self._last_speak_start_at = 0
        
        # Start the TTS subprocess
        self._start_tts_proc()
        
        # Start the high-level speech worker (handles the queue)
        threading.Thread(target=self._speech_worker_loop, daemon=True, name="SpeechQueueWorker").start()

        # ── 3. STT Model ─────────────────────────────────────────────
        self.q = queue.Queue()
        if not model_path:
            model_path = "vosk-model-small-en-us-0.15"
        if not os.path.exists(model_path):
            print(f"⚠️  Vosk model not found at '{model_path}'.")
            self.stt_model = None
        else:
            print(f"✅ VoiceEngine: Vosk model loaded from '{model_path}'")
            self.stt_model = vosk.Model(model_path)

        # ── 4. Audio Device ──────────────────────────────────────────
        try:
            self.device_info = sd.query_devices(None, 'input')
            self.samplerate  = int(self.device_info['default_samplerate'])
        except Exception as e:
            print(f"⚠️  VoiceEngine: Audio device error: {e}")
            self.samplerate = 16000

        # ── 5. Wake-Word Listener State ───────────────────────────────
        self._wake_thread      = None
        self._wake_active      = False
        self._wake_callback    = None
        self._is_processing    = False   # Set to True when Jarvis is busy
        self._processing_lock  = threading.Lock()
        self.WAKE_WORDS        = {"hey jarvis", "jarvis", "hey jarvis wake up"}

    # ──────────────────────────────────────────────────────────────────
    # Subprocess Management
    # ──────────────────────────────────────────────────────────────────
    def _start_tts_proc(self):
        """Launch speak_worker.py as a child process."""
        worker_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "speak_worker.py")
        try:
            if self._tts_proc:
                try: self._tts_proc.kill()
                except: pass

            self._tts_proc = subprocess.Popen(
                [sys.executable, worker_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            # Wait for "TTS_READY" signal
            ready_line = self._tts_proc.stdout.readline().strip()
            if ready_line == "TTS_READY":
                self._tts_ready = True
                print("✅ VoiceEngine: SAPI5 TTS worker ready.")
                # Monitor signaling
                threading.Thread(target=self._monitor_tts_outputs, daemon=True, name="TTSMonitor").start()
            else:
                print(f"❌ VoiceEngine: TTS Worker failed: {ready_line}")
                self._tts_ready = False
        except Exception as e:
            print(f"❌ VoiceEngine: Critical TTS failure: {e}")
            self._tts_ready = False

    def _monitor_tts_outputs(self):
        """Monitor stdout signals for SPEAK_START/FINISHED."""
        proc = self._tts_proc
        if not proc: return
        try:
            for line in proc.stdout:
                msg = line.strip()
                if msg == "TTS_STARTING":
                    self._is_speaking_event.set()
                    self._last_speak_start_at = time.time()
                elif msg == "TTS_FINISHED":
                    self._is_speaking_event.clear()
        except:
            pass
        finally:
            self._is_speaking_event.clear()

    def _ensure_tts_alive(self):
        """Heartbeat: auto-restart TTS if dead or hung."""
        # Check hang: if event is SET for more than 15s.
        has_hung = (self._is_speaking_event.is_set() and (time.time() - self._last_speak_start_at) > 15)
        is_dead = (self._tts_proc is None or self._tts_proc.poll() is not None)

        if is_dead or has_hung:
            if has_hung: print("⚠️ VoiceEngine: SAPI5 HANG detected — RESTARTING.")
            else: print("⚠️ VoiceEngine: SAPI5 Process DIED — RESTARTING.")
            self._start_tts_proc()

    # ──────────────────────────────────────────────────────────────────
    # Robust Sequential Speech Loop
    # ──────────────────────────────────────────────────────────────────
    def _speech_worker_loop(self):
        """Funnels all speak() events into the subprocess one-by-one."""
        while True:
            text = self._speech_queue.get()
            if text is None: break 
            
            with self._tts_lock:
                self._ensure_tts_alive()
                if not self._tts_ready: continue
                
                try:
                    safe = text.replace('\n', ' ').replace('\r', '').strip()
                    if not safe: continue
                    
                    # Log precisely what is being sent to the driver for debugging
                    print(f"🔊 SENDING_TO_SAPI5: {safe[:40]}...")
                    
                    self._tts_proc.stdin.write(safe + "\n")
                    self._tts_proc.stdin.flush()
                    
                    # Wait up to 20s for this specific utterance to finish
                    # This prevents driver collisions.
                    # We wait for STARTING, then wait for it to CLEAR.
                    time.sleep(0.1) # Brief gap to let monitor see STDOUT
                    
                    wait_limit = time.time() + 20
                    while self._is_speaking_event.is_set() and time.time() < wait_limit:
                        time.sleep(0.1)

                except Exception as e:
                    print(f"⚠️ VoiceEngine: Speech transmission error: {e}")
            
            self._speech_queue.task_done()
            time.sleep(0.2) # Clear air gap

    def speak(self, text: str):
        """Queues text to be spoken. Non-blocking."""
        if not text or not text.strip(): return
        print(f"🔊 JARVIS: {text}")
        self._speech_queue.put(text)

    # ──────────────────────────────────────────────────────────────────
    # State & STT (remain stable)
    # ──────────────────────────────────────────────────────────────────
    def set_processing(self, state: bool):
        with self._processing_lock:
            self._is_processing = state

    def stop_tts(self):
        self._speech_queue.put(None)
        if self._tts_proc:
            try:
                self._tts_proc.stdin.write("QUIT\n")
                self._tts_proc.stdin.flush()
            except: pass
            self._tts_proc.terminate()

    def listen(self, timeout: int = 15) -> str:
        if not self.stt_model: return "STT model not found"
        while not self.q.empty():
            try: self.q.get_nowait()
            except: break
        try:
            with sd.RawInputStream(
                samplerate=self.samplerate, blocksize=8000,
                device=None, dtype='int16', channels=1, callback=lambda i,f,t,s: self.q.put(bytes(i))
            ):
                rec = vosk.KaldiRecognizer(self.stt_model, self.samplerate)
                deadline = time.time() + timeout
                print("👂 Listening...")
                while time.time() < deadline:
                    try: data = self.q.get(timeout=1)
                    except: continue
                    if rec.AcceptWaveform(data):
                        res = json.loads(rec.Result()).get("text", "").strip()
                        if res: 
                            print(f"🗣️ USER: '{res}'")
                            return res
                return ""
        except Exception as e:
            print(f"❌ listen() error: {e}")
            return ""

    def start_wake_word_listener(self, callback):
        if not self.stt_model or self._wake_active: return
        self._wake_active, self._wake_callback = True, callback
        threading.Thread(target=self._wake_word_loop, daemon=True).start()

    def stop_wake_word_listener(self):
        self._wake_active = False

    def _wake_word_loop(self):
        # Issue 10: Non-blocking cooldown
        last_wake_at = 0
        cooldown = int(os.getenv("COOLDOWN_SECONDS", "4"))
        grammar = json.dumps(list(self.WAKE_WORDS) + ["[unk]"])
        wq = queue.Queue()

        try:
            with sd.RawInputStream(
                samplerate=self.samplerate, blocksize=8000,
                device=None, dtype='int16', channels=1, callback=lambda i,f,t,s: wq.put(bytes(i))
            ):
                rec = vosk.KaldiRecognizer(self.stt_model, self.samplerate, grammar)
                while self._wake_active:
                    try: data = wq.get(timeout=0.5)
                    except: continue
                    if rec.AcceptWaveform(data):
                        t = json.loads(rec.Result()).get("text", "").strip().lower()
                        if t and t != "[unk]" and any(w in t for w in self.WAKE_WORDS):
                            now = time.time()
                            if self._is_processing or (now - last_wake_at < cooldown):
                                continue
                            
                            print(f"🚨 WAKE: '{t}'")
                            last_wake_at = now
                            if self._wake_callback: self._wake_callback()
                            # rec = vosk.KaldiRecognizer(self.stt_model, self.samplerate, grammar) # Not always needed if grammar is same
        except: self._wake_active = False

if __name__ == "__main__":
    v = VoiceEngine()
    v.speak("Final stability diagnostic complete. Voice system is online.")
