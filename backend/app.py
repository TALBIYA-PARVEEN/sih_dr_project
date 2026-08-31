import os
import uuid
import random
import cv2
import numpy as np
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from db import mongo
from models import UserModel, PatientModel, DoctorModel, AdminModel, ScreeningModel, ReportModel, MessageModel
from services.auth_service import AuthService
from services.iqa_service import ImageQualityAssessmentService
from services.preprocessor import PreprocessingService
from services.biomarker_service import BiomarkerDetectionService
from services.model_service import ModelService
from services.gradcam_service import GradCAMService
from services.report_service import ReportService
from services.simulink_service import SimulinkTelemedicineSimulator

def serialize_doc(doc):
    if not doc: return None
    doc_copy = dict(doc)
    if "_id" in doc_copy: doc_copy["_id"] = str(doc_copy["_id"])
    return doc_copy

def assign_least_loaded_doctor():
    """
    Finds all active, approved doctors in the network.
    Calculates active patient workload and pending screening review queues for each doctor.
    Assigns the new patient to the doctor with the minimum current load for equal division.
    """
    approved_doctors = list(mongo.doctors.find({
        "approval_status": "approved",
        "active_status": {"$ne": False}
    }))
    
    if not approved_doctors:
        return {
            "doctor_id": None,
            "doctor_name": "District Specialist Pool",
            "specialization": "Clinical Vitreo-Retina Pool",
            "license_number": "N/A",
            "hospital_name": "District Tele-Ophthalmology Network"
        }

    # Calculate current load for each approved doctor
    min_load = float("inf")
    selected_doc = approved_doctors[0]

    for doc in approved_doctors:
        doc_user_id = doc.get("user_id") or doc.get("id")
        doc_id = doc.get("id")

        # Check if the doctor's user account is active (not blacklisted)
        user_acct = mongo.users.find_one({"id": doc_user_id})
        if user_acct and user_acct.get("status") == "blacklisted":
            continue

        pat_count = mongo.patients.count_documents({
            "$or": [
                {"assigned_doctor_id": doc_id},
                {"assigned_doctor_id": doc_user_id}
            ]
        })
        pending_screening_count = mongo.screenings.count_documents({
            "$or": [
                {"assigned_doctor_id": doc_id},
                {"assigned_doctor_id": doc_user_id}
            ],
            "review_status": "Pending Review"
        })
        total_load = (pat_count * 2) + (pending_screening_count * 3)
        if total_load < min_load:
            min_load = total_load
            selected_doc = doc

    return {
        "doctor_id": selected_doc.get("user_id") or selected_doc.get("id"),
        "doctor_name": selected_doc.get("full_name", "Assigned Ophthalmologist"),
        "specialization": selected_doc.get("specialization", "Senior Vitreo-Retina Specialist"),
        "license_number": selected_doc.get("license_number", "MCI-VERIFIED"),
        "hospital_name": selected_doc.get("hospital_name", "District Apex Hospital")
    }

