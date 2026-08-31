import cv2
import numpy as np

class PreprocessingService:
    def __init__(self, target_size=456):
        self.target_size = target_size

    def circle_crop(self, img_bgr):
        """
        Crops to circular retinal field of view to remove variable camera borders.
        """
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return img_bgr
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        if w < 10 or h < 10:
            return img_bgr
        return img_bgr[y:y+h, x:x+w]

    def ben_graham_preprocess(self, img_bgr, sigma_frac=0.1):
        """
        Ben Graham local average subtraction + mid-gray mapping.
        Highlights microaneurysms, hemorrhages, and exudates against the background.
        """
        sigma = max(img_bgr.shape[0], img_bgr.shape[1]) * sigma_frac
        blurred = cv2.GaussianBlur(img_bgr, (0, 0), sigma)
        result = cv2.addWeighted(img_bgr, 4, blurred, -4, 128)
        return result

    def clahe_enhance(self, rgb, clip_limit=2.5, tile=(8, 8)):
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile)
        l2 = clahe.apply(l)
        return cv2.cvtColor(cv2.merge((l2, a, b)), cv2.COLOR_LAB2RGB)

    def preprocess(self, img_rgb):
        """
        Full End-to-End Pipeline from Colab:
        1. Circle Crop
        2. Resize to native target size
        3. Ben Graham local-average subtraction
        4. LAB CLAHE contrast enhancement
        """
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        cropped_bgr = self.circle_crop(img_bgr)
        resized_bgr = cv2.resize(cropped_bgr, (self.target_size, self.target_size), interpolation=cv2.INTER_AREA)
        
        bg_bgr = self.ben_graham_preprocess(resized_bgr)
        bg_rgb = cv2.cvtColor(bg_bgr, cv2.COLOR_BGR2RGB)
        enhanced_rgb = self.clahe_enhance(bg_rgb)

        return {
            "enhanced_rgb": enhanced_rgb,
            "green_channel": enhanced_rgb[:, :, 1],
            "original_cropped_rgb": cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2RGB)
        }
