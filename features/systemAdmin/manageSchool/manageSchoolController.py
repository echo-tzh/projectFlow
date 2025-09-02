from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from functools import wraps
from database import db
from shared.models import School, User, Role
from datetime import datetime
import re

# Create blueprint
manage_school_bp = Blueprint('manage_school', __name__, 
                           template_folder='templates',
                           static_folder='static')

def admin_required(f):
    """Decorator to ensure only system admins can access these routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in (assuming you store user_id in session)
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))  # Adjust this route as needed
        
        # Get current user
        current_user = User.query.get(session['user_id'])
        if not current_user:
            flash('Invalid session. Please log in again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if user has system admin role
        admin_role = current_user.roles.filter_by(name='system admin').first()
        if not admin_role:
            flash('Access denied. System admin privileges required.', 'error')
            return redirect(url_for('universal_dashboard.dashboard'))  # Adjust this route as needed
        
        return f(*args, **kwargs)
    return decorated_function

@manage_school_bp.route('/schools')
@admin_required
def view_schools():
    """Display all schools with search functionality"""
    search_query = request.args.get('search', '', type=str).strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Schools per page
    
    # Base query
    query = School.query
    
    # Apply search filter if provided
    if search_query:
        # Search in school name and address
        search_pattern = f"%{search_query}%"
        query = query.filter(
            db.or_(
                School.name.ilike(search_pattern),
                School.address.ilike(search_pattern)
            )
        )
    
    # Order by name alphabetically
    query = query.order_by(School.name.asc())
    
    # Paginate results
    schools_pagination = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    schools = schools_pagination.items
    
    # Get user count for each school
    schools_with_stats = []
    for school in schools:
        user_count = User.query.filter_by(school_id=school.id).count()
        schools_with_stats.append({
            'school': school,
            'user_count': user_count
        })
    
    return render_template('manageSchool.html',
                         schools=schools_with_stats,
                         pagination=schools_pagination,
                         search_query=search_query,
                         total_schools=School.query.count())

@manage_school_bp.route('/schools/search')
@admin_required
def search_schools():
    """AJAX endpoint for live search"""
    search_query = request.args.get('q', '', type=str).strip()
    
    if not search_query:
        return jsonify({'schools': []})
    
    # Search schools
    search_pattern = f"%{search_query}%"
    schools = School.query.filter(
        db.or_(
            School.name.ilike(search_pattern),
            School.address.ilike(search_pattern)
        )
    ).order_by(School.name.asc()).limit(10).all()
    
    # Format response
    schools_data = []
    for school in schools:
        user_count = User.query.filter_by(school_id=school.id).count()
        schools_data.append({
            'id': school.id,
            'name': school.name,
            'address': school.address or 'No address provided',
            'user_count': user_count,
            'created_at': school.created_at.strftime('%d %b %Y')
        })
    
    return jsonify({'schools': schools_data})

@manage_school_bp.route('/schools/<int:school_id>')
@admin_required
def view_school_details(school_id):
    """View detailed information about a specific school"""
    school = School.query.get_or_404(school_id)
    
    # Get users associated with this school
    users = User.query.filter_by(school_id=school_id).order_by(User.name.asc()).all()
    
    # Get statistics
    stats = {
        'total_users': len(users),
        'students': len([u for u in users if u.roles.filter_by(name='student').first()]),
        'supervisors': len([u for u in users if u.roles.filter_by(name='supervisor').first()]),
        'coordinators': len([u for u in users if u.roles.filter_by(name='coordinator').first()]),
        'admins': len([u for u in users if u.roles.filter_by(name='admin').first()])
    }
    
    return render_template('schoolDetails.html',
                         school=school,
                         users=users,
                         stats=stats)

@manage_school_bp.route('/schools/add', methods=['GET', 'POST'])
@admin_required
def add_school():
    """Add a new school"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        
        # Validation
        if not name:
            flash('School name is required.', 'error')
            return redirect(url_for('manage_school.add_school'))
        
        # Check if school already exists
        existing_school = School.query.filter_by(name=name).first()
        if existing_school:
            flash('A school with this name already exists.', 'error')
            return redirect(url_for('manage_school.add_school'))
        
        try:
            # Create new school
            new_school = School(
                name=name,
                address=address if address else None,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_school)
            db.session.commit()
            
            flash(f'School "{name}" has been added successfully.', 'success')
            return redirect(url_for('manage_school.view_schools'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding school: {str(e)}', 'error')
            return redirect(url_for('manage_school.add_school'))
    
    return render_template('addSchool.html')

@manage_school_bp.route('/schools/<int:school_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_school(school_id):
    """Edit an existing school"""
    school = School.query.get_or_404(school_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        
        # Validation
        if not name:
            flash('School name is required.', 'error')
            return redirect(url_for('manage_school.edit_school', school_id=school_id))
        
        # Check if another school has this name
        existing_school = School.query.filter(
            School.name == name,
            School.id != school_id
        ).first()
        
        if existing_school:
            flash('Another school with this name already exists.', 'error')
            return redirect(url_for('manage_school.edit_school', school_id=school_id))
        
        try:
            # Update school
            school.name = name
            school.address = address if address else None
            
            db.session.commit()
            
            flash(f'School "{name}" has been updated successfully.', 'success')
            return redirect(url_for('manage_school.view_schools'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating school: {str(e)}', 'error')
    
    return render_template('editSchool.html', school=school)

@manage_school_bp.route('/schools/<int:school_id>/delete', methods=['POST'])
@admin_required
def delete_school(school_id):
    """Delete a school (with safety checks)"""
    school = School.query.get_or_404(school_id)
    
    # Check if school has users
    user_count = User.query.filter_by(school_id=school_id).count()
    if user_count > 0:
        flash(f'Cannot delete "{school.name}". It has {user_count} associated users. Please reassign or remove users first.', 'error')
        return redirect(url_for('manage_school.view_schools'))
    
    try:
        db.session.delete(school)
        db.session.commit()
        flash(f'School "{school.name}" has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting school: {str(e)}', 'error')
    
    return redirect(url_for('manage_school.view_schools'))