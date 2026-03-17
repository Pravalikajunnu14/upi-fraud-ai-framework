"""
email_alert.py
--------------
Sends real-time HTML email alerts when fraud or anomalous transactions
are detected. Uses Gmail SMTP with TLS (App Password).

Setup:
  1. Enable 2-Step Verification on your Gmail account.
  2. Go to: Google Account → Security → App Passwords → Generate.
  3. Fill the values in backend/.env  (see below).

.env keys needed:
  ALERT_EMAIL_FROM     = your_gmail@gmail.com
  ALERT_EMAIL_PASSWORD = your_16_char_app_password
  ALERT_EMAIL_TO       = analyst@yourbank.com   ← default recipient
  SMTP_HOST            = smtp.gmail.com
  SMTP_PORT            = 587
"""

import smtplib
import datetime
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import Config

try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger("email_alert")


# ── Internal HTML builder ──────────────────────────────────────────────────────

def _build_html(txn_id: str, amount: float, city: str, upi_id: str,
                fraud_score: float, combined_score: float,
                risk_level: str, alert_type: str) -> str:
    """Build a dark-mode HTML email body."""

    is_fraud   = alert_type == "Fraud"
    color_bg   = "#dc2626" if is_fraud else "#d97706"
    color_text = "#fca5a5" if is_fraud else "#fde68a"
    emoji      = "🚨" if is_fraud else "⚠️"
    badge_lbl  = "FRAUDULENT" if is_fraud else "ANOMALY DETECTED"
    body_msg   = (
        "This transaction has been flagged as <strong>FRAUDULENT</strong> and "
        "automatically blocked. <br>Review it immediately in the admin dashboard."
        if is_fraud else
        "An <strong>unusual/novel transaction pattern</strong> was detected. "
        "The AI model has not seen this pattern before. Review manually."
    )
    timestamp  = datetime.datetime.now().strftime("%d %b %Y, %I:%M:%S %p IST")

    return f"""
<html>
<body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px;margin:0;">
  <div style="max-width:540px;margin:auto;background:#1e293b;border-radius:16px;
              overflow:hidden;border:1px solid rgba({('239,68,68' if is_fraud else '245,158,11')},.45);
              box-shadow:0 20px 60px rgba(0,0,0,.5);">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,{color_bg},{'#991b1b' if is_fraud else '#92400e'});
                padding:24px 28px;">
      <h2 style="margin:0;color:#fff;font-size:1.25rem;">{emoji} UPI Shield — {alert_type} Alert</h2>
      <p style="margin:5px 0 0;color:{color_text};font-size:.82rem;">
        Real-Time AI Detection • {timestamp}
      </p>
    </div>

    <!-- Transaction Details -->
    <div style="padding:24px 28px;">
      <table style="width:100%;border-collapse:collapse;font-size:.88rem;">
        <tr>
          <td style="padding:9px 0;color:#94a3b8;width:40%;">Transaction ID</td>
          <td style="padding:9px 0;font-weight:700;font-family:monospace;color:#f1f5f9;">{txn_id}</td>
        </tr>
        <tr style="border-top:1px solid rgba(255,255,255,.06);">
          <td style="padding:9px 0;color:#94a3b8;">UPI / Payee ID</td>
          <td style="padding:9px 0;color:#f1f5f9;">{upi_id or '—'}</td>
        </tr>
        <tr style="border-top:1px solid rgba(255,255,255,.06);">
          <td style="padding:9px 0;color:#94a3b8;">Amount</td>
          <td style="padding:9px 0;font-weight:700;font-size:1.1rem;color:#f87171;">₹{amount:,.2f}</td>
        </tr>
        <tr style="border-top:1px solid rgba(255,255,255,.06);">
          <td style="padding:9px 0;color:#94a3b8;">Location</td>
          <td style="padding:9px 0;color:#f1f5f9;">{city}</td>
        </tr>
        <tr style="border-top:1px solid rgba(255,255,255,.06);">
          <td style="padding:9px 0;color:#94a3b8;">AI Fraud Score</td>
          <td style="padding:9px 0;font-weight:700;color:#f87171;">{fraud_score}%</td>
        </tr>
        <tr style="border-top:1px solid rgba(255,255,255,.06);">
          <td style="padding:9px 0;color:#94a3b8;">Combined Risk Score</td>
          <td style="padding:9px 0;font-weight:700;color:#f87171;">{combined_score}%</td>
        </tr>
        <tr style="border-top:1px solid rgba(255,255,255,.06);">
          <td style="padding:9px 0;color:#94a3b8;">Risk Level</td>
          <td style="padding:9px 0;">
            <span style="background:{color_bg};color:#fff;padding:3px 12px;
                         border-radius:20px;font-size:.78rem;font-weight:700;">
              {risk_level}
            </span>
          </td>
        </tr>
      </table>

      <!-- Alert Message -->
      <div style="margin-top:20px;
                  background:rgba({('239,68,68' if is_fraud else '245,158,11')},.1);
                  border:1px solid rgba({('239,68,68' if is_fraud else '245,158,11')},.3);
                  border-radius:10px;padding:14px;">
        <p style="margin:0;color:{color_text};font-size:.88rem;line-height:1.5;">
          {emoji} <strong>{badge_lbl}</strong><br>{body_msg}
        </p>
      </div>
    </div>

    <!-- Footer -->
    <div style="padding:12px 28px;background:rgba(0,0,0,.25);
                font-size:.72rem;color:#475569;text-align:center;">
      UPI Shield &bull; AI-Driven Fraud Detection &bull; Auto-generated alert &bull; Do not reply
    </div>
  </div>
</body>
</html>
"""


