import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
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

    def send_email_with_connection(self, server, to_email: str, subject: str, body_text: str, body_html: str = None) -> bool:
        """Send email using existing SMTP connection (much faster)"""
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
            
            # Send using existing connection
            server.send_message(msg)
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

def generate_welcome_email_content(user, timeframe, password=None) -> Dict[str, str]:
    """Generate welcome email content for a user"""
    
    # Get user's roles
    roles = ", ".join([role.name.title() for role in user.roles])
    
    subject = f"Welcome! You are invited for the {timeframe.name} Final Year Project"
    
    # Text version
    text_body = f"""
Hello {user.name or user.email},

Welcome to ProjectFlow! You are eligible for Final Year Project for {timeframe.name}

Your Account Details:
- Email: {user.email}*
- Name: {user.name or 'Not specified'}
- Student/Staff ID: {user.student_staff_id or 'Not specified'}
- Course: {user.course or 'Not specified'}
- Role(s): {roles}
- Timeframe: {timeframe.name}
- Period: {timeframe.start_date.strftime('%B %d, %Y')} - {timeframe.end_date.strftime('%B %d, %Y')}

*use email to login to ProjectFlow

"""
    
    if password:
        text_body += f"""
Your login password is: {password}




Best regards,
ProjectFlow Team

"""
    else:
        text_body += f"""


Best regards,
ProjectFlow Team

"""
    
    return {
        'subject': subject,
        'text_body': text_body,
    }

def send_welcome_emails_bulk_fast(users: List, timeframe, passwords: Dict = None) -> Dict[str, Any]:
    """
    Send welcome emails using single SMTP connection (FASTEST for many emails)
    5-10x faster than the original sequential method
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
    
    try:
        # Create single SMTP connection and reuse it for all emails
        with smtplib.SMTP(email_service.smtp_server, email_service.smtp_port) as server:
            server.starttls()
            server.login(email_service.smtp_username, email_service.smtp_password)
            
            logger.info(f"Starting to send {len(users)} emails...")
            
            for user in users:
                try:
                    # Get password if provided
                    password = passwords.get(user.email) if passwords else None
                    
                    # Generate email content
                    email_content = generate_welcome_email_content(user, timeframe, password)
                    
                    # Send email using existing connection
                    success = email_service.send_email_with_connection(
                        server=server,
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
                    
    except Exception as e:
        logger.error(f"SMTP connection failed: {str(e)}")
        return {
            'success': False,
            'error': f'SMTP connection failed: {str(e)}',
            'sent_count': sent_count,
            'failed_count': failed_count
        }
    
    logger.info(f"Email sending completed. Sent: {sent_count}, Failed: {failed_count}")
    
    return {
        'success': True,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'failed_emails': failed_emails
    }

def send_welcome_emails_threaded(users: List, timeframe, passwords: Dict = None) -> Dict[str, Any]:
    """
    Send welcome emails using threading (FASTEST for moderate numbers)
    Can be 10-15x faster than sequential for 20+ emails
    """
    from flask import current_app
    
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
    
    # Get the current Flask app context to pass to threads
    app = current_app._get_current_object()
    
    def send_single_email(user):
        """Send email to single user - runs in separate thread"""
        # Push app context for this thread
        with app.app_context():
            try:
                password = passwords.get(user.email) if passwords else None
                email_content = generate_welcome_email_content(user, timeframe, password)
                
                success = email_service.send_email(
                    to_email=user.email,
                    subject=email_content['subject'],
                    body_text=email_content['text_body']
                )
                
                return {'success': success, 'email': user.email}
                
            except Exception as e:
                logger.error(f"Error sending email to {user.email}: {str(e)}")
                return {'success': False, 'email': user.email}
    
    # Use ThreadPoolExecutor for concurrent sending
    max_workers = min(8, len(users))  # Max 8 concurrent emails (good balance)
    logger.info(f"Starting to send {len(users)} emails with {max_workers} threads...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all email tasks
        future_to_user = {executor.submit(send_single_email, user): user for user in users}
        
        # Collect results as they complete
        for future in as_completed(future_to_user):
            result = future.result()
            if result['success']:
                sent_count += 1
            else:
                failed_count += 1
                failed_emails.append(result['email'])
    
    logger.info(f"Email sending completed. Sent: {sent_count}, Failed: {failed_count}")
    
    return {
        'success': True,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'failed_emails': failed_emails
    }

def send_welcome_emails(users: List, timeframe, passwords: Dict = None) -> Dict[str, Any]:
    """
    Main function - uses bulk connection method for best performance without threading complexity
    """
    if not users:
        return {'success': True, 'sent_count': 0, 'failed_count': 0}
    
    # Always use bulk connection method - fast and reliable
    logger.info(f"Using bulk connection approach for {len(users)} users")
    return send_welcome_emails_bulk_fast(users, timeframe, passwords)