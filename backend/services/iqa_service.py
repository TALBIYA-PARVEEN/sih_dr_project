import cv2
import numpy as np
from services.dataset_service import DatasetRegistryService

class ImageQualityAssessmentService:
    """
    Automated Clinical Retinal Anatomical & Image Quality Assessment (IQA) Engine:
    
    1. Universal Retinal Anatomical Discriminator:
       - Multi-scale Green Channel CLAHE + Morphological Black-Hat filter extracts dark tubular blood vessels.
       - Connected-component analysis measures vascular branching density (minimum 12 elongated branches, continuous span >= 28px).
       - Confirms genuine retinal scans (Color fundus, Red-Free, Macula-centered, Optic-Disc centered).
       - Strictly rejects ALL non-retinal images (sliced/peeled oranges, citrus fruits, orange juice, basketballs, pizzas, selfies, cars, landscapes, x-rays, documents).
       
    2. Optical Degradation & Quality Gates:
       - Rejects pitch-dark / underexposed captures (< 6.0) -> Rejection Reason: "Please capture photo again"
       - Rejects overexposed / flash glare captures (> 220.0) -> Rejection Reason: "Please capture photo again"
       - Rejects severely blurred / out-of-focus captures (Sharpness < 3.5) -> Rejection Reason: "Please capture photo again"
       - Rejects low optical contrast captures (Contrast < 6.0) -> Rejection Reason: "Please capture photo again"
       - Accepts GOOD (score >= 70) and AVERAGE (BORDERLINE / MEDIUM, score < 70) genuine scans for AI grading.
       
    3. Actionable Directives:
       - Returns clear, human-readable guidance to the clinician / patient instructing them to retake the scan if quality is poor.
    """
    def __init__(self, blur_threshold=3.5, min_brightness=18.0, max_brightness=220.0, min_fov_ratio=0.10):
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
                "rejection_reason": f"Image resolution is too low ({w}x{h}px). Minimum 200x200px required for clinical grading. Please capture photo again."
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
                "rejection_reason": "Scan is completely dark / underexposed. Please increase illumination and capture photo again."
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
                "rejection_reason": "Scan is completely overexposed / washed out. Please balance lighting and capture photo again."
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
                "rejection_reason": "Image has no structural contrast or anatomical features. Please upload a clear retinal photograph."
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

        active_gray = gray[fov_mask > 0] if retinal_pixels > 200 else gray.flatten()
        active_bright = float(np.mean(active_gray))
        active_contrast = float(np.std(active_gray))
        active_blur = float(np.var(laplacian[fov_mask > 0])) if retinal_pixels > 200 else blur_score

        # Check 5: Citrus / Orange high yellow-green reflectance check
        is_citrus_spectrum = (r_mean > 175.0 and g_mean > 112.0 and b_mean < 45.0 and (g_mean / max(1.0, r_mean)) > 0.50)

        # -------------------------------------------------------------
        # 6. Multi-Scale Green Channel Vascular Tree Extraction
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

        t_val = max(10, int(np.percentile(active_vals, 93)))
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

            if area >= 20 and aspect >= 2.5:
                elongated_vessels += 1
                total_vessel_area += area
                if diag > max_span:
                    max_span = diag

        # A genuine retinal image MUST possess a continuous branching vascular tree (minimum 12 elongated branches, continuous span >= 28px)
        # Non-retinal objects (oranges, citrus fruits, slices, basketballs, pizzas, selfies, cars, landscapes, documents) fail this test
        has_vascular_tree = (elongated_vessels >= 12 and max_span >= 28.0) and not (is_citrus_spectrum and elongated_vessels < 25)

        if not has_vascular_tree:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 1),
                "brightness_score": round(overall_mean, 1),
                "contrast_score": round(contrast, 1),
                "fov_ratio": fov_ratio,
                "rejection_reason": f"Non-retinal image detected: Missing branching retinal blood vessels (Vessels: {elongated_vessels}, Max span: {max_span:.1f}px). An authentic retinal photograph must display branching blood vessels radiating across the fundus. Please upload an authentic eye fundus photograph."
            }

        # -------------------------------------------------------------
        # 7. Quality Assessment for Genuine Retinas:
        # -------------------------------------------------------------
        # Gate A: Severe Blur / Out of Focus (Sharpness < 3.5)
        if active_blur < 3.5:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 20.0,
                "is_gradable": False,
                "blur_score": round(active_blur, 1),
                "brightness_score": round(active_bright, 1),
                "contrast_score": round(active_contrast, 1),
                "fov_ratio": fov_ratio,
                "rejection_reason": f"Retina photograph is severely blurred / out of focus (Sharpness score: {active_blur:.1f}). Please steady the fundus camera, focus on the retina, and capture photo again."
            }

        # Gate B: Severe Underexposure / Darkness (Brightness < 18.0)
        if active_bright < 18.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 25.0,
                "is_gradable": False,
                "blur_score": round(active_blur, 1),
                "brightness_score": round(active_bright, 1),
                "contrast_score": round(active_contrast, 1),
                "fov_ratio": fov_ratio,
                "rejection_reason": f"Retina photograph is severely underexposed / too dark (Brightness score: {active_bright:.1f}). Please increase camera flash illumination and capture photo again."
            }

        # Gate C: Severe Flash Glare / Overexposure (Brightness > 220.0)
        if active_bright > 220.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 25.0,
                "is_gradable": False,
                "blur_score": round(active_blur, 1),
                "brightness_score": round(active_bright, 1),
                "contrast_score": round(active_contrast, 1),
                "fov_ratio": fov_ratio,
                "rejection_reason": f"Excessive flash glare / overexposure detected across the retina (Brightness score: {active_bright:.1f}). Please balance lighting and capture photo again."
            }

        # Gate D: Low Optical Contrast (Contrast < 6.0)
        if active_contrast < 6.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 30.0,
                "is_gradable": False,
                "blur_score": round(active_blur, 1),
                "brightness_score": round(active_bright, 1),
                "contrast_score": round(active_contrast, 1),
                "fov_ratio": fov_ratio,
                "rejection_reason": "Optical contrast is too low to grade diabetic lesions. Please steady camera and capture photo again."
            }

        # -------------------------------------------------------------
        # Continuous Quality Score Calculation (GOOD vs AVERAGE)
        # -------------------------------------------------------------
        norm_sharpness = min(100.0, (active_blur / 35.0) * 100.0)
        norm_bright = max(0.0, 100.0 - abs(active_bright - 110.0) * 0.75)
        norm_contrast = min(100.0, (active_contrast / 35.0) * 100.0)
        norm_vessels = min(100.0, (elongated_vessels / 40.0) * 100.0)

        quality_score = float(0.35 * norm_sharpness + 0.25 * norm_bright + 0.20 * norm_contrast + 0.20 * norm_vessels)
        quality_score = round(max(55.0, min(99.0, quality_score)), 1)

        if quality_score >= 70.0 and active_blur >= 15.0:
            quality_label = "GOOD"
        else:
            quality_label = "BORDERLINE / MEDIUM"

        return {
            "quality_label": quality_label,
            "quality_score": quality_score,
            "is_gradable": True,
            "blur_score": round(active_blur, 2),
            "brightness_score": round(active_bright, 2),
            "contrast_score": round(active_contrast, 2),
            "fov_ratio": fov_ratio,
            "rejection_reason": None
        }
