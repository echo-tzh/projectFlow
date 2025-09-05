from flask import Blueprint, render_template, session, redirect, url_for, flash
from shared.models import User
from functools import wraps
import os

# Create Blueprint with correct template folder path
viewProfile_bp = Blueprint('viewProfile', __name__, 
                          template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login_bp.login'))
        return f(*args, **kwargs)
    return decorated_function

@viewProfile_bp.route('/profile')
@login_required
def view_own_profile():
    """View current user's profile"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            flash('No user ID in session. Please log in again.', 'danger')
            return redirect(url_for('login_bp.login'))
        
        user = User.query.get(user_id)
        
        if not user:
            flash('User profile not found.', 'danger')
            return redirect(url_for('universal_dashboard.dashboard'))
        return render_template('viewProfile.html', user=user)
        
    except Exception as e:
        print(f"ERROR: Exception occurred: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"ERROR: Full traceback:")
        traceback.print_exc()
        flash('An error occurred while loading your profile.', 'danger')
        return redirect(url_for('universal_dashboard.dashboard'))