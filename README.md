# JARVIS: Advanced Desktop AI Assistant

JARVIS (Just A Rather Very Intelligent System) is a premium, always-on desktop assistant inspired by Tony Stark's legendary AI. It combines local LLM reasoning, offline voice recognition, and a stunning 3D interface to provide a truly immersive assistant experience.

---

## 🚀 Key Features

*   **🎙️ Smart Interaction Modes**: Toggle between **LIVE_SPEECH** (always listening for "Jarvis") and **TEXT_ONLY** (silent typing) directly from the dashboard.
*   **📡 Real-Time Sync**: Instant synchronization across the Dashboard and floating Desktop Widget using SSE-based mode broadcasting.
*   **🏗️ Smart Automation**:
    *   **Dynamic Pathing**: Automatically resolves placeholders like `C:\Users\Username` to your actual Windows home directory.
    *   **Web Fallback**: Intelligently opens browser versions of apps (e.g., YouTube, Netflix) if the local desktop version is missing.
*   **🔊 Stable Speech**: Robust sequential speech queue using direct Windows SAPI5 for 100% reliable verbal responses.
*   **🖱️ Desktop Widget**: A floating, glassmorphic 3D Globe widget (Three.js) for quick status and mode-specific interaction.
*   **🧠 Optimized Brain**: Character-based context truncation and conversational history pruning to prevent LLM context window overflows.
*   **🌐 Developer Dashboard**: A refined React/Vite "Aura" dashboard featuring a personalized developer footer and real-time system diagnostics.

---

## 🏗️ Technical Architecture

*   **Core**: FastAPI (Python) backend running the brain, voice, and vision engines.
*   **Brain**: Local LLM reasoning via **Ollama** (Llama 3.1 / Qwen2.5-VL/phi3).
*   **Voice Engine**:
    *   **STT**: Offline Vosk model (Kaldi-based) with strict wake-word enforcement.
    *   **TTS**: Isolated SAPI5 subprocess with a Heartbeat Monitor and non-blocking speech cooldowns.
*   **Frontend**: React + Vite (Aura Design System) with real-time SSE sync.
*   **Automation**: Advanced fuzzy-matching for application launching and cross-platform portablity guards.

---

## 🛠️ Prerequisites

1.  **Python 3.10+**
2.  **Ollama**: [ollama.com](https://ollama.com)
    *   Required: `ollama pull llama3.1` (or your preferred model)
3.  **Tesseract OCR**: (Optional) [Installation Guide](https://github.com/UB-Mannheim/tesseract/wiki)
4.  **Node.js**: Required for the Vite frontend.

---

## 📥 Installation

1.  Clone the repository.
2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configuration**: Create a `.env` file in the root using the table below.
4.  Download the STT model:
    ```bash
    python setup_vosk.py
    ```
5.  Install Frontend dependencies:
    ```bash
    cd frontend
    npm install
    cd ..
    ```

---

## 🚦 How to Run

To launch the entire JARVIS ecosystem (Backend + Desktop Widget + Frontend), simply run:

```bash
python main.py
```

*   **Backend API**: `http://127.0.0.1:8000`
*   **Satellite UI**: `http://localhost:5173`
*   **Floating Widget**: Standalone window (`widget.html`)

---

## ⚙️ Configuration (.env)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `JARVIS_MODEL` | The Ollama model to use. | `llama3.1:latest` |
| `OLLAMA_URL` | Endpoint for Ollama. | `http://localhost:11434` |
| `HOST` / `PORT` | Backend server settings. | `127.0.0.1` / `8000` |
| `OCR_MAX_CHARS` | Character limit for screen context. | `800` |
| `COOLDOWN_SECONDS` | Interaction cooldown. | `4` |

---

## 📁 Project Structure

*   `main.py`: Ecosystem launcher with health-check polling.
*   `server.py`: FastAPI server and real-time SSE mode/wake broadcaster.
*   `voice_engine.py`: Sequential speech and Vosk wake-word listener.
*   `brain.py`: LLM logic with history pruning and context management.
*   `automation.py`: System control with dynamic pathing and web-fallbacks.
*   `widget.html`: 3D Globe with strict interaction mode support.
*   `frontend/`: React Dashboard with Developer Branding.

---

## 🤝 Developer
**Made with ❤️ by Rudra Kumar Gupta**
[[Portfolio](https://rudra-gupta.vercel.app/)] [[LinkedIn](https://www.linkedin.com/in/rudra-kumar-gupta/)] [[GitHub](https://github.com/Rudra-Gupta15)]
