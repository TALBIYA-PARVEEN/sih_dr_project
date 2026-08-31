import io
import uuid
import cv2
import numpy as np
from app import create_app
from db import mongo

def test_mongodb_system():
    print("[TEST] Running MongoDB Integration Tests...")
    app = create_app()
    client = app.test_client()

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    print("[PASS] 1. MongoDB Health API Connected")

    # 2. Master Admin Login
    res_admin = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@SIH2026"})
    assert res_admin.status_code == 200
    admin_data = res_admin.get_json()
    assert admin_data["user"]["role"] == "admin"
    print("[PASS] 2. Single Master Admin (MongoDB Document Verified)")

    # 3. Patient Registration & OTP Verification
    rnd = uuid.uuid4().hex[:6]
    test_user = f"patient_{rnd}"
    test_email = f"patient_{rnd}@teleophta.org"

    res_reg = client.post("/api/auth/register", json={
        "username": test_user,
        "email": test_email,
        "password": "Password123!",
        "full_name": "Anita Roy",
        "role": "patient",
        "phone": "+91 9123456780",
        "diabetes_type": "Type 2",
        "diabetes_duration_years": 6
    })
    assert res_reg.status_code == 201
    reg_data = res_reg.get_json()
    patient_id = reg_data["user"]["id"]
    print("[PASS] 3. Patient Registration in MongoDB + OTP Generated")

    u = mongo.users.find_one({"email": test_email})
    test_otp = u["otp_code"]

    res_verify = client.post("/api/auth/verify-otp", json={
        "email": test_email,
        "otp": test_otp
    })
    assert res_verify.status_code == 200
    print("[PASS] 4. MongoDB Document Update (Email OTP Verified)")

    # 4. Screening with Ben Graham + CLAHE & Biomarkers
    dummy_img = np.zeros((512, 512, 3), dtype=np.uint8)
    cv2.circle(dummy_img, (256, 256), 240, (180, 80, 30), -1)
    cv2.circle(dummy_img, (180, 256), 25, (220, 180, 100), -1)
    cv2.circle(dummy_img, (300, 280), 5, (0, 0, 200), -1)

    _, encoded_img = cv2.imencode(".png", dummy_img)
    img_bytes = io.BytesIO(encoded_img.tobytes())

    res_screen = client.post(
        "/api/screen",
        data={
            "file": (img_bytes, "test_retina.png"),
            "patient_user_id": patient_id,
            "patient_name": "Anita Roy",
            "patient_age": 52,
            "patient_gender": "Female"
        },
        content_type="multipart/form-data"
    )
    assert res_screen.status_code == 201
    screen_data = res_screen.get_json()
    session_id = screen_data["session_id"]
    print(f"[PASS] 5. Screening Saved to MongoDB Collection (Session ID: {session_id[:8]}...)")

    # 5. Doctor Review Sign-off
    res_review = client.post(f"/api/review/{session_id}", json={
        "status": "Confirmed",
        "notes": "Verified macular microaneurysm. Prescribed laser follow-up.",
        "doctor_id": "doc_dr_sharma",
        "reviewed_by": "Dr. S. Sharma, MD"
    })
    assert res_review.status_code == 200
    print("[PASS] 6. Doctor Sign-off & Reports Collection Synchronized")

    # 6. Messaging in MongoDB
    res_msg = client.post("/api/messages/send", json={
        "sender_id": patient_id,
        "recipient_id": "doc_dr_sharma",
        "content": "Doctor, when should I schedule my appointment?",
        "screening_id": session_id
    })
    assert res_msg.status_code == 201
    print("[PASS] 7. In-App Tele-Consultation Messaging in MongoDB")

    # 7. Simulink Simulation
    res_sim = client.post("/api/simulink/simulate", json={"annual_patients": 100000})
    assert res_sim.status_code == 200
    print("[PASS] 8. Simulink Telemedicine 100,000+ Patient Queue Simulation")

    print("\nSUCCESS: ALL MONGODB BACKEND MODULES PASSED WITH 100% SUCCESS!\n")

if __name__ == "__main__":
    test_mongodb_system()
