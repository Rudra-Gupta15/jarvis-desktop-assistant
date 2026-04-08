import os
import sys
import time

def check_component(name, import_stmt, class_name):
    print(f"🔍 Testing {name}...")
    try:
        start = time.time()
        # Use globals for persistent scope across exec and eval
        exec(import_stmt, globals())
        if class_name:
            obj = eval(f"{class_name}()", globals())
            print(f"✅ {name} initialized in {time.time() - start:.2f}s")
            return obj
        print(f"✅ {name} imported in {time.time() - start:.2f}s")
        return True
    except Exception as e:
        print(f"❌ {name} failed: {e}")
        return False

if __name__ == "__main__":
    print("📋 JARVIS DIAGNOSTIC")
    print("=" * 20)
    
    # 1. Brain (Ollama)
    check_component("Brain", "from brain import JarvisBrain", "JarvisBrain")
    
    # 2. Automation
    check_component("Automation", "from automation import JarvisAutomation", "JarvisAutomation")
    
    # 3. Vision
    check_component("Vision", "from vision_engine import VisionEngine", "VisionEngine")
    
    # 4. Voice
    check_component("Voice", "from voice_engine import VoiceEngine", "VoiceEngine")
    
    print("\nDiagnostic complete.")
