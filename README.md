# 🏥 NetraAI: Automated Diabetic Retinopathy Tele-Screening Network

**Smart India Hackathon (SIH 2026) Prototype**  
An end-to-end, multi-role tele-ophthalmology platform with MATLAB-grade medical feature extraction, YOLO11m deep learning classification, Grad-CAM explainability, and district-level Simulink telemedicine workflow simulation.

---

## 📂 Project Architecture

```
sih_dr_project/
├── backend/
│   ├── app.py                      # Flask API with multi-role auth & all 10 endpoints
│   ├── config.py                   # Configuration & upload directories
│   ├── models.py                   # SQLAlchemy Models (Users, Screenings, Biomarkers)
│   ├── requirements.txt            # Python dependencies
│   ├── services/
│   │   ├── iqa_service.py          # 1. Image Quality Assessment (Focus/Blur, Illumination, FOV)
│   │   ├── preprocessor.py         # 2. Circular Crop, Ben Graham Normalization, CLAHE
│   │   ├── biomarker_service.py    # 3. Sub-pixel Bounding Squares (🟥 Red, 🟨 Yellow, ⬜ White)
│   │   ├── model_service.py        # 4. ICDR 0–4 Severity Grading & Referral Triage
│   │   ├── gradcam_service.py      # 5. Grad-CAM Saliency Heatmap Generation
│   │   ├── report_service.py       # 6. Automated Clinical PDF Report Generator
│   │   └── simulink_service.py     # 7. District Telemedicine Queue Simulator (100k+ patients)
│   ├── matlab/
│   │   └── telemedicine_simulink_model.m  # Standalone MATLAB/Simulink Script
│   ├── uploads/                    # Original uploaded fundus scans
│   ├── processed/                  # Processed & annotated images
│   ├── reports/                    # Generated PDF reports
│   └── weights/                    # Place trained 'sih_dr_best_model.pt' here
│
└── frontend/
    ├── index.html                  # Multi-Role Web Portal (Patient, Doctor, Admin)
    ├── css/style.css               # Styling & responsive medical UI
    └── js/app.js                   # Client-side API integration & canvas rendering
```

---

## 🚀 How to Run in VS Code

### 1. Start the Flask Backend

1. Open VS Code in the `backend/` folder (or open terminal):
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate
   pip install -r requirements.txt
   ```
2. Run the Flask server:
   ```powershell
   python app.py
   ```
   *The backend starts at `http://localhost:5000` with CORS enabled.*

---

### 2. Open the Frontend

You can open the frontend in **either** of these simple ways:

* **Method A (Easiest)**: Double-click `frontend/index.html` to open it in Chrome / Edge.
* **Method B (VS Code Live Server)**: Right-click `frontend/index.html` in VS Code and click **"Open with Live Server"**.

---

## 👥 Role-Based Workflow Demonstration

### 1. 👤 Patient Portal
* Drag and drop any retinal fundus image.
* **Image Quality Assessment**: Instant check on focus, illumination, and field of view. (Ungradable scans are rejected with clear recapture instructions).
* **Multi-Channel Diagnostic View**:
  1. *Original Fundus Scan*
  2. *Retinal Vessel Network Tree*
  3. *Lesions in Bounding Squares* (**🟥 Red Squares** for Microaneurysms, **🟨 Yellow Squares** for Hard Exudates, **⬜ White Squares** for Cotton Wool Spots)
  4. *Grad-CAM Saliency Heatmap*
* **Download PDF Report**: Generates official clinical report with doctor sign-off box.

---

### 2. 🩺 Doctor (Clinician) Portal
* View live clinical worklist of assigned patient screenings.
* Click on any scan to inspect all 4 imaging channels and quantitative lesion counts.
* **Clinical Sign-off**: Select status (*Confirmed*, *Needs Recapture*, *Refer to Specialist*, *Not Referable*, *Overruled*), add notes, and submit. The patient's status updates immediately.

---

### 3. 🏛️ District Admin Portal
* Real-time district dashboard (Total Screened, Referral Rate %, Pending Doctor Reviews, Doctor Workload).
* **Simulink Telemedicine Simulator**: Adjust annual patient targets (100,000+), rural PHCs count, and uplink bandwidth (2 Mbps) to simulate daily doctor hours saved and queuing throughput in real-time.
