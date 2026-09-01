import cv2
import numpy as np
from services.dataset_service import DatasetRegistryService

class ImageQualityAssessmentService:
    def __init__(self, blur_threshold=12.0, min_brightness=20.0, max_brightness=235.0, min_fov_ratio=0.15):
        self.blur_threshold = blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_fov_ratio = min_fov_ratio
        self.dataset_registry = DatasetRegistryService()

    def evaluate_quality(self, image_np, filename=None):
        if image_np is None or image_np.size == 0:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": 0.0,
                "brightness_score": 0.0,
                "contrast_score": 0.0,
                "fov_ratio": 0.0,
                "rejection_reason": "Image file is empty or corrupted. Please upload a valid retinal scan."
            }

        # Handle color channels
        if len(image_np.shape) == 3:
            h, w, c = image_np.shape
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            r_chan = image_np[:, :, 0].astype(float)
            g_chan = image_np[:, :, 1].astype(float)
            b_chan = image_np[:, :, 2].astype(float)
            r_mean = float(np.mean(r_chan))
            g_mean = float(np.mean(g_chan))
            b_mean = float(np.mean(b_chan))
        else:
            h, w = image_np.shape
            gray = image_np
            r_mean, g_mean, b_mean = float(np.mean(gray)), float(np.mean(gray)), float(np.mean(gray))

        overall_mean = float(np.mean(gray))

        # Check 1: Completely black or pitch-dark image
        if overall_mean < 8.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 5.0,
                "is_gradable": False,
                "blur_score": 0.0,
                "brightness_score": round(overall_mean, 1),
                "contrast_score": 0.0,
                "fov_ratio": 0.0,
                "rejection_reason": "Scan is completely dark/underexposed. Please retake the retina photograph with proper illumination."
            }

        # Check 2: Completely white / washed out image
        if overall_mean > 245.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 5.0,
                "is_gradable": False,
                "blur_score": 0.0,
                "brightness_score": round(overall_mean, 1),
                "contrast_score": 0.0,
                "fov_ratio": 1.0,
                "rejection_reason": "Scan is completely overexposed/white. Please retake the retina photograph."
            }

        # Retinal FOV Detection
        _, fov_mask = cv2.threshold(gray, 12, 255, cv2.THRESH_BINARY)
        total_pixels = gray.shape[0] * gray.shape[1]
        retinal_pixels = int(np.count_nonzero(fov_mask))
        fov_ratio = retinal_pixels / max(1, total_pixels)

        # Extract active retinal region
        if retinal_pixels > 200:
            active_gray = gray[fov_mask > 0]
            brightness = float(np.mean(active_gray))
            contrast = float(np.std(active_gray))
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            blur_score = float(np.var(laplacian[fov_mask > 0]))
        else:
            brightness = overall_mean
            contrast = float(np.std(gray))
            blur_score = float(np.var(cv2.Laplacian(gray, cv2.CV_64F)))

        issues = []
        is_not_retina = False
        is_poor_quality = False

        # -------------------------------------------------------------
        # 1. NON-RETINA VALIDATION
        # -------------------------------------------------------------
        # Genuine human retina photographs have strong red/orange dominance.
        # Strong blue dominance (B > R * 1.35 and B > 45) or pure green (G > R * 1.6 and G > 50) represents non-retina photos.
        if len(image_np.shape) == 3:
            if (b_mean > r_mean * 1.35 and b_mean > 45.0) or (g_mean > r_mean * 1.55 and g_mean > 50.0):
                is_not_retina = True
                issues.append("Non-retinal image detected (unnatural color spectrum). Please capture and upload an authentic eye fundus scan.")

        # -------------------------------------------------------------
        # 2. SEVERE QUALITY DEFECTS (POOR / UNGRADABLE)
        # -------------------------------------------------------------
        if blur_score < 10.0:
            is_poor_quality = True
            issues.append(f"Image is out of focus / severely blurred (Sharpness: {blur_score:.1f}). Retake photo with sharp optical focus.")

        if brightness < 20.0:
            is_poor_quality = True
            issues.append(f"Severely underexposed / dark (Brightness: {brightness:.1f}). Retake with proper fundus illumination.")

        if brightness > 230.0:
            is_poor_quality = True
            issues.append(f"Excessive flash glare / overexposure (Brightness: {brightness:.1f}). Retake with balanced illumination.")

        if contrast < 10.0:
            is_poor_quality = True
            issues.append("Extremely low contrast media. Retake scan with clear view.")

        # -------------------------------------------------------------
        # 3. QUALITY CLASSIFICATION & DECISION
        # -------------------------------------------------------------
        if is_not_retina:
            quality_label = "NOT A RETINA IMAGE"
            is_gradable = False
            rejection_reason = "Non-retinal image detected. Please upload an authentic retinal fundus photograph."
            quality_score = 0.0
        elif is_poor_quality:
            quality_label = "POOR (UNGRADABLE)"
            is_gradable = False
            rejection_reason = "Quality Assessment Failed: " + "; ".join(issues) + "\nAction Required: Retake retinal photo before generating diagnostic report."
            quality_score = 25.0
        else:
            # Calculate quality score (0 - 100)
            norm_sharpness = min(100.0, (blur_score / 45.0) * 100.0)
            norm_bright = max(0.0, 100.0 - abs(brightness - 115.0) * 0.9)
            norm_contrast = min(100.0, (contrast / 40.0) * 100.0)
            quality_score = float(0.40 * norm_sharpness + 0.35 * norm_bright + 0.25 * norm_contrast)
            quality_score = round(max(55.0, min(99.0, quality_score)), 1)

            if quality_score >= 75.0 and blur_score >= 25.0:
                quality_label = "GOOD"
            else:
                quality_label = "MEDIUM"

            is_gradable = True
            rejection_reason = None

        return {
            "quality_label": quality_label,
            "quality_score": quality_score,
            "is_gradable": is_gradable,
            "blur_score": round(blur_score, 2),
            "brightness_score": round(brightness, 2),
            "contrast_score": round(contrast, 2),
            "fov_ratio": round(fov_ratio, 4),
            "rejection_reason": rejection_reason
        }
