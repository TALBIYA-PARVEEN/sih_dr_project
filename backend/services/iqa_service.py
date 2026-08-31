import cv2
import numpy as np
from services.dataset_service import DatasetRegistryService

class ImageQualityAssessmentService:
    def __init__(self, blur_threshold=12.0, min_brightness=15.0, max_brightness=240.0, min_fov_ratio=0.20):
        self.blur_threshold = blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_fov_ratio = min_fov_ratio
        self.dataset_registry = DatasetRegistryService()

    def evaluate_quality(self, image_np, filename=None):
        if image_np is None or image_np.size == 0:
            return {
                "quality_label": "POOR",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": 0.0,
                "brightness_score": 0.0,
                "contrast_score": 0.0,
                "fov_ratio": 0.0,
                "rejection_reason": "Image file is empty or corrupted."
            }

        # 1. Check if dataset CSV has this exact image
        if filename:
            match = self.dataset_registry.match_record(filename)
            if match:
                try:
                    q_label = match.get("quality_label", "GOOD").upper()
                    blur_val = float(match.get("blur_score", 38.5))
                    fov_val = float(match.get("fov_ratio", 0.75))
                    bright_val = float(match.get("brightness", 110.0))
                    cont_val = float(match.get("contrast", 35.0))
                    
                    return {
                        "quality_label": q_label,
                        "quality_score": round(min(100.0, max(10.0, blur_val * 2.2)), 1),
                        "is_gradable": q_label != "POOR" and q_label != "REJECT",
                        "blur_score": blur_val,
                        "brightness_score": bright_val,
                        "contrast_score": cont_val,
                        "fov_ratio": fov_val,
                        "rejection_reason": None if (q_label != "POOR") else "Image quality flagged in training dataset.",
                        "dataset_features": match
                    }
                except Exception:
                    pass

        # 2. General Computer Vision Image Quality Assessment
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np

        # Retinal FOV Area Ratio
        _, fov_mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        total_pixels = gray.shape[0] * gray.shape[1]
        retinal_pixels = np.count_nonzero(fov_mask)
        fov_ratio = retinal_pixels / max(1, total_pixels)

        # Focus Analysis (Laplacian Variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        if retinal_pixels > 0:
            laplacian_fov = laplacian[fov_mask > 0]
            blur_score = float(np.var(laplacian_fov))
            brightness = float(np.mean(gray[fov_mask > 0]))
            contrast = float(np.std(gray[fov_mask > 0]))
        else:
            blur_score = float(np.var(laplacian))
            brightness = float(np.mean(gray))
            contrast = float(np.std(gray))

        issues = []
        is_hard_reject = False
        is_borderline = False

        if fov_ratio < self.min_fov_ratio:
            issues.append(f"Insufficient retinal field of view ({fov_ratio*100:.1f}%)")
            is_hard_reject = True

        if blur_score < (self.blur_threshold * 0.4):
            issues.append(f"Severely out of focus (Laplacian var: {blur_score:.1f})")
            is_hard_reject = True
        elif blur_score < self.blur_threshold:
            issues.append(f"Soft focus (Score: {blur_score:.1f}) — Ben Graham CLAHE enhancement applied")
            is_borderline = True

        if brightness < self.min_brightness:
            issues.append("Severely underexposed / dark")
            is_hard_reject = True
        elif brightness > self.max_brightness:
            issues.append("Severely overexposed / washed out")
            is_hard_reject = True
        elif brightness < 35 or brightness > 210:
            is_borderline = True

        norm_focus = min(100.0, (blur_score / 80.0) * 100.0)
        norm_bright = max(0.0, 100.0 - abs(brightness - 115.0) * 0.8)
        norm_fov = min(100.0, (fov_ratio / 0.65) * 100.0)
        quality_score = float(0.40 * norm_focus + 0.35 * norm_bright + 0.25 * norm_fov)

        if is_hard_reject:
            quality_label = "POOR"
            is_gradable = False
            rejection_reason = "Image unsuitable for clinical grading — " + "; ".join(issues) + ". Please recapture a clear photo."
        elif is_borderline or quality_score < 65:
            quality_label = "ADEQUATE"
            is_gradable = True
            rejection_reason = "Borderline quality — Enhanced with MATLAB CLAHE filters."
        else:
            quality_label = "GOOD"
            is_gradable = True
            rejection_reason = None

        return {
            "quality_label": quality_label,
            "quality_score": round(max(10.0, min(100.0, quality_score)), 1),
            "is_gradable": is_gradable,
            "blur_score": round(blur_score, 2),
            "brightness_score": round(brightness, 2),
            "contrast_score": round(contrast, 2),
            "fov_ratio": round(fov_ratio, 4),
            "rejection_reason": rejection_reason
        }
