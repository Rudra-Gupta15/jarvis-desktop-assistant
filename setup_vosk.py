import os
import requests
import zipfile
import sys

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_ZIP = "vosk-model.zip"
MODEL_DIR = "vosk-model-small-en-us-0.15"

def download_model():
    if os.path.exists(MODEL_DIR):
        print(f"Model already exists at {MODEL_DIR}")
        return True

    print(f"Downloading Vosk model from {MODEL_URL}...")
    try:
        response = requests.get(MODEL_URL, stream=True)
        response.raise_for_status()
        
        with open(MODEL_ZIP, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("Extracting model...")
        with zipfile.ZipFile(MODEL_ZIP, "r") as zip_ref:
            zip_ref.extractall(".")
        
        os.remove(MODEL_ZIP)
        print("Model setup complete.")
        return True
    except Exception as e:
        print(f"Error downloading model: {e}")
        return False

if __name__ == "__main__":
    if download_model():
        sys.exit(0)
    else:
        sys.exit(1)
