import cv2
import numpy as np
from services.biomarker_service import BiomarkerDetectionService

bio = BiomarkerDetectionService(target_size=456)

img = np.zeros((456, 456, 3), dtype=np.uint8)
cv2.circle(img, (228, 228), 210, (180, 80, 25), -1)
cv2.circle(img, (130, 228), 28, (220, 190, 110), -1)
cv2.ellipse(img, (228, 228), (140, 90), 45, 0, 180, (110, 40, 10), 3)

res = bio.analyze_structures(img)
print("Normal retina analysis:", {
    "red_count": res["red_count"],
    "yellow_count": res["yellow_count"],
    "white_count": res["white_count"],
    "vessel_density_pct": res["vessel_density_pct"]
})
