import os
import urllib.parse
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "sih_dr_telemedicine_screening_secret_2026")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "sih_jwt_super_secret_key_2026")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get("JWT_EXPIRATION_HOURS", 24)))

    # MongoDB Atlas Cloud Connection URI
    MONGO_URI = os.environ.get(
        "MONGO_URI",
        "mongodb+srv://2k24cs1q2413756_db_user:NetraAI2026@cluster0.orlzz77.mongodb.net/NetraAI-db?retryWrites=true&w=majority&appName=Cluster0"
    )
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "NetraAI-db")

    # 1 Master Admin Configuration
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@teleophta.org")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@SIH2026")
    ADMIN_NAME = os.environ.get("ADMIN_NAME", "Master District Admin")

    # Google OAuth 2.0 Client ID
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "387784977439-ql7h183e12mgdvbfpcd2061d411p269c.apps.googleusercontent.com")

    # Resend & Brevo HTTPS REST API (Port 443 - Cloud Delivery)
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    RESEND_FROM = os.environ.get("RESEND_FROM", "Netra Setu Healthcare <onboarding@resend.dev>")
    BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")

    # Email / SMTP Configuration for Real OTP Delivery
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() in ["true", "1"]
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "2k24.cs1q.2413756@gmail.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "tyhelznlhlknqowp")

    # Upload and Model Paths
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    PROCESSED_FOLDER = os.path.join(BASE_DIR, "processed")
    REPORTS_FOLDER = os.path.join(BASE_DIR, "reports")
    MODEL_WEIGHTS_PATH = os.environ.get(
        "MODEL_WEIGHTS_PATH",
        os.path.join(BASE_DIR, "weights", "sih_dr_best_model.pt")
    )
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "tif", "tiff", "bmp"}

for folder in [Config.UPLOAD_FOLDER, Config.PROCESSED_FOLDER, Config.REPORTS_FOLDER, os.path.join(BASE_DIR, "weights")]:
    os.makedirs(folder, exist_ok=True)
