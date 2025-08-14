from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from functools import wraps
from shared.models import User, School, Role, Project, Timeframe
from database import db

universal_dashboard_bp = Blueprint('universal_dashboard', __name__, template_folder='templates')

# Decorator to protect dashboard routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login_bp.login'))
        
        user = User.query.get(session['user_id'])
        if not user:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login_bp.login'))
        
        # Check if user has any roles
        if not user.roles.first():
            flash('Your account does not have any assigned roles. Please contact support.', 'error')
            return redirect(url_for('login_bp.logout'))
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_role(user):
    """Get the current active role for the user"""
    # If role is specified in session, use that
    if 'current_role' in session:
        # Verify the user actually has this role
        user_role_names = [role.name for role in user.roles]
        if session['current_role'] in user_role_names:
            return session['current_role']
    
    # Default to first role if no valid session role
    first_role = user.roles.first()
    if first_role:
        session['current_role'] = first_role.name
        return first_role.name
    
    return None



@universal_dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    current_role = get_current_role(user)
    
    if not current_role:
        flash('Unable to determine your role. Please contact support.', 'error')
        return redirect(url_for('login_bp.logout'))
    
    # Get all user roles for dropdown
    user_roles = [{'name': role.name, 'display_name': role.description or role.name} 
                  for role in user.roles]
    
    # Get role-specific dashboard data

    
    # Get school name for display
    school_name = user.school.name if user.school else 'Your Institution'
    
    return render_template('dashboard.html', 
                         user=user,
                         current_role=current_role,
                         current_role_display=next((role.description or role.name for role in user.roles if role.name == current_role), current_role),
                         user_roles=user_roles,
                         school_name=school_name,
                         )

@universal_dashboard_bp.route('/switch-role', methods=['POST'])
@login_required
def switch_role():
    """API endpoint to switch user's active role"""
    user = User.query.get(session['user_id'])
    requested_role = request.json.get('role')
    
    # Verify user has the requested role
    user_role_names = [role.name for role in user.roles]
    if requested_role not in user_role_names:
        return jsonify({'success': False, 'message': 'You do not have access to this role'}), 403
    
    # Update session
    session['current_role'] = requested_role
    
    return jsonify({
        'success': True, 
        'message': f'Role switched successfully',
        'redirect_url': url_for('universal_dashboard.dashboard')
    })

@universal_dashboard_bp.route('/dashboard-data/<role>')
@login_required
def get_dashboard_data_api(role):
    """API endpoint to get dashboard data for a specific role"""
    user = User.query.get(session['user_id'])
    
    # Verify user has the requested role
    user_role_names = [role.name for role in user.roles]
    if role not in user_role_names:
        return jsonify({'error': 'Unauthorized'}), 403
    
    dashboard_data = get_dashboard_data(user, role)
    return jsonify(dashboard_data)