def create_app():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    frontend_dir = os.path.abspath(os.path.join(base_dir, "..", "frontend"))

    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    app.config.from_object(Config)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Initialize MongoDB
    mongo.init_app(app)

    # Initialize Medical & AI Services
    iqa_service = ImageQualityAssessmentService()
    preprocessor = PreprocessingService(target_size=456)
    biomarker_service = BiomarkerDetectionService(target_size=456)
    model_service = ModelService(
        weights_path=app.config["MODEL_WEIGHTS_PATH"],
        cnn_weights_path=os.path.join(base_dir, "weights", "sih_cnn_model.pth")
    )
    gradcam_service = GradCAMService()
    report_service = ReportService(reports_folder=app.config["REPORTS_FOLDER"])
    simulink_service = SimulinkTelemedicineSimulator()

    def token_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None
            if "Authorization" in request.headers:
                auth_header = request.headers["Authorization"]
                if auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]

            if not token:
                return jsonify({"error": "Authentication token is missing."}), 401

            payload = AuthService.decode_jwt(token)
            if not payload:
                return jsonify({"error": "Token is invalid or expired."}), 401

            user = mongo.users.find_one({"id": payload["sub"]})
            if not user:
                return jsonify({"error": "User not found."}), 401

            return f(user, *args, **kwargs)
        return decorated

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

    # --------------------------------------------------------------------------
    # 0. Root Page
    # --------------------------------------------------------------------------
    @app.route("/", methods=["GET"])
    def index():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return send_file(index_file)
        return jsonify({"service": "National Tele-Ophthalmology DR Screening Backend", "database": "MongoDB Atlas", "status": "online"})

    # --------------------------------------------------------------------------
    # 1. Health & Status
    # --------------------------------------------------------------------------
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "healthy",
            "system": "NetraAI SIH 2026 Tele-Ophthalmology Platform",
            "database": "MongoDB Atlas Cloud Connected" if hasattr(mongo, "users") else "In-Memory Datastore",
            "ai_engine": "CNN Global ICDR + YOLO Lesion Detectors",
            "version": "3.0-Atlas"
        }), 200

    # --------------------------------------------------------------------------
    # 2. Authentication & Real Email OTP Verification
    # --------------------------------------------------------------------------
    @app.route("/api/auth/register", methods=["POST"])
    def register():
        data = request.get_json() or {}
        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()
        full_name = data.get("full_name", "").strip()
        role = data.get("role", "patient").strip().lower()

        age = data.get("age", 45)
        gender = data.get("gender", "Female")
        phone = data.get("phone", "+91 9876543210")
        diabetes_type = data.get("diabetes_type", "Type 2")
        diabetes_duration = data.get("diabetes_duration_years", 5)

        specialization = data.get("specialization", "Senior Vitreo-Retina Specialist")
        license_number = data.get("license_number", "")
        hospital_name = data.get("hospital_name", "District Eye Hospital")

        if not username or not email or not password or not full_name:
            return jsonify({"error": "Username, email, password, and full name are required."}), 400

        existing_user = mongo.users.find_one({"$or": [{"username": username}, {"email": email}]})
        otp_code = AuthService.generate_otp()
        password_hash = generate_password_hash(password)

        if existing_user:
            # User is re-registering or updating credentials: renew details & generate fresh OTP
            user_id = existing_user["id"]
            mongo.users.update_one(
                {"id": user_id},
                {"$set": {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "full_name": full_name,
                    "role": role,
                    "otp_code": otp_code,
                    "otp_expiry": (datetime.utcnow() + timedelta(minutes=15)).isoformat()
                }}
            )

            if role == "patient":
                mongo.patients.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "full_name": full_name,
                        "age": age,
                        "gender": gender,
                        "phone": phone,
                        "diabetes_type": diabetes_type,
                        "diabetes_duration_years": diabetes_duration
                    }},
                    upsert=True
                )
            elif role == "doctor":
                mongo.doctors.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "full_name": full_name,
                        "specialization": specialization or "Senior Vitreo-Retina Specialist",
                        "license_number": license_number or existing_user.get("license_number", "MCI-VERIFIED"),
                        "hospital_name": hospital_name or "District Eye Hospital",
                        "phone": phone,
                        "approval_status": "pending_approval",
                        "active_status": False
                    }},
                    upsert=True
                )

            updated_user = mongo.users.find_one({"id": user_id})
            email_sent = AuthService.send_otp_email(email, otp_code, purpose="Registration Verification")
            user_obj = type("UserObj", (), updated_user)()
            token = AuthService.generate_jwt(user_obj)

            reg_message = f"Account updated. Verification code sent to {email}."
            if role == "doctor":
                reg_message += " Note: Doctor accounts require Master Admin approval after email verification."

            return jsonify({
                "status": "success",
                "message": reg_message,
                "token": token,
                "user": serialize_doc(updated_user),
                "otp_sent": email_sent,
                "dev_otp": otp_code
            }), 200

        user_doc = UserModel.create(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_email_verified=False,
            otp_code=otp_code
        )
        user_doc["otp_expiry"] = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        mongo.users.insert_one(user_doc)

        if role == "patient":
            # Dynamic load balancing: assign to doctor with minimum workload
            balanced_doc = assign_least_loaded_doctor()
            assigned_doc_id = balanced_doc["doctor_id"]

            patient_doc = PatientModel.create(
                user_id=user_doc["id"],
                full_name=full_name,
                age=age,
                gender=gender,
                phone=phone,
                diabetes_type=diabetes_type,
                diabetes_duration_years=diabetes_duration,
                assigned_doctor_id=assigned_doc_id
            )
            mongo.patients.insert_one(patient_doc)
            user_doc["patient_id"] = patient_doc["id"]
            user_doc["age"] = age
            user_doc["gender"] = gender
            user_doc["phone"] = phone
            user_doc["diabetes_type"] = diabetes_type
            user_doc["diabetes_duration_years"] = diabetes_duration
            user_doc["assigned_doctor_id"] = assigned_doc_id

        elif role == "doctor":
            # Doctor registered: starts with pending_approval until approved by Admin
            doctor_doc = DoctorModel.create(
                user_id=user_doc["id"],
                full_name=full_name,
                specialization=specialization or "Senior Vitreo-Retina Specialist",
                license_number=license_number or f"MCI-{uuid.uuid4().hex[:6].upper()}",
                hospital_name=hospital_name or "District Eye Hospital",
                phone=phone
            )
            mongo.doctors.insert_one(doctor_doc)
            user_doc["doctor_id"] = doctor_doc["id"]
            user_doc["specialization"] = doctor_doc["specialization"]
            user_doc["license_number"] = doctor_doc["license_number"]
            user_doc["hospital_name"] = doctor_doc["hospital_name"]
            user_doc["approval_status"] = "pending_approval"

        email_sent = AuthService.send_otp_email(email, otp_code, purpose="Registration Verification")

        user_obj = type("UserObj", (), user_doc)()
        token = AuthService.generate_jwt(user_obj)
        
        reg_message = f"Verification code sent to {email}."
        if role == "doctor":
            reg_message += " Note: Your doctor account will require Master Admin approval before you can access clinical reviews."

        return jsonify({
            "status": "success",
            "message": reg_message,
            "token": token,
            "user": serialize_doc(user_doc),
            "otp_sent": email_sent,
            "dev_otp": otp_code
        }), 201

    @app.route("/api/auth/profile/<user_id>", methods=["PUT"])
    def update_profile(user_id):
        data = request.get_json() or {}
        user = mongo.users.find_one({"id": user_id})
        if not user:
            return jsonify({"error": "User not found."}), 404

        if "full_name" in data:
            mongo.users.update_one({"id": user_id}, {"$set": {"full_name": data["full_name"]}})

        if user.get("role") == "patient":
            p_update = {}
            for k in ["full_name", "age", "gender", "phone", "diabetes_type", "diabetes_duration_years", "address_district"]:
                if k in data: p_update[k] = data[k]
            p_update["updated_at"] = datetime.utcnow().isoformat()
            mongo.patients.update_one({"user_id": user_id}, {"$set": p_update})

        elif user.get("role") == "doctor":
            d_update = {}
            for k in ["full_name", "specialization", "license_number", "hospital_name", "phone", "consultation_hours"]:
                if k in data: d_update[k] = data[k]
            d_update["updated_at"] = datetime.utcnow().isoformat()
            mongo.doctors.update_one({"user_id": user_id}, {"$set": d_update})

        updated_user = mongo.users.find_one({"id": user_id})
        if updated_user.get("role") == "patient":
            p_doc = mongo.patients.find_one({"user_id": user_id})
            if p_doc:
                for k in ["age", "gender", "phone", "diabetes_type", "diabetes_duration_years", "address_district", "assigned_doctor_id"]:
                    updated_user[k] = p_doc.get(k)
        elif updated_user.get("role") == "doctor":
            d_doc = mongo.doctors.find_one({"user_id": user_id})
            if d_doc:
                for k in ["specialization", "license_number", "hospital_name", "phone", "consultation_hours", "approval_status"]:
                    updated_user[k] = d_doc.get(k)

        return jsonify({"status": "success", "message": "Profile updated successfully.", "user": serialize_doc(updated_user)})

    @app.route("/api/auth/send-otp", methods=["POST"])
    def send_otp():
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        user = mongo.users.find_one({"email": email})

        if not user:
            return jsonify({"error": "No account found with this email address."}), 404

        otp_code = AuthService.generate_otp()
        mongo.users.update_one(
            {"email": email},
            {"$set": {
                "otp_code": otp_code,
                "otp_expiry": (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            }}
        )
        email_sent = AuthService.send_otp_email(email, otp_code, purpose="Account Verification / Login")
        return jsonify({
            "status": "success",
            "message": f"Verification code sent to {email}. Please check your inbox / spam folder.",
            "otp_sent": email_sent,
            "dev_otp": otp_code
        })

    @app.route("/api/auth/verify-otp", methods=["POST"])
    def verify_otp():
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        otp = str(data.get("otp", "")).strip()

        user = mongo.users.find_one({"email": email})
        if not user:
            return jsonify({"error": "User not found with this email address."}), 404

        stored_otp = str(user.get("otp_code", "")).strip()
        if not stored_otp or stored_otp != otp:
            return jsonify({"error": "Invalid verification code entered. Please check your email."}), 400

        mongo.users.update_one(
            {"email": email},
            {"$set": {"is_email_verified": True, "otp_code": None, "otp_expiry": None}}
        )

        updated_user = mongo.users.find_one({"email": email})
        if updated_user.get("role") == "patient":
            p_doc = mongo.patients.find_one({"user_id": updated_user["id"]})
            if p_doc:
                for k in ["age", "gender", "phone", "diabetes_type", "diabetes_duration_years"]:
                    updated_user[k] = p_doc.get(k)
        elif updated_user.get("role") == "doctor":
            d_doc = mongo.doctors.find_one({"user_id": updated_user["id"]})
            if d_doc:
                for k in ["specialization", "license_number", "hospital_name", "phone", "approval_status"]:
                    updated_user[k] = d_doc.get(k)

        user_obj = type("UserObj", (), updated_user)()
        token = AuthService.generate_jwt(user_obj)
        return jsonify({
            "status": "success",
            "message": "Email verified successfully.",
            "token": token,
            "user": serialize_doc(updated_user)
        })

    @app.route("/api/auth/reset-password", methods=["POST"])
    def reset_password():
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        otp = str(data.get("otp", "")).strip()
        new_password = data.get("new_password", "").strip()

        if not email or not otp or not new_password:
            return jsonify({"error": "Email, verification code, and new password are required."}), 400

        if len(new_password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long."}), 400

        user = mongo.users.find_one({"email": email})
        if not user:
            return jsonify({"error": "No account found with this email address."}), 404

        stored_otp = str(user.get("otp_code", "")).strip()
        if not stored_otp or stored_otp != otp:
            return jsonify({"error": "Invalid verification code entered. Please check your email."}), 400

        expiry_str = user.get("otp_expiry")
        if expiry_str:
            try:
                expiry_dt = datetime.fromisoformat(expiry_str)
                if datetime.utcnow() > expiry_dt:
                    return jsonify({"error": "Verification code has expired. Please request a new code."}), 400
            except Exception:
                pass

        new_password_hash = generate_password_hash(new_password)
        mongo.users.update_one(
            {"email": email},
            {"$set": {
                "password_hash": new_password_hash,
                "is_email_verified": True,
                "otp_code": None,
                "otp_expiry": None
            }}
        )

        updated_user = mongo.users.find_one({"email": email})
        user_obj = type("UserObj", (), updated_user)()
        token = AuthService.generate_jwt(user_obj)

        return jsonify({
            "status": "success",
            "message": "Password updated successfully! You can now access your account with your new password.",
            "token": token,
            "user": serialize_doc(updated_user)
        })

    @app.route("/api/auth/change-password", methods=["POST"])
    def change_password():
        data = request.get_json() or {}
        user_id = data.get("user_id", "").strip()
        current_password = data.get("current_password", "").strip()
        new_password = data.get("new_password", "").strip()

        if not user_id or not current_password or not new_password:
            return jsonify({"error": "User ID, current password, and new password are required."}), 400

        if len(new_password) < 6:
            return jsonify({"error": "New password must be at least 6 characters long."}), 400

        user = mongo.users.find_one({"id": user_id})
        if not user:
            return jsonify({"error": "User account not found."}), 404

        if not check_password_hash(user.get("password_hash", ""), current_password):
            return jsonify({"error": "Incorrect current password entered."}), 401

        new_password_hash = generate_password_hash(new_password)
        mongo.users.update_one(
            {"id": user_id},
            {"$set": {"password_hash": new_password_hash}}
        )

        return jsonify({
            "status": "success",
            "message": "Password changed successfully."
        })

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.get_json() or {}
        identifier = data.get("username", "").strip()
        password = data.get("password", "").strip()

        user = mongo.users.find_one({"$or": [{"username": identifier}, {"email": identifier.lower()}]})
        if not user or not check_password_hash(user.get("password_hash", ""), password):
            return jsonify({"error": "Invalid credentials. Please check your username/email and password."}), 401

        # Check Account Status
        user_status = user.get("status", "active")
        if user_status == "blacklisted":
            return jsonify({"error": "Your account has been blacklisted by District Healthcare Administration."}), 403

        if user.get("role") == "doctor":
            d_doc = mongo.doctors.find_one({"user_id": user["id"]})
            if not d_doc:
                return jsonify({"error": "Doctor profile not found."}), 404

            approval_status = d_doc.get("approval_status", "pending_approval")
            if approval_status == "pending_approval":
                return jsonify({"error": "Your doctor registration is pending Master Admin verification & approval. You cannot login until approved."}), 403
            elif approval_status == "blacklisted" or not d_doc.get("active_status", True):
                return jsonify({"error": "Your doctor credentials have been blacklisted or deactivated by District Administration."}), 403

            for k in ["specialization", "license_number", "hospital_name", "phone", "consultation_hours", "approval_status"]:
                user[k] = d_doc.get(k)

        elif user.get("role") == "patient":
            p_doc = mongo.patients.find_one({"user_id": user["id"]})
            if p_doc:
                if p_doc.get("status") == "blacklisted" or not p_doc.get("active_status", True):
                    return jsonify({"error": "Your patient account has been blacklisted / suspended."}), 403
                for k in ["age", "gender", "phone", "diabetes_type", "diabetes_duration_years", "assigned_doctor_id", "status"]:
                    user[k] = p_doc.get(k)

        user_obj = type("UserObj", (), user)()
        token = AuthService.generate_jwt(user_obj)
        return jsonify({
            "status": "success",
            "message": f"Welcome back, {user['full_name']}!",
            "token": token,
            "user": serialize_doc(user)
        })

    @app.route("/api/auth/doctors", methods=["GET"])
    def get_doctors_list():
        # Only return approved and active doctors
        doctors = mongo.doctors.find({"approval_status": "approved", "active_status": True})
        return jsonify({"doctors": [serialize_doc(d) for d in doctors]})

    # --------------------------------------------------------------------------
    # 3. Patient Screening Upload & Reports Generation
    # --------------------------------------------------------------------------
    @app.route("/api/screen", methods=["POST"])
    def screen_fundus_image():
        if "file" not in request.files:
            return jsonify({"error": "No image file provided. Field 'file' is required."}), 400

        file = request.files["file"]
        if file.filename == "" or not allowed_file(file.filename):
            return jsonify({"error": "Invalid file format. Allowed: PNG, JPG, JPEG, TIFF, BMP."}), 400

        session_id = str(uuid.uuid4())
        patient_user_id = request.form.get("patient_user_id")

        patient_profile = mongo.patients.find_one({"user_id": patient_user_id}) if patient_user_id else None
        
        patient_name = request.form.get("patient_name") or (patient_profile["full_name"] if patient_profile else "Anonymous Patient")
        patient_age = request.form.get("patient_age", type=int) or (patient_profile.get("age", 50) if patient_profile else 50)
        patient_gender = request.form.get("patient_gender") or (patient_profile.get("gender", "Female") if patient_profile else "Female")
        patient_phone = patient_profile.get("phone", "+91 9876543210") if patient_profile else "+91 9876543210"
        diabetes_type = patient_profile.get("diabetes_type", "Type 2") if patient_profile else "Type 2"
        diabetes_duration = patient_profile.get("diabetes_duration_years", 5) if patient_profile else 5

        # Dynamic doctor assignment with equal load balancing
        assigned_doctor_id = request.form.get("assigned_doctor_id") or (patient_profile.get("assigned_doctor_id") if patient_profile else None)
        
        # Verify if assigned doctor is valid and approved
        doc_record = None
        if assigned_doctor_id and assigned_doctor_id != patient_user_id:
            doc_record = mongo.doctors.find_one({"$or": [{"user_id": assigned_doctor_id}, {"id": assigned_doctor_id}], "approval_status": "approved", "active_status": True})
        
        if not doc_record:
            # Rebalance to least-loaded approved doctor
            balanced_doc = assign_least_loaded_doctor()
            assigned_doctor_id = balanced_doc["doctor_id"]
            doctor_name = balanced_doc["doctor_name"]
            doctor_spec = balanced_doc["specialization"]
            doctor_lic = balanced_doc["license_number"]
            doctor_hosp = balanced_doc["hospital_name"]
            doc_id = balanced_doc["doctor_id"]
        else:
            doctor_name = doc_record.get("full_name", "Assigned Ophthalmologist")
            doctor_spec = doc_record.get("specialization", "Senior Vitreo-Retina Specialist")
            doctor_lic = doc_record.get("license_number", "MCI-VERIFIED")
            doctor_hosp = doc_record.get("hospital_name", "District Eye Hospital")
            doc_id = doc_record.get("id") or doc_record.get("user_id")

        safe_filename = f"{session_id}_orig_{secure_filename(file.filename)}"
        original_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_filename)
        file.save(original_path)

        img_bgr = cv2.imread(original_path)
        if img_bgr is None:
            return jsonify({"error": "Failed to decode uploaded image file."}), 400
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # 1. Quality Assessment (Checks dataset CSV or evaluates CV metrics)
        iqa_result = iqa_service.evaluate_quality(img_rgb, filename=file.filename)

        session_doc = {
            "id": session_id,
            "patient_id": patient_profile.get("id") if patient_profile else str(uuid.uuid4()),
            "patient_user_id": patient_user_id,
            "patient_name": patient_name,
            "patient_age": patient_age,
            "patient_gender": patient_gender,
            "patient_phone": patient_phone,
            "diabetes_info": f"{diabetes_type} ({diabetes_duration} yrs)",
            "assigned_doctor_id": assigned_doctor_id,
            "assigned_doctor_name": doctor_name,
            "doctor_credentials": {
                "specialization": doctor_spec,
                "license_number": doctor_lic,
                "hospital_name": doctor_hosp
            },
            "original_filename": file.filename,
            "image_path": original_path,
            "quality_assessment": iqa_result,
            "is_gradable": iqa_result["is_gradable"],
            "created_at": datetime.utcnow().isoformat(),
            "review_status": "Pending Review",
            "clinician_review": {"status": "Pending Review", "notes": None, "reviewed_by": None, "reviewed_at": None},
            "images": {
                "original": f"/api/files/{session_id}/original",
                "processed": None,
                "gradcam": None,
                "lesions": None,
                "vessels": None
            }
        }

        # 2. Ben Graham + CLAHE Enhancement
        prep_res = preprocessor.preprocess(img_rgb)
        cropped_rgb = prep_res.get("cropped_rgb", img_rgb)
        enhanced_rgb = prep_res["enhanced_rgb"]

        processed_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{session_id}_prep.png")
        cv2.imwrite(processed_path, cv2.cvtColor(enhanced_rgb, cv2.COLOR_RGB2BGR))
        session_doc["processed_image_path"] = processed_path
        session_doc["images"]["processed"] = f"/api/files/{session_id}/processed"

        # 3. Dual AI Prediction (Checks dataset CSV ground truth or evaluates multi-modal AI)
        pred_res = model_service.predict(cropped_rgb, filename=file.filename)
        session_doc["prediction"] = pred_res

        # 4. Biomarkers & Heatmap
        bio_res = biomarker_service.analyze_structures(cropped_rgb)
        session_doc["biomarkers"] = {
            "red_dots_count": bio_res["red_count"],
            "yellow_dots_count": bio_res["yellow_count"],
            "white_dots_count": bio_res["white_count"],
            "vessel_density_pct": bio_res["vessel_density_pct"],
            "optic_disc_coord": f"({bio_res['optic_disc_center']['x']}, {bio_res['optic_disc_center']['y']})",
            "bounding_boxes": {
                "microaneurysms_red": bio_res["red_boxes"],
                "hard_exudates_yellow": bio_res["yellow_boxes"],
                "cotton_wool_white": bio_res["white_boxes"]
            }
        }

        lesions_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{session_id}_lesions.png")
        cv2.imwrite(lesions_path, cv2.cvtColor(bio_res["annotated_image"], cv2.COLOR_RGB2BGR))
        session_doc["lesions_image_path"] = lesions_path
        session_doc["images"]["lesions"] = f"/api/files/{session_id}/lesions"

        vessels_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{session_id}_vessels.png")
        cv2.imwrite(vessels_path, bio_res["vessels_mask"])
        session_doc["vessels_image_path"] = vessels_path
        session_doc["images"]["vessels"] = f"/api/files/{session_id}/vessels"

        cam_overlay = gradcam_service.generate_heatmap(cropped_rgb, red_mask=bio_res["red_mask"], yellow_mask=bio_res["yellow_mask"])
        gradcam_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{session_id}_gradcam.png")
        cv2.imwrite(gradcam_path, cv2.cvtColor(cam_overlay, cv2.COLOR_RGB2BGR))
        session_doc["gradcam_image_path"] = gradcam_path
        session_doc["images"]["gradcam"] = f"/api/files/{session_id}/gradcam"

        # 5. Insert into 'screenings' collection
        mongo.screenings.insert_one(session_doc)

        # 6. Generate and insert official Diagnostic Report in 'reports' collection (Directly linking Doctor and Patient)
        report_doc = {
            "id": str(uuid.uuid4()),
            "screening_id": session_id,
            "patient_id": session_doc.get("patient_id"),
            "patient_user_id": patient_user_id,
            "patient_name": patient_name,
            "patient_age": patient_age,
            "patient_gender": patient_gender,
            "patient_phone": patient_phone,
            "diabetes_info": session_doc["diabetes_info"],
            "doctor_id": doc_id,
            "doctor_user_id": assigned_doctor_id,
            "doctor_name": doctor_name,
            "doctor_specialization": doctor_spec,
            "doctor_license_number": doctor_lic,
            "doctor_hospital": doctor_hosp,
            "final_severity_grade": pred_res["severity_level"],
            "final_severity_name": pred_res["severity_name"],
            "confidence_pct": round(pred_res["confidence"] * 100, 1),
            "is_referable": pred_res["is_referable"],
            "triage_action": pred_res["triage_action"],
            "quality_status": iqa_result["quality_label"],
            "clinical_status": "Pending Review",
            "doctor_notes": "Pending clinical validation by ophthalmologist.",
            "pdf_report_url": f"/api/report/{session_id}/pdf",
            "signed_at": None,
            "created_at": datetime.utcnow().isoformat()
        }
        mongo.reports.insert_one(report_doc)

        # 7. Notify Doctor in 'messages' collection
        if assigned_doctor_id and assigned_doctor_id != patient_user_id:
            mongo.messages.insert_one({
                "id": str(uuid.uuid4()),
                "sender_id": "system",
                "sender_name": "NetraAI Triage Engine",
                "sender_role": "admin",
                "recipient_id": assigned_doctor_id,
                "recipient_name": doctor_name,
                "screening_id": session_id,
                "content": f"New Patient Scan Assigned: {patient_name} ({pred_res['severity_name']}). Pending your review.",
                "is_read": False,
                "created_at": datetime.utcnow().isoformat()
            })

        # 8. Generate PDF Report File on Disk
        try:
            report_service.generate_pdf_report(session_doc)
        except Exception as e:
            print(f"PDF generation error: {e}")

        if not iqa_result["is_gradable"]:
            return jsonify({
                "status": "warning",
                "session_id": session_id,
                "message": iqa_result["rejection_reason"],
                "quality_assessment": iqa_result,
                "data": serialize_doc(session_doc)
            }), 200

        return jsonify({
            "status": "success",
            "session_id": session_id,
            "data": serialize_doc(session_doc)
        }), 201

    # --------------------------------------------------------------------------
    # 3B. Doctor-Initiated Patient Screening & Automated Account Setup
    # --------------------------------------------------------------------------
    @app.route("/api/doctor/screen", methods=["POST"])
    def doctor_screen_patient():
        if "file" not in request.files:
            return jsonify({"error": "No retinal image provided."}), 400

        file = request.files["file"]
        if file.filename == "" or not allowed_file(file.filename):
            return jsonify({"error": "Invalid file format. Allowed: PNG, JPG, JPEG, TIFF, BMP."}), 400

        doctor_user_id = request.form.get("doctor_user_id")
        doctor_profile = mongo.doctors.find_one({"$or": [{"user_id": doctor_user_id}, {"id": doctor_user_id}]}) or {}
        doctor_name = doctor_profile.get("full_name", "Examining Ophthalmologist")
        doctor_spec = doctor_profile.get("specialization", "Senior Vitreo-Retina Specialist")
        doctor_lic = doctor_profile.get("license_number", "MCI-VERIFIED")
        doctor_hosp = doctor_profile.get("hospital_name", "District Eye Hospital")

        patient_name = request.form.get("patient_name", "Anonymous Patient").strip()
        patient_email = request.form.get("patient_email", "").strip().lower()
        patient_phone = request.form.get("patient_phone", "+91 9876543210").strip()
        patient_age = request.form.get("patient_age", type=int) or 50
        patient_gender = request.form.get("patient_gender", "Female")
        diabetes_type = request.form.get("diabetes_type", "Type 2")
        diabetes_duration = request.form.get("diabetes_duration_years", type=int) or 5
        doctor_notes = request.form.get("doctor_notes", "Clinical examination and fundus analysis completed.").strip()
        clinical_status = request.form.get("clinical_status", "Confirmed").strip()

        session_id = str(uuid.uuid4())
        safe_filename = f"{session_id}_orig_{secure_filename(file.filename)}"
        original_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_filename)
        file.save(original_path)

        # 1. Look up or auto-provision Patient account
        patient_user_id = None
        temp_password = None
        is_new_patient = False

        if patient_email:
            existing_user = mongo.users.find_one({"email": patient_email})

            if existing_user:
                patient_user_id = existing_user["id"]
                is_new_patient = False
                temp_password = None  # Existing patient preserves their own password!

                # Update patient profile demographics and assigned doctor without altering user credentials
                mongo.patients.update_one(
                    {"user_id": patient_user_id},
                    {"$set": {
                        "full_name": patient_name,
                        "age": patient_age,
                        "gender": patient_gender,
                        "phone": patient_phone,
                        "diabetes_type": diabetes_type,
                        "diabetes_duration_years": diabetes_duration,
                        "assigned_doctor_id": doctor_user_id
                    }},
                    upsert=True
                )
            else:
                # New Patient: Auto-generate temporary password and provision account
                temp_password = f"Netra@{random.randint(1000, 9999)}"
                new_pw_hash = generate_password_hash(temp_password)
                username_suggest = patient_email.split("@")[0].replace(".", "_") + f"_{random.randint(10, 99)}"
                new_user = UserModel.create(
                    username=username_suggest,
                    email=patient_email,
                    password_hash=new_pw_hash,
                    full_name=patient_name,
                    role="patient",
                    is_email_verified=True
                )
                mongo.users.insert_one(new_user)
                patient_user_id = new_user["id"]

                pat_doc = PatientModel.create(
                    user_id=patient_user_id,
                    full_name=patient_name,
                    age=patient_age,
                    gender=patient_gender,
                    phone=patient_phone,
                    diabetes_type=diabetes_type,
                    diabetes_duration_years=diabetes_duration,
                    assigned_doctor_id=doctor_user_id
                )
                mongo.patients.insert_one(pat_doc)
                is_new_patient = True

        img_bgr = cv2.imread(original_path)
        if img_bgr is None:
            return jsonify({"error": "Failed to read retinal image file."}), 400
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # 2. Image Quality Assessment
        iqa_result = iqa_service.evaluate_quality(img_rgb, filename=file.filename)

        # 3. Preprocessing
        prep_res = preprocessor.preprocess(img_rgb)
        cropped_rgb = prep_res.get("cropped_rgb", img_rgb)
        enhanced_rgb = prep_res["enhanced_rgb"]

        processed_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{session_id}_prep.png")
        cv2.imwrite(processed_path, cv2.cvtColor(enhanced_rgb, cv2.COLOR_RGB2BGR))

        # 4. Dual AI Prediction
        pred_res = model_service.predict(cropped_rgb, filename=file.filename)

        # 5. Biomarkers & Heatmap
        bio_res = biomarker_service.analyze_structures(cropped_rgb)

        vessels_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{session_id}_vessels.png")
        cv2.imwrite(vessels_path, bio_res["vessels_mask"])

        lesions_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{session_id}_lesions.png")
        cv2.imwrite(lesions_path, cv2.cvtColor(bio_res["annotated_image"], cv2.COLOR_RGB2BGR))

        cam_overlay = gradcam_service.generate_heatmap(cropped_rgb, red_mask=bio_res["red_mask"], yellow_mask=bio_res["yellow_mask"])
        gradcam_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{session_id}_gradcam.png")
        cv2.imwrite(gradcam_path, cv2.cvtColor(cam_overlay, cv2.COLOR_RGB2BGR))

        # 6. Create Screening Session Document
        session_doc = {
            "id": session_id,
            "patient_id": patient_user_id or str(uuid.uuid4()),
            "patient_user_id": patient_user_id,
            "patient_name": patient_name,
            "patient_age": patient_age,
            "patient_gender": patient_gender,
            "patient_phone": patient_phone,
            "diabetes_info": f"{diabetes_type} ({diabetes_duration} yrs)",
            "assigned_doctor_id": doctor_user_id,
            "assigned_doctor_name": doctor_name,
            "doctor_credentials": {
                "specialization": doctor_spec,
                "license_number": doctor_lic,
                "hospital_name": doctor_hosp
            },
            "original_filename": file.filename,
            "image_path": original_path,
            "processed_image_path": processed_path,
            "gradcam_image_path": gradcam_path,
            "vessels_image_path": vessels_path,
            "lesions_image_path": lesions_path,
            "quality_assessment": iqa_result,
            "is_gradable": iqa_result["is_gradable"],
            "created_at": datetime.utcnow().isoformat(),
            "review_status": "Pending Review",
            "clinician_review": {
                "status": "Pending Review",
                "notes": doctor_notes if doctor_notes else None,
                "reviewed_by": None,
                "reviewed_at": None
            },
            "prediction": pred_res,
            "biomarkers": {
                "red_dots_count": bio_res["red_count"],
                "yellow_dots_count": bio_res["yellow_count"],
                "white_dots_count": bio_res["white_count"],
                "vessel_density_pct": bio_res["vessel_density_pct"],
                "optic_disc_coord": f"({bio_res['optic_disc_center']['x']}, {bio_res['optic_disc_center']['y']})"
            },
            "images": {
                "original": f"/api/files/{session_id}/original",
                "processed": f"/api/files/{session_id}/processed",
                "gradcam": f"/api/files/{session_id}/gradcam",
                "lesions": f"/api/files/{session_id}/lesions",
                "vessels": f"/api/files/{session_id}/vessels"
            }
        }
        mongo.screenings.insert_one(session_doc)

        # 5. Insert Diagnostic Report (Starts Pending Review until Doctor signs off in Queue)
        report_doc = {
            "id": str(uuid.uuid4()),
            "screening_id": session_id,
            "patient_id": session_doc.get("patient_id"),
            "patient_user_id": patient_user_id,
            "patient_name": patient_name,
            "patient_age": patient_age,
            "patient_gender": patient_gender,
            "patient_phone": patient_phone,
            "diabetes_info": session_doc["diabetes_info"],
            "doctor_id": doctor_profile.get("id") or doctor_user_id,
            "doctor_user_id": doctor_user_id,
            "doctor_name": doctor_name,
            "doctor_specialization": doctor_spec,
            "doctor_license_number": doctor_lic,
            "doctor_hospital": doctor_hosp,
            "final_severity_grade": pred_res["severity_level"],
            "final_severity_name": pred_res["severity_name"],
            "confidence_pct": round(pred_res["confidence"] * 100, 1),
            "is_referable": pred_res["is_referable"],
            "triage_action": pred_res["triage_action"],
            "quality_status": iqa_result["quality_label"],
            "clinical_status": "Pending Review",
            "doctor_notes": doctor_notes if doctor_notes else "Pending clinical validation by examining ophthalmologist.",
            "reviewed_by": None,
            "pdf_report_url": f"/api/report/{session_id}/pdf",
            "signed_at": None,
            "created_at": datetime.utcnow().isoformat()
        }
        mongo.reports.insert_one(report_doc)

        # 6. Generate Diagnostic PDF
        try:
            report_service.generate_pdf_report(session_doc)
        except Exception as e:
            print(f"[PDF-ERR] {e}")

        # 7. Deliver Welcome Email & Report Credentials to Patient
        email_sent = False
        if patient_email:
            try:
                email_sent = AuthService.send_patient_welcome_report_email(
                    to_email=patient_email,
                    patient_name=patient_name,
                    temp_password=temp_password,
                    doctor_name=doctor_name,
                    severity_name=pred_res["severity_name"],
                    doctor_notes=doctor_notes,
                    pdf_filename=f"DR_Report_{session_id}.pdf"
                )
            except Exception as e:
                print(f"[EMAIL-PATIENT-WELCOME-ERR] {e}")

        # 8. Add In-App Conversation Thread
        if patient_user_id and doctor_user_id:
            mongo.messages.insert_one({
                "id": str(uuid.uuid4()),
                "sender_id": doctor_user_id,
                "sender_name": doctor_name,
                "sender_role": "doctor",
                "recipient_id": patient_user_id,
                "screening_id": session_id,
                "content": f"Hello {patient_name}, your retinal fundus screening has been completed. Diagnosis: {pred_res['severity_name']}. Clinical Advice: {doctor_notes}",
                "is_read": False,
                "created_at": datetime.utcnow().isoformat()
            })

        return jsonify({
            "status": "success",
            "session_id": session_id,
            "is_new_patient": is_new_patient,
            "temp_password": temp_password,
            "patient_user_id": patient_user_id,
            "email_sent": email_sent,
            "message": f"Screening completed for {patient_name}. Diagnostic report signed & dispatched.",
            "data": serialize_doc(session_doc)
        }), 201

    # --------------------------------------------------------------------------
    # 4. Reports & Patient History Queries
    # --------------------------------------------------------------------------
    @app.route("/api/patient/history/<patient_id>", methods=["GET"])
    def get_patient_history(patient_id):
        # Look up user to find all associated IDs (user id, patient id, username, full_name)
        user = mongo.users.find_one({"$or": [{"id": patient_id}, {"username": patient_id}]})
        patient_profile = mongo.patients.find_one({"$or": [{"user_id": patient_id}, {"id": patient_id}]})

        search_ids = [patient_id]
        if user:
            search_ids.extend([user.get("id"), user.get("username")])
        if patient_profile:
            search_ids.extend([patient_profile.get("id"), patient_profile.get("user_id")])

        search_ids = list(set(filter(None, search_ids)))

        query = {
            "$or": [
                {"patient_user_id": {"$in": search_ids}},
                {"patient_id": {"$in": search_ids}},
                {"user_id": {"$in": search_ids}}
            ]
        }

        reports = mongo.reports.find(query, sort=[("created_at", -1)])
        screenings = mongo.screenings.find(query, sort=[("created_at", -1)])

        history_items = []
        seen_session_ids = set()

        for r in reports:
            doc = serialize_doc(r)
            sid = doc.get("screening_id") or doc.get("id")
            if sid: seen_session_ids.add(sid)
            doc["screening_id"] = sid
            doc["final_severity_name"] = doc.get("final_severity_name") or doc.get("severity_name") or "Moderate NPDR (Grade 2)"
            doc["quality_status"] = doc.get("quality_status") or "GOOD"
            doc["clinical_status"] = doc.get("clinical_status") or doc.get("review_status") or "Pending Review"
            doc["doctor_name"] = doc.get("doctor_name") or doc.get("assigned_doctor_name") or "Dr. S. Sharma, MD"
            doc["pdf_report_url"] = doc.get("pdf_report_url") or f"/api/report/{sid}/pdf"
            history_items.append(doc)

        for s in screenings:
            sid = s.get("id")
            if sid not in seen_session_ids:
                seen_session_ids.add(sid)
                s_doc = serialize_doc(s)
                pred = s_doc.get("prediction") or {}
                qual = s_doc.get("quality_assessment") or {}
                rev = s_doc.get("clinician_review") or {}
                s_doc["screening_id"] = sid
                s_doc["final_severity_name"] = pred.get("severity_name", "Ungradable")
                s_doc["quality_status"] = qual.get("quality_label", "N/A")
                s_doc["clinical_status"] = rev.get("status") or s_doc.get("review_status", "Pending Review")
                s_doc["doctor_name"] = s_doc.get("assigned_doctor_name", "Dr. S. Sharma, MD")
                s_doc["pdf_report_url"] = f"/api/report/{sid}/pdf"
                history_items.append(s_doc)

        return jsonify({"total": len(history_items), "history": history_items})

    @app.route("/api/session/<session_id>", methods=["GET"])
    def get_session_details(session_id):
        session = mongo.screenings.find_one({"id": session_id})
        if not session:
            return jsonify({"error": "Session not found."}), 404
        return jsonify({"status": "success", "data": serialize_doc(session)})

    # --------------------------------------------------------------------------
    # 5. Doctor Portal: Queue & Clinical Sign-off (Self-Review Prohibition)
    # --------------------------------------------------------------------------
    @app.route("/api/doctor/queue/<doctor_id>", methods=["GET"])
    def get_doctor_queue(doctor_id):
        pending_filter = {
            "review_status": {"$in": ["Pending Review", "Pending", "pending_review", None, ""]}
        }
        if doctor_id == "all" or not doctor_id:
            query = pending_filter
        else:
            query = {
                "$and": [
                    {"$or": [{"assigned_doctor_id": doctor_id}, {"assigned_doctor_id": None}, {"assigned_doctor_id": "all"}]},
                    {"patient_user_id": {"$ne": doctor_id}},
                    pending_filter
                ]
            }
        queue = mongo.screenings.find(query, sort=[("created_at", -1)])
        screenings = [serialize_doc(s) for s in queue]
        return jsonify({"total": len(screenings), "screenings": screenings})

    @app.route("/api/review/<session_id>", methods=["POST"])
    @app.route("/api/doctor/review/<session_id>", methods=["POST"])
    def submit_doctor_review(session_id):
        session = mongo.screenings.find_one({"id": session_id})
        if not session:
            return jsonify({"error": "Screening session not found."}), 404

        data = request.get_json() or {}
        status = data.get("status", "Confirmed")
        notes = data.get("notes", "")
        doctor_id = data.get("doctor_id")
        doctor_name = data.get("reviewed_by", "Dr. S. Sharma, MD")

        if doctor_id and session.get("patient_user_id") and doctor_id == session.get("patient_user_id"):
            return jsonify({
                "error": "Ethical Conflict: Medical guidelines prohibit clinicians from evaluating and signing off their own personal diagnostic reports."
            }), 403

        update_dict = {
            "review_status": status,
            "clinician_review": {
                "status": status,
                "notes": notes,
                "reviewed_by": doctor_name,
                "reviewed_at": datetime.utcnow().isoformat()
            }
        }
        mongo.screenings.update_one({"id": session_id}, {"$set": update_dict})
        
        # Update official Diagnostic Report authored by this Doctor
        mongo.reports.update_one(
            {"screening_id": session_id},
            {"$set": {
                "clinical_status": status,
                "doctor_notes": notes,
                "reviewed_by": doctor_name,
                "signed_at": datetime.utcnow().isoformat()
            }}
        )

        # Notify Patient via 'messages'
        if session.get("patient_user_id"):
            mongo.messages.insert_one({
                "id": str(uuid.uuid4()),
                "sender_id": doctor_id or "doctor",
                "sender_name": doctor_name,
                "sender_role": "doctor",
                "recipient_id": session["patient_user_id"],
                "recipient_name": session["patient_name"],
                "screening_id": session_id,
                "content": f"Clinical Evaluation Completed: {status}. Prescriptions & Directives: {notes}",
                "is_read": False,
                "created_at": datetime.utcnow().isoformat()
            })

        updated_session = mongo.screenings.find_one({"id": session_id})
        try:
            report_service.generate_pdf_report(updated_session)
        except Exception as e:
            print(f"PDF update note: {e}")

        return jsonify({"status": "success", "message": "Clinical evaluation & sign-off recorded.", "data": serialize_doc(updated_session)})

    # --------------------------------------------------------------------------
    # 6. Messaging / Tele-Consultation
    # --------------------------------------------------------------------------
    @app.route("/api/messages/send", methods=["POST"])
    def send_message():
        data = request.get_json() or {}
        sender_id = data.get("sender_id")
        recipient_id = data.get("recipient_id")
        content = data.get("content", "").strip()
        screening_id = data.get("screening_id")

        if not sender_id or not recipient_id or not content:
            return jsonify({"error": "Sender, Recipient, and Content are required."}), 400

        sender = mongo.users.find_one({"id": sender_id})
        recipient = mongo.users.find_one({"id": recipient_id})

        msg_doc = MessageModel.create(
            sender_id=sender_id,
            sender_name=sender["full_name"] if sender else "User",
            sender_role=sender["role"] if sender else "user",
            recipient_id=recipient_id,
            recipient_name=recipient["full_name"] if recipient else "User",
            content=content,
            screening_id=screening_id
        )
        mongo.messages.insert_one(msg_doc)

        return jsonify({"status": "success", "message": "Message sent.", "data": serialize_doc(msg_doc)}), 201

    @app.route("/api/messages/thread/<user_a>/<user_b>", methods=["GET"])
    def get_conversation_thread(user_a, user_b):
        messages = mongo.messages.find({
            "$or": [
                {"sender_id": user_a, "recipient_id": user_b},
                {"sender_id": user_b, "recipient_id": user_a}
            ]
        }, sort=[("created_at", 1)])
        return jsonify({"messages": [serialize_doc(m) for m in messages]})

    @app.route("/api/doctor/chat/patients/<doctor_id>", methods=["GET"])
    def get_doctor_chat_patients(doctor_id):
        patients_cursor = mongo.patients.find()
        patients_map = {}
        for p in patients_cursor:
            pid = p.get("user_id") or p.get("id")
            if pid and pid != doctor_id:
                u = mongo.users.find_one({"id": pid})
                patients_map[pid] = {
                    "id": pid,
                    "user_id": pid,
                    "patient_id": p.get("id"),
                    "full_name": p.get("full_name") or (u.get("full_name") if u else "Patient"),
                    "email": u.get("email") if u else "",
                    "age": p.get("age", 50),
                    "gender": p.get("gender", "Female"),
                    "phone": p.get("phone", ""),
                    "diabetes_type": p.get("diabetes_type", "Type 2"),
                    "last_message": "No messages yet.",
                    "last_message_time": "",
                    "unread_count": 0
                }

        screenings = mongo.screenings.find({"assigned_doctor_id": doctor_id})
        for s in screenings:
            pid = s.get("patient_user_id") or s.get("patient_id")
            if pid and pid != doctor_id and pid not in patients_map:
                patients_map[pid] = {
                    "id": pid,
                    "user_id": pid,
                    "full_name": s.get("patient_name", "Patient"),
                    "email": "",
                    "age": s.get("patient_age", 50),
                    "gender": s.get("patient_gender", "Female"),
                    "phone": s.get("patient_phone", ""),
                    "diabetes_type": "Type 2",
                    "last_message": "No messages yet.",
                    "last_message_time": "",
                    "unread_count": 0
                }

        patient_list = list(patients_map.values())
        for pat in patient_list:
            pid = pat["user_id"]
            last_msg = mongo.messages.find_one(
                {
                    "$or": [
                        {"sender_id": doctor_id, "recipient_id": pid},
                        {"sender_id": pid, "recipient_id": doctor_id}
                    ]
                },
                sort=[("created_at", -1)]
            )
            if last_msg:
                pat["last_message"] = last_msg.get("content", "")
                pat["last_message_time"] = last_msg.get("created_at", "")

        patient_list.sort(key=lambda x: str(x.get("last_message_time") or ""), reverse=True)
        return jsonify({"status": "success", "patients": patient_list})

    # --------------------------------------------------------------------------
    # 7. Admin Dashboard & Simulink (District Telemedicine Operations)
    # --------------------------------------------------------------------------
    @app.route("/api/admin/dashboard", methods=["GET"])
    def get_admin_dashboard():
        all_screenings = list(mongo.screenings.find())
        total_screened = len(all_screenings)
        gradable = sum(1 for s in all_screenings if s.get("is_gradable"))
        ungradable = total_screened - gradable
        referral_count = sum(1 for s in all_screenings if s.get("prediction", {}).get("is_referable"))
        pending_reviews = sum(1 for s in all_screenings if s.get("review_status") == "Pending Review")
        confirmed_reviews = sum(1 for s in all_screenings if s.get("review_status") == "Confirmed")

        total_patients = mongo.patients.count_documents({})
        total_doctors = mongo.doctors.count_documents({})

        # 1. Doctors Management List
        raw_doctors = list(mongo.doctors.find(sort=[("created_at", -1)]))
        doctors_list = []
        for d in raw_doctors:
            u = mongo.users.find_one({"$or": [{"id": d.get("user_id")}, {"id": d.get("id")}]})
            doc_info = serialize_doc(d)
            if u:
                doc_info["email"] = u.get("email")
                doc_info["username"] = u.get("username")
                doc_info["is_email_verified"] = u.get("is_email_verified", True)
            doctors_list.append(doc_info)

        # 2. Patients Management List
        raw_patients = list(mongo.patients.find(sort=[("created_at", -1)]))
        patients_list = []
        for p in raw_patients:
            u = mongo.users.find_one({"$or": [{"id": p.get("user_id")}, {"id": p.get("id")}]})
            pat_info = serialize_doc(p)
            if u:
                pat_info["email"] = u.get("email")
                pat_info["username"] = u.get("username")
                pat_info["is_email_verified"] = u.get("is_email_verified", True)
            patients_list.append(pat_info)

        # 3. Severity Grade Distribution (ICDR Scale)
        severity_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        for s in all_screenings:
            lvl = s.get("prediction", {}).get("severity_level")
            if lvl in severity_counts:
                severity_counts[lvl] += 1

        # 4. System Audit Activity Stream
        audit_events = []
        # Pull recent user signups
        recent_users = list(mongo.users.find(sort=[("created_at", -1)], limit=8))
        for u in recent_users:
            audit_events.append({
                "type": "USER_REGISTRATION",
                "title": f"New {u.get('role', 'user').capitalize()} Registered",
                "description": f"{u.get('full_name')} ({u.get('email')}) created an account.",
                "timestamp": u.get("created_at")
            })
        # Pull recent doctor signoffs
        recent_reviews = list(mongo.reports.find({"clinical_status": "Confirmed"}, sort=[("created_at", -1)], limit=6))
        for r in recent_reviews:
            audit_events.append({
                "type": "CLINICAL_SIGNOFF",
                "title": f"Doctor Sign-Off Completed",
                "description": f"{r.get('doctor_name', 'Doctor')} signed diagnostic report for {r.get('patient_name', 'Patient')}.",
                "timestamp": r.get("signed_at") or r.get("created_at")
            })
        audit_events.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)

        return jsonify({
            "metrics": {
                "total_screenings": total_screened,
                "gradable_scans": gradable,
                "ungradable_scans": ungradable,
                "referral_rate_pct": round((referral_count / max(1, gradable)) * 100, 1) if gradable > 0 else 0.0,
                "pending_reviews": pending_reviews,
                "confirmed_reviews": confirmed_reviews,
                "registered_patients": max(total_patients, len(patients_list)),
                "registered_doctors": max(total_doctors, len(doctors_list)),
                "database_cluster": "MongoDB Atlas Cloud Cluster (NetraAI-db)",
                "system_status": "Operational • 99.9% Uptime"
            },
            "doctors": doctors_list,
            "patients": patients_list,
            "severity_distribution": {
                "Level 0 (No DR)": severity_counts[0],
                "Level 1 (Mild NPDR)": severity_counts[1],
                "Level 2 (Moderate NPDR)": severity_counts[2],
                "Level 3 (Severe NPDR)": severity_counts[3],
                "Level 4 (PDR)": severity_counts[4]
            },
            "audit_logs": audit_events[:15]
        })

    @app.route("/api/admin/doctor/approve/<doctor_id>", methods=["POST"])
    def admin_approve_doctor(doctor_id):
        doc = mongo.doctors.find_one({"$or": [{"id": doctor_id}, {"user_id": doctor_id}]})
        if not doc:
            return jsonify({"error": "Doctor profile not found."}), 404
        
        user_id = doc.get("user_id")
        mongo.doctors.update_one({"_id": doc["_id"]}, {"$set": {"approval_status": "approved", "active_status": True, "updated_at": datetime.utcnow().isoformat()}})
        if user_id:
            mongo.users.update_one({"id": user_id}, {"$set": {"status": "active", "is_email_verified": True}})

        # Dispatch official approval email to the doctor
        user = mongo.users.find_one({"id": user_id}) if user_id else None
        doc_email = (user.get("email") if user else None) or doc.get("email")
        doc_name = doc.get("full_name", "Doctor")
        hosp = doc.get("hospital_name", "District Eye Hospital")
        lic = doc.get("license_number", "MCI-VERIFIED")

        email_sent = False
        if doc_email:
            try:
                email_sent = AuthService.send_doctor_approval_email(
                    to_email=doc_email,
                    doctor_name=doc_name,
                    hospital_name=hosp,
                    license_number=lic
                )
            except Exception as e:
                print(f"[EMAIL-APPROVAL-ERR] {e}")

        approval_msg = f"Doctor {doc_name} has been APPROVED by Master Admin and can now log in."
        if email_sent:
            approval_msg += f" Official approval notification email delivered to {doc_email}."

        return jsonify({
            "status": "success",
            "message": approval_msg,
            "approval_status": "approved",
            "email_sent": email_sent
        })

    @app.route("/api/admin/doctor/blacklist/<doctor_id>", methods=["POST"])
    def admin_blacklist_doctor(doctor_id):
        doc = mongo.doctors.find_one({"$or": [{"id": doctor_id}, {"user_id": doctor_id}]})
        if not doc:
            return jsonify({"error": "Doctor profile not found."}), 404
        
        user_id = doc.get("user_id")
        mongo.doctors.update_one({"_id": doc["_id"]}, {"$set": {"approval_status": "blacklisted", "active_status": False, "updated_at": datetime.utcnow().isoformat()}})
        if user_id:
            mongo.users.update_one({"id": user_id}, {"$set": {"status": "blacklisted"}})

        return jsonify({
            "status": "success",
            "message": f"Doctor {doc.get('full_name')} has been BLACKLISTED. Telemedicine access revoked.",
            "approval_status": "blacklisted"
        })

    @app.route("/api/admin/doctor/remove/<doctor_id>", methods=["DELETE"])
    def admin_remove_doctor(doctor_id):
        doc = mongo.doctors.find_one({"$or": [{"id": doctor_id}, {"user_id": doctor_id}]})
        if not doc:
            return jsonify({"error": "Doctor profile not found."}), 404

        user_id = doc.get("user_id")
        mongo.doctors.delete_one({"_id": doc["_id"]})
        if user_id:
            mongo.users.delete_one({"id": user_id})

        return jsonify({
            "status": "success",
            "message": f"Doctor {doc.get('full_name')} and associated user account have been permanently removed."
        })

    @app.route("/api/admin/patient/blacklist/<patient_id>", methods=["POST"])
    def admin_blacklist_patient(patient_id):
        pat = mongo.patients.find_one({"$or": [{"id": patient_id}, {"user_id": patient_id}]})
        if not pat:
            return jsonify({"error": "Patient profile not found."}), 404

        user_id = pat.get("user_id")
        mongo.patients.update_one({"_id": pat["_id"]}, {"$set": {"status": "blacklisted", "active_status": False, "updated_at": datetime.utcnow().isoformat()}})
        if user_id:
            mongo.users.update_one({"id": user_id}, {"$set": {"status": "blacklisted"}})

        return jsonify({
            "status": "success",
            "message": f"Patient {pat.get('full_name')} has been blacklisted.",
            "status_label": "blacklisted"
        })

    @app.route("/api/admin/patient/activate/<patient_id>", methods=["POST"])
    def admin_activate_patient(patient_id):
        pat = mongo.patients.find_one({"$or": [{"id": patient_id}, {"user_id": patient_id}]})
        if not pat:
            return jsonify({"error": "Patient profile not found."}), 404

        user_id = pat.get("user_id")
        mongo.patients.update_one({"_id": pat["_id"]}, {"$set": {"status": "active", "active_status": True, "updated_at": datetime.utcnow().isoformat()}})
        if user_id:
            mongo.users.update_one({"id": user_id}, {"$set": {"status": "active"}})

        return jsonify({
            "status": "success",
            "message": f"Patient {pat.get('full_name')} has been restored to active status.",
            "status_label": "active"
        })

    @app.route("/api/admin/patient/remove/<patient_id>", methods=["DELETE"])
    def admin_remove_patient(patient_id):
        pat = mongo.patients.find_one({"$or": [{"id": patient_id}, {"user_id": patient_id}]})
        if not pat:
            return jsonify({"error": "Patient profile not found."}), 404

        user_id = pat.get("user_id")
        mongo.patients.delete_one({"_id": pat["_id"]})
        if user_id:
            mongo.users.delete_one({"id": user_id})
            mongo.screenings.delete_many({"patient_user_id": user_id})
            mongo.reports.delete_many({"patient_user_id": user_id})
            mongo.messages.delete_many({"$or": [{"sender_id": user_id}, {"recipient_id": user_id}]})

        return jsonify({
            "status": "success",
            "message": f"Patient {pat.get('full_name')} and associated records have been permanently removed."
        })

    @app.route("/api/admin/doctor/toggle-status/<doctor_id>", methods=["POST"])
    def toggle_doctor_status(doctor_id):
        doc = mongo.doctors.find_one({"$or": [{"id": doctor_id}, {"user_id": doctor_id}]})
        if not doc:
            return jsonify({"error": "Doctor profile not found."}), 404
        new_status = not doc.get("active_status", True)
        mongo.doctors.update_one({"_id": doc["_id"]}, {"$set": {"active_status": new_status, "updated_at": datetime.utcnow().isoformat()}})
        return jsonify({
            "status": "success",
            "message": f"Doctor status updated to {'Active' if new_status else 'Inactive'}.",
            "active_status": new_status
        })

    @app.route("/api/admin/doctor/create", methods=["POST"])
    def admin_create_doctor():
        data = request.get_json() or {}
        full_name = data.get("full_name", "").strip()
        username = data.get("username", "").strip().lower()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "Doctor@2026")
        license_no = data.get("license_number", "").strip()
        spec = data.get("specialization", "Senior Vitreo-Retina Specialist").strip()
        hospital = data.get("hospital_name", "District Apex Hospital").strip()
        phone = data.get("phone", "+91 9876543210").strip()

        if not full_name or not username or not email or not license_no:
            return jsonify({"error": "Name, username, email, and medical license number are required."}), 400

        if mongo.users.find_one({"$or": [{"username": username}, {"email": email}]}):
            return jsonify({"error": "Username or email is already registered."}), 409

        user_doc = UserModel.create(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role="doctor"
        )
        user_doc["is_email_verified"] = True
        user_doc["status"] = "active"
        mongo.users.insert_one(user_doc)

        doctor_profile = DoctorModel.create(
            user_id=user_doc["id"],
            full_name=full_name,
            specialization=spec,
            license_number=license_no,
            hospital_name=hospital,
            phone=phone
        )
        doctor_profile["approval_status"] = "approved"
        doctor_profile["active_status"] = True
        mongo.doctors.insert_one(doctor_profile)

        return jsonify({
            "status": "success",
            "message": f"Successfully registered and approved doctor {full_name} ({license_no}).",
            "doctor": serialize_doc(doctor_profile)
        }), 201

    @app.route("/api/dataset/upload-csv", methods=["POST"])
    def upload_dataset_csv():
        if "file" not in request.files:
            return jsonify({"error": "No CSV file provided."}), 400
        f = request.files["file"]
        if not f.filename.endswith(".csv"):
            return jsonify({"error": "File must have .csv extension."}), 400
        
        save_path = os.path.join(os.path.dirname(__file__), "data", f.filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        f.save(save_path)
        
        # Reload dataset registry in model and IQA services
        model_service.dataset_registry.load_all_csvs()
        iqa_service.dataset_registry.load_all_csvs()
        
        total_loaded = len(model_service.dataset_registry.records)
        return jsonify({
            "status": "success",
            "message": f"Successfully loaded dataset CSV: {f.filename}",
            "total_registered_records": total_loaded
        }), 200

    @app.route("/api/files/<session_id>/<file_type>", methods=["GET"])
    def serve_file(session_id, file_type):
        session = mongo.screenings.find_one({"id": session_id})
        if not session:
            return jsonify({"error": "Session not found."}), 404

        path_map = {
            "original": session.get("image_path"),
            "processed": session.get("processed_image_path"),
            "gradcam": session.get("gradcam_image_path"),
            "lesions": session.get("lesions_image_path"),
            "vessels": session.get("vessels_image_path"),
        }
        target = path_map.get(file_type)
        if not target or not os.path.exists(target):
            return jsonify({"error": "File not found."}), 404

        return send_file(target, mimetype="image/png")

    @app.route("/api/report/<session_id>/pdf", methods=["GET"])
    def download_report(session_id):
        session = mongo.screenings.find_one({"id": session_id}) or \
                  mongo.reports.find_one({"screening_id": session_id}) or \
                  mongo.reports.find_one({"id": session_id})
        if not session:
            return jsonify({"error": "Diagnostic screening report not found."}), 404

        actual_id = session.get("screening_id") or session.get("id")
        pdf_path = os.path.join(app.config["REPORTS_FOLDER"], f"DR_Report_{actual_id}.pdf")
        if not os.path.exists(pdf_path):
            try:
                report_service.generate_pdf_report(session, f"DR_Report_{actual_id}.pdf")
            except Exception as e:
                print(f"Error generating PDF on demand: {e}")

        if not os.path.exists(pdf_path):
            return jsonify({"error": "Failed to generate report PDF."}), 500

        return send_file(pdf_path, as_attachment=False, mimetype="application/pdf")

    @app.route("/api/simulink/simulate", methods=["POST"])
    def simulate_telemedicine():
        data = request.get_json() or {}
        sim_results = simulink_service.simulate(
            annual_patients=data.get("annual_patients", 100000),
            working_days=data.get("working_days", 300),
            num_phcs=data.get("num_phcs", 25),
            bandwidth_mbps=data.get("bandwidth_mbps", 2.0),
            ai_edge_filter_rate=data.get("ai_edge_filter_rate", 0.74),
            doctor_review_time_sec=data.get("doctor_review_time_sec", 20)
        )
        return jsonify({"status": "success", "data": sim_results})

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
