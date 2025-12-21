import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Optional

# Email configuration - use environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")  # Your email
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Your app password
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
APP_NAME = "DoCchat"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """
    Send an email using SMTP
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        text_content: Plain text fallback (optional)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = f"{APP_NAME} <{FROM_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject
        
        # Add text version (fallback)
        if text_content:
            text_part = MIMEText(text_content, "plain")
            message.attach(text_part)
        
        # Add HTML version
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Check if email is configured
        if not SMTP_USER or not SMTP_PASSWORD:
            print("⚠️ Email service not configured. Email would have been sent to:", to_email)
            print("Subject:", subject)
            print("Content:", text_content or html_content[:100])
            return True  # Simulate success for development
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(message)
        
        print(f"✅ Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {str(e)}")
        return False


async def send_password_reset_email(email: str, reset_token: str) -> bool:
    """
    Send password reset email with reset link
    
    Args:
        email: User's email address
        reset_token: Password reset token
    
    Returns:
        bool: True if email sent successfully
    """
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    
    subject = f"Password reset request"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: #ffffff;
                padding: 60px 20px;
                line-height: 1.7;
                color: #1a1a1a;
            }}
            .container {{
                max-width: 520px;
                margin: 0 auto;
            }}
            .header {{
                margin-bottom: 48px;
            }}
            .logo {{
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.5px;
                color: #1a1a1a;
                text-transform: uppercase;
                margin-bottom: 12px;
            }}
            .title {{
                font-size: 28px;
                font-weight: 600;
                color: #1a1a1a;
                letter-spacing: -0.5px;
                line-height: 1.2;
            }}
            .content {{
                margin-bottom: 40px;
            }}
            .text {{
                font-size: 15px;
                color: #525252;
                line-height: 1.7;
                margin-bottom: 20px;
            }}
            .button-container {{
                margin: 40px 0;
            }}
            .button {{
                display: inline-block;
                background: #1a1a1a;
                color: #ffffff !important;
                padding: 14px 28px;
                text-decoration: none;
                font-size: 14px;
                font-weight: 500;
                letter-spacing: 0.2px;
                border-radius: 6px;
                transition: background 0.2s;
            }}
            .divider {{
                height: 1px;
                background: #e5e5e5;
                margin: 40px 0;
            }}
            .notice {{
                background: #fafafa;
                border: 1px solid #e5e5e5;
                padding: 20px;
                border-radius: 6px;
                margin: 32px 0;
            }}
            .notice-text {{
                font-size: 13px;
                color: #525252;
                line-height: 1.6;
            }}
            .notice-text strong {{
                color: #1a1a1a;
                font-weight: 500;
            }}
            .link-section {{
                margin: 32px 0;
            }}
            .link-label {{
                font-size: 13px;
                color: #737373;
                margin-bottom: 8px;
            }}
            .link {{
                font-size: 12px;
                color: #525252;
                word-break: break-all;
                font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
                background: #fafafa;
                padding: 12px;
                border-radius: 4px;
                border: 1px solid #e5e5e5;
            }}
            .footer {{
                margin-top: 60px;
                padding-top: 24px;
                border-top: 1px solid #e5e5e5;
            }}
            .footer-text {{
                font-size: 12px;
                color: #a3a3a3;
                line-height: 1.6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">{APP_NAME}</div>
                <h1 class="title">Reset your password</h1>
            </div>
            
            <div class="content">
                <p class="text">
                    We received a request to reset the password for your account. 
                    Use the button below to create a new password.
                </p>
                
                <div class="button-container">
                    <a href="{reset_link}" class="button">Reset Password</a>
                </div>
                
                <div class="notice">
                    <p class="notice-text">
                        <strong>Security notice:</strong> This link will expire in 1 hour. 
                        If you didn't request this reset, you can safely ignore this email.
                    </p>
                </div>
                
                <div class="link-section">
                    <div class="link-label">Or copy this link:</div>
                    <div class="link">{reset_link}</div>
                </div>
            </div>
            
            <div class="footer">
                <p class="footer-text">
                    This email was sent to {email} because a password reset was requested for your {APP_NAME} account.
                </p>
                <p class="footer-text" style="margin-top: 12px;">
                    © 2025 {APP_NAME}. All rights reserved.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Reset your password
    
    We received a request to reset the password for your account. Use the link below to create a new password.
    
    {reset_link}
    
    This link will expire in 1 hour. If you didn't request this reset, you can safely ignore this email.
    
    © 2025 {APP_NAME}
    """
    
    return await send_email(email, subject, html_content, text_content)


