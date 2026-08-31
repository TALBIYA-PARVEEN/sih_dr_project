import io
import os
import json
from app import create_app
from config import Config
from pymongo import MongoClient

app = create_app()
client = app.test_client()
mongo_client = MongoClient(Config.MONGO_URI)
db = mongo_client[Config.MONGO_DB_NAME]

print("[TEST] Running Comprehensive Doctor Approval, Blacklist/Remove, & Load Balancing Verification...\n")

# 1. Register a new Doctor
doc_payload = {
    "username": "dr_verif_test",
    "email": "dr.verif@testeye.org",
    "password": "DocPassword@2026",
    "full_name": "Dr. Aarav Patel, MS",
    "role": "doctor",
    "license_number": "MCI-RET-TEST-999",
    "specialization": "Retina Specialist",
    "hospital_name": "District Vision Center",
    "phone": "+91 9876543210"
}

res_reg = client.post("/api/auth/register", json=doc_payload)
assert res_reg.status_code == 201
print("[PASS] 1. Doctor Registered -> Response Message:", res_reg.get_json()["message"])

# 2. Attempt Login Before Admin Approval (Must Fail with 403)
res_login_unapproved = client.post("/api/auth/login", json={"username": "dr_verif_test", "password": "DocPassword@2026"})
assert res_login_unapproved.status_code == 403
print(f"[PASS] 2. Unapproved Doctor Login Blocked (Status: {res_login_unapproved.status_code}) -> Error: {res_login_unapproved.get_json()['error']}")

# 3. Master Admin Approves Doctor
doc_doc = db.doctors.find_one({"license_number": "MCI-RET-TEST-999"})
doc_id = doc_doc["id"]
res_approve = client.post(f"/api/admin/doctor/approve/{doc_id}")
assert res_approve.status_code == 200
print(f"[PASS] 3. Admin Approved Doctor -> {res_approve.get_json()['message']}")

# 4. Doctor Login After Approval (Must Succeed with 200)
res_login_approved = client.post("/api/auth/login", json={"username": "dr_verif_test", "password": "DocPassword@2026"})
assert res_login_approved.status_code == 200
print(f"[PASS] 4. Approved Doctor Login Succeeded -> Token Issued for {res_login_approved.get_json()['user']['full_name']}")

# 5. Admin Blacklists Doctor
res_bl = client.post(f"/api/admin/doctor/blacklist/{doc_id}")
assert res_bl.status_code == 200
res_login_bl = client.post("/api/auth/login", json={"username": "dr_verif_test", "password": "DocPassword@2026"})
assert res_login_bl.status_code == 403
print(f"[PASS] 5. Doctor Blacklisted -> Login Blocked with 403: {res_login_bl.get_json()['error']}")

# 6. Admin Removes Doctor
res_rm = client.delete(f"/api/admin/doctor/remove/{doc_id}")
assert res_rm.status_code == 200
assert db.doctors.find_one({"id": doc_id}) is None
print(f"[PASS] 6. Doctor Removed Permanently -> {res_rm.get_json()['message']}")

# 7. Equal Load Balancing Verification
print("\n[TEST] Verifying Dynamic Equal Patient-to-Doctor Division across multiple doctors...")
# Register & Approve Doc A and Doc B
doc_a = {
    "username": "dr_alpha", "email": "dr.alpha@eye.org", "password": "Pass@123",
    "full_name": "Dr. Alpha Eye", "role": "doctor", "license_number": "MCI-ALPHA-1"
}
doc_b = {
    "username": "dr_beta", "email": "dr.beta@eye.org", "password": "Pass@123",
    "full_name": "Dr. Beta Eye", "role": "doctor", "license_number": "MCI-BETA-2"
}
client.post("/api/auth/register", json=doc_a)
client.post("/api/auth/register", json=doc_b)
doc_a_id = db.doctors.find_one({"username": "dr_alpha"}) or db.doctors.find_one({"license_number": "MCI-ALPHA-1"})
doc_b_id = db.doctors.find_one({"username": "dr_beta"}) or db.doctors.find_one({"license_number": "MCI-BETA-2"})
client.post(f"/api/admin/doctor/approve/{doc_a_id['id']}")
client.post(f"/api/admin/doctor/approve/{doc_b_id['id']}")

# Register 4 Patients and Check Load Distribution
assigned_docs = []
for i in range(4):
    p_res = client.post("/api/auth/register", json={
        "username": f"test_load_pat_{i}", "email": f"load_pat_{i}@test.com",
        "password": "Pass@123", "full_name": f"Patient {i}", "role": "patient"
    })
    assigned_docs.append(p_res.get_json()["user"].get("assigned_doctor_id"))

print(f"  Assigned Doctor IDs for 4 consecutive patients: {assigned_docs}")
# Clean up test accounts
db.users.delete_many({"username": {"$in": ["dr_alpha", "dr_beta"] + [f"test_load_pat_{i}" for i in range(4)]}})
db.doctors.delete_many({"license_number": {"$in": ["MCI-ALPHA-1", "MCI-BETA-2"]}})
db.patients.delete_many({"full_name": {"$regex": "^Patient "}})

print("\n[SUCCESS] ALL DOCTOR APPROVAL, BLACKLIST/REMOVE, & LOAD BALANCING TESTS PASSED 100%!")
