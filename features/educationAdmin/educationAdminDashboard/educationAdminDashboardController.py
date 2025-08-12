from flask import Blueprint, render_template, session, redirect, url_for, flash
from functools import wraps
from shared.models import User, School  # Assuming User and School models are in shared.models

educational_admin_bp = Blueprint('educational_admin', __name__, template_folder='templates')

# Decorator to protect admin routes
def educational_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login_bp.login'))
        
        user = User.query.get(session['user_id'])
        if not user:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login_bp.login'))
        
        # Check if user has educational_admin role using the new role relationship
        user_roles = [role.name for role in user.roles]
        if 'educational_admin' not in user_roles:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('login_bp.login'))
        
        return f(*args, **kwargs)
    return decorated_function

@educational_admin_bp.route('/educational-admin-dashboard')
@educational_admin_required
def dashboard():
    user = User.query.get(session['user_id'])
    
    # Check if user is associated with a school
    if not user.school:
        flash('Your admin account is not linked to a school. Please contact support.', 'danger')
        return redirect(url_for('logout'))
    
    school_name = user.school.name if user.school else 'Your School'
    return render_template('educational_admin_dashboard.html', user=user, school_name=school_name)