async def send_password_changed_confirmation(email: str, name: str) -> bool:
    """
    Send confirmation email after password has been changed
    
    Args:
        email: User's email address
        name: User's name
    
    Returns:
        bool: True if email sent successfully
    """
    subject = f"Password changed successfully"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: #ffffff;
                padding: 60px 20px;
                line-height: 1.7;
                color: #1a1a1a;
            }}
            .container {{
                max-width: 520px;
                margin: 0 auto;
            }}
            .header {{
                margin-bottom: 48px;
            }}
            .logo {{
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.5px;
                color: #1a1a1a;
                text-transform: uppercase;
                margin-bottom: 12px;
            }}
            .title {{
                font-size: 28px;
                font-weight: 600;
                color: #1a1a1a;
                letter-spacing: -0.5px;
                line-height: 1.2;
            }}
            .content {{
                margin-bottom: 40px;
            }}
            .greeting {{
                font-size: 15px;
                color: #525252;
                margin-bottom: 32px;
            }}
            .text {{
                font-size: 15px;
                color: #525252;
                line-height: 1.7;
                margin-bottom: 20px;
            }}
            .notice {{
                background: #fafafa;
                border: 1px solid #e5e5e5;
                padding: 20px;
                border-radius: 6px;
                margin: 32px 0;
            }}
            .notice-text {{
                font-size: 13px;
                color: #525252;
                line-height: 1.6;
            }}
            .notice-text strong {{
                color: #1a1a1a;
                font-weight: 500;
            }}
            .status {{
                display: inline-block;
                background: #1a1a1a;
                color: #ffffff;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 0.3px;
                border-radius: 4px;
                margin-bottom: 24px;
            }}
            .divider {{
                height: 1px;
                background: #e5e5e5;
                margin: 40px 0;
            }}
            .footer {{
                margin-top: 60px;
                padding-top: 24px;
                border-top: 1px solid #e5e5e5;
            }}
            .footer-text {{
                font-size: 12px;
                color: #a3a3a3;
                line-height: 1.6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">{APP_NAME}</div>
                <h1 class="title">Password changed</h1>
            </div>
            
            <div class="content">
                <div class="status">CONFIRMED</div>
                
                <p class="greeting">Hi {name},</p>
                
                <p class="text">
                    The password for your {APP_NAME} account has been successfully changed.
                </p>
                
                <p class="text">
                    If you made this change, no further action is required.
                </p>
                
                <div class="divider"></div>
                
                <div class="notice">
                    <p class="notice-text">
                        <strong>Didn't make this change?</strong> If you didn't authorize this password change, 
                        please contact support immediately to secure your account.
                    </p>
                </div>
            </div>
            
            <div class="footer">
                <p class="footer-text">
                    This is a security notification for your {APP_NAME} account ({email}).
                </p>
                <p class="footer-text" style="margin-top: 12px;">
                    © 2025 {APP_NAME}. All rights reserved.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Password changed successfully
    
    Hi {name},
    
    The password for your {APP_NAME} account has been successfully changed.
    
    If you made this change, no further action is required.
    
    If you didn't authorize this change, please contact support immediately.
    
    © 2025 {APP_NAME}
    """
    
    return await send_email(email, subject, html_content, text_content)
