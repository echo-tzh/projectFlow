from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from shared.models import User, Timeframe, Project, db
from datetime import datetime
import logging

# Create blueprint for academic coordinator project management
manage_projects_bp = Blueprint('manage_projects', __name__, 
                              template_folder='templates',
                              url_prefix='/academic-coordinator')

@manage_projects_bp.route('/course-term/<int:timeframe_id>/manage-projects')
def manage_projects(timeframe_id):
    """
    Display project management page for a specific course term
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
    
    # Check if user has academic coordinator role
    user_roles = [role.name for role in user.roles]
    if 'academic coordinator' not in user_roles:
        flash('Access denied. Academic coordinator privileges required.', 'error')
        return redirect(url_for('universal_dashboard.dashboard'))
    
    try:
        # Get the timeframe and verify user has access
        timeframe = Timeframe.query.get_or_404(timeframe_id)
        
        # Check if user is assigned to this timeframe
        user_timeframes_ids = [tf.id for tf in user.timeframes]
        if timeframe_id not in user_timeframes_ids:
            flash('Access denied. You are not assigned to this course term.', 'error')
            return redirect(url_for('view_course_term.view_course_terms'))
        
        # Get all projects for this timeframe
        projects = Project.query.filter_by(timeframe_id=timeframe_id).order_by(Project.created_at.desc()).all()
        
        # Calculate total capacity across all projects
        total_student_capacity = sum(p.student_capacity or 0 for p in projects)
        total_supervisor_capacity = sum(p.supervisor_capacity or 0 for p in projects)
        total_assessor_capacity = sum(p.assessor_capacity or 0 for p in projects)
        
        return render_template('manageProjects.html',
                             timeframe=timeframe,
                             projects=projects,
                             user=user,
                             total_projects=len(projects),
                             total_student_capacity=total_student_capacity,
                             total_supervisor_capacity=total_supervisor_capacity,
                             total_assessor_capacity=total_assessor_capacity)
    
    except Exception as e:
        logging.error(f"Error in manage_projects: {str(e)}")
        flash(f'An error occurred while loading projects: {str(e)}', 'error')
        return redirect(url_for('view_course_term.view_course_terms'))

@manage_projects_bp.route('/course-term/<int:timeframe_id>/update-preference-limit', methods=['POST'])
def update_preference_limit(timeframe_id):
    """
    Update the preference limit for a course term
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Check role
    user_roles = [role.name for role in user.roles]
    if 'academic coordinator' not in user_roles:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        timeframe = Timeframe.query.get_or_404(timeframe_id)
        
        # Verify user access
        user_timeframes_ids = [tf.id for tf in user.timeframes]
        if timeframe_id not in user_timeframes_ids:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        preference_limit = request.json.get('preference_limit')
        
        if not preference_limit or not str(preference_limit).isdigit():
            return jsonify({'success': False, 'message': 'Invalid preference limit'}), 400
        
        preference_limit = int(preference_limit)
        if preference_limit < 1 or preference_limit > 10:
            return jsonify({'success': False, 'message': 'Preference limit must be between 1 and 10'}), 400
        
        timeframe.preference_limit = preference_limit
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Preference limit updated successfully'})
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating preference limit: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to update preference limit'}), 500

