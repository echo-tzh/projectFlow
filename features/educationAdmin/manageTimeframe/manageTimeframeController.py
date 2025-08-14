from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from database import db
from shared.models import User, Timeframe, Project
from datetime import datetime
from sqlalchemy import func

# Create the blueprint
manage_timeframe_bp = Blueprint('manage_timeframe_bp', __name__, template_folder='templates')

@manage_timeframe_bp.route('/manage-timeframes')
def manage_timeframes():
    """
    Main page to display all timeframes for the school
    """
    try:
        # Get user_id from session
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in again.', 'error')
            return redirect(url_for('login_bp.login'))
        
        # Get the user and their school information
        user = User.query.get(user_id)
        if not user:
            flash('User not found. Please log in again.', 'error')
            return redirect(url_for('login_bp.login'))
        
        if not user.school_id:
            flash('No school associated with your account. Please contact administrator.', 'error')
            return redirect(url_for('login_bp.login'))
        
        school_id = user.school_id
        
        # Get all timeframes for this school, ordered by creation date (newest first)
        timeframes = Timeframe.query.filter_by(school_id=school_id).order_by(Timeframe.created_at.desc()).all()
        
        # Get school name for display
        school_name = user.school.name if user.school else 'Your School'
        
        return render_template('manage_timeframes.html',
                             timeframes=timeframes,
                             school_name=school_name)
    
    except Exception as e:
        flash(f'Error loading timeframes: {str(e)}', 'error')
        return redirect(url_for('universal_dashboard.dashboard'))


