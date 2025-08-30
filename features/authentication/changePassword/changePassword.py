from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from shared.models import User, db
import re

# Create blueprint for change password functionality
change_password_bp = Blueprint('change_password', __name__, 
                              template_folder='templates',
                              url_prefix='/account')

@change_password_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """
    Allow authenticated users to change their password
    """
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'GET':
        return render_template('changePassword.html', user=user)
    
    # Handle POST request
    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validation
        errors = []
        
        # Check if all fields are provided
        if not current_password:
            errors.append('Current password is required.')
        
        if not new_password:
            errors.append('New password is required.')
            
        if not confirm_password:
            errors.append('Password confirmation is required.')
        
        # Verify current password
        if current_password and not check_password_hash(user.password_hash, current_password):
            errors.append('Current password is incorrect.')
        
        # Password strength validation
        if new_password:
            if len(new_password) < 8:
                errors.append('New password must be at least 8 characters long.')
            
            if not re.search(r'[A-Z]', new_password):
                errors.append('New password must contain at least one uppercase letter.')
            
            if not re.search(r'[a-z]', new_password):
                errors.append('New password must contain at least one lowercase letter.')
            
            if not re.search(r'\d', new_password):
                errors.append('New password must contain at least one number.')
            
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
                errors.append('New password must contain at least one special character.')
        
        # Check if new passwords match
        if new_password and confirm_password and new_password != confirm_password:
            errors.append('New password and confirmation do not match.')
        
        # Check if new password is different from current
        if current_password and new_password and current_password == new_password:
            errors.append('New password must be different from current password.')
        
        # If there are errors, return them
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('changePassword.html', user=user)
        
        try:
            # Update password
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            flash('Password changed successfully!', 'success')
            return redirect(url_for('change_password.change_password'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating your password: {str(e)}', 'error')
            return render_template('changePassword.html', user=user)

@change_password_bp.route('/validate-password', methods=['POST'])
def validate_password():
    """
    AJAX endpoint to validate password strength in real-time
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    password = request.json.get('password', '')
    
    # Password validation rules
    validations = {
        'length': len(password) >= 8,
        'uppercase': bool(re.search(r'[A-Z]', password)),
        'lowercase': bool(re.search(r'[a-z]', password)),
        'number': bool(re.search(r'\d', password)),
        'special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    }
    
    # Calculate strength score
    score = sum(validations.values())
    
    if score <= 2:
        strength = 'weak'
    elif score <= 3:
        strength = 'fair'
    elif score <= 4:
        strength = 'good'
    else:
        strength = 'strong'
    
    return jsonify({
        'validations': validations,
        'strength': strength,
        'score': score,
        'is_valid': all(validations.values())
    })

@change_password_bp.route('/verify-current-password', methods=['POST'])
def verify_current_password():
    """
    AJAX endpoint to verify current password
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    current_password = request.json.get('password', '')
    is_valid = check_password_hash(user.password_hash, current_password)
    
    return jsonify({'is_valid': is_valid})