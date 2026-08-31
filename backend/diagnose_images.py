import os
import cv2
import glob
from services.preprocessor import PreprocessingService
from services.biomarker_service import BiomarkerDetectionService
from services.model_service import ModelService

pre = PreprocessingService(target_size=456)
bio = BiomarkerDetectionService(target_size=456)
model = ModelService()

uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
image_files = glob.glob(os.path.join(uploads_dir, "*_orig_*.png"))

print(f"[DIAGNOSTIC] Inspecting {len(image_files)} uploaded images...")

for img_path in sorted(image_files, key=os.path.getmtime, reverse=True)[:6]:
    fname = os.path.basename(img_path)
    img_bgr = cv2.imread(img_path)
    if img_bgr is None: continue
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    
    prep_res = pre.preprocess(img_rgb)
    enhanced = prep_res["enhanced_rgb"]
    
    struct = bio.analyze_structures(enhanced)
    pred = model.predict(enhanced)
    
    print(f"\nImage: {fname}")
    print(f"  Predicted Severity: {pred['severity_name']} (Grade {pred['severity_level']})")
    print(f"  Biomarkers Detected: red_dots={struct['red_count']}, yellow_dots={struct['yellow_count']}, white_dots={struct['white_count']}, vessel_density={struct['vessel_density_pct']}%")
