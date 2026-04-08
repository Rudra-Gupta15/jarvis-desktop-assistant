import requests
import json
import os
from collections import deque
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "You are JARVIS, a sophisticated, witty, and proactive AI desktop assistant. "
    "Respond naturally and fluently, like Tony Stark's JARVIS — confident, precise, and helpful. "
    "Keep responses concise (1-3 sentences) unless detail is explicitly needed. "
    "ALWAYS verbally confirm any system action you take (e.g., 'Of course, launching Steam now.'). "
    "You have access to live screen context (OCR text from the user's screen) — use it proactively when relevant. "
    "For all system operations, you MUST include exactly one ACTION tag at the end of your response:\n"
    "- [[ACTION: OPEN_APP(Natural Name)]] (e.g., 'GitHub', 'YouTube', 'Settings')\n"
    "- [[ACTION: OPEN_URL(url)]]\n"
    "- [[ACTION: OPEN_FOLDER(path)]] (Note: Use 'C:\\Users\\Username' for the home directory; I will resolve 'Username' automatically.)\n"
    "- [[ACTION: GET_STATS()]]\n"
    "- [[ACTION: SET_BRIGHTNESS(0-100)]]\n"
    "- [[ACTION: SET_VOLUME(0-100)]]\n"
    "- [[ACTION: MUTE_UNMUTE()]]\n"
    "- [[ACTION: TAKE_SCREENSHOT()]]\n\n"
    "CRITICAL: For OPEN_APP, JARVIS will automatically fallback to a web version (e.g., YouTube.com) if the desktop app is missing. "
    "REMINDER: Use the REAL hardware specs from Context when asked about the machine. "
    "If the user uses a shortcut keyword, find its action in the context and execute it. "
    "If no system action is needed, do NOT include an ACTION tag."
)


class JarvisBrain:
    def __init__(self, model=None):
        self.model = model or os.getenv("JARVIS_MODEL", "phi3:mini")
        self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.generate_url = f"{self.base_url}/api/generate"
        # Issue 13: History pruning - keep only last 20 messages (10 turns) in memory
        self.history = deque(maxlen=20) 
        self.ollama_available = False
        self._check_ollama_health()
        
        # Issue 3: OCR/Context limit
        self.max_context_chars = int(os.getenv("OCR_MAX_CHARS", "800"))

    # ──────────────────────────────────────────────
    # Health check
    # ──────────────────────────────────────────────
    def _check_ollama_health(self):
        """Ping Ollama on init to verify it's running and ensure model exists."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            
            if not models:
                print("⚠️  JARVIS Brain: Ollama is running but no models are pulled yet.")
                self.ollama_available = False
                return

            self.ollama_available = True
            
            # Verify if current model exists
            current_exists = any(self.model in m or m in self.model for m in models)
            if not current_exists:
                fallback = models[0]
                print(f"⚠️  JARVIS Brain: Model '{self.model}' not found. Falling back to '{fallback}'.")
                self.model = fallback
            else:
                print(f"✅ JARVIS Brain: Connected. Using model: {self.model}")

        except requests.exceptions.ConnectionError:
            print("❌ JARVIS Brain: Ollama is NOT running at localhost:11434.")
            self.ollama_available = False
        except Exception as e:
            print(f"⚠️  JARVIS Brain: Health-check error: {e}")
            self.ollama_available = False

    def ping(self):
        """Re-check Ollama availability (called by server on each request if needed)."""
        if not self.ollama_available:
            self._check_ollama_health()
        return self.ollama_available

    # ──────────────────────────────────────────────
    # Core reasoning
    # ──────────────────────────────────────────────
    def think(self, prompt: str, context: str = "", image_b64=None) -> str:
        """
        Send a prompt to Ollama and return the response.
        Maintains multi-turn conversation history.
        """
        if not self.ollama_available:
            # Try to reconnect before giving up
            self._check_ollama_health()
            if not self.ollama_available:
                return ("I'm having trouble reaching my neural core right now. "
                        "Please ensure Ollama is running (`ollama serve`) and try again.")

        # Issue 3 & 13: Build full prompt with system context + history + new user message
        # history_text is already limited by the deque (maxlen=20)
        history_text = ""
        for turn in self.history:
            role_label = "User" if turn["role"] == "user" else "Assistant"
            history_text += f"{role_label}: {turn['content']}\n"

        # Truncate context to prevent overflow (Issue 3)
        if len(context) > 2000: # Broad limit for the whole context block
            context = context[:2000] + "... [Truncated]"

        full_prompt = (
            f"System: {SYSTEM_PROMPT}\n\n"
            f"Context:\n{context}\n\n"
            f"Conversation History:\n{history_text}"
            f"User: {prompt}\n\n"
            f"Assistant:"
        )

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
        }

        if image_b64:
            payload["images"] = [image_b64]

        # Retry once on failure
        for attempt in range(2):
            try:
                print(f"🧠 JARVIS Brain: Thinking... (model: {self.model}, attempt {attempt + 1})")
                response = requests.post(self.generate_url, json=payload, timeout=90)
                response.raise_for_status()
                result = response.json()
                answer = result.get("response", "I'm sorry, I couldn't process that request.")

                # Save to history
                self.history.append({"role": "user", "content": prompt})
                self.history.append({"role": "assistant", "content": answer})

                print(f"✅ JARVIS Brain: Response received ({len(answer)} chars)")
                return answer

            except requests.exceptions.Timeout:
                if attempt == 0:
                    print("⚠️  JARVIS Brain: Timeout on attempt 1, retrying...")
                    continue
                return "My neural core is taking too long to respond. Ollama might be under heavy load."
            except requests.exceptions.ConnectionError:
                self.ollama_available = False
                return "I've lost connection to my neural core. Please ensure Ollama is running."
            except Exception as e:
                return f"An unexpected error occurred in my brain: {e}"

    # ──────────────────────────────────────────────
    # Memory management
    # ──────────────────────────────────────────────
    def clear_history(self):
        """Wipe conversation memory (called when Jarvis goes to sleep/resets)."""
        self.history.clear()
        print("🧹 JARVIS Brain: Conversation history cleared.")

    def get_history_summary(self):
        """Return a short readable summary of conversation turns."""
        if not self.history:
            return "No conversation history."
        return f"{len(self.history) // 2} exchange(s) in memory."


if __name__ == "__main__":
    brain = JarvisBrain()
    if brain.ollama_available:
        print("\n--- Turn 1 ---")
        r1 = brain.think("Hello Jarvis. What is your primary function?")
        print(f"JARVIS: {r1}")
        print("\n--- Turn 2 (tests memory) ---")
        r2 = brain.think("What did I just ask you about?")
        print(f"JARVIS: {r2}")
