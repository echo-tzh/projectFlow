from flask import Blueprint, request, redirect, url_for, flash
from shared.models import db, Timeframe
from shared.service.email_service import send_welcome_emails
# Import the passwords dictionary at module level for better performance
from features.educationAdmin.load_data.loadDataController import passwords_for_email

# Create blueprint for email functionality
send_welcome_email_bp = Blueprint('send_welcome_email', __name__, url_prefix='/load_data')

@send_welcome_email_bp.route('/send_welcome_emails/<int:timeframe_id>', methods=['POST'])
def send_welcome_notifications(timeframe_id):
    """Send welcome emails to all users in the specified timeframe using the pre-generated passwords."""
    try:
        timeframe = Timeframe.query.get_or_404(timeframe_id)
        users_in_timeframe = timeframe.users
        
        # 📧 Call the email service with the pre-generated passwords
        result = send_welcome_emails(users_in_timeframe, timeframe, passwords=passwords_for_email)
        
        if result['success']:
            flash(f'Successfully sent welcome emails to {result["sent_count"]} users!', 'success')
            if result['failed_count'] > 0:
                flash(f'{result["failed_count"]} emails failed to send. Check logs for details.', 'warning')
        else:
            flash(f'Failed to send emails: {result["error"]}', 'error')
        
        # 🔒 Security step: Clear the passwords from memory after sending emails
        passwords_for_email.clear()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error sending emails: {str(e)}', 'error')
    
    return redirect(url_for('load_data.select_timeframe', timeframe_id=timeframe_id))