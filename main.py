import subprocess
import time
import os
import sys


def run_jarvis_web():
    procs = {}

    # ── 1. Backend (FastAPI + Uvicorn) ─────────────────────────────
    print("🚀 JARVIS: Starting System Core (FastAPI)...")
    procs['backend'] = subprocess.Popen([sys.executable, "server.py"])
    
    # Issue 7: Poll /health instead of static sleep
    print("⌛ Waiting for System Core to stabilize...")
    import requests
    max_retries = 20
    for i in range(max_retries):
        try:
            r = requests.get("http://localhost:8000/health", timeout=1)
            if r.status_code == 200:
                print("✅ System Core Online.")
                break
        except:
            pass
        time.sleep(1)
    else:
        print("❌ System Core failed to start in time. Aborting.")
        procs['backend'].terminate()
        return

    # ── 2. Desktop Widget (loads widget.html — no Vite needed) ─────
    print("💎 JARVIS: Deploying Desktop Widget...")
    procs['widget'] = subprocess.Popen([sys.executable, "widget_launcher.py"])

    # ── 3. Main UI (Vite/React — optional, for full command center) ─
    print("🌐 JARVIS: Starting Satellite UI (Vite)...")
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    procs['frontend'] = subprocess.Popen(
        "npm run dev -- --no-open", shell=True, cwd=frontend_dir
    )

    print("\n✅ JARVIS IS ONLINE")
    print("─" * 44)
    print("  Backend API : http://localhost:8000")
    print("  Frontend UI : http://localhost:5173")
    print("  Widget      : Standalone (widget.html)")
    print("─" * 44)
    print("  Press Ctrl+C to shut down all systems.")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 JARVIS: Shutting down systems...")
        for name, proc in procs.items():
            try:
                proc.terminate()
                print(f"   ✓ {name} stopped")
            except Exception:
                pass
        print("Goodbye, Sir.")


if __name__ == "__main__":
    run_jarvis_web()
