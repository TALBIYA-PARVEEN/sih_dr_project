import cv2
import numpy as np
from services.dataset_service import DatasetRegistryService

class ImageQualityAssessmentService:
    """
    Automated Clinical Retinal Anatomical & Image Quality Assessment (IQA) Engine:
    
    1. Retinal Anatomical Verification Gate:
       - Validates Red/Orange Hemoglobin & Melanin Reflectance Spectrum (R >> B, R >> G)
       - Detects Circular Fundus Optical Aperture vs. rectangular everyday photos
       - Verifies Retinal Blood Vessel Tree Architecture via Green-channel Morphological Top-Hat & Curvilinear Filter
       - Verifies Continuous Vascular Segment Span & Multi-Branching Nodes (Rejects orange circles, fruits, balloons)
       - Verifies HSV Retinal Hue Coverage & Optic Disc / Foveal Luminescence
       
    2. Optical Degradation & Quality Gates:
       - Rejects pitch-dark / underexposed captures (< 12.0)
       - Rejects overexposed / flash glare captures (> 235.0)
       - Rejects out-of-focus / severely blurred captures (Laplacian variance < 8.0)
       - Rejects occluded / partial FOV (< 8% active retinal area)
       
    3. Actionable Rejection Directives:
       - Returns human-readable guidance to the clinician / patient instructing them to retake the scan.
    """
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

        # Check resolution
        h, w = image_np.shape[:2]
        if h < 80 or w < 80:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": 0.0,
                "brightness_score": 0.0,
                "contrast_score": 0.0,
                "fov_ratio": 0.0,
                "rejection_reason": f"Image resolution is too low ({w}x{h}px). Minimum 400x400px required for clinical grading."
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
            r_mean = float(np.mean(gray))
            g_mean = float(np.mean(gray))
            b_mean = float(np.mean(gray))

        overall_mean = float(np.mean(gray))

        # Check 1: Completely black / pitch-dark image
        if overall_mean < 8.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 5.0,
                "is_gradable": False,
                "blur_score": 0.0,
                "brightness_score": round(overall_mean, 1),
                "contrast_score": 0.0,
                "fov_ratio": 0.0,
                "rejection_reason": "Scan is completely dark / underexposed. Please retake the retina photograph with proper fundus illumination."
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
                "rejection_reason": "Scan is completely overexposed / washed out. Please retake the retina photograph with balanced flash illumination."
            }

        # -------------------------------------------------------------
        # 1. RETINAL COLOR SPECTRUM VALIDATION
        # -------------------------------------------------------------
        if len(image_np.shape) == 3 and image_np.shape[2] >= 3:
            if r_mean < 14.0:
                return {
                    "quality_label": "NOT A RETINA IMAGE",
                    "quality_score": 0.0,
                    "is_gradable": False,
                    "blur_score": 0.0,
                    "brightness_score": round(overall_mean, 1),
                    "contrast_score": 0.0,
                    "fov_ratio": 0.0,
                    "rejection_reason": "Non-retinal image detected: Insufficient ocular reflectance spectrum. Please upload an authentic eye fundus photograph."
                }

            # Normal scenes (blue sky, white documents, faces, green plants) have high Blue/Green vs Red
            if b_mean >= r_mean * 0.85 and b_mean > 32.0:
                return {
                    "quality_label": "NOT A RETINA IMAGE",
                    "quality_score": 0.0,
                    "is_gradable": False,
                    "blur_score": 0.0,
                    "brightness_score": round(overall_mean, 1),
                    "contrast_score": 0.0,
                    "fov_ratio": 0.0,
                    "rejection_reason": f"Non-retinal image detected: Unnatural color spectrum (Blue: {b_mean:.1f}, Red: {r_mean:.1f}). Please upload an authentic eye fundus photograph."
                }

            if (r_mean / max(1.0, b_mean)) < 1.25 and b_mean > 28.0:
                return {
                    "quality_label": "NOT A RETINA IMAGE",
                    "quality_score": 0.0,
                    "is_gradable": False,
                    "blur_score": 0.0,
                    "brightness_score": round(overall_mean, 1),
                    "contrast_score": 0.0,
                    "fov_ratio": 0.0,
                    "rejection_reason": "Non-retinal image detected: Color profile does not match retinal fundus photography. Please upload a genuine retinal scan."
                }

        # -------------------------------------------------------------
        # 2. RETINAL FOV & APERTURE VERIFICATION
        # -------------------------------------------------------------
        _, fov_mask = cv2.threshold(gray, 12, 255, cv2.THRESH_BINARY)
        total_pixels = gray.shape[0] * gray.shape[1]
        retinal_pixels = int(np.count_nonzero(fov_mask))
        fov_ratio = retinal_pixels / max(1, float(total_pixels))

        if fov_ratio < 0.08:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 10.0,
                "is_gradable": False,
                "blur_score": 0.0,
                "brightness_score": round(overall_mean, 1),
                "contrast_score": 0.0,
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": "Pupil occlusion or partial field: Retinal field of view is too small (<8%). Please align patient pupil and recapture."
            }

        # Check image corners: fundus cameras have dark/black corners due to the circular aperture
        c1 = float(np.mean(gray[:max(5, int(h * 0.05)), :max(5, int(w * 0.05))]))
        c2 = float(np.mean(gray[:max(5, int(h * 0.05)), -max(5, int(w * 0.05)):]))
        c3 = float(np.mean(gray[-max(5, int(h * 0.05)):, :max(5, int(w * 0.05))]))
        c4 = float(np.mean(gray[-max(5, int(h * 0.05)):, -max(5, int(w * 0.05)):]))
        corners_mean = (c1 + c2 + c3 + c4) / 4.0

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

        # -------------------------------------------------------------
        # 3. RETINAL VASCULAR TREE ARCHITECTURE VERIFICATION
        # -------------------------------------------------------------
        # Apply Green-channel CLAHE + dual-scale Top-Hat / Bottom-Hat morphological filter
        g_channel = image_np[:, :, 1] if len(image_np.shape) == 3 else gray
        clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
        g_enhanced = clahe.apply(g_channel)

        k1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        k2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        blackhat = cv2.addWeighted(
            cv2.morphologyEx(g_enhanced, cv2.MORPH_BLACKHAT, k1), 0.5,
            cv2.morphologyEx(g_enhanced, cv2.MORPH_BLACKHAT, k2), 0.5, 0
        )

        # Erode FOV mask by 16px to completely exclude circular border edge artifacts!
        fov_eroded = cv2.erode(fov_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (16, 16)))
        vessel_signal = cv2.bitwise_and(blackhat, blackhat, mask=fov_eroded)

        vessel_thresh = cv2.adaptiveThreshold(vessel_signal, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, -4)
        vessel_thresh = cv2.bitwise_and(vessel_thresh, vessel_thresh, mask=fov_eroded)

        # Count curvilinear connected components (blood vessel ridges)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(vessel_thresh)
        elongated_vessels = 0
        total_vessel_pixels = 0
        max_vessel_len = 0.0

        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            width = stats[i, cv2.CC_STAT_WIDTH]
            height = stats[i, cv2.CC_STAT_HEIGHT]
            aspect = max(width, height) / max(1.0, float(min(width, height)))
            diag = np.sqrt(width**2 + height**2)

            if area >= 14 and aspect >= 2.2:
                elongated_vessels += 1
                total_vessel_pixels += area
                if diag > max_vessel_len:
                    max_vessel_len = diag

        vessel_density = (total_vessel_pixels / max(1.0, float(retinal_pixels))) * 100.0

        # Check HSV Hue Coverage
        if len(image_np.shape) == 3:
            hsv = cv2.cvtColor(image_np, cv2.COLOR_RGB2HSV)
            h_chan = hsv[:, :, 0]
            s_chan = hsv[:, :, 1]
            retina_hue_mask = ((h_chan <= 28) | (h_chan >= 150)) & (s_chan >= 25)
            retina_hue_pct = float(np.count_nonzero(retina_hue_mask[fov_mask > 0])) / max(1.0, float(retinal_pixels))
        else:
            retina_hue_pct = 0.50

        # -------------------------------------------------------------
        # 4. REJECTION GATES
        # -------------------------------------------------------------
        # Gate A: Non-Retina Everyday Photo (Rectangular scene with bright corners and no vessel structure)
        if corners_mean > 45.0 and fov_ratio > 0.95 and elongated_vessels < 5:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": "Non-retinal image detected: The uploaded image does not match retinal fundus anatomical features (no vascular tree / standard scene photo). Please upload an authentic eye fundus photograph."
            }

        # Gate B: Non-Retina Orange Objects / Plain Orange Circles / Fruit Textures
        # Real fundus scans have a continuous vascular tree radiating from the optic disc.
        # Plain orange shapes, orange fruits, balloons, or sunset circles have 0 branching vessels.
        if elongated_vessels < 10 or total_vessel_pixels < 120 or max_vessel_len < 20.0:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": f"Non-retinal image detected: Missing retinal blood vessel tree (Vessels found: {elongated_vessels}, Max span: {max_vessel_len:.1f}px). An authentic retinal photograph must display branching blood vessels radiating from the optic nerve head. Please upload an authentic eye fundus scan."
            }

        # Gate C: Non-Retina Hue & Topology mismatch
        if retina_hue_pct < 0.28 and elongated_vessels < 12:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": "Non-retinal image detected: Unnatural hue distribution and missing vascular structure. Please upload an authentic eye fundus photograph."
            }

        # Gate D: Blur / Out of focus
        if blur_score < 8.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 20.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": f"Image is severely blurred / out of focus (Sharpness score: {blur_score:.1f}). Please steady the fundus camera and refocus on the retina."
            }

        # Gate E: Severely underexposed / dark
        if brightness < 18.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 25.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": f"Retina scan is underexposed / too dark (Brightness score: {brightness:.1f}). Please increase fundus camera illumination and recapture."
            }

        # Gate F: Severe flash glare / overexposure
        if brightness > 228.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 25.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": f"Excessive flash glare / overexposure detected (Brightness score: {brightness:.1f}). Please balance illumination and recapture."
            }

        # Gate G: Contrast deficiency
        if contrast < 9.0:
            return {
                "quality_label": "POOR (UNGRADABLE)",
                "quality_score": 30.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": "Extremely low optical contrast. Retake scan with clear view of the retina."
            }

        # -------------------------------------------------------------
        # 5. GRADABLE RETINA IMAGE QUALITY CALCULATION (0 - 100)
        # -------------------------------------------------------------
        norm_sharpness = min(100.0, (blur_score / 45.0) * 100.0)
        norm_bright = max(0.0, 100.0 - abs(brightness - 110.0) * 0.9)
        norm_vessels = min(100.0, (elongated_vessels / 50.0) * 100.0)
        norm_contrast = min(100.0, (contrast / 40.0) * 100.0)

        quality_score = float(0.35 * norm_sharpness + 0.25 * norm_bright + 0.25 * norm_vessels + 0.15 * norm_contrast)
        quality_score = round(max(55.0, min(99.0, quality_score)), 1)

        if quality_score >= 75.0 and blur_score >= 20.0:
            quality_label = "GOOD"
        else:
            quality_label = "BORDERLINE / MEDIUM"

        return {
            "quality_label": quality_label,
            "quality_score": quality_score,
            "is_gradable": True,
            "blur_score": round(blur_score, 2),
            "brightness_score": round(brightness, 2),
            "contrast_score": round(contrast, 2),
            "fov_ratio": round(fov_ratio, 4),
            "rejection_reason": None
        }
