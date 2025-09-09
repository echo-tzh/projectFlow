from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from shared.models import User, Timeframe, Project, Wishlist, Preference, db
from datetime import datetime
import logging

# Create blueprint for student preferences
student_preferences_bp = Blueprint('student_preferences', __name__, 
                                 template_folder='templates',
                                 url_prefix='/student')

@student_preferences_bp.route('/preferences')
def preferences():
    """
    Display the student preferences page
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
    
    # Check if user has student role
    user_roles = [role.name for role in user.roles]
    if 'student' not in user_roles:
        flash('Access denied. Student privileges required.', 'error')
        return redirect(url_for('universal_dashboard.dashboard'))
    
    try:
        # Get student's active timeframes
        active_timeframes = []
        current_date = datetime.now().date()
        
        for timeframe in user.timeframes:
            # Check if preference submission is currently open
            if (timeframe.preference_startTiming <= current_date <= timeframe.preference_endTiming):
                active_timeframes.append(timeframe)
        
        if not active_timeframes:
            flash('No active preference submission periods available.', 'info')
            return render_template('studentPreferences.html', 
                                 user=user,
                                 active_timeframes=[],
                                 wishlist_projects=[],
                                 existing_preferences={})
        
        # For now, use the first active timeframe
        # In a more complex system, you might let students choose
        current_timeframe = active_timeframes[0]
        
        # Get student's wishlist projects for this timeframe
        wishlist_projects = db.session.query(Project, Wishlist).join(
            Wishlist, Project.id == Wishlist.project_id
        ).filter(
            Wishlist.user_id == user_id,
            Project.timeframe_id == current_timeframe.id
        ).all()
        
        # Get existing preferences for this timeframe
        existing_preferences = Preference.query.filter_by(
            user_id=user_id,
            timeframe_id=current_timeframe.id
        ).order_by(Preference.preference_rank).all()
        
        # Create a dictionary mapping preference rank to project
        existing_prefs_dict = {}
        for pref in existing_preferences:
            existing_prefs_dict[pref.preference_rank] = {
                'project': pref.project,
                'notes': pref.notes
            }
        
        return render_template('studentPreferences.html',
                             user=user,
                             current_timeframe=current_timeframe,
                             active_timeframes=active_timeframes,
                             wishlist_projects=wishlist_projects,
                             existing_preferences=existing_prefs_dict,
                             preference_limit=current_timeframe.preference_limit)
    
    except Exception as e:
        logging.error(f"Error in student preferences: {str(e)}")
        flash(f'An error occurred while loading preferences: {str(e)}', 'error')
        return redirect(url_for('universal_dashboard.dashboard'))

@student_preferences_bp.route('/preferences/submit', methods=['POST'])
def submit_preferences():
    """
    Submit student project preferences
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Check role
    user_roles = [role.name for role in user.roles]
    if 'student' not in user_roles:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.json
        timeframe_id = data.get('timeframe_id')
        preferences_data = data.get('preferences', [])
        
        if not timeframe_id:
            return jsonify({'success': False, 'message': 'Timeframe ID is required'}), 400
        
        # Get timeframe and validate
        timeframe = Timeframe.query.get(timeframe_id)
        if not timeframe:
            return jsonify({'success': False, 'message': 'Timeframe not found'}), 404
        
        # Check if student has access to this timeframe
        user_timeframes_ids = [tf.id for tf in user.timeframes]
        if timeframe_id not in user_timeframes_ids:
            return jsonify({'success': False, 'message': 'Access denied to this timeframe'}), 403
        
        # Check if preference submission is still open
        current_date = datetime.now().date()
        if not (timeframe.preference_startTiming <= current_date <= timeframe.preference_endTiming):
            return jsonify({'success': False, 'message': 'Preference submission period has ended'}), 400
        
        # Validate preferences data
        if not preferences_data:
            return jsonify({'success': False, 'message': 'At least one preference is required'}), 400
        
        if len(preferences_data) > timeframe.preference_limit:
            return jsonify({'success': False, 'message': f'Cannot exceed {timeframe.preference_limit} preferences'}), 400
        
        # Validate that all projects exist and are in the student's wishlist
        project_ids = [pref.get('project_id') for pref in preferences_data]
        
        # Check if all projects are in student's wishlist
        wishlist_project_ids = db.session.query(Wishlist.project_id).filter_by(
            user_id=user_id
        ).join(Project).filter(Project.timeframe_id == timeframe_id).all()
        wishlist_project_ids = [pid[0] for pid in wishlist_project_ids]
        
        for project_id in project_ids:
            if project_id not in wishlist_project_ids:
                return jsonify({'success': False, 'message': 'All preferences must be from your wishlist'}), 400
        
        # Check for duplicate project IDs
        if len(set(project_ids)) != len(project_ids):
            return jsonify({'success': False, 'message': 'Cannot select the same project multiple times'}), 400
        
        # Delete existing preferences for this timeframe
        Preference.query.filter_by(
            user_id=user_id,
            timeframe_id=timeframe_id
        ).delete()
        
        # Create new preferences
        for pref_data in preferences_data:
            project_id = pref_data.get('project_id')
            preference_rank = pref_data.get('rank')
            notes = pref_data.get('notes', '')
            
            # Validate project exists
            project = Project.query.get(project_id)
            if not project or project.timeframe_id != timeframe_id:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Invalid project ID: {project_id}'}), 400
            
            new_preference = Preference(
                user_id=user_id,
                project_id=project_id,
                timeframe_id=timeframe_id,
                preference_rank=preference_rank,
                notes=notes,
                selected_at=datetime.utcnow()
            )
            db.session.add(new_preference)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully submitted {len(preferences_data)} preferences!'
        })
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error submitting preferences: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to submit preferences'}), 500

