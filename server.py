import asyncio
import json
import os
import re
import threading
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from brain import JarvisBrain
from automation import JarvisAutomation
from vision_engine import VisionEngine
from voice_engine import VoiceEngine

# ──────────────────────────────────────────────────────────────────
# Wake-word event broadcast (SSE)
# ──────────────────────────────────────────────────────────────────
_wake_clients = []           # List of asyncio.Queue for connected SSE clients
_wake_triggered_flag = threading.Event()
_mode_changed_flag = threading.Event() # Issue 16: Mode Sync Flag

# ──────────────────────────────────────────────────────────────────
# App lifespan — start/stop wake-word listener with the server
# ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _wake_clients
    _wake_clients = []

    def _on_wake_word():
        """Called from voice thread when wake word detected."""
        _wake_triggered_flag.set()          # Signal the SSE flusher coroutine
        print("🚨 SERVER: Wake-word detected!")

    # Run Startup Diagnostic
    print("\n🔍 JARVIS: Running Startup Diagnostics...")
    diag = auto.check_dependencies()
    print(diag)
    print("─" * 44)

    # Start background wake-word listener (daemon thread — dies with server)
    voice.start_wake_word_listener(_on_wake_word)

    # Start async task that watches for wake flag and pushes SSE events
    _sse_task = asyncio.create_task(_wake_flag_watcher())

    yield  # ← server runs here

    # Shutdown
    voice.stop_wake_word_listener()
    _sse_task.cancel()
    print("🛑 SERVER: Shutdown complete.")


async def _wake_flag_watcher():
    """Watcher task that broadcasts thread-safe flag triggers to all SSE client queues."""
    global _wake_clients
    while True:
        await asyncio.sleep(0.3)
        if _wake_triggered_flag.is_set():
            _wake_triggered_flag.clear()
            # Push to all connected clients
            for q in _wake_clients:
                await q.put("wake")
        
        if _mode_changed_flag.is_set():
            _mode_changed_flag.clear()
            # Broadcast the current mode info
            for q in _wake_clients:
                await q.put(f"mode:{_interaction_mode}")


# ──────────────────────────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────────────────────────
app = FastAPI(lifespan=lifespan)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Core engine instances ──────────────────────────────────────────
brain  = JarvisBrain()
auto   = JarvisAutomation()
vision = VisionEngine()
voice  = VoiceEngine()

# ── Global state ──────────────────────────────────────────────────
_cached_specs = None
_interaction_mode = "speech"  # 'text' or 'speech' (Issue 16: Mode Toggle)

def get_specs():
    """Lazy-load specs to avoid blocking server startup."""
    global _cached_specs
    if _cached_specs is None:
        _cached_specs = auto.get_detailed_specs()
    return _cached_specs

COMMANDS_FILE = "commands.json"

# ──────────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────────
class CommandRequest(BaseModel):
    command: str

# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────
def get_custom_commands() -> dict:
    if not os.path.exists(COMMANDS_FILE):
        return {}
    with open(COMMANDS_FILE, 'r') as f:
        return json.load(f)


def _gather_screen_context(force=False) -> str:
    """
    Capture a screenshot and run OCR on it.
    Returns a formatted string to inject into the brain's context.
    Returns empty string if OCR yields no useful text or if not requested.
    """
    if not force:
        # Issue 5: Skip expensive OCR unless specifically needed
        return ""
        
    try:
        img = vision.capture_screen()
        text = vision.get_ocr_text(img)
        if text and len(text.strip()) > 20:
            # Truncate to avoid blowing up the prompt (Issue 3/Config)
            max_chars = int(os.getenv("OCR_MAX_CHARS", "800"))
            trimmed = text.strip()[:max_chars]
            return f"SCREEN CONTEXT (OCR of current display):\n{trimmed}"
    except Exception as e:
        print(f"⚠️  Vision context error: {e}")
    return ""


