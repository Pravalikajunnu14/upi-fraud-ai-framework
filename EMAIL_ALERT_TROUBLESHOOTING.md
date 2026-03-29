# 📧 Email Alerts Troubleshooting Guide

## Issue: Not Receiving Email Alerts

### Root Causes (in order of likelihood)

#### 1. ❌ **JWT Token Missing Email Field**
Your JWT token might not have an `email` claim, so alerts default to `ALERT_EMAIL_TO`.

**Check:**
- Open DevTools → Network tab
- Submit a transaction that triggers fraud
- Look at the response `data` object
- Check if it tries to send to the email address in `.env`

**Fix:** Add email to JWT token in `backend/routes/auth.py`

#### 2. ❌ **Gmail App Password Not Working**
The 16-character app password might be incorrect or expired.

**Check:**
```bash
# Test the email configuration
python -c "
import smtplib
sender = 'pravalikajunnu14@gmail.com'
pwd = 'ivhmtdgqdclzvrhu'
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender, pwd)
    print('✅ Gmail authentication SUCCESS')
    server.quit()
except Exception as e:
    print(f'❌ Gmail authentication FAILED: {e}')
"
```

#### 3. ❌ **Gmail 2-Factor Authentication Required**
Gmail blocks app passwords if 2FA is not enabled.

**Fix:**
1. Go to: `myaccount.google.com` → Security
2. Enable 2-Step Verification
3. Then generate a new App Password
4. Update `.env` with new password

#### 4. ❌ **Gmail App Password Has Spaces**
Sometimes Gmail displays the password with spaces, but don't include them.

**Check your `.env`:**
```bash
# ❌ WRONG (with spaces):
ALERT_EMAIL_PASSWORD=ivhm tdgq dclz vrhu

# ✅ CORRECT (no spaces):
ALERT_EMAIL_PASSWORD=ivhmtdgqdclzvrhu
```

#### 5. ❌ **Firewall/Network Blocking SMTP**
Port 587 might be blocked.

**Check:**
```bash
# Test SMTP connection
telnet smtp.gmail.com 587
# Or on Windows:
Test-NetConnection -ComputerName smtp.gmail.com -Port 587
```

#### 6. ❌ **Transaction Not Triggering Fraud/Anomaly**
Email only sends if `final_label` is "Fraud" or "Anomaly", not "Legitimate".

**Check:** Use test data with high fraud score

---

## Solutions

### Solution 1: Add Email to JWT Token

Edit `backend/routes/auth.py` and ensure email is included:

```python
# After successful login, add email to JWT
access_token = create_access_token(
    identity=str(user_id),
    additional_claims={
        "email": user_email,  # ← ADD THIS LINE
        "role": user_role,
        "username": username
    }
)
```

### Solution 2: Verify Email Configuration

Create `backend/test_email.py`:

```python
#!/usr/bin/env python
"""Test email alert configuration"""

import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

def test_email_config():
    sender = Config.ALERT_EMAIL_FROM
    password = Config.ALERT_EMAIL_PASSWORD
    recipient = Config.ALERT_EMAIL_TO
    
    print("=" * 60)
    print("📧 Email Configuration Test")
    print("=" * 60)
    
    print(f"\n✓ Sender:    {sender}")
    print(f"✓ Recipient: {recipient}")
    print(f"✓ SMTP Host: {Config.SMTP_HOST}:{Config.SMTP_PORT}")
    
    if not sender or sender == "your_gmail@gmail.com":
        print("❌ ERROR: ALERT_EMAIL_FROM not configured in .env")
        return False
    
    if not password or password == "your_app_password_here":
        print("❌ ERROR: ALERT_EMAIL_PASSWORD not configured in .env")
        return False
    
    if not recipient:
        print("❌ ERROR: ALERT_EMAIL_TO not configured in .env")
        return False
    
    # Test SMTP connection
    print("\n🔓 Testing SMTP connection...")
    try:
        if Config.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10)
            server.starttls()
        
        print("✅ Connected to SMTP server")
        
        # Test login
        print("🔐 Testing Gmail authentication...")
        server.login(sender, password)
        print("✅ Authentication successful!")
        
        # Send test email
        print("📬 Sending test email...")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🧪 UPI Shield Test Email"
        msg["From"] = f"UPI Shield <{sender}>"
        msg["To"] = recipient
        msg.attach(MIMEText("""
<html><body style="font-family:Arial;background:#0f172a;color:#fff;padding:20px;">
<div style="max-width:500px;margin:auto;background:#1e293b;padding:20px;border-radius:8px;">
    <h2>✅ Email Alerts are Working!</h2>
    <p>This is a test email from UPI Shield.</p>
    <p>If you received this, email alerts are properly configured.</p>
    <p><strong>Next Steps:</strong></p>
    <ul>
        <li>Submit a fraudulent transaction to test real alerts</li>
        <li>Check your inbox for fraud alerts</li>
        <li>Verify alert details are correct</li>
    </ul>
</div>
</body></html>
        """, "html"))
        
        server.sendmail(sender, recipient, msg.as_string())
        print(f"✅ Test email sent to {recipient}")
        
        server.quit()
        print("\n✅ ALL TESTS PASSED! Email alerts should work.")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("   → Check App Password in .env")
        print("   → Ensure 2-Factor Auth is enabled on Gmail")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {e}")
        print("   → Check SMTP_HOST and SMTP_PORT in .env")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("   → Check network/firewall")
        return False

if __name__ == "__main__":
    sys.path.insert(0, ".")
    success = test_email_config()
    sys.exit(0 if success else 1)
```

**Run it:**
```bash
cd backend
python test_email.py
```

### Solution 3: Enable Email Logging

Add this to `backend/config.py`:

```python
# Add logging for email_alert module
EMAIL_ALERT_DEBUG = os.getenv("EMAIL_ALERT_DEBUG", "False") == "True"
```

### Solution 4: Check Logs

Look for email errors in logs:

```bash
# Check if send_fraud_alert was called
grep -i "email\|alert\|smtp" backend/logs/*.log

# Check if there are errors
grep -i "error\|failed\|authentication" backend/logs/*.log
```

---

## Quick Test Procedure

1. **Verify .env is configured:**
   ```bash
   cat backend/.env | grep ALERT_EMAIL
   ```

2. **Test email system:**
   ```bash
   cd backend
   python test_email.py
   ```

3. **Submit fraudulent transaction with high amount:**
   - Go to transactions page
   - Amount: 500,000 (high risk)
   - UPI ID: test@fraud
   - Submit

4. **Check:**
   - Browser console for errors
   - Email inbox for alert
   - Backend logs for email send status

5. **If still not working:**
   - Check email in JWT token
   - Verify SMTP port 587 is not blocked
   - Regenerate Gmail App Password

---

## Current Configuration Status

✅ **Configured in `.env`:**
- `ALERT_EMAIL_FROM`: pravalikajunnu14@gmail.com
- `ALERT_EMAIL_PASSWORD`: ••••••••••••••••
- `ALERT_EMAIL_TO`: pravalikajunnu14@gmail.com
- `SMTP_HOST`: smtp.gmail.com
- `SMTP_PORT`: 587

⚠️ **Potential Issues:**
- Email field might not be in JWT token
- Gmail 2-Factor might not be enabled
- App password might be incorrect or expired

---

## Next Step

Run the email test to diagnose the issue:

```bash
cd backend && python test_email.py
```

This will tell you exactly what's wrong! 📧
