import os
import json
import base64
import hmac
import hashlib
import random
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import current_app

try:
    import jwt
    HAS_PYJWT = True
except ImportError:
    HAS_PYJWT = False

class AuthService:
    @staticmethod
    def generate_jwt(user):
        """Generates a secure JWT / token for a user session."""
        secret = current_app.config.get("JWT_SECRET_KEY", "sih_jwt_super_secret_key_2026")
        exp_seconds = int(current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", timedelta(hours=24)).total_seconds())

        if isinstance(user, dict):
            sub = str(user.get("id", ""))
            username = user.get("username", "")
            email = user.get("email", "")
            role = user.get("role", "patient")
            is_doctor = user.get("is_doctor", False)
        else:
            sub = str(getattr(user, "id", ""))
            username = getattr(user, "username", "")
            email = getattr(user, "email", "")
            role = getattr(user, "role", "patient")
            is_doctor = getattr(user, "is_doctor", False)

        payload = {
            "sub": sub,
            "username": username,
            "email": email,
            "role": role,
            "is_doctor": is_doctor,
            "exp": int(time.time()) + exp_seconds,
            "iat": int(time.time())
        }

        if HAS_PYJWT:
            return jwt.encode(payload, secret, algorithm="HS256")
        else:
            header_b64 = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
            payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
            signature = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
            sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
            return f"{header_b64}.{payload_b64}.{sig_b64}"

    @staticmethod
    def decode_jwt(token):
        """Decodes and validates a token."""
        secret = current_app.config.get("JWT_SECRET_KEY", "sih_jwt_super_secret_key_2026")
        if not token:
            return None

        if HAS_PYJWT:
            try:
                return jwt.decode(token, secret, algorithms=["HS256"])
            except Exception:
                return None
        else:
            try:
                parts = token.split(".")
                if len(parts) != 3: return None
                header_b64, payload_b64, sig_b64 = parts
                expected_sig = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
                expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
                if not hmac.compare_digest(sig_b64, expected_sig_b64):
                    return None

                padding = "=" * (4 - (len(payload_b64) % 4))
                payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding).decode())
                if payload.get("exp", 0) < int(time.time()):
                    return None
                return payload
            except Exception:
                return None

    @staticmethod
    def verify_google_token(id_token_str):
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
            client_id = current_app.config.get("GOOGLE_CLIENT_ID")
            id_info = id_token.verify_oauth2_token(
                id_token_str, google_requests.Request(), client_id
            )
            return {
                "google_id": id_info.get("sub"),
                "email": id_info.get("email"),
                "name": id_info.get("name"),
                "picture": id_info.get("picture")
            }
        except Exception as e:
            print(f"[AUTH] Google OAuth note: {e}")
            return None

    @staticmethod
    def generate_otp():
        return f"{random.randint(100000, 999999)}"

    @staticmethod
    def send_otp_email(to_email, otp_code, purpose="verification"):
        """Sends real email OTP via Gmail SMTP using multipart plain + HTML."""
        mail_server = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
        mail_port = int(current_app.config.get("MAIL_PORT", 587))
        mail_user = current_app.config.get("MAIL_USERNAME", "").strip()
        mail_pass = current_app.config.get("MAIL_PASSWORD", "").strip()

        subject = f"NetraAI Verification Code: {otp_code}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
            <div style="max-width: 500px; margin: auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h2 style="color: #4338ca; margin: 0; font-size: 22px;">NetraAI Tele-Ophthalmology</h2>
                    <p style="color: #64748b; font-size: 13px; margin-top: 4px;">National DR Screening & Diagnostics Network</p>
                </div>
                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 15px 0;">
                <p style="font-size: 14px; color: #334155;">Hello,</p>
                <p style="font-size: 14px; color: #334155;">Your 6-digit verification code to complete your registration / login is:</p>
                <div style="text-align: center; margin: 25px 0;">
                    <span style="display: inline-block; font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #4338ca; background: #eef2ff; padding: 12px 24px; border-radius: 12px; border: 1px dashed #818cf8;">
                        {otp_code}
                    </span>
                </div>
                <p style="font-size: 12px; color: #64748b; text-align: center;">This code is valid for 15 minutes. Please do not share it with anyone.</p>
                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 20px 0;">
                <p style="font-size: 11px; color: #94a3b8; text-align: center;">Smart India Hackathon (SIH 2026) • Rural Healthcare AI Deployment</p>
            </div>
        </body>
        </html>
        """

        text_body = f"Your NetraAI Verification Code is: {otp_code}\n\nValid for 15 minutes.\nSmart India Hackathon 2026."

        if mail_user and mail_pass:
            try:
                from email.utils import formatdate, make_msgid

                msg = MIMEMultipart("alternative")
                msg["From"] = f"NetraAI Screening <{mail_user}>"
                msg["To"] = to_email
                msg["Reply-To"] = mail_user
                msg["Subject"] = subject
                msg["Date"] = formatdate(localtime=True)
                msg["Message-ID"] = make_msgid(domain="teleophta.org")
                msg["X-Mailer"] = "NetraAI-SIH2026-Platform"

                msg.attach(MIMEText(text_body, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))

                with smtplib.SMTP(mail_server, mail_port, timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(mail_user, mail_pass)
                    server.sendmail(mail_user, [to_email], msg.as_string())

                print(f"[EMAIL-SENT] Successfully delivered OTP {otp_code} to {to_email}")
                return True
            except Exception as e:
                print(f"[EMAIL-SMTP-ERROR] Failed to send email to {to_email}: {e}")
                return False
        else:
            print(f"[DEV-FALLBACK] SMTP not configured. OTP for {to_email}: {otp_code}")
            return True

    @staticmethod
    def send_doctor_approval_email(to_email, doctor_name, hospital_name="District Eye Hospital", license_number="MCI-VERIFIED"):
        """Sends official confirmation email to the doctor when Master Admin approves their registration."""
        mail_server = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
        mail_port = int(current_app.config.get("MAIL_PORT", 587))
        mail_user = current_app.config.get("MAIL_USERNAME", "").strip()
        mail_pass = current_app.config.get("MAIL_PASSWORD", "").strip()

        subject = "Official Account Approval • NetraAI Tele-Ophthalmology Network"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
            <div style="max-width: 520px; margin: auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 20px; padding: 32px; box-shadow: 0 6px 18px rgba(0,0,0,0.06);">
                <div style="text-align: center; margin-bottom: 24px;">
                    <div style="width: 56px; height: 56px; background-color: #ecfdf5; color: #059669; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 28px; line-height: 56px; margin-bottom: 12px;">
                        ✓
                    </div>
                    <h2 style="color: #065f46; margin: 0; font-size: 22px;">Doctor Registration Approved</h2>
                    <p style="color: #64748b; font-size: 13px; margin-top: 4px;">National Tele-Ophthalmology Diagnostic Network</p>
                </div>
                
                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 16px 0;">
                
                <p style="font-size: 14px; color: #334155;">Dear <b>{doctor_name}</b>,</p>
                
                <p style="font-size: 14px; color: #334155; line-height: 1.6;">
                    Your professional clinical credentials (License: <code style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px; color: #4338ca; font-weight: bold;">{license_number}</code>) have been officially verified and <b>APPROVED</b> by the District Healthcare Administration.
                </p>

                <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 14px; padding: 18px; margin: 20px 0;">
                    <p style="margin: 0 0 8px 0; font-size: 13px; font-weight: bold; color: #166534;">You now have full clinical clearance to:</p>
                    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #14532d; line-height: 1.6;">
                        <li>Evaluate assigned fundus image screening queues</li>
                        <li>Verify AI lesion classifications (Microaneurysms, Hemorrhages, Exudates)</li>
                        <li>Electronically sign diagnostic reports and telemedicine referrals</li>
                        <li>Conduct real-time tele-consultations with diabetic patients</li>
                    </ul>
                </div>

                <div style="text-align: center; margin: 28px 0;">
                    <a href="http://127.0.0.1:5000" style="background-color: #059669; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 10px; font-weight: bold; font-size: 14px; display: inline-block;">
                        Log In to Doctor Review Portal
                    </a>
                </div>

                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 20px 0;">
                <p style="font-size: 11px; color: #94a3b8; text-align: center; margin: 0;">
                    Smart India Hackathon (SIH 2026) • District Tele-Ophthalmology Network • Confidential Medical Communication
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""Official Approval Notification - NetraAI Tele-Ophthalmology

Dear {doctor_name},

Your clinical credentials ({license_number}, {hospital_name}) have been officially APPROVED by the District Master Admin.

You may now log in to the NetraAI Doctor Portal to examine assigned patient fundus screenings and sign diagnostic reports.

Login URL: http://127.0.0.1:5000
Smart India Hackathon 2026."""

        if mail_user and mail_pass:
            try:
                from email.utils import formatdate, make_msgid
                msg = MIMEMultipart("alternative")
                msg["From"] = f"NetraAI Administration <{mail_user}>"
                msg["To"] = to_email
                msg["Reply-To"] = mail_user
                msg["Subject"] = subject
                msg["Date"] = formatdate(localtime=True)
                msg["Message-ID"] = make_msgid(domain="teleophta.org")
                msg["X-Mailer"] = "NetraAI-SIH2026-Platform"

                msg.attach(MIMEText(text_body, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))

                with smtplib.SMTP(mail_server, mail_port, timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(mail_user, mail_pass)
                    server.sendmail(mail_user, [to_email], msg.as_string())

                print(f"[EMAIL-SENT] Successfully delivered Doctor Approval Email to {to_email}")
                return True
            except Exception as e:
                print(f"[EMAIL-SMTP-ERROR] Failed to send Doctor Approval email to {to_email}: {e}")
                return False
        else:
            print(f"[DEV-FALLBACK] SMTP not configured. Doctor Approval for {to_email}")
            return True