def _execute_actions(actions: list) -> list:
    """Parse and execute all [[ACTION: ...]] tags extracted from the brain's response."""
    executed = []

    for action in actions:
        print(f"⚡ JARVIS: Executing action → {action}")
        action_upper = action.strip().upper()

        if action_upper.startswith("OPEN_APP"):
            m = re.search(r'\((.*?)\)', action)
            if m:
                result = auto.open_app(m.group(1).strip())
                executed.append(result)

        elif action_upper.startswith("OPEN_URL"):
            m = re.search(r'\((.*?)\)', action)
            if m:
                result = auto.open_url(m.group(1).strip())
                executed.append(result)

        elif action_upper.startswith("OPEN_FOLDER"):
            m = re.search(r'\((.*?)\)', action)
            if m:
                result = auto.open_folder(m.group(1).strip())
                executed.append(result)

        elif action_upper.startswith("GET_STATS"):
            stats = auto.get_system_stats()
            executed.append(stats)

        elif action_upper.startswith("SET_BRIGHTNESS"):
            m = re.search(r'\((.*?)\)', action)
            if m:
                result = auto.set_brightness(m.group(1).strip())
                executed.append(result)

        elif action_upper.startswith("SET_VOLUME"):
            m = re.search(r'\((.*?)\)', action)
            if m:
                result = auto.set_volume(m.group(1).strip())
                executed.append(result)

        elif action_upper.startswith("MUTE_UNMUTE"):
            result = auto.toggle_mute()
            executed.append(result)

        elif action_upper.startswith("TAKE_SCREENSHOT"):
            result = auto.take_screenshot()
            executed.append(result)

    return executed


# ──────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Quick health check — also tests Ollama connectivity."""
    ollama_ok = brain.ping()
    return {
        "server": "online",
        "ollama": "online" if ollama_ok else "offline",
        "jarvis_awake": True, # Issue 2 Fix: Jarvis is always awake when the server is on
        "history_turns": len(brain.history) // 2,
    }


@app.get("/stats")
async def get_stats():
    return {"stats": auto.get_system_stats()}


@app.get("/commands")
async def list_commands():
    return get_custom_commands()


@app.post("/commands")
async def save_commands(commands: dict):
    with open(COMMANDS_FILE, 'w') as f:
        json.dump(commands, f, indent=2)
    return {"status": "ok"}


@app.get("/settings/mode")
async def get_mode():
    return {"mode": _interaction_mode}


@app.post("/settings/mode")
async def set_mode(request: dict):
    global _interaction_mode
    new_mode = request.get("mode", "speech").lower()
    if new_mode not in ["text", "speech"]:
        raise HTTPException(status_code=400, detail="Invalid mode")
    
    _interaction_mode = new_mode
    _mode_changed_flag.set() # Trigger SSE broadcast
    
    if _interaction_mode == "text":
        voice.stop_wake_word_listener()
        print("🔇 SERVER: Interaction Mode -> TEXT (Mic Off)")
    else:
        # Re-start with the same callback used in lifespan
        def _on_wake_word():
            _wake_triggered_flag.set()
            print("🚨 SERVER: Wake-word detected!")
        voice.start_wake_word_listener(_on_wake_word)
        print("🔊 SERVER: Interaction Mode -> SPEECH (Mic On)")
        
    return {"mode": _interaction_mode}


