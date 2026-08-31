# NetraAI Tele-Ophthalmology Database & Data Architecture (ER Model)
**Database:** MongoDB Atlas Cloud Cluster (`NetraAI-db`)

---

## 1. Corrected Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    USERS ||--o| PATIENTS : "role: 'patient'"
    USERS ||--o| DOCTORS : "role: 'doctor'"
    USERS ||--o| ADMINS : "role: 'admin'"
    
    PATIENTS ||--o{ SCREENINGS : "submits retinal scan"
    
    SCREENINGS ||--|| REPORTS : "provides imaging & AI evidence"
    DOCTORS ||--o{ REPORTS : "evaluates, authors & signs off"
    PATIENTS ||--o{ REPORTS : "receives diagnostic report"
    
    PATIENTS ||--o{ MESSAGES : "tele-consults"
    DOCTORS ||--o{ MESSAGES : "provides clinical advice"
    SCREENINGS ||--o{ MESSAGES : "references case"

    USERS {
        string id PK "Unique User UUID"
        string username "Unique Login Username"
        string email "Unique Email Address"
        string password_hash "Argon2/SHA256 Encrypted Hash"
        string full_name "Full Registered Name"
        string role "admin | doctor | patient"
        boolean is_email_verified "OTP Verified Flag"
        string created_at "Account Creation Timestamp"
    }

    PATIENTS {
        string id PK "Patient Profile ID"
        string user_id FK "References USERS.id"
        string full_name "Patient Full Name"
        int age "Patient Age"
        string gender "Female | Male | Other"
        string phone "Patient Mobile Number"
        string assigned_doctor_id FK "References DOCTORS.id"
        int total_screenings "Count of Scans Taken"
        string created_at "Profile Creation Timestamp"
    }

    DOCTORS {
        string id PK "Doctor Profile ID"
        string user_id FK "References USERS.id"
        string full_name "Doctor Full Name"
        string specialization "e.g. Vitreo-Retina Specialist"
        string hospital_name "Affiliated Hospital / PHC Center"
        string license_number "Medical Council Reg Number"
        string phone "Clinical Contact Number"
        boolean active_status "Available for Tele-Consultation"
        string created_at "Doctor Registration Timestamp"
    }

    ADMINS {
        string id PK "Admin Profile ID"
        string user_id FK "References USERS.id"
        string full_name "Admin Full Name"
        string email "Admin Official Email"
        string district_jurisdiction "National District Level"
        string telemetry_access_level "SuperAdmin"
        string created_at "Creation Timestamp"
    }

    SCREENINGS {
        string id PK "Screening Session UUID"
        string patient_id FK "References PATIENTS.id"
        string image_path "Original Fundus Image File"
        string processed_image_path "Ben Graham + CLAHE Image File"
        string lesions_image_path "YOLO Biomarkers Map"
        string vessels_image_path "Frangi Vessel Mask"
        string gradcam_image_path "Grad-CAM Saliency Heatmap"
        json quality_assessment "Focus, Illumination, FOV, Verdict"
        boolean is_gradable "True if image passes IQA check"
        json ai_prediction "CNN ICDR Grade (0-4), Confidence"
        json biomarkers_count "Microaneurysms, Exudates, Hemorrhages"
        string created_at "Screening ISO Timestamp"
    }

    REPORTS {
        string id PK "Official Diagnostic Report UUID"
        string screening_id FK "References SCREENINGS.id"
        string patient_id FK "References PATIENTS.id"
        string doctor_id FK "References DOCTORS.id (Author & Signer)"
        string doctor_name "Doctor Full Name & Credentials"
        int final_severity_grade "ICDR Level (0: Normal to 4: PDR)"
        string final_severity_name "ICDR Severity Label"
        float confidence_pct "Diagnostic Accuracy %"
        boolean is_referable "Specialist Referral Required Flag"
        string triage_action "Clinical Directive (e.g. Urgent Laser/Anti-VEGF)"
        string clinical_status "Confirmed | Overruled | Needs Recapture"
        string doctor_notes "Ophthalmologist Clinical Directives"
        string pdf_report_url "Official EMR PDF Download URL"
        string signed_at "Doctor Sign-off Timestamp"
        string created_at "Report Creation Timestamp"
    }

    MESSAGES {
        string id PK "Message UUID"
        string sender_id FK "References USERS.id"
        string recipient_id FK "References USERS.id"
        string screening_id FK "References SCREENINGS.id"
        string content "Tele-consultation text dialogue"
        boolean is_read "Message Read Status"
        string created_at "Message Timestamp"
    }
```

---

## 2. Explanation of Key Design Decisions

1. **Why `DOCTORS` is directly connected to `REPORTS`:**
   * A diagnostic report is a **legal medical document**. While AI provides evidence in `SCREENINGS`, the **Doctor** in `DOCTORS` evaluates, validates, enters clinical directives, and officially signs off on the report in `REPORTS`.

2. **Why Notifications were merged into `MESSAGES`:**
   * Having separate `notifications` and `messages` collections was redundant. All tele-consultations, doctor alerts, and clinical communications are now unified directly inside the **`messages`** collection.
