import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging
from typing import List, Dict, Any, Optional
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails with dynamic configuration"""
    
    def __init__(self, config=None):
        """Initialize EmailService with config from database or fallback to environment"""
        self.config = config
        
        if config:
            # Use database configuration
            self.smtp_server = config.smtp_server
            self.smtp_port = config.smtp_port
            self.smtp_username = config.smtp_username
            self.smtp_password = config.smtp_password
            self.from_email = config.from_email
            self.from_name = config.from_name or 'ProjectFlow Team'
            self.use_tls = config.use_tls
            self.use_ssl = config.use_ssl
        else:
            # Fallback to environment variables (backward compatibility)
            self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
            self.smtp_username = os.getenv('SMTP_USERNAME', 'projectflow25@gmail.com')
            self.smtp_password = os.getenv('SMTP_PASSWORD', 'qpst jcwt ulaw xzql')
            self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
            self.from_name = 'ProjectFlow Team'
            self.use_tls = True
            self.use_ssl = False
    
    @classmethod
    def get_service_with_config(cls, school_id=None):
        """Get EmailService instance with current database configuration"""
        from shared.models import EmailConfig
        
        try:
            if school_id:
                config = EmailConfig.query.filter_by(school_id=school_id, is_active=True).first()
            else:
                config = EmailConfig.query.filter_by(is_active=True).first()
                
            if config:
                return cls(config)
            else:
                # Fallback to environment variables
                logger.warning("No email config found in database, using environment variables")
                return cls()
        except Exception as e:
            logger.warning(f"Could not load email config from database: {e}")
            # Fallback to environment variables
            return cls()
    
    def test_connection(self) -> Dict[str, Any]:
        """Test SMTP connection and return result"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_ssl:
                    server.starttls()
                elif self.use_tls:
                    server.starttls()
                
                server.login(self.smtp_username, self.smtp_password)
                
            return {
                'success': True,
                'message': 'SMTP connection successful'
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                'success': False,
                'message': 'Authentication failed. Please check your username and password.'
            }
        except smtplib.SMTPConnectError:
            return {
                'success': False,
                'message': f'Could not connect to SMTP server {self.smtp_server}:{self.smtp_port}'
            }
        except smtplib.SMTPServerDisconnected:
            return {
                'success': False,
                'message': 'SMTP server disconnected unexpectedly'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}'
            }
    
    def update_config_test_result(self, test_result: Dict[str, Any]):
        """Update the database config with test results"""
        if self.config:
            try:
                from database import db
                from datetime import datetime
                
                self.config.last_test_at = datetime.utcnow()
                self.config.last_test_success = test_result['success']
                self.config.last_test_error = None if test_result['success'] else test_result['message']
                
                db.session.commit()
            except Exception as e:
                logger.error(f"Could not update config test result: {e}")
        
    def send_email(self, to_email: str, subject: str, body_text: str, body_html: str = None) -> bool:
        """Send a single email"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
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
                if self.use_ssl:
                    server.starttls()
                elif self.use_tls:
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
            msg['From'] = f"{self.from_name} <{self.from_email}>"
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
- Course Term: {timeframe.name}
- Period: {timeframe.start_date.strftime('%B %d, %Y')} - {timeframe.end_date.strftime('%B %d, %Y')}

*use email to login to ProjectFlow

This is an auto-generated email, please do not reply to this email.

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

def send_welcome_emails_bulk_fast(users: List, timeframe, passwords: Dict = None, school_id=None) -> Dict[str, Any]:
    """
    Send welcome emails using single SMTP connection (FASTEST for many emails)
    5-10x faster than the original sequential method
    """
    # Use school-specific config or get from database
    if school_id:
        email_service = EmailService.get_service_with_config(school_id)
    else:
        email_service = EmailService.get_service_with_config()
    
    # Check if email is configured
    if not email_service.smtp_username or not email_service.smtp_password:
        return {
            'success': False,
            'error': 'Email service not configured. Please configure email settings in the dashboard.',
            'sent_count': 0,
            'failed_count': 0
        }
    
    sent_count = 0
    failed_count = 0
    failed_emails = []
    
    try:
        # Create single SMTP connection and reuse it for all emails
        with smtplib.SMTP(email_service.smtp_server, email_service.smtp_port) as server:
            if email_service.use_ssl:
                server.starttls()
            elif email_service.use_tls:
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

def send_welcome_emails_threaded(users: List, timeframe, passwords: Dict = None, school_id=None) -> Dict[str, Any]:
    """
    Send welcome emails using threading (FASTEST for moderate numbers)
    Can be 10-15x faster than sequential for 20+ emails
    """
    from flask import current_app
    
    # Use school-specific config or get from database
    if school_id:
        email_service = EmailService.get_service_with_config(school_id)
    else:
        email_service = EmailService.get_service_with_config()
    
    # Check if email is configured
    if not email_service.smtp_username or not email_service.smtp_password:
        return {
            'success': False,
            'error': 'Email service not configured. Please configure email settings in the dashboard.',
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

def send_welcome_emails(users: List, timeframe, passwords: Dict = None, school_id=None) -> Dict[str, Any]:
    """
    Main function - uses bulk connection method for best performance without threading complexity
    """
    if not users:
        return {'success': True, 'sent_count': 0, 'failed_count': 0}
    
    # Always use bulk connection method - fast and reliable
    logger.info(f"Using bulk connection approach for {len(users)} users")
    return send_welcome_emails_bulk_fast(users, timeframe, passwords, school_id)

def send_test_email(to_email: str, school_id=None) -> Dict[str, Any]:
    """Send a test email to verify configuration"""
    try:
        # Use school-specific config or get from database
        if school_id:
            email_service = EmailService.get_service_with_config(school_id)
        else:
            email_service = EmailService.get_service_with_config()
        
        subject = "ProjectFlow Email Configuration Test"
        body_text = f"""
Hello,

This is a test email to verify that your ProjectFlow email configuration is working correctly.

Configuration Details:
- SMTP Server: {email_service.smtp_server}
- SMTP Port: {email_service.smtp_port}
- From Email: {email_service.from_email}
- From Name: {email_service.from_name}

If you received this email, your configuration is working properly!

Best regards,
ProjectFlow Team
"""
        
        success = email_service.send_email(
            to_email=to_email,
            subject=subject,
            body_text=body_text
        )
        
        if success:
            return {
                'success': True,
                'message': f'Test email sent successfully to {to_email}'
            }
        else:
            return {
                'success': False,
                'message': 'Failed to send test email'
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Error sending test email: {str(e)}'
        }