@manage_projects_bp.route('/course-term/<int:timeframe_id>/create-project', methods=['POST'])
def create_project(timeframe_id):
    """
    Create a new project for the course term
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Check role
    user_roles = [role.name for role in user.roles]
    if 'academic coordinator' not in user_roles:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        timeframe = Timeframe.query.get_or_404(timeframe_id)
        
        # Verify user access
        user_timeframes_ids = [tf.id for tf in user.timeframes]
        if timeframe_id not in user_timeframes_ids:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get form data
        data = request.json
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        student_capacity = data.get('student_capacity')
        supervisor_capacity = data.get('supervisor_capacity')
        assessor_capacity = data.get('assessor_capacity')
        
        # Validation
        if not title:
            return jsonify({'success': False, 'message': 'Project title is required'}), 400
        
        if len(title) > 255:
            return jsonify({'success': False, 'message': 'Title must be less than 255 characters'}), 400
        
        # Validate capacities
        for capacity, name in [(student_capacity, 'Student'), (supervisor_capacity, 'Supervisor'), (assessor_capacity, 'Assessor')]:
            if capacity is None or not str(capacity).isdigit():
                return jsonify({'success': False, 'message': f'{name} capacity must be a valid number'}), 400
            capacity_int = int(capacity)
            if capacity_int < 0 or capacity_int > 100:
                return jsonify({'success': False, 'message': f'{name} capacity must be between 0 and 100'}), 400
        
        # Create new project
        new_project = Project(
            title=title,
            description=description if description else None,
            student_capacity=int(student_capacity),
            supervisor_capacity=int(supervisor_capacity),
            assessor_capacity=int(assessor_capacity),
            timeframe_id=timeframe_id,
            created_by=user_id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_project)
        db.session.commit()
        
        # Return the created project data
        return jsonify({
            'success': True,
            'message': 'Project created successfully',
            'project': {
                'id': new_project.id,
                'title': new_project.title,
                'description': new_project.description,
                'student_capacity': new_project.student_capacity,
                'supervisor_capacity': new_project.supervisor_capacity,
                'assessor_capacity': new_project.assessor_capacity,
                'created_at': new_project.created_at.strftime('%B %d, %Y at %I:%M %p') if new_project.created_at else 'Unknown'
            }
        })
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating project: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to create project'}), 500

@manage_projects_bp.route('/project/<int:project_id>/update', methods=['PUT'])
def update_project(project_id):
    """
    Update an existing project
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Check role
    user_roles = [role.name for role in user.roles]
    if 'academic coordinator' not in user_roles:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        project = Project.query.get_or_404(project_id)
        
        # Verify user has access to this project's timeframe
        user_timeframes_ids = [tf.id for tf in user.timeframes]
        if project.timeframe_id not in user_timeframes_ids:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get form data
        data = request.json
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        student_capacity = data.get('student_capacity')
        supervisor_capacity = data.get('supervisor_capacity')
        assessor_capacity = data.get('assessor_capacity')
        
        # Validation
        if not title:
            return jsonify({'success': False, 'message': 'Project title is required'}), 400
        
        if len(title) > 255:
            return jsonify({'success': False, 'message': 'Title must be less than 255 characters'}), 400
        
        # Validate capacities
        for capacity, name in [(student_capacity, 'Student'), (supervisor_capacity, 'Supervisor'), (assessor_capacity, 'Assessor')]:
            if capacity is None or not str(capacity).isdigit():
                return jsonify({'success': False, 'message': f'{name} capacity must be a valid number'}), 400
            capacity_int = int(capacity)
            if capacity_int < 0 or capacity_int > 100:
                return jsonify({'success': False, 'message': f'{name} capacity must be between 0 and 100'}), 400
        
        # Update project
        project.title = title
        project.description = description if description else None
        project.student_capacity = int(student_capacity)
        project.supervisor_capacity = int(supervisor_capacity)
        project.assessor_capacity = int(assessor_capacity)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Project updated successfully',
            'project': {
                'id': project.id,
                'title': project.title,
                'description': project.description,
                'student_capacity': project.student_capacity,
                'supervisor_capacity': project.supervisor_capacity,
                'assessor_capacity': project.assessor_capacity
            }
        })
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating project: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to update project'}), 500

@manage_projects_bp.route('/project/<int:project_id>/delete', methods=['DELETE'])
def delete_project(project_id):
    """
    Delete a project
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Check role
    user_roles = [role.name for role in user.roles]
    if 'academic coordinator' not in user_roles:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        project = Project.query.get_or_404(project_id)
        
        # Verify user has access to this project's timeframe
        user_timeframes_ids = [tf.id for tf in user.timeframes]
        if project.timeframe_id not in user_timeframes_ids:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Check if project has any allocations or preferences
        # You might want to add this check based on your business logic
        # if project.allocated_users.count() > 0 or project.preferred_by.count() > 0:
        #     return jsonify({'success': False, 'message': 'Cannot delete project with existing allocations or preferences'}), 400
        
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Project deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting project: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to delete project'}), 500