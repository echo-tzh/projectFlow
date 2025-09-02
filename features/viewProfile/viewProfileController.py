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
        # Debug step 1: Check session
        user_id = session.get('user_id')
        #print(f"DEBUG: Session user_id = {user_id}")
       # print(f"DEBUG: Session contents = {dict(session)}")
        
        if not user_id:
            flash('No user ID in session. Please log in again.', 'danger')
            return redirect(url_for('login_bp.login'))
        
        # Debug step 2: Check database query
        #print(f"DEBUG: Attempting to query User with ID {user_id}")
        user = User.query.get(user_id)
        #print(f"DEBUG: Query result = {user}")
        
        if not user:
            print("DEBUG: User not found in database")
            flash('User profile not found.', 'danger')
            return redirect(url_for('universal_dashboard.dashboard'))
        
        # Debug step 3: Check user attributes
        #print(f"DEBUG: User name = {user.name}")
        #print(f"DEBUG: User email = {user.email}")
        #print(f"DEBUG: User roles = {list(user.roles)}")
        #print(f"DEBUG: User school = {user.school}")
        
        # Debug step 4: Try rendering template
        #print("DEBUG: About to render template")
        #print(f"DEBUG: Blueprint template folder: {viewProfile_bp.template_folder}")
        #print(f"DEBUG: Looking for template at: {os.path.join(viewProfile_bp.template_folder, 'viewProfile.html')}")
        #print(f"DEBUG: Template file exists: {os.path.exists(os.path.join(viewProfile_bp.template_folder, 'viewProfile.html'))}")
        return render_template('viewProfile.html', user=user)
        
    except Exception as e:
        print(f"ERROR: Exception occurred: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"ERROR: Full traceback:")
        traceback.print_exc()
        flash('An error occurred while loading your profile.', 'danger')
        return redirect(url_for('universal_dashboard.dashboard'))