@student_preferences_bp.route('/preferences/clear', methods=['POST'])
def clear_preferences():
    """
    Clear all student preferences for a timeframe
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Check role
    user_roles = [role.name for role in user.roles]
    if 'student' not in user_roles:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.json
        timeframe_id = data.get('timeframe_id')
        
        if not timeframe_id:
            return jsonify({'success': False, 'message': 'Timeframe ID is required'}), 400
        
        # Validate access to timeframe
        timeframe = Timeframe.query.get(timeframe_id)
        if not timeframe:
            return jsonify({'success': False, 'message': 'Timeframe not found'}), 404
        
        user_timeframes_ids = [tf.id for tf in user.timeframes]
        if timeframe_id not in user_timeframes_ids:
            return jsonify({'success': False, 'message': 'Access denied to this timeframe'}), 403
        
        # Check if preference submission is still open
        current_date = datetime.now().date()
        if not (timeframe.preference_startTiming <= current_date <= timeframe.preference_endTiming):
            return jsonify({'success': False, 'message': 'Preference submission period has ended'}), 400
        
        # Delete preferences
        deleted_count = Preference.query.filter_by(
            user_id=user_id,
            timeframe_id=timeframe_id
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Cleared {deleted_count} preferences'
        })
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error clearing preferences: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to clear preferences'}), 500

@student_preferences_bp.route('/preferences/status')
def preferences_status():
    """
    Get current preferences status for the student
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    try:
        # Get active timeframes
        current_date = datetime.now().date()
        active_timeframes = []
        
        for timeframe in user.timeframes:
            if (timeframe.preference_startTiming <= current_date <= timeframe.preference_endTiming):
                # Get preferences count for this timeframe
                prefs_count = Preference.query.filter_by(
                    user_id=user_id,
                    timeframe_id=timeframe.id
                ).count()
                
                active_timeframes.append({
                    'id': timeframe.id,
                    'name': timeframe.name,
                    'preference_limit': timeframe.preference_limit,
                    'current_preferences': prefs_count,
                    'deadline': timeframe.preference_endTiming.strftime('%B %d, %Y')
                })
        
        return jsonify({
            'success': True,
            'active_timeframes': active_timeframes
        })
    
    except Exception as e:
        logging.error(f"Error getting preferences status: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to get status'}), 500