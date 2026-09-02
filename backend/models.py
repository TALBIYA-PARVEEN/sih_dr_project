import uuid
from datetime import datetime

class UserModel:
    """Base authentication credentials and authorization roles."""
    @staticmethod
    def create(username, email, password_hash, full_name, role, is_email_verified=False, otp_code=None):
        role_clean = role.strip().lower()
        # Doctor accounts start as pending_approval until approved by Admin
        initial_status = "pending_approval" if role_clean == "doctor" else "active"
        return {
            "id": str(uuid.uuid4()),
            "username": username.strip(),
            "email": email.strip().lower(),
            "password_hash": password_hash,
            "full_name": full_name.strip(),
            "role": role_clean,  # "patient" | "doctor" | "admin"
            "status": initial_status,  # "active" | "pending_approval" | "blacklisted"
            "is_email_verified": is_email_verified,
            "otp_code": otp_code,
            "otp_expiry": None,
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None
        }

class PatientModel:
    """Clinical demographics and health profile for patients."""
    @staticmethod
    def create(user_id, full_name, age, gender, phone="", diabetes_type="Type 2", diabetes_duration_years=5, assigned_doctor_id=None, address_district="District Rural PHC"):
        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "full_name": full_name.strip(),
            "age": int(age),
            "gender": gender,  # "Female" | "Male" | "Other"
            "phone": phone.strip(),
            "diabetes_type": diabetes_type,  # "Type 2" | "Type 1" | "Gestational" | "Pre-diabetic"
            "diabetes_duration_years": int(diabetes_duration_years),
            "assigned_doctor_id": assigned_doctor_id,
            "address_district": address_district,
            "status": "active",  # "active" | "blacklisted"
            "active_status": True,
            "total_screenings": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

class DoctorModel:
    """Professional clinical credentials and hospital affiliation for ophthalmologists."""
    @staticmethod
    def create(user_id, full_name, specialization, license_number, hospital_name, qualifications="MBBS, MS (Ophthalmology)", email="", phone="", consultation_hours="09:00 - 17:00 IST"):
        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "full_name": full_name.strip(),
            "specialization": specialization.strip() or "Senior Vitreo-Retina Specialist",
            "license_number": license_number.strip() or f"MCI-{uuid.uuid4().hex[:6].upper()}",
            "qualifications": qualifications.strip(),
            "hospital_name": hospital_name.strip() or "District Eye Hospital",
            "email": email.strip().lower() if email else "",
            "phone": phone.strip(),
            "consultation_hours": consultation_hours,
            "rating": 0.0,
            "review_count": 0,
            "approval_status": "pending_approval",  # "pending_approval" | "approved" | "blacklisted"
            "active_status": False,  # False until Master Admin approves
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

class DoctorReviewModel:
    """Patient clinical review, star rating, and feedback for an ophthalmologist."""
    @staticmethod
    def create(doctor_id, patient_id, patient_name, rating, comment="", screening_id=None):
        return {
            "id": str(uuid.uuid4()),
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "patient_name": patient_name.strip(),
            "rating": max(1, min(5, int(rating))),
            "comment": comment.strip(),
            "screening_id": screening_id,
            "created_at": datetime.utcnow().isoformat()
        }

class AdminModel:
    """District-wide administrator authority profile."""
    @staticmethod
    def create(user_id, full_name, email, district_jurisdiction="National Tele-Ophthalmology Network"):
        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "full_name": full_name.strip(),
            "email": email.strip().lower(),
            "district_jurisdiction": district_jurisdiction,
            "telemetry_access_level": "SuperAdmin",
            "created_at": datetime.utcnow().isoformat()
        }

class ScreeningModel:
    """Fundus image screening session, IQA checks, image paths, and AI predictions."""
    @staticmethod
    def create(patient_id, patient_user_id, patient_meta, assigned_doctor_id, image_path, original_filename, quality_assessment, ai_prediction=None, biomarkers=None, processed_paths=None):
        return {
            "id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "patient_user_id": patient_user_id,
            "patient_name": patient_meta.get("full_name", "Anonymous"),
            "patient_age": patient_meta.get("age", 50),
            "patient_gender": patient_meta.get("gender", "Female"),
            "assigned_doctor_id": assigned_doctor_id,
            "original_filename": original_filename,
            "image_path": image_path,
            "processed_image_path": (processed_paths or {}).get("processed"),
            "lesions_image_path": (processed_paths or {}).get("lesions"),
            "vessels_image_path": (processed_paths or {}).get("vessels"),
            "gradcam_image_path": (processed_paths or {}).get("gradcam"),
            "quality_assessment": quality_assessment,
            "is_gradable": quality_assessment.get("is_gradable", False),
            "ai_prediction": ai_prediction or {},
            "biomarkers": biomarkers or {},
            "created_at": datetime.utcnow().isoformat()
        }

class ReportModel:
    """Official EMR diagnostic report evaluated, authored, and signed off by the Doctor."""
    @staticmethod
    def create(screening_id, patient_doc, doctor_doc, ai_prediction, quality_status, pdf_report_url):
        return {
            "id": str(uuid.uuid4()),
            "screening_id": screening_id,
            
            # Patient Details Snapshot
            "patient_id": patient_doc.get("id"),
            "patient_user_id": patient_doc.get("user_id"),
            "patient_name": patient_doc.get("full_name"),
            "patient_age": patient_doc.get("age"),
            "patient_gender": patient_doc.get("gender"),
            "patient_phone": patient_doc.get("phone"),
            "diabetes_info": f"{patient_doc.get('diabetes_type', 'Type 2')} ({patient_doc.get('diabetes_duration_years', 5)} yrs)",
            
            # Doctor Credentials Snapshot
            "doctor_id": doctor_doc.get("id"),
            "doctor_user_id": doctor_doc.get("user_id"),
            "doctor_name": doctor_doc.get("full_name"),
            "doctor_specialization": doctor_doc.get("specialization"),
            "doctor_license_number": doctor_doc.get("license_number"),
            "doctor_hospital": doctor_doc.get("hospital_name"),
            
            # Clinical Findings & AI Evidence
            "final_severity_grade": ai_prediction.get("severity_level", 0),
            "final_severity_name": ai_prediction.get("severity_name", "No DR"),
            "confidence_pct": round(ai_prediction.get("confidence", 0.95) * 100, 1),
            "is_referable": ai_prediction.get("is_referable", False),
            "triage_action": ai_prediction.get("triage_action", "Routine Follow-Up"),
            "quality_status": quality_status,
            
            # Clinical Review & Directives
            "clinical_status": "Pending Review",  # "Pending Review" | "Confirmed" | "Overruled" | "Needs Recapture"
            "doctor_notes": "Pending clinical validation by ophthalmologist.",
            "pdf_report_url": pdf_report_url,
            "signed_at": None,
            "created_at": datetime.utcnow().isoformat()
        }

class MessageModel:
    """In-app tele-consultation dialogue between Patient and Doctor."""
    @staticmethod
    def create(sender_id, sender_name, sender_role, recipient_id, recipient_name, content, screening_id=None):
        return {
            "id": str(uuid.uuid4()),
            "sender_id": sender_id,
            "sender_name": sender_name,
            "sender_role": sender_role,
            "recipient_id": recipient_id,
            "recipient_name": recipient_name,
            "screening_id": screening_id,
            "content": content.strip(),
            "is_read": False,
            "created_at": datetime.utcnow().isoformat()
        }