@manage_timeframe_bp.route('/create-timeframe', methods=['POST'])
def create_timeframe():
    """
    Handle timeframe creation
    """
    try:
        # Get form data
        name = request.form.get('name', '').strip()
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        # Validation
        if not all([name, start_date_str, end_date_str]):
            flash('All fields are required.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Check if end date is after start date
        if end_date <= start_date:
            flash('End date must be after start date.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Get user_id from session
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in again.', 'error')
            return redirect(url_for('login_bp.login'))
        
        # Get the user and their school information
        user = User.query.get(user_id)
        if not user or not user.school_id:
            flash('School information not found. Please log in again.', 'error')
            return redirect(url_for('login_bp.login'))
        
        school_id = user.school_id
        
        # Check if timeframe name already exists for this school
        existing_timeframe = Timeframe.query.filter_by(
            school_id=school_id,
            name=name
        ).first()
        
        if existing_timeframe:
            flash('A timeframe with this name already exists.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Create new timeframe
        new_timeframe = Timeframe(
            name=name,
            start_date=start_date,
            end_date=end_date,
            school_id=school_id
        )
        
        # Save to database
        db.session.add(new_timeframe)
        db.session.commit()
        
        flash(f'Timeframe "{name}" created successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating timeframe: {str(e)}', 'error')
    
    return redirect(url_for('manage_timeframe_bp.manage_timeframes'))


@manage_timeframe_bp.route('/edit-timeframe', methods=['POST'])
def edit_timeframe():
    """
    Handle timeframe updates
    """
    try:
        # Get form data
        timeframe_id = request.form.get('timeframe_id')
        name = request.form.get('name', '').strip()
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        # Validation
        if not all([timeframe_id, name, start_date_str, end_date_str]):
            flash('All fields are required.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Check if end date is after start date
        if end_date <= start_date:
            flash('End date must be after start date.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Get user_id from session
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in again.', 'error')
            return redirect(url_for('login_bp.login'))
        
        # Get the user and their school information
        user = User.query.get(user_id)
        if not user or not user.school_id:
            flash('School information not found. Please log in again.', 'error')
            return redirect(url_for('login_bp.login'))
        
        school_id = user.school_id
        
        # Find the timeframe to update
        timeframe = Timeframe.query.filter_by(
            id=timeframe_id,
            school_id=school_id
        ).first()
        
        if not timeframe:
            flash('Timeframe not found.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Check if new name conflicts with another timeframe (excluding current one)
        existing_timeframe = Timeframe.query.filter_by(
            school_id=school_id,
            name=name
        ).filter(Timeframe.id != timeframe_id).first()
        
        if existing_timeframe:
            flash('Another timeframe with this name already exists.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Update timeframe
        old_name = timeframe.name
        timeframe.name = name
        timeframe.start_date = start_date
        timeframe.end_date = end_date
        
        # Save changes
        db.session.commit()
        
        flash(f'Timeframe "{old_name}" updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating timeframe: {str(e)}', 'error')
    
    return redirect(url_for('manage_timeframe_bp.manage_timeframes'))


@manage_timeframe_bp.route('/delete-timeframe', methods=['POST'])
def delete_timeframe():
    """
    Handle timeframe deletion
    """
    try:
        # Get timeframe ID
        timeframe_id = request.form.get('timeframe_id')
        if not timeframe_id:
            flash('Invalid timeframe ID.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Get user_id from session
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in again.', 'error')
            return redirect(url_for('login_bp.login'))
        
        # Get the user and their school information
        user = User.query.get(user_id)
        if not user or not user.school_id:
            flash('School information not found. Please log in again.', 'error')
            return redirect(url_for('login_bp.login'))
        
        school_id = user.school_id
        
        # Find the timeframe to delete
        timeframe = Timeframe.query.filter_by(
            id=timeframe_id,
            school_id=school_id
        ).first()
        
        if not timeframe:
            flash('Timeframe not found.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Check if timeframe has associated projects
        project_count = Project.query.filter_by(timeframe_id=timeframe_id).count()
        if project_count > 0:
            flash(f'Cannot delete timeframe "{timeframe.name}". It has {project_count} associated project(s). Please remove or reassign these projects first.', 'error')
            return redirect(url_for('manage_timeframe_bp.manage_timeframes'))
        
        # Store name for success message
        timeframe_name = timeframe.name
        
        # Delete the timeframe
        db.session.delete(timeframe)
        db.session.commit()
        
        flash(f'Timeframe "{timeframe_name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting timeframe: {str(e)}', 'error')
    
    return redirect(url_for('manage_timeframe_bp.manage_timeframes'))


# Additional utility routes that might be useful

@manage_timeframe_bp.route('/timeframe-details/<int:timeframe_id>')
def timeframe_details(timeframe_id):
    """
    Get details for a specific timeframe (useful for AJAX calls)
    """
    try:
        # Get user_id from session
        user_id = session.get('user_id')
        if not user_id:
            return {'error': 'Not authenticated'}, 401
        
        # Get user and school info
        user = User.query.get(user_id)
        if not user or not user.school_id:
            return {'error': 'School information not found'}, 403
        
        # Find timeframe
        timeframe = Timeframe.query.filter_by(
            id=timeframe_id,
            school_id=user.school_id
        ).first()
        
        if not timeframe:
            return {'error': 'Timeframe not found'}, 404
        
        # Get project count
        project_count = Project.query.filter_by(timeframe_id=timeframe_id).count()
        
        return {
            'id': timeframe.id,
            'name': timeframe.name,
            'start_date': timeframe.start_date.strftime('%Y-%m-%d'),
            'end_date': timeframe.end_date.strftime('%Y-%m-%d'),
            'created_at': timeframe.created_at.strftime('%Y-%m-%d'),
            'project_count': project_count
        }
        
    except Exception as e:
        return {'error': str(e)}, 500


@manage_timeframe_bp.route('/validate-timeframe-name', methods=['POST'])
def validate_timeframe_name():
    """
    Check if a timeframe name is available (useful for AJAX validation)
    """
    try:
        name = request.json.get('name', '').strip()
        timeframe_id = request.json.get('timeframe_id')  # For edits
        
        if not name:
            return {'available': False, 'message': 'Name is required'}
        
        # Get user info
        user_id = session.get('user_id')
        if not user_id:
            return {'error': 'Not authenticated'}, 401
        
        user = User.query.get(user_id)
        if not user or not user.school_id:
            return {'error': 'School information not found'}, 403
        
        # Check for existing name
        query = Timeframe.query.filter_by(school_id=user.school_id, name=name)
        
        # Exclude current timeframe if editing
        if timeframe_id:
            query = query.filter(Timeframe.id != timeframe_id)
        
        existing = query.first()
        
        return {
            'available': existing is None,
            'message': 'Name is available' if existing is None else 'Name already exists'
        }
        
    except Exception as e:
        return {'error': str(e)}, 500