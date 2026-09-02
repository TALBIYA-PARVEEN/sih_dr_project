import os
import uuid
import json
import base64
import hmac
import hashlib
import random
import time
import smtplib
import threading
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
            is_doctor = (role == "doctor")
        else:
            sub = str(getattr(user, "id", ""))
            username = getattr(user, "username", "")
            email = getattr(user, "email", "")
            role = getattr(user, "role", "patient")
            is_doctor = (role == "doctor")

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
    def validate_password_strength(password):
        """
        Enforces strict strong password security:
        - Minimum 8 characters
        - At least 1 uppercase letter (A-Z)
        - At least 1 lowercase letter (a-z)
        - At least 1 number (0-9)
        - At least 1 special character (@, $, !, %, *, #, etc.)
        """
        import re
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter (A-Z)."
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter (a-z)."
        if not re.search(r"[0-9]", password):
            return False, "Password must contain at least one number (0-9)."
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]", password):
            return False, "Password must contain at least one special character (e.g. @, #, $, %, !, *)."
        return True, None

    @staticmethod
    def generate_otp():
        return f"{random.randint(100000, 999999)}"

    @staticmethod
    def _deliver_email(to_email, subject, text_body, html_body=None):
        """High-reliability delivery via HTTPS REST API (Google Relay / Brevo / Resend) with fast SMTP fallback."""
        # 0. Primary Cloud Gateway: Google Apps Script HTTPS Mail Relay (Sends to ANY email via Gmail's servers on Port 443)
        gmail_relay_url = os.environ.get("GMAIL_RELAY_URL", "").strip()
        if not gmail_relay_url:
            try:
                gmail_relay_url = current_app.config.get("GMAIL_RELAY_URL", "").strip()
            except Exception:
                pass

        if gmail_relay_url:
            try:
                import requests
                payload = {
                    "to": to_email,
                    "subject": subject,
                    "body": text_body,
                    "htmlBody": html_body if html_body else text_body
                }
                r = requests.post(gmail_relay_url, json=payload, timeout=8.0, allow_redirects=True)
                if r.status_code in [200, 201, 302]:
                    print(f"[GMAIL-RELAY-SUCCESS] Delivered '{subject}' to {to_email} via Google Apps Script Relay!")
                    return True
                else:
                    print(f"[GMAIL-RELAY-NOTE] Status {r.status_code}: {r.text}")
            except Exception as e_relay:
                print(f"[GMAIL-RELAY-ERROR] {e_relay}")

        # 1. Secondary Cloud Gateway: Brevo HTTPS REST API (Port 443 - Sends to ANY email worldwide without domain requirement)
        brevo_api_key = os.environ.get("BREVO_API_KEY", "").strip()
        if not brevo_api_key:
            try:
                brevo_api_key = current_app.config.get("BREVO_API_KEY", "").strip()
            except Exception:
                pass

        if brevo_api_key:
            try:
                import requests
                headers = {
                    "api-key": brevo_api_key,
                    "Content-Type": "application/json"
                }
                payload = {
                    "sender": {"name": "Netra Setu Healthcare", "email": "2k24.cs1q.2413756@gmail.com"},
                    "to": [{"email": to_email}],
                    "subject": subject,
                    "textContent": text_body
                }
                if html_body:
                    payload["htmlContent"] = html_body
                r = requests.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=5.0)
                if r.status_code in [200, 201]:
                    print(f"[BREVO-HTTPS-SUCCESS] Delivered '{subject}' to {to_email} via Brevo API!")
                    return True
                else:
                    print(f"[BREVO-API-NOTE] Status {r.status_code}: {r.text}")
            except Exception as e_brevo:
                print(f"[BREVO-API-ERROR] {e_brevo}")

        # 2. Tertiary Cloud Gateway: Resend HTTPS REST API (Port 443)
        resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
        if not resend_api_key:
            try:
                resend_api_key = current_app.config.get("RESEND_API_KEY", "").strip()
            except Exception:
                pass

        if resend_api_key:
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "from": os.environ.get("RESEND_FROM", "Netra Setu Healthcare <onboarding@resend.dev>"),
                    "to": [to_email],
                    "subject": subject,
                    "text": text_body
                }
                if html_body:
                    payload["html"] = html_body
                r = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=5.0)
                if r.status_code in [200, 201]:
                    print(f"[RESEND-HTTPS-SUCCESS] Delivered '{subject}' to {to_email} via Resend API!")
                    return True
                else:
                    print(f"[RESEND-API-NOTE] Status {r.status_code}: {r.text}")
            except Exception as e_resend:
                print(f"[RESEND-API-ERROR] {e_resend}")

        # 3. Standard SMTP (Local / VPS)
        mail_server = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
        mail_user = os.environ.get("MAIL_USERNAME", "2k24.cs1q.2413756@gmail.com").strip()
        mail_pass = os.environ.get("MAIL_PASSWORD", "tyhelznlhlknqowp").strip()

        if mail_user and mail_pass:
            try:
                from email.message import EmailMessage
                msg = EmailMessage()
                msg["Subject"] = subject
                msg["From"] = mail_user
                msg["To"] = to_email
                msg.set_content(text_body)
                if html_body:
                    msg.add_alternative(html_body, subtype="html")

                # Fast port 465 attempt (2s timeout)
                try:
                    with smtplib.SMTP_SSL(mail_server, 465, timeout=2.0) as s:
                        s.login(mail_user, mail_pass)
                        s.send_message(msg)
                    print(f"[EMAIL-SENT] Delivered '{subject}' to {to_email} via Port 465 (SSL)")
                    return True
                except Exception as e_ssl:
                    pass

                # Fast port 587 attempt (2s timeout)
                try:
                    with smtplib.SMTP(mail_server, 587, timeout=2.0) as s:
                        s.ehlo()
                        s.starttls()
                        s.ehlo()
                        s.login(mail_user, mail_pass)
                        s.send_message(msg)
                    print(f"[EMAIL-SENT] Delivered '{subject}' to {to_email} via Port 587 (TLS)")
                    return True
                except Exception as e_tls:
                    pass
            except Exception as e:
                print(f"[EMAIL-SMTP-ERROR] {e}")

        return False

    @staticmethod
    def send_otp_email(to_email, otp_code, purpose="verification"):
        """Sends clean email OTP via Resend HTTPS API / SMTP in a background worker."""
        subject = f"Your Netra Setu Verification Code: {otp_code}"
        text_body = f"Hello,\n\nYour Netra Setu verification code is: {otp_code}\n\nThis code is valid for 15 minutes.\n\nThank you,\nNetra Setu Tele-Ophthalmology Team"
        html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
  <div style="max-width: 480px; margin: auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; text-align: center;">
    <h3 style="color: #4338ca; margin-bottom: 12px;">Netra Setu Tele-Ophthalmology</h3>
    <p style="color: #475569; font-size: 14px;">Your 6-digit verification code is:</p>
    <div style="display: inline-block; font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #4338ca; background: #eef2ff; padding: 12px 24px; border-radius: 10px; margin: 16px 0;">
      {otp_code}
    </div>
    <p style="color: #64748b; font-size: 12px;">This code is valid for 15 minutes. Please do not share it with anyone.</p>
  </div>
