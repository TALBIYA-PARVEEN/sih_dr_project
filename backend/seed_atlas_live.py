import uuid
from datetime import datetime
from pymongo import MongoClient

uri = "mongodb+srv://2k24cs1q2413756_db_user:NetraAI2026@cluster0.orlzz77.mongodb.net/NetraAI-db?retryWrites=true&w=majority&appName=Cluster0"

print("[TEST] Connecting to MongoDB Atlas Cluster0 with NetraAI2026...")
try:
    import certifi
    client = MongoClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=8000)
    client.admin.command('ping')
    print("[SUCCESS] CONNECTED TO MONGODB ATLAS CLOUD!")
    
    db = client["NetraAI-db"]
    print("Database:", db.name)
    
    # 1. Seed 'users' collection
    admin_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    pat_id = str(uuid.uuid4())
    
    db.users.update_one(
        {"username": "admin"},
        {"$set": {
            "id": admin_id,
            "username": "admin",
            "email": "admin@teleophta.org",
            "full_name": "Master District Admin",
            "role": "admin",
            "is_email_verified": True,
            "created_at": datetime.utcnow().isoformat()
        }},
        upsert=True
    )
    
    db.users.update_one(
        {"username": "doctor_sharma"},
        {"$set": {
            "id": doc_id,
            "username": "doctor_sharma",
            "email": "dr.sharma@teleophta.org",
            "full_name": "Dr. S. Sharma, MD",
            "role": "doctor",
            "is_email_verified": True,
            "created_at": datetime.utcnow().isoformat()
        }},
        upsert=True
    )
    
    db.users.update_one(
        {"username": "patient_ramesh"},
        {"$set": {
            "id": pat_id,
            "username": "patient_ramesh",
            "email": "ramesh.kumar@gmail.com",
            "full_name": "Ramesh Kumar",
            "role": "patient",
            "is_email_verified": True,
            "created_at": datetime.utcnow().isoformat()
        }},
        upsert=True
    )
    
    # 2. Seed 'admins' collection
    db.admins.update_one(
        {"user_id": admin_id},
        {"$set": {
            "id": str(uuid.uuid4()),
            "user_id": admin_id,
            "full_name": "Master District Admin",
            "email": "admin@teleophta.org",
            "district_jurisdiction": "National District Level",
            "telemetry_access_level": "SuperAdmin",
            "created_at": datetime.utcnow().isoformat()
        }},
        upsert=True
    )
    
    # 3. Seed 'doctors' collection
    db.doctors.update_one(
        {"user_id": doc_id},
        {"$set": {
            "id": str(uuid.uuid4()),
            "user_id": doc_id,
            "full_name": "Dr. S. Sharma, MD",
            "specialization": "Senior Vitreo-Retina Specialist",
            "hospital_name": "District Eye Hospital",
            "license_number": "MCI-RET-2026-889",
            "phone": "+91 9123456780",
            "active_status": True,
            "created_at": datetime.utcnow().isoformat()
        }},
        upsert=True
    )
    
    # 4. Seed 'patients' collection
    db.patients.update_one(
        {"user_id": pat_id},
        {"$set": {
            "id": str(uuid.uuid4()),
            "user_id": pat_id,
            "full_name": "Ramesh Kumar",
            "age": 54,
            "gender": "Male",
            "phone": "+91 9876543210",
            "assigned_doctor_id": doc_id,
            "total_screenings": 1,
            "created_at": datetime.utcnow().isoformat()
        }},
        upsert=True
    )
    
    # 5. Seed 'screenings' collection
    scr_id = str(uuid.uuid4())
    db.screenings.update_one(
        {"id": scr_id},
        {"$set": {
            "id": scr_id,
            "patient_user_id": pat_id,
            "patient_name": "Ramesh Kumar",
            "patient_age": 54,
            "patient_gender": "Male",
            "assigned_doctor_id": doc_id,
            "quality_assessment": {
                "quality_label": "GOOD",
                "quality_score": 95,
                "is_gradable": True
            },
            "prediction": {
                "severity_level": 2,
                "severity_name": "Moderate NPDR (Grade 2)",
                "confidence": 0.938,
                "is_referable": True,
                "triage_action": "Ophthalmologist Referral within 4-6 Weeks"
            },
            "review_status": "Confirmed",
            "created_at": datetime.utcnow().isoformat()
        }},
        upsert=True
    )
    
    # 6. Seed 'reports' collection (Directly authored/signed by Doctor)
    rep_id = str(uuid.uuid4())
    db.reports.update_one(
        {"screening_id": scr_id},
        {"$set": {
            "id": rep_id,
            "screening_id": scr_id,
            "patient_user_id": pat_id,
            "patient_name": "Ramesh Kumar",
            "patient_age": 54,
            "patient_gender": "Male",
            "doctor_id": doc_id,
            "doctor_name": "Dr. S. Sharma, MD",
            "severity_grade": 2,
            "severity_name": "Moderate NPDR (Grade 2)",
            "confidence_pct": 93.8,
            "is_referable": True,
            "triage_action": "Ophthalmologist Referral within 4-6 Weeks",
            "clinical_status": "Confirmed",
            "doctor_notes": "Verified macular hard exudates. Routine laser photocoagulation advised.",
            "pdf_report_url": f"/api/report/{scr_id}/pdf",
            "signed_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }},
        upsert=True
    )
    
    # 7. Seed 'messages' collection
    db.messages.insert_one({
        "id": str(uuid.uuid4()),
        "sender_id": doc_id,
        "sender_name": "Dr. S. Sharma, MD",
        "sender_role": "doctor",
        "recipient_id": pat_id,
        "recipient_name": "Ramesh Kumar",
        "screening_id": scr_id,
        "content": "Hello Ramesh, I have reviewed your retinal scan. Please schedule a follow-up visit.",
        "is_read": False,
        "created_at": datetime.utcnow().isoformat()
    })
    
    print("\n[VERIFIED] ALL COLLECTIONS ACTIVELY CREATED IN MONGODB ATLAS:")
    for col in sorted(db.list_collection_names()):
        count = db[col].count_documents({})
        print(f"  📁 Collection '{col}': {count} documents")

except Exception as e:
    print(f"[ERROR] {e}")
