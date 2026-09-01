import cv2
import numpy as np
from services.dataset_service import DatasetRegistryService

class ImageQualityAssessmentService:
    def __init__(self, blur_threshold=30.0, min_brightness=40.0, max_brightness=195.0, min_fov_ratio=0.32):
        self.blur_threshold = blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_fov_ratio = min_fov_ratio
        self.dataset_registry = DatasetRegistryService()

    def evaluate_quality(self, image_np, filename=None):
        if image_np is None or image_np.size == 0:
            return {
                "quality_label": "UNGRADABLE - REJECTED",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": 0.0,
                "brightness_score": 0.0,
                "contrast_score": 0.0,
                "fov_ratio": 0.0,
                "rejection_reason": "Image file is empty or corrupted. Please upload a valid fundus photograph."
            }

        # 1. General Computer Vision Image Quality Assessment
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            r_mean = float(np.mean(image_np[:, :, 0]))
            g_mean = float(np.mean(image_np[:, :, 1]))
            b_mean = float(np.mean(image_np[:, :, 2]))
        else:
            gray = image_np
            r_mean, g_mean, b_mean = float(np.mean(gray)), float(np.mean(gray)), float(np.mean(gray))

        # Retinal FOV Area Ratio (Circular illumination disc)
        _, fov_mask = cv2.threshold(gray, 18, 255, cv2.THRESH_BINARY)
        total_pixels = gray.shape[0] * gray.shape[1]
        retinal_pixels = np.count_nonzero(fov_mask)
        fov_ratio = retinal_pixels / max(1, total_pixels)

        # Focus Analysis (Laplacian Variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        if retinal_pixels > 100:
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

        # Check 1: Severe Blur / Out of Focus (Laplacian Variance < 25.0)
        if blur_score < 25.0:
            issues.append(f"Severely blurred / out of focus (Sharpness score: {blur_score:.1f}, Min required: 25.0)")
            is_hard_reject = True

        # Check 2: Severe Underexposure / Darkness
        if brightness < self.min_brightness:
            issues.append(f"Severely underexposed / too dark (Brightness: {brightness:.1f}, Min required: {self.min_brightness})")
            is_hard_reject = True

        # Check 3: Severe Overexposure / Flash Glare / Washed Out
        if brightness > self.max_brightness:
            issues.append(f"Severely overexposed / excessive flash glare (Brightness: {brightness:.1f}, Max allowed: {self.max_brightness})")
            is_hard_reject = True

        # Check 4: Low Contrast / Hazy Media (Cataract or dirty lens)
        if contrast < 18.0:
            issues.append(f"Low contrast / hazy media (Contrast: {contrast:.1f}, Min required: 18.0)")
            is_hard_reject = True

        # Check 5: Retinal Field of View (Must cover at least 32% of frame)
        if fov_ratio < self.min_fov_ratio:
            issues.append(f"Incomplete retinal field of view ({fov_ratio*100:.1f}%, Min required: 32%)")
            is_hard_reject = True

        # Check 6: Non-Retinal Color Spectrum Verification
        # Authentic human fundus photographs have strong red-channel dominance (R > B)
        if len(image_np.shape) == 3 and (r_mean < b_mean or (r_mean < 35 and g_mean < 35 and b_mean < 35)):
            issues.append("Non-retinal color profile detected. Please upload an authentic eye fundus photograph.")
            is_hard_reject = True

        # Quality scoring (0 - 100)
        norm_focus = min(100.0, (blur_score / 70.0) * 100.0)
        norm_bright = max(0.0, 100.0 - abs(brightness - 110.0) * 1.0)
        norm_fov = min(100.0, (fov_ratio / 0.65) * 100.0)
        quality_score = float(0.45 * norm_focus + 0.30 * norm_bright + 0.25 * norm_fov)

        if is_hard_reject:
            quality_label = "POOR (UNGRADABLE)"
            is_gradable = False
            rejection_reason = "Quality Assessment Failed: " + "; ".join(issues) + ".\nAction: Clinical AI cannot grade this scan. Please retake a clear retinal photo."
        elif quality_score < 60.0 or blur_score < 38.0:
            quality_label = "ADEQUATE"
            is_gradable = True
            rejection_reason = "Borderline image quality — enhanced with Ben Graham & CLAHE filters."
        else:
            quality_label = "GOOD"
            is_gradable = True
            rejection_reason = None

        return {
            "quality_label": quality_label,
            "quality_score": round(max(5.0, min(100.0, quality_score)), 1),
            "is_gradable": is_gradable,
            "blur_score": round(blur_score, 2),
            "brightness_score": round(brightness, 2),
            "contrast_score": round(contrast, 2),
            "fov_ratio": round(fov_ratio, 4),
            "rejection_reason": rejection_reason
        }
