import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# Gmail SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", os.getenv("GMAIL_USER", ""))
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", os.getenv("GMAIL_APP_PASSWORD", ""))
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "noreply@brightleafmarket.com")


def send_otp_email(to_email: str, otp: str, user_name: str = "User") -> bool:
    """
    Sends a 6-digit OTP verification code to the recipient's Gmail.
    Uses standard Gmail SMTP with STARTTLS.
    If credentials are not yet configured, logs the OTP securely to server output.
    """
    subject = f"Brightleaf Market — Password Reset Verification Code: {otp}"
    
    text_content = f"""Hello {user_name},

We received a request to reset your password for your Brightleaf Retail Operations Platform account ({to_email}).

Your 6-digit verification code is:
{otp}

This code is valid for 15 minutes. If you did not request this code, please ignore this email.

— Brightleaf Market Operations Security Team
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #0f172a; }}
    .card {{ max-width: 480px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
    .header {{ border-bottom: 1px solid #f1f5f9; padding-bottom: 16px; margin-bottom: 24px; }}
    .logo {{ font-size: 18px; font-weight: 700; color: #0f172a; letter-spacing: -0.5px; }}
    .badge {{ display: inline-block; background-color: #f1f5f9; color: #475569; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600; text-transform: uppercase; margin-left: 8px; }}
    .code-box {{ background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; padding: 18px; text-align: center; margin: 24px 0; font-family: 'Courier New', monospace; font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #0f172a; }}
    .footer {{ font-size: 12px; color: #64748b; margin-top: 24px; border-top: 1px solid #f1f5f9; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <span class="logo">Brightleaf Market</span>
      <span class="badge">Security Code</span>
    </div>
    <p>Hello <strong>{user_name}</strong>,</p>
    <p>We received a request to reset the password for your Retail Operations Platform account (<strong>{to_email}</strong>).</p>
    <p>Use the following 6-digit one-time verification code to proceed:</p>
    <div class="code-box">{otp}</div>
    <p style="font-size: 13px; color: #64748b;">This code will expire in <strong>15 minutes</strong>. If you did not request a password reset, you can safely disregard this message.</p>
    <div class="footer">
      Brightleaf Market • Operations & Store Security Team
    </div>
  </div>
</body>
</html>
"""

    # If SMTP credentials are configured, send real email via Gmail SMTP
    if SMTP_USER and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Brightleaf Market <{SMTP_FROM}>"
            msg["To"] = to_email
            
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)
            
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to_email], msg.as_string())
            server.quit()
            logger.info(f"Verification code successfully sent via Gmail SMTP to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Gmail SMTP dispatch failed: {e}. Logging OTP locally as fallback.")
    else:
        logger.warning("SMTP_USER and SMTP_PASSWORD not set in environment. Falling back to local logging.")
    
    # Dev / Fallback log
    print(f"\n=======================================================")
    print(f"[AUTH EMAIL SIMULATOR] Recipient: {to_email}")
    print(f"[AUTH EMAIL SIMULATOR] 6-Digit Verification Code: {otp}")
    print(f"=======================================================\n")
    return True