</body>
</html>"""
        import threading
        t = threading.Thread(target=AuthService._deliver_email, args=(to_email, subject, text_body, html_body))
        t.daemon = True
        t.start()
        return True

    @staticmethod
    def send_doctor_credentials_email(to_email, doctor_name, username, password, hospital_name="District Eye Hospital", license_number="MCI-VERIFIED"):
        """Sends official credentials and login access email when Master Admin registers a new doctor."""
        subject = "Doctor Account Credentials & Clinical Clearance • Netra Setu"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
            <div style="max-width: 540px; margin: auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 20px; padding: 32px; box-shadow: 0 6px 20px rgba(0,0,0,0.06);">
                <div style="text-align: center; margin-bottom: 24px;">
                    <div style="width: 56px; height: 56px; background-color: #ecfdf5; color: #059669; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 28px; line-height: 56px; margin-bottom: 12px;">
                        🩺
                    </div>
                    <h2 style="color: #065f46; margin: 0; font-size: 22px;">Doctor Clinical Account Created</h2>
                    <p style="color: #64748b; font-size: 13px; margin-top: 4px;">National Tele-Ophthalmology Diagnostic Network</p>
                </div>
                
                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 16px 0;">
                
                <p style="font-size: 14px; color: #334155;">Dear <b>{doctor_name}</b>,</p>
                
                <p style="font-size: 14px; color: #334155; line-height: 1.6;">
                    An authorized clinical doctor account has been provisioned for you by the <b>District Healthcare Administration</b>. You are officially verified for <b>{hospital_name}</b> (License: <code style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px; color: #4338ca; font-weight: bold;">{license_number}</code>).
                </p>

                <!-- Credentials Box -->
                <div style="background-color: #eef2ff; border: 1px solid #c7d2fe; border-radius: 14px; padding: 18px; margin: 20px 0;">
                    <div style="font-size: 12px; font-weight: bold; color: #3730a3; text-transform: uppercase;">Your Doctor Portal Login Credentials:</div>
                    
                    <div style="background: #ffffff; border: 1px solid #e0e7ff; border-radius: 10px; padding: 12px; font-family: monospace; font-size: 13px; color: #1e1b4b; margin-top: 10px;">
                        <div><b>Login Email / Username:</b> {to_email} <i>(or {username})</i></div>
                        <div style="margin-top: 6px;"><b>Password:</b> <span style="background: #e0e7ff; padding: 2px 8px; border-radius: 6px; font-weight: bold; color: #312e81;">{password}</span></div>
                    </div>
                </div>

                <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 14px; padding: 16px; margin: 20px 0;">
                    <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: bold; color: #166534;">Your Active Clinical Privileges:</p>
                    <ul style="margin: 0; padding-left: 20px; font-size: 12px; color: #14532d; line-height: 1.6;">
                        <li>Perform walk-in patient retinal fundus examinations</li>
                        <li>Evaluate assigned AI triage screening queues in real time</li>
                        <li>Electronically sign & stamp diagnostic reports</li>
                        <li>Conduct tele-consultations with diabetic patients</li>
                    </ul>
                </div>

                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 20px 0;">
                <p style="font-size: 11px; color: #94a3b8; text-align: center; margin: 0;">
                    Smart India Hackathon (SIH 2026) • District Tele-Ophthalmology Network • Confidential Medical Communication
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""Official Doctor Account Credentials - Netra Setu Tele-Ophthalmology

Dear {doctor_name},

An authorized clinical doctor account has been provisioned for you by the District Healthcare Administration.
Hospital: {hospital_name}
License: {license_number}

Your Doctor Portal Login Credentials:
Email / Username: {to_email} (or {username})
Password: {password}

You may now log in to the Netra Setu Doctor Portal to examine patient screenings and sign diagnostic reports.
Smart India Hackathon 2026."""

        import threading
        t = threading.Thread(target=AuthService._deliver_email, args=(to_email, subject, text_body, html_body))
        t.daemon = True
        t.start()
        return True

    @staticmethod
    def send_doctor_approval_email(to_email, doctor_name, hospital_name="District Eye Hospital", license_number="MCI-VERIFIED"):
        """Sends official confirmation email to the doctor when Master Admin approves their registration."""
        subject = "Official Account Approval • Netra Setu Tele-Ophthalmology Network"

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

                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 20px 0;">
                <p style="font-size: 11px; color: #94a3b8; text-align: center; margin: 0;">
                    Smart India Hackathon (SIH 2026) • District Tele-Ophthalmology Network • Confidential Medical Communication
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""Official Approval Notification - Netra Setu Tele-Ophthalmology

