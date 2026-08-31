import io
import cv2
import numpy as np
from app import create_app

def test_fullstack():
    print("[TEST] Running Multi-Role Fullstack Backend Tests...")
    app = create_app()
    client = app.test_client()

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    print("[PASS] 1. Health Check API")

    # 2. Auth Login (Doctor)
    res_login = client.post("/api/auth/login", json={"username": "doctor_sharma", "password": "doctor123"})
    assert res_login.status_code == 200
    doc_id = res_login.get_json()["user"]["id"]
    print("[PASS] 2. Multi-Role Authentication (Doctor Login)")

    # 3. Patient Image Upload & Screen
    img_good = np.zeros((512, 512, 3), dtype=np.uint8)
    cv2.circle(img_good, (256, 256), 220, (180, 80, 40), -1)
    cv2.circle(img_good, (180, 256), 35, (240, 220, 100), -1)
    cv2.line(img_good, (180, 256), (380, 180), (30, 20, 150), 3)
    cv2.circle(img_good, (300, 280), 4, (10, 10, 220), -1)
    cv2.circle(img_good, (320, 230), 5, (230, 230, 20), -1)
    _, enc = cv2.imencode(".png", img_good)

    data = {
        "file": (io.BytesIO(enc.tobytes()), "fundus.png"),
        "patient_name": "Ramesh Kumar",
        "patient_age": "54",
        "patient_gender": "Male"
    }
    res_screen = client.post("/api/screen", data=data, content_type="multipart/form-data")
    assert res_screen.status_code == 201
    session_id = res_screen.get_json()["session_id"]
    print(f"[PASS] 3. Patient Screening Upload & Inference Pipeline (Session ID: {session_id[:8]}...)")

    # 4. Doctor Queue & Sign-off
    res_queue = client.get(f"/api/doctor/queue/{doc_id}")
    assert res_queue.status_code == 200
    print("[PASS] 4. Doctor Worklist & Queue Retrieval")

    res_signoff = client.post(f"/api/review/{session_id}", json={
        "status": "Confirmed",
        "notes": "Verified macular hard exudates. Priority tele-referral generated.",
        "reviewed_by": "Dr. S. Sharma, MD"
    })
    assert res_signoff.status_code == 200
    print("[PASS] 5. Clinician Human-In-The-Loop Sign-off & Patient Record Update")

    # 5. Admin Dashboard & Simulink
    res_admin = client.get("/api/admin/dashboard")
    assert res_admin.status_code == 200
    print("[PASS] 6. Admin Telemedicine Analytics Dashboard")

    res_sim = client.post("/api/simulink/simulate", json={"annual_patients": 100000})
    assert res_sim.status_code == 200
    print("[PASS] 7. Simulink Telemedicine District Screening Model")

    print("\nSUCCESS: ALL MULTI-ROLE FULLSTACK BACKEND TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_fullstack()
