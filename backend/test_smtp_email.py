import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

print("Testing Gmail SMTP Credentials...")
print(f"MAIL_SERVER: {Config.MAIL_SERVER}")
print(f"MAIL_PORT: {Config.MAIL_PORT}")
print(f"MAIL_USERNAME: {Config.MAIL_USERNAME}")
print(f"MAIL_PASSWORD length: {len(Config.MAIL_PASSWORD)}")

to_email = "2k24.cs1q.2413756@gmail.com"
msg = MIMEMultipart("alternative")
msg["From"] = f"NetraAI Screening <{Config.MAIL_USERNAME}>"
msg["To"] = to_email
msg["Subject"] = "NetraAI SMTP Diagnostics Test Code: 789123"
msg.attach(MIMEText("This is a test verification code from NetraAI.", "plain"))

try:
    with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=15) as server:
        server.set_debuglevel(1)
        server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.sendmail(Config.MAIL_USERNAME, [to_email], msg.as_string())
    print("\n[SUCCESS] EMAIL SENT SUCCESSFULLY TO", to_email)
except Exception as e:
    print("\n[ERROR] FAILED TO SEND EMAIL:", e)