Dear {doctor_name},

Your clinical credentials ({license_number}, {hospital_name}) have been officially APPROVED by the District Master Admin.

You may now log in to the Netra Setu Doctor Portal to examine assigned patient fundus screenings and sign diagnostic reports.
Smart India Hackathon 2026."""

        import threading
        t = threading.Thread(target=AuthService._deliver_email, args=(to_email, subject, text_body, html_body))
        t.daemon = True
        t.start()
        return True

    @staticmethod
    def send_patient_welcome_report_email(to_email, patient_name, temp_password, doctor_name, severity_name, doctor_notes="", pdf_filename=""):
        """Sends patient diagnostic report notification along with login credentials to view past scans & consult doctor."""
        if temp_password:
            subject = f"Your Diabetic Retinopathy Diagnostic Report & Login Credentials • Netra Setu"
            credentials_box = f"""
                <div style="background-color: #eef2ff; border: 1px solid #c7d2fe; border-radius: 14px; padding: 18px; margin: 20px 0;">
                    <div style="font-size: 12px; font-weight: bold; color: #3730a3; text-transform: uppercase;">Your Patient Portal Login Credentials:</div>
                    <p style="font-size: 13px; color: #4338ca; margin: 6px 0 12px 0;">Use these credentials to view your full retina scans, download PDF reports, and chat directly with your ophthalmologist from home.</p>
                    
                    <div style="background: #ffffff; border: 1px solid #e0e7ff; border-radius: 10px; padding: 12px; font-family: monospace; font-size: 13px; color: #1e1b4b;">
                        <div><b>Email/Username:</b> {to_email}</div>
                        <div style="margin-top: 4px;"><b>Temporary Password:</b> <span style="background: #e0e7ff; padding: 2px 8px; border-radius: 6px; font-weight: bold; color: #312e81;">{temp_password}</span></div>
                    </div>
                </div>
            """
            credentials_text = f"Your Patient Portal Login Credentials:\nEmail/Username: {to_email}\nPassword: {temp_password}"
        else:
            subject = f"Your New Diabetic Retinopathy Diagnostic Report • Netra Setu"
            credentials_box = f"""
                <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 14px; padding: 18px; margin: 20px 0;">
                    <div style="font-size: 12px; font-weight: bold; color: #166534; text-transform: uppercase;">Scan Added to Your Existing Patient Portal:</div>
                    <p style="font-size: 13px; color: #15803d; margin: 6px 0 12px 0;">This new retinal screening and clinical examination has been linked to your existing Netra Setu patient account.</p>
                    
                    <div style="background: #ffffff; border: 1px solid #dcfce7; border-radius: 10px; padding: 12px; font-size: 13px; color: #14532d;">
                        <div><b>Login Email:</b> {to_email}</div>
                        <div style="margin-top: 4px;"><b>Password:</b> Log in using your existing account password (or reset anytime via Email OTP).</div>
                    </div>
                </div>
            """
            credentials_text = f"Scan Added to Your Existing Patient Portal Account ({to_email}). Log in using your existing password to view your updated records."

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
            <div style="max-width: 540px; margin: auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 20px; padding: 32px; box-shadow: 0 6px 20px rgba(0,0,0,0.06);">
                <div style="text-align: center; margin-bottom: 24px;">
                    <div style="width: 56px; height: 56px; background-color: #e0e7ff; color: #4338ca; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 26px; line-height: 56px; margin-bottom: 12px;">
                        👁️
                    </div>
                    <h2 style="color: #312e81; margin: 0; font-size: 22px;">Retinal Screening Diagnostic Report</h2>
                    <p style="color: #64748b; font-size: 13px; margin-top: 4px;">National Tele-Ophthalmology Healthcare Network</p>
                </div>
                
                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 16px 0;">
                
                <p style="font-size: 14px; color: #334155;">Hello <b>{patient_name}</b>,</p>
                
                <p style="font-size: 14px; color: #334155; line-height: 1.6;">
                    Your retinal fundus examination conducted by <b>{doctor_name}</b> has been completed and processed through our AI diagnostic workstation.
                </p>

                <!-- Diagnosis Summary Box -->
                <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 14px; padding: 18px; margin: 20px 0;">
                    <div style="font-size: 11px; font-weight: bold; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">Diagnosis Result</div>
                    <div style="font-size: 17px; font-weight: bold; color: #1e293b; margin-top: 4px;">{severity_name}</div>
                    
                    {f'<div style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #e2e8f0; font-size: 13px; color: #475569;"><b>Doctor Clinical Notes:</b> {doctor_notes}</div>' if doctor_notes else ''}
                </div>

                <!-- Credentials / Account Link Box -->
                {credentials_box}

                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 20px 0;">
                <p style="font-size: 11px; color: #94a3b8; text-align: center; margin: 0;">
                    Smart India Hackathon (SIH 2026) • Rural Healthcare AI Tele-Screening Network • Confidential Patient Communication
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""Netra Setu Retinal Diagnostic Report

Hello {patient_name},

Your retinal fundus examination by {doctor_name} has been completed.
Diagnosis: {severity_name}
Doctor Notes: {doctor_notes}

{credentials_text}
Smart India Hackathon 2026."""

        import threading
        t = threading.Thread(target=AuthService._deliver_email, args=(to_email, subject, text_body, html_body))
        t.daemon = True
        t.start()
        return True
