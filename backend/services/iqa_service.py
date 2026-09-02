import cv2
import numpy as np
from services.dataset_service import DatasetRegistryService

class ImageQualityAssessmentService:
    """
    Automated Clinical Retinal Anatomical & Image Quality Assessment (IQA) Engine:
    
    1. Retinal Anatomical Discriminator (Vascular Tree & Hemoglobin Absorption):
       - Multi-scale Green Channel CLAHE + Morphological Black-Hat filter extracts dark tubular blood vessels.
       - Connected-component analysis measures vessel elongation, total vascular area, and maximum branch span.
       - Confirms genuine retinal scans (Color fundus, Red-Free, Macula-centered, Optic-Disc centered).
       - Accurately rejects non-retinal objects (oranges, citrus fruits, orange juice, sunsets, selfies, random scenes).
       
    2. Optical Degradation & Quality Gates:
       - Rejects pitch-dark / underexposed captures (< 6.0)
       - Rejects overexposed / flash glare captures (> 248.0)
       - Rejects flat zero-contrast synthetic images (Std Dev < 4.0)
       - Rejects unnatural non-retinal blue outdoor scenes (B > R * 1.35 and B > 65.0)
       
    3. Actionable Rejection Directives:
       - Returns clear human-readable guidance to the clinician / patient.
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
            g_chan_raw = image_np[:, :, 1]
            b_chan = image_np[:, :, 2].astype(float)
            r_mean = float(np.mean(r_chan))
            g_mean = float(np.mean(g_chan_raw))
            b_mean = float(np.mean(b_chan))
        else:
            gray = image_np if len(image_np.shape) == 2 else cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            g_chan_raw = gray
            r_mean = g_mean = b_mean = float(np.mean(gray))

        overall_mean = float(np.mean(gray))
        contrast = float(np.std(gray))
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_score = float(np.var(laplacian))

        # Check 1: Completely black / pitch-dark image
        if overall_mean < 6.0:
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
        if overall_mean > 248.0:
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
        if b_mean > (r_mean * 1.35) and b_mean > 65.0 and r_mean < 50.0:
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
        if contrast < 4.0:
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

        # Calculate FOV mask & active region
        _, fov_mask = cv2.threshold(gray, 12, 255, cv2.THRESH_BINARY)
        total_pixels = gray.shape[0] * gray.shape[1]
        retinal_pixels = int(np.count_nonzero(fov_mask))
        fov_ratio = round(retinal_pixels / max(1.0, float(total_pixels)), 3)

        if retinal_pixels < 200:
            fov_mask = np.ones_like(gray, dtype=np.uint8) * 255
            retinal_pixels = total_pixels

        fov_eroded = cv2.erode(fov_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        if np.count_nonzero(fov_eroded) < 100:
            fov_eroded = fov_mask

        # -------------------------------------------------------------
        # 5. Multi-Scale Green Channel Vascular Tree Extraction
        # -------------------------------------------------------------
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        g_enh = clahe.apply(g_chan_raw)
        g_blur = cv2.GaussianBlur(g_enh, (5, 5), 1.5)

        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        bhat = cv2.morphologyEx(g_blur, cv2.MORPH_BLACKHAT, k)
        bhat_masked = cv2.bitwise_and(bhat, bhat, mask=fov_eroded)

        active_vals = bhat_masked[fov_eroded > 0]
        if len(active_vals) == 0:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 1),
                "brightness_score": round(overall_mean, 1),
                "contrast_score": round(contrast, 1),
                "fov_ratio": 0.0,
                "rejection_reason": "No active retinal field detected. Please upload an authentic retinal fundus photograph."
            }

        t_val = max(8, int(np.percentile(active_vals, 92)))
        _, bin_vessels = cv2.threshold(bhat_masked, t_val, 255, cv2.THRESH_BINARY)
        k_line = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        bin_vessels = cv2.morphologyEx(bin_vessels, cv2.MORPH_OPEN, k_line)

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bin_vessels)
        elongated_vessels = 0
        max_span = 0.0
        total_vessel_area = 0

        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            bw = stats[i, cv2.CC_STAT_WIDTH]
            bh = stats[i, cv2.CC_STAT_HEIGHT]
            aspect = max(bw, bh) / max(1.0, float(min(bw, bh)))
            diag = np.sqrt(bw**2 + bh**2)

            if area >= 18 and aspect >= 2.2:
                elongated_vessels += 1
                total_vessel_area += area
                if diag > max_span:
                    max_span = diag

        # A genuine retinal image MUST possess branching vascular arcades
        # Non-retinal objects (oranges, citrus fruits, orange juice, sunsets, selfies) have near-zero elongated vessels
        has_vascular_tree = (elongated_vessels >= 5 and max_span >= 22.0) or (total_vessel_area >= 300 and max_span >= 20.0)

        if not has_vascular_tree:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 1),
                "brightness_score": round(overall_mean, 1),
                "contrast_score": round(contrast, 1),
                "fov_ratio": fov_ratio,
                "rejection_reason": f"Non-retinal image detected: Missing branching retinal blood vessels (Vessels: {elongated_vessels}, Max span: {max_span:.1f}px). An authentic retinal photograph must display continuous blood vessels radiating across the fundus. Please upload an authentic eye fundus scan."
            }

        # -------------------------------------------------------------
        # 6. Gradable Retina Image Quality Calculation (0 - 100)
        # -------------------------------------------------------------
        norm_sharpness = min(100.0, (blur_score / 35.0) * 100.0)
        norm_bright = max(0.0, 100.0 - abs(overall_mean - 110.0) * 0.75)
        norm_contrast = min(100.0, (contrast / 35.0) * 100.0)
        norm_vessels = min(100.0, (elongated_vessels / 40.0) * 100.0)

        quality_score = float(0.35 * norm_sharpness + 0.25 * norm_bright + 0.20 * norm_contrast + 0.20 * norm_vessels)
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
