import os
import shutil

src = r"C:\Users\TALBIYA PARVEEN\.gemini\antigravity\brain\e094ba78-662e-4e04-80e4-05d710576e3a\dr_screening_backend\weights\sih_dr_best_model.pt"
dst_dir = r"C:\Users\TALBIYA PARVEEN\.gemini\antigravity\brain\e094ba78-662e-4e04-80e4-05d710576e3a\sih_dr_project\backend\weights"
os.makedirs(dst_dir, exist_ok=True)
dst = os.path.join(dst_dir, "sih_dr_best_model.pt")

if os.path.exists(src):
    shutil.copy2(src, dst)
    print(f"[COPIED] Successfully placed {dst} (Size: {os.path.getsize(dst)} bytes)")
else:
    print(f"[NOTE] Source not found: {src}")
