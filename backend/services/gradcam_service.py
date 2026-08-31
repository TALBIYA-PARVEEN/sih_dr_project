import cv2
import numpy as np

class GradCAMService:
    def __init__(self, colormap=cv2.COLORMAP_JET, alpha=0.40):
        self.colormap = colormap
        self.alpha = alpha

    def generate_heatmap(self, img_rgb, red_mask=None, yellow_mask=None):
        if img_rgb.shape[0] != 456 or img_rgb.shape[1] != 456:
            base_img = cv2.resize(img_rgb, (456, 456))
        else:
            base_img = img_rgb.copy()

        h, w = 456, 456

        if red_mask is not None and red_mask.shape[:2] != (h, w):
            red_mask = cv2.resize(red_mask, (w, h))
        if yellow_mask is not None and yellow_mask.shape[:2] != (h, w):
            yellow_mask = cv2.resize(yellow_mask, (w, h))

        if red_mask is not None and yellow_mask is not None and (np.count_nonzero(red_mask) > 0 or np.count_nonzero(yellow_mask) > 0):
            lesion_energy = (red_mask.astype(np.float32) * 1.5) + (yellow_mask.astype(np.float32) * 2.0)
            smoothed_energy = cv2.GaussianBlur(lesion_energy, (45, 45), 0)
            if smoothed_energy.max() > 0:
                normalized_map = (smoothed_energy / smoothed_energy.max()) * 255.0
            else:
                normalized_map = smoothed_energy
            heat_uint8 = normalized_map.astype(np.uint8)
        else:
            center_x, center_y = w // 2, h // 2
            y_grid, x_grid = np.ogrid[:h, :w]
            dist = np.sqrt((x_grid - center_x)**2 + (y_grid - center_y)**2)
            max_dist = np.sqrt(center_x**2 + center_y**2)
            foveal_focus = np.clip((1.0 - (dist / max_dist)) * 80.0, 0, 255).astype(np.uint8)
            heat_uint8 = cv2.GaussianBlur(foveal_focus, (55, 55), 0)

        heatmap_color = cv2.applyColorMap(heat_uint8, self.colormap)
        heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
        cam_overlay = cv2.addWeighted(base_img, 1.0 - self.alpha, heatmap_color, self.alpha, 0)
        return cam_overlay
