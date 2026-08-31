import os
import glob
import cv2
from services.preprocessor import PreprocessingService
from services.biomarker_service import BiomarkerDetectionService
from services.model_service import ModelService

pre = PreprocessingService(target_size=456)
bio = BiomarkerDetectionService(target_size=456)
model = ModelService()

uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
image_files = glob.glob(os.path.join(uploads_dir, "*_orig_*.png"))

print(f"[TEST] Comparing img_rgb vs enhanced_rgb across {len(image_files)} uploaded images:\n")

for img_path in sorted(image_files, key=os.path.getmtime, reverse=True)[:6]:
    fname = os.path.basename(img_path)
    img_bgr = cv2.imread(img_path)
    if img_bgr is None: continue
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    
    # 1. Prediction on clean img_rgb
    struct_raw = bio.analyze_structures(img_rgb)
    pred_raw = model.predict(img_rgb)
    
    # 2. Prediction on Ben Graham enhanced_rgb
    prep_res = pre.preprocess(img_rgb)
    enhanced = prep_res["enhanced_rgb"]
    struct_bg = bio.analyze_structures(enhanced)
    pred_bg = model.predict(enhanced)
    
    print(f"Image: {fname}")
    print(f"  [CLEAN RGB]   Grade: {pred_raw['severity_level']} ({pred_raw['severity_name'][:25]}) | MAs: {struct_raw['microaneurysms_count']}, Hems: {struct_raw['hemorrhages_count']}, Exu: {struct_raw['yellow_count']}, Vessel Density: {struct_raw['vessel_density_pct']}%")
    print(f"  [BEN GRAHAM]  Grade: {pred_bg['severity_level']} ({pred_bg['severity_name'][:25]}) | MAs: {struct_bg['microaneurysms_count']}, Hems: {struct_bg['hemorrhages_count']}, Exu: {struct_bg['yellow_count']}, Vessel Density: {struct_bg['vessel_density_pct']}%")
    print("-" * 80)
