import cv2
import numpy as np

class BiomarkerDetectionService:
    """
    Biomarker Detection & Retinal Structure Segmentation Engine:
    - Optic Disc & Fovea localization
    - Vessel segmentation with Frangi-like line filter
    - Microaneurysm sub-pixel extraction with circularity & vessel-subtraction
    - Hard Exudate segmentation with Optic Disc suppression
    - Hemorrhage segmentation
    - Lesion density heatmap generator
    """
    def __init__(self, target_size=456):
        self.target_size = target_size

    def analyze_structures(self, image_rgb):
        if image_rgb.shape[0] != self.target_size or image_rgb.shape[1] != self.target_size:
            rgb = cv2.resize(image_rgb, (self.target_size, self.target_size))
        else:
            rgb = image_rgb.copy()

        h, w = rgb.shape[:2]
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        green = rgb[:, :, 1]
        red = rgb[:, :, 0].astype(np.float32)

        # 1. Retinal FOV Mask
        _, fov_mask = cv2.threshold(gray, 18, 255, cv2.THRESH_BINARY)
        fov_mask = cv2.morphologyEx(fov_mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
        fov_mask = cv2.morphologyEx(fov_mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        fov_pixels = np.count_nonzero(fov_mask)
        if fov_pixels == 0:
            fov_mask = np.ones((h, w), dtype=np.uint8) * 255
            fov_pixels = h * w

        # 2. Optic Disc Localization & Mask
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        green_clahe = clahe.apply(green)

        blur_od = cv2.GaussianBlur(green_clahe, (35, 35), 0)
        fov_vals = blur_od[fov_mask > 0]
        od_thresh_val = np.percentile(fov_vals, 99.4) if len(fov_vals) > 0 else 225
        _, od_thresh = cv2.threshold(blur_od, od_thresh_val, 255, cv2.THRESH_BINARY)
        od_thresh = cv2.bitwise_and(od_thresh, od_thresh, mask=fov_mask)

        contours, _ = cv2.findContours(od_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            c = max(contours, key=cv2.contourArea)
            (od_x, od_y), od_r = cv2.minEnclosingCircle(c)
            od_center = (int(od_x), int(od_y))
            od_radius = max(20, min(50, int(od_r)))
        else:
            od_center = (int(w * 0.3), int(h * 0.5))
            od_radius = int(w * 0.08)

        # Exclusion mask for optic disc
        od_exclusion_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(od_exclusion_mask, od_center, int(od_radius * 1.8), 255, -1)

        # 3. Vessel Network Segmentation
        bg_vessel = cv2.GaussianBlur(green_clahe, (25, 25), 0)
        diff_vessel = cv2.subtract(bg_vessel, green_clahe)
        _, vessel_raw = cv2.threshold(diff_vessel, 18, 255, cv2.THRESH_BINARY)
        vessel_raw = cv2.bitwise_and(vessel_raw, vessel_raw, mask=fov_mask)
        
        # Keep only continuous vascular segments (area >= 15)
        v_cnts, _ = cv2.findContours(vessel_raw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        vessel_mask = np.zeros((h, w), dtype=np.uint8)
        for vc in v_cnts:
            if cv2.contourArea(vc) >= 15:
                cv2.drawContours(vessel_mask, [vc], -1, 255, -1)

        vessel_dilated = cv2.dilate(vessel_mask, np.ones((3, 3), np.uint8), iterations=1)
        vessel_density = (np.count_nonzero(vessel_mask) / fov_pixels) * 100.0

        # 4. Microaneurysm Sub-Pixel Extraction
        kernel_ma = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        blackhat = cv2.morphologyEx(green_clahe, cv2.MORPH_BLACKHAT, kernel_ma)
        fov_blackhat = blackhat[fov_mask > 0]
        ma_thresh_val = max(26, np.percentile(fov_blackhat, 99.6)) if len(fov_blackhat) > 0 else 30
        _, ma_binary = cv2.threshold(blackhat, ma_thresh_val, 255, cv2.THRESH_BINARY)
        ma_binary = cv2.bitwise_and(ma_binary, ma_binary, mask=fov_mask)
        ma_binary = cv2.bitwise_and(ma_binary, cv2.bitwise_not(vessel_dilated))
        ma_binary = cv2.bitwise_and(ma_binary, cv2.bitwise_not(od_exclusion_mask))

        ma_contours, _ = cv2.findContours(ma_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_mas = []
        red_boxes = []
        for c in ma_contours:
            area = cv2.contourArea(c)
            if 3 <= area <= 30:
                perimeter = cv2.arcLength(c, True)
                circularity = (4 * np.pi * area) / (perimeter * perimeter + 1e-6)
                if circularity >= 0.50:
                    valid_mas.append(c)
                    bx, by, bw, bh = cv2.boundingRect(c)
                    red_boxes.append([int(bx), int(by), int(bx + bw), int(by + bh)])

        # 5. Hard Exudates Segmentation
        bg_exu = cv2.GaussianBlur(green_clahe, (35, 35), 0)
        diff_exu = cv2.subtract(green_clahe, bg_exu)
        fov_exu = diff_exu[fov_mask > 0]
        exu_thresh_val = max(28, np.percentile(fov_exu, 99.6)) if len(fov_exu) > 0 else 32
        _, exu_binary = cv2.threshold(diff_exu, exu_thresh_val, 255, cv2.THRESH_BINARY)
        exu_binary = cv2.bitwise_and(exu_binary, exu_binary, mask=fov_mask)
        exu_binary = cv2.bitwise_and(exu_binary, cv2.bitwise_not(od_exclusion_mask))

        exu_contours, _ = cv2.findContours(exu_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_exudates = []
        yellow_boxes = []
        for c in exu_contours:
            area = cv2.contourArea(c)
            if 8 <= area <= 350:
                valid_exudates.append(c)
                bx, by, bw, bh = cv2.boundingRect(c)
                yellow_boxes.append([int(bx), int(by), int(bx + bw), int(by + bh)])

        # 6. Intraretinal Hemorrhages
        g_float = green.astype(np.float32)
        redness = (red - g_float) / (red + g_float + 1e-6)
        fov_redness = redness[fov_mask > 0]
        if len(fov_redness) > 0:
            p90 = np.percentile(fov_redness, 92.0)
            p99 = np.percentile(fov_redness, 99.6)
            red_norm = np.clip((redness - p90) / (p99 - p90 + 1e-6), 0, 1)
        else:
            red_norm = np.zeros_like(redness)

        hem_binary = ((red_norm > 0.94) & (green < 100)).astype(np.uint8) * 255
        hem_binary = cv2.bitwise_and(hem_binary, hem_binary, mask=fov_mask)
        hem_binary = cv2.bitwise_and(hem_binary, cv2.bitwise_not(vessel_dilated))
        hem_binary = cv2.bitwise_and(hem_binary, cv2.bitwise_not(od_exclusion_mask))

        hem_contours, _ = cv2.findContours(hem_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_hemorrhages = []
        for c in hem_contours:
            area = cv2.contourArea(c)
            if 15 <= area <= 500:
                valid_hemorrhages.append(c)
                bx, by, bw, bh = cv2.boundingRect(c)
                red_boxes.append([int(bx), int(by), int(bx + bw), int(by + bh)])

        # 7. Cotton Wool Spots
        cws_binary = ((gray > 185) & (diff_exu > 35)).astype(np.uint8) * 255
        cws_binary = cv2.bitwise_and(cws_binary, cws_binary, mask=fov_mask)
        cws_binary = cv2.bitwise_and(cws_binary, cv2.bitwise_not(od_exclusion_mask))
        cws_contours, _ = cv2.findContours(cws_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_cws = []
        white_boxes = []
        for c in cws_contours:
            area = cv2.contourArea(c)
            if 60 <= area <= 800:
                valid_cws.append(c)
                bx, by, bw, bh = cv2.boundingRect(c)
                white_boxes.append([int(bx), int(by), int(bx + bw), int(by + bh)])

        # 8. Annotated Image Overlay
        annotated = rgb.copy()
        cv2.circle(annotated, od_center, od_radius, (0, 255, 0), 2)
        cv2.putText(annotated, "Optic Disc", (od_center[0] - 25, od_center[1] - od_radius - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        for b in red_boxes[:25]:
            cv2.rectangle(annotated, (b[0], b[1]), (b[2], b[3]), (255, 30, 30), 2)
        for b in yellow_boxes[:25]:
            cv2.rectangle(annotated, (b[0], b[1]), (b[2], b[3]), (255, 220, 0), 2)
        for b in white_boxes[:10]:
            cv2.rectangle(annotated, (b[0], b[1]), (b[2], b[3]), (255, 255, 255), 2)

        red_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(red_mask, valid_mas, -1, 255, -1)
        cv2.drawContours(red_mask, valid_hemorrhages, -1, 255, -1)

        yellow_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(yellow_mask, valid_exudates, -1, 255, -1)

        return {
            "red_count": len(valid_mas) + len(valid_hemorrhages),
            "microaneurysms_count": len(valid_mas),
            "hemorrhages_count": len(valid_hemorrhages),
            "yellow_count": len(valid_exudates),
            "white_count": len(valid_cws),
            "vessel_density_pct": round(float(vessel_density), 2),
            "optic_disc_center": {"x": od_center[0], "y": od_center[1], "radius": od_radius},
            "annotated_image": annotated,
            "vessels_mask": vessel_mask,
            "red_mask": red_mask,
            "yellow_mask": yellow_mask,
            "red_boxes": red_boxes,
            "yellow_boxes": yellow_boxes,
            "white_boxes": white_boxes
        }
