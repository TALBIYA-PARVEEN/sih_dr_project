from pymongo import MongoClient
from config import Config
from services.auth_service import AuthService
from flask import Flask

app = Flask(__name__)
app.config.from_object(Config)

client = MongoClient(Config.MONGO_URI)
db = client[Config.MONGO_DB_NAME]

user = db.users.find_one({"email": "parveentalbiya2005@gmail.com"})
print("=== USER IN DB ===")
print("Username:", user.get("username") if user else "Not found")
print("Full Name:", user.get("full_name") if user else "")
print("Email:", user.get("email") if user else "")
print("Role:", user.get("role") if user else "")
print("Status:", user.get("status") if user else "")
print("OTP Code in DB:", user.get("otp_code") if user else "")
print("Is Verified:", user.get("is_email_verified") if user else "")

if user:
    otp = user.get("otp_code")
    print(f"\nAttempting to send live email with OTP {otp} to parveentalbiya2005@gmail.com...")
    with app.app_context():
        success = AuthService.send_otp_email("parveentalbiya2005@gmail.com", otp, purpose="Doctor Registration Verification")
    print("Email Delivery Success Status:", success)
