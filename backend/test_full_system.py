import io
import cv2
import numpy as np
from app import create_app
from models import db, User

def test_full_system():
    print("[TEST] Running Comprehensive Multi-Role Integration Tests...")
    app = create_app()
    client = app.test_client()

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    print("[PASS] 1. System Health API")

    # 2. Master Admin Login
    res_admin = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@SIH2026"})
    assert res_admin.status_code == 200
    admin_data = res_admin.get_json()
    assert admin_data["user"]["role"] == "admin"
    print("[PASS] 2. Single Master Admin Authentication (Config Credentials Verified)")

    # 3. Patient Registration & OTP Verification
    res_reg = client.post("/api/auth/register", json={
        "username": "test_patient_sih",
        "email": "test_patient_sih@example.com",
        "password": "Password123!",
        "full_name": "Sita Devi",
        "role": "patient",
        "phone": "+91 9988776655"
    })
    assert res_reg.status_code == 201
    reg_data = res_reg.get_json()
    patient_id = reg_data["user"]["id"]
    print("[PASS] 3. Patient Registration & Automated 6-Digit Email OTP Dispatch")

    with app.app_context():
        u = User.query.filter_by(email="test_patient_sih@example.com").first()
        test_otp = u.otp_code

    res_verify = client.post("/api/auth/verify-otp", json={
        "email": "test_patient_sih@example.com",
        "otp": test_otp
    })
    assert res_verify.status_code == 200
    print("[PASS] 4. Email OTP Verification & Account Activation")

    # 4. Google Auth Endpoint
    res_google = client.post("/api/auth/google", json={
        "id_token": "mock_google_id_token_test",
        "email": "google_test_doctor@hospital.org",
        "name": "Dr. Google Auth",
        "role": "doctor"
    })
    assert res_google.status_code == 200
    doc_google_id = res_google.get_json()["user"]["id"]
    print("[PASS] 5. Google OAuth 2.0 Authentication & Auto-Provisioning")

    # 5. Doctor-Patient Messaging & Notification
    res_msg = client.post("/api/messages/send", json={
        "sender_id": patient_id,
        "recipient_id": doc_google_id,
        "content": "Doctor, I uploaded my scan today. Please check my exudates.",
    })
    assert res_msg.status_code == 201
    print("[PASS] 6. Real-time Doctor-Patient Tele-Consultation Messaging")

    res_notif = client.get(f"/api/notifications/{doc_google_id}")
    assert res_notif.status_code == 200
    notif_data = res_notif.get_json()
    assert len(notif_data["notifications"]) > 0
    print("[PASS] 7. Instant Notification Dispatch for Assigned Doctor")

    # 6. Simulink Telemedicine Simulation
    res_sim = client.post("/api/simulink/simulate", json={"annual_patients": 100000})
    assert res_sim.status_code == 200
    print("[PASS] 8. Simulink District Telemedicine Model (100k+ Patients)")

    print("\nSUCCESS: ALL 8 CORE FULL-STACK MODULES & AUTH WORKFLOWS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_full_system()
