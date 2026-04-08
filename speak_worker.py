"""
speak_worker.py — Standalone TTS subprocess for JARVIS using direct SAPI5.
Finalized for maximum stability on Windows.
"""
import sys
import os
import time
import comtypes.client

def main():
    try:
        # Initialize COM
        import comtypes
        comtypes.CoInitialize()
        
        # Create SAPI.SpVoice directly
        voice = comtypes.client.CreateObject("SAPI.SpVoice")
        
        # Signal ready
        print("TTS_READY", flush=True)
    except Exception as e:
        print(f"TTS_ERROR:SAPI5 Init failed: {e}", flush=True)
        sys.exit(1)

    # Main loop
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            text = line.strip()
            if not text or text == "QUIT":
                if text == "QUIT": break
                continue
                
            # Signal STARTING
            print("TTS_STARTING", flush=True)
            
            # Speak synchronously (this blocks until done)
            voice.Speak(text)
            
            # Signal FINISHED
            print("TTS_FINISHED", flush=True)
            
        except Exception as e:
            sys.stderr.write(f"TTS_RUNTIME_ERR: {e}\n")
            # Re-init SAPI if it crashed
            try:
                voice = comtypes.client.CreateObject("SAPI.SpVoice")
            except:
                pass

    print("TTS_EXITING", flush=True)

if __name__ == "__main__":
    main()
