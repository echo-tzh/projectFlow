from flask import Blueprint, render_template, session, redirect, url_for, flash
from shared.models import User, Timeframe, School, db
from sqlalchemy import and_
from datetime import datetime

# Create blueprint for academic coordinator course term viewing
view_course_term_bp = Blueprint('view_course_term', __name__, 
                               template_folder='templates',
                               url_prefix='/academic-coordinator')

@view_course_term_bp.route('/course-terms')
def view_course_terms():
    """
    Display all course terms (timeframes) that the academic coordinator is assigned to
    """
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    # Get the current user and verify they have academic coordinator role
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))
    
    # Check if user has coordinator role (assuming role name is 'coordinator' or 'academic_coordinator')
    user_roles = [role.name for role in user.roles]
    if 'coordinator' not in user_roles and 'academic coordinator' not in user_roles:
        flash('Access denied. Academic coordinator privileges required.', 'error')
        return redirect(url_for('universal_dashboard.dashboard'))  # Redirect to main dashboard
    
    try:
        # Get all timeframes assigned to this user
        assigned_timeframes = user.timeframes.all()
        
        # Organize timeframes by status (current, upcoming, past)
        current_date = datetime.now().date()
        current_timeframes = []
        upcoming_timeframes = []
        past_timeframes = []
        
        for timeframe in assigned_timeframes:
            if timeframe.start_date <= current_date <= timeframe.end_date:
                current_timeframes.append(timeframe)
            elif timeframe.start_date > current_date:
                upcoming_timeframes.append(timeframe)
            else:
                past_timeframes.append(timeframe)
        
        # Sort timeframes by start date
        current_timeframes.sort(key=lambda x: x.start_date)
        upcoming_timeframes.sort(key=lambda x: x.start_date)
        past_timeframes.sort(key=lambda x: x.start_date, reverse=True)
        
        # Get summary statistics
        total_timeframes = len(assigned_timeframes)
        active_timeframes = len(current_timeframes)
        
        return render_template('viewCourseTerm.html',
                             user=user,
                             current_timeframes=current_timeframes,
                             upcoming_timeframes=upcoming_timeframes,
                             past_timeframes=past_timeframes,
                             total_timeframes=total_timeframes,
                             active_timeframes=active_timeframes,
                             current_date=current_date)
    
    except Exception as e:
        flash(f'An error occurred while loading course terms: {str(e)}', 'error')
        return redirect(url_for('universal_dashboard.dashboard'))

@view_course_term_bp.route('/course-term/<int:timeframe_id>')
def view_course_term_detail(timeframe_id):
    """
    Display detailed information about a specific course term
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
    
    try:
        # Get the specific timeframe and verify user has access to it
        timeframe = Timeframe.query.get_or_404(timeframe_id)
        
        # Check if user is assigned to this timeframe
        user_timeframes_ids = [tf.id for tf in user.timeframes]
        if timeframe_id not in user_timeframes_ids:
            flash('Access denied. You are not assigned to this course term.', 'error')
            return redirect(url_for('view_course_term.view_course_terms'))
        
        # Get projects associated with this timeframe
        projects = timeframe.projects
        
        # Determine timeframe status
        current_date = datetime.now().date()
        if timeframe.start_date <= current_date <= timeframe.end_date:
            status = 'current'
        elif timeframe.start_date > current_date:
            status = 'upcoming'
        else:
            status = 'past'
        
        # Calculate duration
        duration_days = (timeframe.end_date - timeframe.start_date).days + 1
        
        return render_template('viewCourseTermDetail.html',
                             timeframe=timeframe,
                             projects=projects,
                             status=status,
                             duration_days=duration_days,
                             current_date=current_date)
    
    except Exception as e:
        flash(f'An error occurred while loading course term details: {str(e)}', 'error')
        return redirect(url_for('view_course_term.view_course_terms'))