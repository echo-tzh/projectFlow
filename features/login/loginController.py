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
            session['role'] = user.role
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            # For security, use a generic error message for both invalid email and password.
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')