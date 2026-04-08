import mss
import mss.tools
import cv2
import numpy as np
import pytesseract
import os
import base64
from io import BytesIO
from PIL import Image

class VisionEngine:
    def __init__(self, tesseract_path=None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        self.last_screenshot = None

    def capture_screen(self, region=None):
        """
        region: dict with {'top', 'left', 'width', 'height'}
        """
        with mss.mss() as sct:
            if region is None:
                # Full screen of monitor 1
                region = sct.monitors[1]
            
            screenshot = sct.grab(region)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            self.last_screenshot = img
            return img

    def get_ocr_text(self, img=None):
        """Extracts text from image using Tesseract."""
        if img is None:
            img = self.last_screenshot
        
        if img is None:
            return ""

        try:
            # Preprocess for better OCR
            open_cv_image = np.array(img)
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
            # Thresholding
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            
            text = pytesseract.image_to_string(thresh)
            return text.strip()
        except Exception as e:
            return f"OCR Error: {e} (Tesseract might not be installed or configured)"

    def img_to_base64(self, img=None):
        """Converts PIL image to base64 for LLM consumption."""
        if img is None:
            img = self.last_screenshot
        
        if img is None:
            return None

        buffered = BytesIO()
        # Resize if too large to save tokens/bandwidth
        img_copy = img.copy()
        img_copy.thumbnail((1280, 720)) 
        img_copy.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

if __name__ == "__main__":
    # Test
    vision = VisionEngine()
    print("Capturing screen...")
    img = vision.capture_screen()
    print("Screen captured. Size:", img.size)
    # text = vision.get_ocr_text()
    # print("OCR Text Sample:", text[:100])
