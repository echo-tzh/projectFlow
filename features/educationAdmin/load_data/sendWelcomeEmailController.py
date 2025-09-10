from flask import Blueprint, request, redirect, url_for, flash
from shared.models import db, Timeframe, User
from shared.service.email_service import send_welcome_emails
from werkzeug.security import generate_password_hash
# Import the passwords dictionary at module level for better performance
from features.educationAdmin.load_data.loadDataController import passwords_for_email, generate_random_password
# Create blueprint for email functionality
send_welcome_email_bp = Blueprint('send_welcome_email', __name__, url_prefix='/load_data')

@send_welcome_email_bp.route('/send_welcome_emails/<int:timeframe_id>', methods=['POST'])
def send_welcome_notifications(timeframe_id):
    """Send welcome emails to all users in the specified timeframe using the pre-generated passwords."""
    try:
        timeframe = Timeframe.query.get_or_404(timeframe_id)
        users_in_timeframe = timeframe.users
        
        # Build the passwords dictionary for first-time users
        updated_passwords_for_email = {}
        
        for user in users_in_timeframe:
            # Check if this user has never received a welcome email
            if not user.email_sent:
                # If this is their first time, we need a password
                if user.email in passwords_for_email:
                    # Use the password that was generated during user creation
                    updated_passwords_for_email[user.email] = passwords_for_email[user.email]
                else:
                    # This shouldn't happen for newly created users, but as fallback:
                    # Generate a new password and update their hash in the database
                    new_password = generate_random_password()
                    updated_passwords_for_email[user.email] = new_password
                    user.password_hash = generate_password_hash(new_password)
                    
        # Call the email service with the passwords for first-time users only
        result = send_welcome_emails(users_in_timeframe, timeframe, passwords=updated_passwords_for_email)
        
        if result['success']:
            # Mark users as having received their welcome email
            for user in users_in_timeframe:
                if user.email in updated_passwords_for_email:
                    user.email_sent = True
            
            db.session.commit()
            
            flash(f'Successfully sent welcome emails to {result["sent_count"]} users!', 'success')
            if result['failed_count'] > 0:
                flash(f'{result["failed_count"]} emails failed to send. Check logs for details.', 'warning')
        else:
            flash(f'Failed to send emails: {result["error"]}', 'error')
        
        # Clear the passwords from memory after sending emails
        passwords_for_email.clear()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error sending emails: {str(e)}', 'error')
    
    return redirect(url_for('load_data.select_timeframe', timeframe_id=timeframe_id))