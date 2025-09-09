from datetime import date
from flask import Blueprint, session, redirect, url_for, flash, request, jsonify
from functools import wraps
from shared.models import User, Project, Timeframe, Wishlist
from database import db

student_wishlist_bp = Blueprint(
    "student_wishlist",
    __name__,
    template_folder="templates"
)

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login_bp.login"))
        return f(*args, **kwargs)
    return wrapped

@student_wishlist_bp.route("/wishlist/add", methods=["POST"])
@login_required
def add_to_wishlist():
    """Add a project to the user's wishlist."""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        
        if not project_id:
            return jsonify({'success': False, 'message': 'Project ID is required'}), 400
        
        user = User.query.get(session["user_id"])
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Check if project exists and user has access to it
        project = Project.query.join(Timeframe, Project.timeframe_id == Timeframe.id).filter(
            Project.id == project_id,
            Timeframe.school_id == user.school_id if user.school_id else True
        ).first()
        
        if not project:
            return jsonify({'success': False, 'message': 'Project not found or access denied'}), 404
        
        # Check if already in wishlist
        existing_wishlist = Wishlist.query.filter_by(user_id=user.id, project_id=project_id).first()
        if existing_wishlist:
            return jsonify({'success': False, 'message': 'Project already in wishlist'}), 409
        
        # Add to wishlist
        new_wishlist_item = Wishlist(user_id=user.id, project_id=project_id)
        db.session.add(new_wishlist_item)
        db.session.commit()
        
        # Get updated wishlist count
        wishlist_count = user.wishlists.count()
        
        return jsonify({
            'success': True, 
            'message': 'Project added to wishlist successfully',
            'wishlist_count': wishlist_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@student_wishlist_bp.route("/wishlist/remove", methods=["POST"])
@login_required
def remove_from_wishlist():
    """Remove a project from the user's wishlist."""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        
        if not project_id:
            return jsonify({'success': False, 'message': 'Project ID is required'}), 400
        
        user = User.query.get(session["user_id"])
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Find and remove from wishlist
        wishlist_item = Wishlist.query.filter_by(user_id=user.id, project_id=project_id).first()
        if not wishlist_item:
            return jsonify({'success': False, 'message': 'Project not in wishlist'}), 404
        
        db.session.delete(wishlist_item)
        db.session.commit()
        
        # Get updated wishlist count
        wishlist_count = user.wishlists.count()
        
        return jsonify({
            'success': True, 
            'message': 'Project removed from wishlist successfully',
            'wishlist_count': wishlist_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@student_wishlist_bp.route("/wishlist", methods=["GET"])
@login_required
def get_wishlist():
    """Get all projects in the user's wishlist."""
    try:
        user = User.query.get(session["user_id"])
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Get all wishlisted projects with their details
        wishlist_projects = db.session.query(Project, Wishlist).join(
            Wishlist, Project.id == Wishlist.project_id
        ).join(
            Timeframe, Project.timeframe_id == Timeframe.id
        ).filter(
            Wishlist.user_id == user.id,
            Timeframe.school_id == user.school_id if user.school_id else True
        ).order_by(Wishlist.id.desc()).all()
        
        projects_data = []
        for project, wishlist_item in wishlist_projects:
            projects_data.append({
                'id': project.id,
                'title': project.title,
                'description': project.description or 'No description provided.',
                'timeframe': project.timeframe.name if project.timeframe else 'Unscheduled Term',
                'student_capacity': project.student_capacity,
                'created_at': project.created_at.strftime('%Y-%m-%d') if project.created_at else 'Unknown'
            })
        
        return jsonify({
            'success': True,
            'projects': projects_data,
            'count': len(projects_data)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500