# ── Public SendEmail API ───────────────────────────────────────────────────────

def send_fraud_alert(txn_id: str, amount: float, city: str,
                     upi_id: str, fraud_score: float, risk_level: str,
                     user_email: str = "",
                     combined_score: float = 0.0,
                     alert_type: str = "Fraud") -> bool:
    """
    Send a real-time fraud/anomaly alert email.

    Parameters
    ----------
    txn_id        : Transaction ID (e.g. TXN1A2B3C4D)
    amount        : Transaction amount in INR
    city          : City of the transaction
    upi_id        : Payee UPI ID / VPA
    fraud_score   : Supervised model score 0-100
    risk_level    : "Low" | "Medium" | "High"
    user_email    : If provided, sends to THIS email; else uses ALERT_EMAIL_TO from .env
    combined_score: Fused fraud+anomaly score (70/30 weighted)
    alert_type    : "Fraud" or "Anomaly"

    Returns True if sent successfully, False if skipped or failed.
    """
    sender    = Config.ALERT_EMAIL_FROM
    password  = Config.ALERT_EMAIL_PASSWORD
    recipient = (
        user_email.strip()
        if user_email and "@" in user_email
        else Config.ALERT_EMAIL_TO
    )

    # ── Guard: skip if credentials not configured ──────────────────────────────
    if not sender or not password or not recipient:
        logger.warning(
            "[EmailAlert] Skipped — email credentials not configured in .env. "
            "Set ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD, ALERT_EMAIL_TO."
        )
        return False

    if sender == "your_gmail@gmail.com" or password == "your_app_password_here":
        logger.warning(
            "[EmailAlert] Skipped — .env still has placeholder values. "
            "Replace ALERT_EMAIL_FROM and ALERT_EMAIL_PASSWORD with real credentials."
        )
        return False

    # ── Build email ────────────────────────────────────────────────────────────
    emoji   = "🚨" if alert_type == "Fraud" else "⚠️"
    subject = f"{emoji} UPI {alert_type} ALERT — {risk_level} Risk | TXN: {txn_id}"
    html    = _build_html(txn_id, amount, city, upi_id,
                          fraud_score, combined_score or fraud_score,
                          risk_level, alert_type)

    # ── Send via Gmail SMTP ────────────────────────────────────────────────────
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"UPI Shield Alerts <{sender}>"
        msg["To"]      = recipient
        msg.attach(MIMEText(html, "html"))

        if Config.SMTP_PORT == 465:
            # Native SSL
            with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                server.login(sender, password)
                server.sendmail(sender, recipient, msg.as_string())
        else:
            # STARTTLS
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, recipient, msg.as_string())

        logger.info(
            f"[EmailAlert] ✅ {alert_type} alert sent → {recipient} "
            f"| TXN: {txn_id} | ₹{amount:,.0f} | Score: {fraud_score}%"
        )
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "[EmailAlert] ❌ Gmail authentication failed. "
            "Make sure you are using an App Password, not your regular Gmail password. "
            "Generate one at: Google Account → Security → 2-Step → App Passwords"
        )
        return False
    except smtplib.SMTPException as e:
        logger.error(f"[EmailAlert] ❌ SMTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"[EmailAlert] ❌ Unexpected error: {e}")
        return False
