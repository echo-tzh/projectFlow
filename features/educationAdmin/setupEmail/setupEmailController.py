from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from database import db
from shared.models import EmailConfig, School, User
from shared.service.email_service import EmailService
from functools import wraps

setup_email_bp = Blueprint('setup_email_bp', __name__, 
                          url_prefix='/setup-email',
                          template_folder='templates') 
def educational_admin_required(f):
    """Decorator to ensure only educational_admins can access email setup"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login_bp.login'))
        
        user = User.query.get(session['user_id'])
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('login_bp.login'))
        
        # Check if user has educational_admin role
        user_roles = [role.name for role in user.roles]
        if 'educational_admin' not in user_roles:
            flash('Access denied. Educational admin privileges required.', 'error')
            return redirect(url_for('universal_dashboard_bp.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@setup_email_bp.route('/')
@educational_admin_required
def setup_email():
    """Main email setup page"""
    user = User.query.get(session['user_id'])
    
    if not user.school:
        flash('No school associated with your account. Please contact support.', 'error')
        return redirect(url_for('universal_dashboard_bp.dashboard'))
    
    # Get existing email config for the user's school
    email_config = EmailConfig.query.filter_by(school_id=user.school_id, is_active=True).first()
    
    return render_template('setup_email.html', 
                         user=user, 
                         email_config=email_config,
                         school=user.school)

@setup_email_bp.route('/save', methods=['POST'])
@educational_admin_required
def save_email_config():
    """Save or update email configuration"""
    user = User.query.get(session['user_id'])
    
    if not user.school:
        flash('No school associated with your account.', 'error')
        return redirect(url_for('setup_email_bp.setup_email'))
    
    try:
        # Get form data
        smtp_server = request.form.get('smtp_server', '').strip()
        smtp_port = int(request.form.get('smtp_port', 587))
        smtp_username = request.form.get('smtp_username', '').strip()
        smtp_password = request.form.get('smtp_password', '').strip()
        from_email = request.form.get('from_email', '').strip()
        from_name = request.form.get('from_name', '').strip()
        use_tls = request.form.get('use_tls') == 'on'
        use_ssl = request.form.get('use_ssl') == 'on'
        
        # Validation
        if not all([smtp_server, smtp_username, smtp_password, from_email]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('setup_email_bp.setup_email'))
        
        # Check for existing config
        existing_config = EmailConfig.query.filter_by(school_id=user.school_id, is_active=True).first()
        
        if existing_config:
            # Update existing config
            existing_config.smtp_server = smtp_server
            existing_config.smtp_port = smtp_port
            existing_config.smtp_username = smtp_username
            existing_config.smtp_password = smtp_password
            existing_config.from_email = from_email
            existing_config.from_name = from_name or 'ProjectFlow Team'
            existing_config.use_tls = use_tls
            existing_config.use_ssl = use_ssl
            
            email_config = existing_config
            action = 'updated'
        else:
            # Create new config
            email_config = EmailConfig(
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                smtp_username=smtp_username,
                smtp_password=smtp_password,
                from_email=from_email,
                from_name=from_name or 'ProjectFlow Team',
                use_tls=use_tls,
                use_ssl=use_ssl,
                school_id=user.school_id,
                created_by=user.id,
                is_active=True
            )
            db.session.add(email_config)
            action = 'saved'
        
        db.session.commit()
        flash(f'Email configuration {action} successfully!', 'success')
        
    except ValueError:
        flash('Invalid port number. Please enter a valid number.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving email configuration: {str(e)}', 'error')
    
    return redirect(url_for('setup_email_bp.setup_email'))

@setup_email_bp.route('/test', methods=['POST'])
@educational_admin_required
def test_email_config():
    """Test email configuration"""
    user = User.query.get(session['user_id'])
    
    if not user.school:
        return jsonify({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        test_email = request.form.get('test_email', '').strip()
        if not test_email:
            return jsonify({'success': False, 'message': 'Please provide a test email address.'})
        
        # Get email config for the school
        email_config = EmailConfig.query.filter_by(school_id=user.school_id, is_active=True).first()
        
        if not email_config:
            return jsonify({'success': False, 'message': 'No email configuration found. Please save your settings first.'})
        
        # Test the connection first
        email_service = EmailService(email_config)
        connection_result = email_service.test_connection()
        
        if not connection_result['success']:
            return jsonify({
                'success': False, 
                'message': f"Connection failed: {connection_result['message']}"
            })
        
        # Send test email
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
            to_email=test_email,
            subject=subject,
            body_text=body_text
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Test email sent successfully to {test_email}!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send test email'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error testing email: {str(e)}'
        })

@setup_email_bp.route('/delete', methods=['POST'])
@educational_admin_required
def delete_email_config():
    """Delete email configuration"""
    user = User.query.get(session['user_id'])
    
    if not user.school:
        flash('No school associated with your account.', 'error')
        return redirect(url_for('setup_email_bp.setup_email'))
    
    try:
        email_config = EmailConfig.query.filter_by(school_id=user.school_id, is_active=True).first()
        
        if email_config:
            # Soft delete - just mark as inactive
            email_config.is_active = False
            db.session.commit()
            flash('Email configuration deleted successfully.', 'success')
        else:
            flash('No email configuration found to delete.', 'warning')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting email configuration: {str(e)}', 'error')
    
    return redirect(url_for('setup_email_bp.setup_email'))