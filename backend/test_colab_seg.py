import os
import cv2
import numpy as np

# Load one of the APTOS images
import glob
matches = glob.glob(r"C:\Users\TALBIYA PARVEEN\.gemini\antigravity\brain\e094ba78-662e-4e04-80e4-05d710576e3a\sih_dr_project\backend\uploads\*1f31701dd61b.png")
if not matches:
    matches = glob.glob(r"C:\Users\TALBIYA PARVEEN\.gemini\antigravity\brain\e094ba78-662e-4e04-80e4-05d710576e3a\sih_dr_project\backend\uploads\*000c1434d8d7.png")

img_path = matches[0]
img_bgr = cv2.imread(img_path)
rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
h, w = rgb.shape[:2]

# 1. FOV Mask
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
_, fov_mask = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)
fov_mask = cv2.morphologyEx(fov_mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
fov_mask = cv2.morphologyEx(fov_mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))

# 2. Optic Disc Localization
green = rgb[..., 1]
blur_od = cv2.GaussianBlur(green, (25, 25), 0)
thresh_od = np.percentile(blur_od[fov_mask > 0], 99.0)
od_mask = (blur_od >= thresh_od).astype(np.uint8) * 255
od_mask = cv2.bitwise_and(od_mask, od_mask, mask=fov_mask)
contours, _ = cv2.findContours(od_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if contours:
    c = max(contours, key=cv2.contourArea)
    (od_x, od_y), od_r = cv2.minEnclosingCircle(c)
    od_center, od_radius = (int(od_x), int(od_y)), int(od_r)
else:
    od_center, od_radius = (int(w*0.3), int(h*0.5)), int(w*0.08)

# 3. Vessel Segmentation
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
green_eq = clahe.apply(green)
bg_v = cv2.GaussianBlur(green_eq, (21, 21), 0)
diff_v = cv2.subtract(bg_v, green_eq)
_, vmask = cv2.threshold(diff_v, 14, 255, cv2.THRESH_BINARY)
vmask = cv2.bitwise_and(vmask, vmask, mask=fov_mask)

# 4. Microaneurysm detection on enhanced green channel
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
blackhat = cv2.morphologyEx(green_eq, cv2.MORPH_BLACKHAT, kernel)
_, ma_thresh = cv2.threshold(blackhat, 18, 255, cv2.THRESH_BINARY)
ma_thresh = cv2.bitwise_and(ma_thresh, ma_thresh, mask=fov_mask)
ma_thresh = cv2.bitwise_and(ma_thresh, cv2.bitwise_not(vmask))
cv2.circle(ma_thresh, od_center, int(od_radius * 1.5), 0, -1)

ma_contours, _ = cv2.findContours(ma_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
mas = [c for c in ma_contours if 2 <= cv2.contourArea(c) <= 40]

# 5. Exudate segmentation
bg_e = cv2.GaussianBlur(green_eq, (0, 0), 15)
diff_e = cv2.subtract(green_eq.astype(np.int16), bg_e.astype(np.int16))
diff_e = np.clip(diff_e, 0, 255).astype(np.uint8)
_, exu_thresh = cv2.threshold(diff_e, 25, 255, cv2.THRESH_BINARY)
exu_thresh = cv2.bitwise_and(exu_thresh, exu_thresh, mask=fov_mask)
cv2.circle(exu_thresh, od_center, int(od_radius * 1.6), 0, -1)
exu_contours, _ = cv2.findContours(exu_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
exudates = [c for c in exu_contours if cv2.contourArea(c) >= 10]

# 6. Hemorrhages
r = rgb[..., 0].astype(np.float32)
g = rgb[..., 1].astype(np.float32)
redness = (r - g) / (r + g + 1e-6)
red_norm = np.clip((redness - np.percentile(redness[fov_mask > 0], 50)) / (np.percentile(redness[fov_mask > 0], 98) - np.percentile(redness[fov_mask > 0], 50) + 1e-6), 0, 1)
hem_mask = (red_norm > 0.88).astype(np.uint8) * 255
hem_mask = cv2.bitwise_and(hem_mask, hem_mask, mask=fov_mask)
hem_mask = cv2.bitwise_and(hem_mask, cv2.bitwise_not(vmask))
cv2.circle(hem_mask, od_center, int(od_radius * 1.5), 0, -1)
hem_contours, _ = cv2.findContours(hem_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
hemorrhages = [c for c in hem_contours if cv2.contourArea(c) >= 25]

print(f"APTOS Image: {os.path.basename(img_path)}")
print(f"  Isolated Microaneurysms: {len(mas)}")
print(f"  Isolated Hard Exudates:  {len(exudates)}")
print(f"  Isolated Hemorrhages:    {len(hemorrhages)}")

n_ma = len(mas)
n_exu = len(exudates)
n_hem = len(hemorrhages)

if (n_ma > 25 and n_hem > 12) or (n_exu > 30 and n_hem > 8):
    grade = 4
elif (n_hem >= 6 and n_ma > 6) or (n_ma >= 18):
    grade = 3
elif n_ma >= 4 or n_exu >= 1 or n_hem >= 1:
    grade = 2
elif n_ma >= 1:
    grade = 1
else:
    grade = 0

print(f"  Resulting Clinical Grade: Grade {grade}")
