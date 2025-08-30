from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from shared.models import User
from werkzeug.security import check_password_hash

login_bp = Blueprint('login_bp', __name__, template_folder='templates')

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        # Correctly check the password hash
        # The password from the form is plain text, while user.password_hash is a hash.
        # You must use check_password_hash to securely compare them.
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            
            # Get all role names for the user
            role_names = [role.name for role in user.roles]
            session['roles'] = role_names  # Store as list
            
            # For backward compatibility, store primary role as 'role'
            # You can customize this logic based on your needs
            if role_names:
                session['role'] = role_names[0]  # First role as primary
            else:
                session['role'] = None
                
            #flash('Login successful!', 'success')
            return redirect(url_for('universal_dashboard.dashboard'))
        else:
            # For security, use a generic error message for both invalid email and password.
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')
@login_bp.route('/logout')
def logout():
    session.clear()  # Remove all session data (user_id, roles, etc.)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login_bp.login'))  # Redirect to login page
