#!/usr/bin/env python
"""
test_email.py
=============
Tests email alert configuration and SMTP connectivity.
Run this to diagnose email alert issues.
"""

import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add backend to path
sys.path.insert(0, ".")

from config import Config

def test_email_config():
    sender = Config.ALERT_EMAIL_FROM
    password = Config.ALERT_EMAIL_PASSWORD
    recipient = Config.ALERT_EMAIL_TO
    
    print("\n" + "=" * 70)
    print("📧 UPI SHIELD - EMAIL ALERT CONFIGURATION TEST")
    print("=" * 70)
    
    # 1. Check configuration values
    print("\n[STEP 1] Checking Configuration...")
    print("-" * 70)
    
    if not sender or sender == "your_gmail@gmail.com":
        print("❌ ERROR: ALERT_EMAIL_FROM not configured")
        print("   → Set ALERT_EMAIL_FROM in backend/.env")
        return False
    print(f"✅ Sender configured: {sender}")
    
    if not password or password == "your_app_password_here":
        print("❌ ERROR: ALERT_EMAIL_PASSWORD not configured")
        print("   → Generate App Password at: myaccount.google.com → Security → App Passwords")
        return False
    print(f"✅ Password configured: {'*' * len(password)}")
    
    if not recipient:
        print("❌ ERROR: ALERT_EMAIL_TO not configured")
        print("   → Set ALERT_EMAIL_TO in backend/.env")
        return False
    print(f"✅ Recipient configured: {recipient}")
    
    print(f"✅ SMTP Host: {Config.SMTP_HOST}")
    print(f"✅ SMTP Port: {Config.SMTP_PORT}")
    
    # 2. Test SMTP connection
    print("\n[STEP 2] Testing SMTP Connection...")
    print("-" * 70)
    
    try:
        if Config.SMTP_PORT == 465:
            print("🔐 Using SSL connection (port 465)...")
            server = smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10)
        else:
            print("🔐 Using TLS connection (port 587)...")
            server = smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10)
            server.starttls()
        
        print("✅ SMTP connection successful")
        
    except smtplib.SMTPServerDisconnected:
        print("❌ ERROR: SMTP server disconnected")
        print("   → Check SMTP_HOST and SMTP_PORT in .env")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("   → Check network/firewall for port 587")
        print("   → Firewall might be blocking SMTP")
        return False
    
    # 3. Test authentication
    print("\n[STEP 3] Testing Gmail Authentication...")
    print("-" * 70)
    
    try:
        print(f"🔓 Attempting login as {sender}...")
        server.login(sender, password)
        print("✅ Gmail authentication successful!")
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed!")
        print("   → Check your Gmail App Password")
        print("   → Ensure 2-Factor Authentication is enabled")
        print("   → Password should be 16 characters (no spaces)")
        print("   → Generate a new one at: https://myaccount.google.com/apppasswords")
        server.quit()
        return False
    except Exception as e:
        print(f"❌ Login error: {e}")
        server.quit()
        return False
    
    # 4. Send test email
    print("\n[STEP 4] Sending Test Email...")
    print("-" * 70)
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🧪 UPI Shield - Email Test"
        msg["From"] = f"UPI Shield <{sender}>"
        msg["To"] = recipient
        
        html_body = """
<html>
<body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:20px;">
<div style="max-width:540px;margin:auto;background:#1e293b;border-radius:8px;
            padding:20px;border:1px solid rgba(59,130,246,0.3);">
    <h2 style="color:#3b82f6;margin-top:0;">✅ Email Alerts Working!</h2>
    
    <p>This is a test email from <strong>UPI Shield</strong>.</p>
    
    <p>If you received this email, your configuration is correct and fraud alerts will be sent.</p>
    
    <div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);
                border-radius:6px;padding:12px;margin:15px 0;font-size:14px;">
        <strong>✅ What's Working:</strong>
        <ul style="margin:8px 0;padding-left:20px;">
            <li>Gmail SMTP connection</li>
            <li>Authentication successful</li>
            <li>Email sending enabled</li>
        </ul>
    </div>
    
    <p><strong>Next:</strong> Submit a fraudulent transaction to test real alerts.</p>
    
    <p style="color:#cbd5e1;font-size:12px;margin-top:20px;">
        UPI Shield • AI Fraud Detection • Test Email
    </p>
</div>
</body>
</html>
        """
        
        msg.attach(MIMEText(html_body, "html"))
        
        print(f"📬 Sending email to {recipient}...")
        server.sendmail(sender, recipient, msg.as_string())
        print("✅ Test email sent successfully!")
        
        server.quit()
        
    except Exception as e:
        print(f"❌ Email send failed: {e}")
        try:
            server.quit()
        except:
            pass
        return False
    
    # Success!
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print("\n📧 Email alerts are properly configured and working.")
    print("\n📋 Next Steps:")
    print("   1. Check your inbox for the test email")
    print("   2. Submit a fraudulent transaction to test real alerts")
    print("   3. Verify fraud alerts are received correctly")
    print("   4. Check email contains transaction details")
    print("\n" + "=" * 70 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = test_email_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        sys.exit(1)
