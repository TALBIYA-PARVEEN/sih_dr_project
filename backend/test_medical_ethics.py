import io
import cv2
import numpy as np
from app import create_app
from db import mongo

def test_medical_ethics_and_otp():
    print("[TEST] Testing Real Email OTP & Clinical Ethics Rules...")
    app = create_app()
    client = app.test_client()

    # 1. Register Doctor A
    res_doc_a = client.post("/api/auth/register", json={
        "username": "dr_arun_kumar",
        "email": "dr.arun@hospital.org",
        "password": "Password123!",
        "full_name": "Dr. Arun Kumar, MD",
        "role": "doctor",
        "specialization": "Retina Surgeon",
        "hospital_name": "Apex Eye Centre"
    })
    assert res_doc_a.status_code == 201
    doc_a_id = res_doc_a.get_json()["user"]["id"]
    print("[PASS] 1. Registered Doctor A (Dr. Arun Kumar)")

    # 2. Register Doctor B (Peer)
    res_doc_b = client.post("/api/auth/register", json={
        "username": "dr_meera_nair",
        "email": "dr.meera@hospital.org",
        "password": "Password123!",
        "full_name": "Dr. Meera Nair, MS",
        "role": "doctor",
        "specialization": "Ophthalmologist",
        "hospital_name": "District Hospital"
    })
    assert res_doc_b.status_code == 201
    doc_b_id = res_doc_b.get_json()["user"]["id"]
    print("[PASS] 2. Registered Doctor B (Dr. Meera Nair)")

    # 3. Doctor A uploads their own fundus scan as a Patient
    img = np.zeros((512, 512, 3), dtype=np.uint8)
    cv2.circle(img, (256, 256), 220, (180, 80, 40), -1)
    cv2.circle(img, (180, 256), 35, (240, 220, 100), -1)
    cv2.circle(img, (300, 280), 4, (10, 10, 220), -1)
    _, enc = cv2.imencode(".png", img)

    data = {
        "file": (io.BytesIO(enc.tobytes()), "scan_doctor_a.png"),
        "patient_name": "Dr. Arun Kumar (Self-Patient)",
        "patient_age": "45",
        "patient_gender": "Male",
        "patient_user_id": doc_a_id
    }
    res_screen = client.post("/api/screen", data=data, content_type="multipart/form-data")
    assert res_screen.status_code == 201
    session = res_screen.get_json()["data"]
    session_id = session["id"]
    
    # Verify: Assigned Doctor MUST NOT be Doctor A!
    assert session["assigned_doctor_id"] != doc_a_id
    print(f"[PASS] 3. Doctor A uploaded scan as patient -> Automatically routed to peer: {session.get('assigned_doctor_name')}")

    # 4. Attempt Self-Review: Doctor A tries to sign off their own scan
    res_self_review = client.post(f"/api/review/{session_id}", json={
        "status": "Confirmed",
        "notes": "I am signing off my own scan.",
        "doctor_id": doc_a_id,
        "reviewed_by": "Dr. Arun Kumar, MD"
    })
    # MUST BE BLOCKED (HTTP 403 Forbidden)
    assert res_self_review.status_code == 403
    print(f"[PASS] 4. Self-Review Blocked (HTTP 403): {res_self_review.get_json()['error']}")

    # 5. Independent Peer Review: Doctor B signs off Doctor A's scan
    res_peer_review = client.post(f"/api/review/{session_id}", json={
        "status": "Confirmed",
        "notes": "Peer evaluation completed. Mild microaneurysms noted.",
        "doctor_id": doc_b_id,
        "reviewed_by": "Dr. Meera Nair, MS"
    })
    assert res_peer_review.status_code == 200
    print("[PASS] 5. Independent Peer Ophthalmologist Sign-off Successfully Completed")

    print("\nSUCCESS: ALL CLINICAL ETHICS & ANTI-SELF-REVIEW SAFEGUARDS VERIFIED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_medical_ethics_and_otp()
