import os
import torch

pt_path = r"C:\Users\TALBIYA PARVEEN\.gemini\antigravity\brain\e094ba78-662e-4e04-80e4-05d710576e3a\dr_screening_backend\weights\sih_dr_best_model.pt"
print(f"Checking {pt_path} (Size: {os.path.getsize(pt_path)} bytes)...")

try:
    data = torch.load(pt_path, map_location="cpu")
    print("Type of data:", type(data))
    if isinstance(data, dict):
        print("Keys:", list(data.keys())[:10])
        if "model" in data:
            print("Model keys:", type(data["model"]))
    else:
        print("Data attributes:", dir(data)[:10])
except Exception as e:
    print(f"Load error: {e}")
