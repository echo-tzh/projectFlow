from flask import Blueprint, render_template, session, redirect, url_for, flash
from shared.models import User, Role

navigation_bp = Blueprint('navigation_bp', __name__)

def get_user_roles():
    """Get current user's roles from session"""
    if 'user_id' not in session:
        return []
    
    user = User.query.get(session['user_id'])
    if not user:
        return []
    
    return [role.name for role in user.roles]

def get_navigation_items(user_roles):
    """Return navigation items based on user roles"""
    nav_items = []
    
    # Common items for all authenticated users
    nav_items.append({
        'title': 'Dashboard',
        'icon': 'fas fa-tachometer-alt',
        'url': url_for('universal_dashboard.dashboard'),
        'active_class': 'dashboard'
    })
    
    nav_items.append({
        'title': 'Profile',
        'icon': 'fas fa-user',
        'url': url_for('viewProfile.view_own_profile'),
        'active_class': 'profile'
    })
    
    # System Admin specific items
    if 'system admin' in user_roles:
        nav_items.extend([
            {
                'title': 'Edit Marketing Content',
                'icon': 'fas fa-paint-brush',
                'url': url_for('edit_marketing_bp.edit_marketing'),
                'active_class': 'edit-marketing'
            },
            {
                'title': 'School Management',
                'icon': 'fas fa-school',
                'url': url_for('manage_school.view_schools'),
                'active_class': 'manage-school'
            }
        ])
    
    # Education Admin specific items
    if 'educational_admin' in user_roles:
        nav_items.extend([
            {
                'title': 'Manage Course Term',
                'icon': 'fas fa-calendar-alt',
                'url': url_for('manage_timeframe_bp.manage_timeframes'),
                'active_class': 'manage-timeframes'
            },
            {
                'title': 'Load Data',
                'icon': 'fas fa-upload',
                'url': url_for('load_data.index'),
                'active_class': 'load-data'
            },
            {
                'title': 'Setup Email',
                'icon': 'fas fa-envelope-open-text',
                'url': url_for('setup_email_bp.setup_email'),
                'active_class': 'setup-email'
            }
        ])
    
    # Student specific items
    if 'student' in user_roles:
        nav_items.extend([
            {
                'title': 'View Projects',
                'icon': 'fas fa-project-diagram',
                'url': url_for('student_projects.view_projects'),
                'active_class': 'view-projects'
            }
        ])
    
    # Academic Coordinator specific items  
    if 'academic coordinator' in user_roles:
        nav_items.extend([
            {
                'title': 'Course Terms',
                'icon': 'fas fa-graduation-cap',
                'url': url_for('view_course_term.view_course_terms'),
                'active_class': 'course-terms'
            }
        ])
    
    # Common items at bottom
    nav_items.extend([
        {
            'title': 'Change Password',
            'icon': 'fas fa-key',
            'url': url_for('change_password.change_password'),
            'active_class': 'change-password'
        },
        {
            'title': 'Logout',
            'icon': 'fas fa-sign-out-alt',
            'url': url_for('login_bp.logout'),
            'active_class': 'logout'
        }
    ])
    
    return nav_items

def inject_navigation():
    """Make navigation data available to all templates"""
    if 'user_id' not in session:
        return {}
    
    user_role_names = get_user_roles()  # List of role name strings
    nav_items = get_navigation_items(user_role_names)
    
    return {
        'nav_items': nav_items
    }