@app.post("/command")
async def process_command(request: CommandRequest, background_tasks: BackgroundTasks):
    """Main AI command endpoint — always active, no sleep mode."""
    cmd = request.command.strip()
    print(f"📨 SERVER: Command received → '{cmd}'")

    # ── Suppress wake-word while processing ──────────────────
    voice.set_processing(True)
    
    try:
        # ── Build context: date/time + specs + shortcuts + screen vision ─
        now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        shortcuts = get_custom_commands()
        context = f"CURRENT DATE/TIME: {now}\n\n"
        context += f"SYSTEM HARDWARE SPECS (REAL):\n{get_specs()}\n\n"
        context += "CUSTOM USER SHORTCUTS:\n"
        context += "\n".join([f"  - Say '{k}' to execute: {v}" for k, v in shortcuts.items()])

        # Issue 5: Only trigger OCR if command implies vision/screen focus
        vision_keywords = ["screen", "look", "see", "read", "display", "window", "show me"]
        needs_vision = any(k in cmd.lower() for k in vision_keywords)
        
        screen_ctx = await asyncio.to_thread(_gather_screen_context, force=needs_vision)
        if screen_ctx:
            context += f"\n\n{screen_ctx}"

        # ── Rewrite prompt for shortcut commands ──────────────────
        brain_prompt = cmd
        if cmd.lower() in shortcuts:
            brain_prompt = (
                f"The user said the shortcut keyword '{cmd}', which maps to '{shortcuts[cmd.lower()]}'. "
                f"Acknowledge naturally and execute the mapped action."
            )

        # ── Think ─────────────────────────────────────────────────
        response = await asyncio.to_thread(brain.think, brain_prompt, context)

        # ── Clean response text (strip action tags) ───────────────
        clean_response = re.sub(
            r'\[\[ACTION:\s*.*?\]\]', '', response, flags=re.IGNORECASE
        ).strip()

        # ── Parse & execute all actions ───────────────────────────
        # Issue 4: More robust action parsing (case-insensitive, handles small typos)
        actions_raw = re.findall(r'\[\[ACTION:\s*(.*?)\]\]', response, flags=re.IGNORECASE)
        if not actions_raw:
            # Fallback for models that might omit brackets or forget the ACTION prefix
            # but still output the function call
            lazy_matches = re.findall(r'OPEN_APP\(.*?\)|OPEN_URL\(.*?\)|SET_VOLUME\(.*?\)', response, flags=re.IGNORECASE)
            actions_raw = lazy_matches

        executed_actions = _execute_actions(actions_raw)

        # ── TTS (now non-blocking via internal queue) ─────────────
        voice.speak(clean_response)

        return {
            "response": clean_response,
            "actions": executed_actions,
        }
    finally:
        # ── Release wake-word suppression ─────────────────────
        voice.set_processing(False)



@app.get("/listen")
async def trigger_listening():
    """
    Activate the microphone and return the transcribed command.
    ✅ Fixed: runs in thread so it doesn't block the async server.
    """
    try:
        print("🎤 SERVER: Triggering microphone listen...")
        text = await asyncio.to_thread(voice.listen)
        return {"text": text or ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/speak")
async def trigger_speaking(request: dict, background_tasks: BackgroundTasks):
    """Speak text via TTS — runs in background so endpoint returns immediately."""
    text = request.get("text", "").strip()
    if text:
        background_tasks.add_task(voice.speak, text)
    return {"status": "ok"}


@app.post("/wake")
async def manual_wake():
    """No-op — Jarvis is always active. Kept for frontend compatibility."""
    return {"status": "active", "response": "Online and ready, Sir."}


@app.get("/clear-history")
async def clear_history():
    """Wipe the conversation memory."""
    brain.clear_history()
    return {"status": "ok", "message": "Conversation memory cleared."}


@app.get("/wake-stream")
async def wake_stream():
    """SSE endpoint for wake-word and mode-change notifications."""
    async def event_generator():
        q = asyncio.Queue()
        _wake_clients.append(q)
        print(f"📡 SSE: Client connected. Total clients: {len(_wake_clients)}")
        
        try:
            # Send initial mode on connect
            yield f"data: mode:{_interaction_mode}\n\n"
            while True:
                try:
                    # Wait for a wake event (with periodic keepalive pings)
                    event = await asyncio.wait_for(q.get(), timeout=20)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if q in _wake_clients:
                _wake_clients.remove(q)
            print(f"📡 SSE: Client disconnected. Total clients: {len(_wake_clients)}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    # Use 'warning' level to keep the terminal clean of polling logs
    uvicorn.run(app, host=host, port=port, log_level="warning")
