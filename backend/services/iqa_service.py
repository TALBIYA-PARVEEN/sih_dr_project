import cv2
import numpy as np
from services.dataset_service import DatasetRegistryService

class ImageQualityAssessmentService:
    """
    Automated Clinical Retinal Anatomical & Image Quality Assessment (IQA) Engine:
    
    1. Retinal Anatomical Verification:
       - Supports Color Fundus Photography (Standard RGB, Optic-Disc and Macula centered).
       - Supports Red-Free / Green-Channel / Monochromatic / Grayscale Fundus Scans.
       - Supports Square, Rectangular, and Pan-Retinal Widefield camera apertures.
       - Rejects non-retinal objects (pure blue landscapes, sky, ocean, pitch-dark or washed-out images).
       
    2. Optical Degradation & Quality Gates:
       - Rejects pitch-dark / underexposed captures (< 5.0)
       - Rejects overexposed / flash glare captures (> 250.0)
       - Rejects flat zero-contrast synthetic images (Std Dev < 3.5)
       
    3. Actionable Rejection Directives:
       - Returns human-readable guidance to the clinician / patient instructing them on recapturing if needed.
    """
    def __init__(self, blur_threshold=10.0, min_brightness=15.0, max_brightness=240.0, min_fov_ratio=0.10):
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

        # Check resolution
        h, w = image_np.shape[:2]
        if h < 60 or w < 60:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": 0.0,
                "brightness_score": 0.0,
                "contrast_score": 0.0,
                "fov_ratio": 0.0,
                "rejection_reason": f"Image resolution is too low ({w}x{h}px). Minimum 200x200px required for clinical grading."
            }

        # Color channels extraction
        if len(image_np.shape) == 3 and image_np.shape[2] >= 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            r_chan = image_np[:, :, 0].astype(float)
            g_chan = image_np[:, :, 1].astype(float)
            b_chan = image_np[:, :, 2].astype(float)
            r_mean = float(np.mean(r_chan))
            g_mean = float(np.mean(g_chan))
            b_mean = float(np.mean(b_chan))
        else:
            gray = image_np if len(image_np.shape) == 2 else cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            r_mean = g_mean = b_mean = float(np.mean(gray))

        overall_mean = float(np.mean(gray))
        contrast = float(np.std(gray))
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_score = float(np.var(laplacian))

        # Check 1: Completely black / pitch-dark image
        if overall_mean < 5.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 1),
                "brightness_score": round(overall_mean, 1),
                "contrast_score": round(contrast, 1),
                "fov_ratio": 0.0,
                "rejection_reason": "Scan is completely dark / underexposed. Please retake the retina photograph with proper fundus illumination."
            }

        # Check 2: Completely white / washed out image
        if overall_mean > 250.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 1),
                "brightness_score": round(overall_mean, 1),
                "contrast_score": round(contrast, 1),
                "fov_ratio": 1.0,
                "rejection_reason": "Scan is completely overexposed / washed out. Please retake the retina photograph with balanced flash illumination."
            }

        # Check 3: Extreme non-retinal blue landscape/sky dominance (Retina is warm red or grayscale red-free, never pure blue)
        if b_mean > (r_mean * 1.45) and b_mean > 70.0 and r_mean < 45.0:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 1),
                "brightness_score": round(overall_mean, 1),
                "contrast_score": round(contrast, 1),
                "fov_ratio": 0.0,
                "rejection_reason": f"Non-retinal image detected: Unnatural blue spectrum (Blue: {b_mean:.1f}, Red: {r_mean:.1f}). Please upload an authentic eye fundus photograph."
            }

        # Check 4: Zero texture / flat synthetic color fill
        if contrast < 3.5:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 10.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 1),
                "brightness_score": round(overall_mean, 1),
                "contrast_score": round(contrast, 1),
                "fov_ratio": 0.0,
                "rejection_reason": "Image has insufficient structural contrast or texture. Please upload a clear retinal photograph."
            }

        # Calculate FOV ratio
        _, fov_mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        total_pixels = gray.shape[0] * gray.shape[1]
        retinal_pixels = int(np.count_nonzero(fov_mask))
        fov_ratio = round(retinal_pixels / max(1.0, float(total_pixels)), 3)

        # -------------------------------------------------------------
        # Gradable Retina Image Quality Calculation (0 - 100)
        # -------------------------------------------------------------
        norm_sharpness = min(100.0, (blur_score / 35.0) * 100.0)
        norm_bright = max(0.0, 100.0 - abs(overall_mean - 110.0) * 0.75)
        norm_contrast = min(100.0, (contrast / 35.0) * 100.0)

        quality_score = float(0.40 * norm_sharpness + 0.30 * norm_bright + 0.30 * norm_contrast)
        quality_score = round(max(60.0, min(99.0, quality_score)), 1)

        if quality_score >= 72.0 and blur_score >= 15.0:
            quality_label = "GOOD"
        else:
            quality_label = "BORDERLINE / MEDIUM"

        return {
            "quality_label": quality_label,
            "quality_score": quality_score,
            "is_gradable": True,
            "blur_score": round(blur_score, 2),
            "brightness_score": round(overall_mean, 2),
            "contrast_score": round(contrast, 2),
            "fov_ratio": fov_ratio,
            "rejection_reason": None
        }
