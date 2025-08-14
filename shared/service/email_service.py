import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import logging
from typing import List, Dict, Any
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', 'projectflow25@gmail.com')
        self.smtp_password = os.getenv('SMTP_PASSWORD', 'qpst jcwt ulaw xzql')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        
    def send_email(self, to_email: str, subject: str, body_text: str, body_html: str = None) -> bool:
        """Send a single email"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text part
            text_part = MIMEText(body_text, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if body_html:
                html_part = MIMEText(body_html, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

def generate_welcome_email_content(user, timeframe, school_name, password=None) -> Dict[str, str]:
    """Generate welcome email content for a user"""
    
    # Get user's roles
    roles = ", ".join([role.name.title() for role in user.roles])
    
    subject = f"Welcome to {school_name} - {timeframe.name} Final Year Project"
    
    # Text version
    text_body = f"""
Hello {user.name or user.email},

Welcome to ProjectFlow at {school_name}! You are eligible for Final Year Project for {timeframe.name}

Your Account Details:
- Email: {user.email}*
- Name: {user.name or 'Not specified'}
- Student/Staff ID: {user.student_staff_id or 'Not specified'}
- Course: {user.course or 'Not specified'}
- Role(s): {roles}
- Institution: {school_name}
- Timeframe: {timeframe.name}
- Period: {timeframe.start_date.strftime('%B %d, %Y')} - {timeframe.end_date.strftime('%B %d, %Y')}

*use email to login to ProjectFlow

"""
    
    if password:
        text_body += f"""
Your login password is: {password}




Best regards,
ProjectFlow Team
{school_name}
"""
    else:
        text_body += f"""


Best regards,
ProjectFlow Team
{school_name}
"""
    
    return {
        'subject': subject,
        'text_body': text_body,
    }

def send_welcome_emails(users: List, timeframe, school_name, passwords: Dict = None) -> Dict[str, Any]:
    """
    Send welcome emails to a list of users
    
    Args:
        users: List of User objects
        timeframe: Timeframe object
        school_name: Name of the school/institution
        passwords: Optional dict mapping user emails to their passwords
    
    Returns:
        Dict with success status, counts, and any errors
    """
    email_service = EmailService()
    
    # Check if email is configured
    if not email_service.smtp_username or not email_service.smtp_password:
        return {
            'success': False,
            'error': 'Email service not configured. Please set SMTP environment variables.',
            'sent_count': 0,
            'failed_count': 0
        }
    
    sent_count = 0
    failed_count = 0
    failed_emails = []
    
    for user in users:
        try:
            # Get password if provided
            password = passwords.get(user.email) if passwords else None
            
            # Generate email content
            email_content = generate_welcome_email_content(user, timeframe, school_name, password)
            
            # Send email
            success = email_service.send_email(
                to_email=user.email,
                subject=email_content['subject'],
                body_text=email_content['text_body']
            )
            
            if success:
                sent_count += 1
            else:
                failed_count += 1
                failed_emails.append(user.email)
                
        except Exception as e:
            logger.error(f"Error sending email to {user.email}: {str(e)}")
            failed_count += 1
            failed_emails.append(user.email)
    
    logger.info(f"Email sending completed. Sent: {sent_count}, Failed: {failed_count}")
    
    return {
        'success': True,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'failed_emails': failed_emails
    }