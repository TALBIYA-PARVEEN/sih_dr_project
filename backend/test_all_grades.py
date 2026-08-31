import cv2
import numpy as np
from services.model_service import ModelService

model_service = ModelService()

def create_sample_retina(n_red=0, n_yellow=0, n_white=0):
    img = np.zeros((456, 456, 3), dtype=np.uint8)
    cv2.circle(img, (228, 228), 210, (180, 80, 25), -1)
    cv2.circle(img, (130, 228), 28, (220, 190, 110), -1)
    cv2.ellipse(img, (228, 228), (140, 90), 45, 0, 180, (110, 40, 10), 3)

    rng = np.random.default_rng(42)
    for _ in range(n_red):
        rx, ry = rng.integers(170, 320), rng.integers(170, 320)
        cv2.circle(img, (int(rx), int(ry)), 3, (0, 0, 220), -1)

    for _ in range(n_yellow):
        yx, yy = rng.integers(240, 340), rng.integers(180, 300)
        cv2.circle(img, (int(yx), int(yy)), 4, (40, 220, 240), -1)

    for _ in range(n_white):
        wx, wy = rng.integers(180, 280), rng.integers(180, 280)
        cv2.circle(img, (int(wx), int(wy)), 6, (230, 230, 230), -1)

    return img

test_cases = [
    ("Normal Retina", create_sample_retina(0, 0, 0), 0),
    ("Mild NPDR", create_sample_retina(2, 0, 0), 1),
    ("Moderate NPDR", create_sample_retina(5, 3, 0), 2),
    ("Severe NPDR", create_sample_retina(14, 2, 4), 3),
    ("Proliferative DR", create_sample_retina(35, 20, 2), 4)
]

for label, img, expected_grade in test_cases:
    res = model_service.predict(img)
    grade = res["severity_level"]
    name = res["severity_name"]
    ev = res.get("biomarkers_evidence", {})
    print(f"Condition: {label:<20} -> Grade {grade} ({name}) | Detected Evidence: {ev}")
