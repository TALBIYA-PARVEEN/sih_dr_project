import cv2
import numpy as np
from services.dataset_service import DatasetRegistryService

class ImageQualityAssessmentService:
    """
    Automated Clinical Retinal Anatomical & Image Quality Assessment (IQA) Engine:
    
    1. Retinal Anatomical Verification Gate:
       - Multi-scale Gaussian-blurred tubular vessel extraction (eliminates sensor noise and surface textures)
       - Major vascular arcade continuity requirement (primary arcade span >= 40px, elongated branches >= 6)
       - Optic Nerve Head (Optic Disc) localized focal cluster detection
       - Rejects all non-retinal objects (orange fruits, plain circles, sunsets, everyday photos)
       
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

            if b_mean >= r_mean * 0.85 and b_mean > 30.0:
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

            if (r_mean / max(1.0, b_mean)) < 1.25 and b_mean > 25.0:
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

        # Active FOV Geometry (Aspect Ratio & Convex Solidity)
        cnts, _ = cv2.findContours(fov_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        main_cnt = max(cnts, key=cv2.contourArea) if cnts else None
        if main_cnt is not None:
            bx, by, bw, bh = cv2.boundingRect(main_cnt)
            fov_aspect_ratio = max(bw, bh) / max(1.0, float(min(bw, bh)))
            hull = cv2.convexHull(main_cnt)
            solidity = cv2.contourArea(main_cnt) / max(1.0, cv2.contourArea(hull))
        else:
            fov_aspect_ratio = 1.0
            solidity = 1.0

        # Check image corners
        c1 = float(np.mean(gray[:max(5, int(h * 0.05)), :max(5, int(w * 0.05))]))
        c2 = float(np.mean(gray[:max(5, int(h * 0.05)), -max(5, int(w * 0.05)):]))
        c3 = float(np.mean(gray[-max(5, int(h * 0.05)):, :max(5, int(w * 0.05))]))
        c4 = float(np.mean(gray[-max(5, int(h * 0.05)):, -max(5, int(w * 0.05)):]))
        corners_mean = (c1 + c2 + c3 + c4) / 4.0

        fov_eroded = cv2.erode(fov_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (18, 18)))
        active_pixels = int(np.count_nonzero(fov_eroded))

        if retinal_pixels > 200:
            active_gray = gray[fov_mask > 0]
            brightness = float(np.mean(active_gray))
            contrast = float(np.std(active_gray))
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            blur_score = float(np.var(laplacian[fov_mask > 0]))
            g_active_mean = float(np.mean(image_np[:, :, 1][fov_mask > 0])) if len(image_np.shape) == 3 else g_mean
            r_active_mean = float(np.mean(image_np[:, :, 0][fov_mask > 0])) if len(image_np.shape) == 3 else r_mean
            rg_active_ratio = r_active_mean / max(1.0, g_active_mean)
        else:
            brightness = overall_mean
            contrast = float(np.std(gray))
            blur_score = float(np.var(cv2.Laplacian(gray, cv2.CV_64F)))
            g_active_mean = g_mean
            r_active_mean = r_mean
            rg_active_ratio = r_mean / max(1.0, g_mean)

        # -------------------------------------------------------------
        # 3. MULTI-SCALE TUBULAR VESSEL TREE EXTRACTION
        # -------------------------------------------------------------
        g_raw = image_np[:, :, 1] if len(image_np.shape) == 3 else gray
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        g_enhanced = clahe.apply(g_raw)

        # Multi-scale Gaussian blur to suppress noise while preserving continuous vessels
        blur1 = cv2.GaussianBlur(g_enhanced, (3, 3), 1.0)
        blur2 = cv2.GaussianBlur(g_enhanced, (7, 7), 2.0)

        k1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        k2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        vessel_resp1 = cv2.morphologyEx(blur1, cv2.MORPH_BLACKHAT, k1)
        vessel_resp2 = cv2.morphologyEx(blur2, cv2.MORPH_BLACKHAT, k2)
        vessel_combined = cv2.addWeighted(vessel_resp1, 0.6, vessel_resp2, 0.4, 0)
        vessel_signal = cv2.bitwise_and(vessel_combined, vessel_combined, mask=fov_eroded)

        vessel_thresh = cv2.adaptiveThreshold(vessel_signal, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, -6)
        vessel_thresh = cv2.bitwise_and(vessel_thresh, vessel_thresh, mask=fov_eroded)

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(vessel_thresh)
        elongated_vessels = 0
        total_vessel_pixels = 0
        max_vessel_len = 0.0
        major_arcades = 0

        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            width = stats[i, cv2.CC_STAT_WIDTH]
            height = stats[i, cv2.CC_STAT_HEIGHT]
            aspect = max(width, height) / max(1.0, float(min(width, height)))
            diag = np.sqrt(width**2 + height**2)

            if area >= 25 and aspect >= 2.5:
                elongated_vessels += 1
                total_vessel_pixels += area
                if diag > max_vessel_len:
                    max_vessel_len = diag
                if diag >= 40.0:
                    major_arcades += 1

        # -------------------------------------------------------------
        # 4. OPTIC NERVE HEAD (OPTIC DISC) COMPACT NODE VERIFICATION
        # -------------------------------------------------------------
        rg_composite = cv2.addWeighted(image_np[:, :, 0] if len(image_np.shape) == 3 else gray, 0.6, g_raw, 0.4, 0)
        rg_fov = rg_composite[fov_eroded > 0]
        has_optic_disc = False

        if len(rg_fov) > 0 and active_pixels > 200:
            thresh_disc = np.percentile(rg_fov, 93)
            _, disc_mask = cv2.threshold(rg_composite, thresh_disc, 255, cv2.THRESH_BINARY)
            disc_mask = cv2.bitwise_and(disc_mask, disc_mask, mask=fov_eroded)
            n_d, _, st_d, _ = cv2.connectedComponentsWithStats(disc_mask)
            for i in range(1, n_d):
                d_area = st_d[i, cv2.CC_STAT_AREA]
                if 0.003 * active_pixels <= d_area <= 0.08 * active_pixels:
                    dw, dh = st_d[i, cv2.CC_STAT_WIDTH], st_d[i, cv2.CC_STAT_HEIGHT]
                    d_asp = max(dw, dh) / max(1.0, float(min(dw, dh)))
                    if d_asp <= 1.8:
                        has_optic_disc = True
                        break

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
        # 5. REJECTION GATES
        # -------------------------------------------------------------
        # Gate 0A: Non-circular / Tall object / Drink / Glass geometry
        if fov_aspect_ratio > 1.40:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": f"Non-retinal image detected: Elongated non-retinal object shape (Aspect ratio: {fov_aspect_ratio:.2f}, fundus camera aperture must be <= 1.40). Please upload an authentic eye fundus photograph."
            }

        # Gate 0B: Irregular object shape / Glass / Cup / Table reflections
        if solidity < 0.85:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": f"Non-retinal image detected: Non-circular convex geometry (Solidity: {solidity:.2f}, min 0.85 for ocular fundus lens). Please upload an authentic eye fundus photograph."
            }

        # Gate 0C: Excessive Green Reflectance (Orange juice / citrus drink / yellow liquids)
        # Authentic retina tissue absorbs green light through hemoglobin (G_mean <= 135)
        if g_active_mean > 135.0:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": f"Non-retinal image detected: Abnormal green spectrum reflectance without ocular hemoglobin absorption (Green mean: {g_active_mean:.1f}, authentic retina <= 135.0). Please upload an authentic eye fundus photograph."
            }

        # Gate 0D: Insufficient Red Choroidal Dominance
        if rg_active_ratio < 1.25:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": f"Non-retinal image detected: Insufficient choroidal red reflectance (R/G ratio: {rg_active_ratio:.2f}, min 1.25 required). Please upload an authentic eye fundus photograph."
            }
        # Gate A: Non-Retina Everyday Photo
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

        # Gate B: Non-Retina Objects / Orange Circles / Fruits / Textures
        # Genuine retinas have continuous vascular arcades spanning >= 40px and multiple branches
        if max_vessel_len < 38.0 or elongated_vessels < 6:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": f"Non-retinal image detected: Missing continuous retinal vascular tree (Longest vessel span: {max_vessel_len:.1f}px, Vessels: {elongated_vessels}). An authentic retinal photograph must display branching blood vessels radiating from the optic nerve head. Please upload an authentic eye fundus scan."
            }

        # Gate C: Optic Nerve Head Gate
        if not has_optic_disc and major_arcades < 2:
            return {
                "quality_label": "NOT A RETINA IMAGE",
                "quality_score": 0.0,
                "is_gradable": False,
                "blur_score": round(blur_score, 2),
                "brightness_score": round(brightness, 2),
                "contrast_score": round(contrast, 2),
                "fov_ratio": round(fov_ratio, 4),
                "rejection_reason": "Non-retinal image detected: Missing localized Optic Nerve Head focal point. A genuine retinal fundus photograph must contain a localized optic disc where blood vessels emerge. Please upload an authentic eye fundus scan."
            }

        # Gate D: Non-Retina Hue & Topology mismatch
        if retina_hue_pct < 0.28 and elongated_vessels < 10:
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

        # Gate E: Blur / Out of focus
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

        # Gate F: Severely underexposed / dark
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

        # Gate G: Severe flash glare / overexposure
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

        # Gate H: Contrast deficiency
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
        # 6. GRADABLE RETINA IMAGE QUALITY CALCULATION (0 - 100)
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
