from datetime import date
from flask import Blueprint, render_template, session, redirect, url_for, flash
from functools import wraps
from shared.models import User, Project, Timeframe
from database import db

student_projects_bp = Blueprint(
    "student_projects",
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

@student_projects_bp.route("/projects", methods=["GET"])
@login_required
def view_projects():
    """List available projects for the logged-in student's *current* timeframe(s)."""
    user = User.query.get(session["user_id"])
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("login_bp.logout"))

    # Get user timeframes - since timeframes relationship is defined with lazy='dynamic', it returns a query object
    user_timeframes = user.timeframes.all()
    user_tf_ids = [tf.id for tf in user_timeframes]

    # today must be inside the timeframe window, and timeframe must belong to the student's school
    q = Project.query.join(Timeframe, Project.timeframe_id == Timeframe.id)

    if user.school_id:
        q = q.filter(Timeframe.school_id == user.school_id)

    today = date.today()
    # Students can only view projects during the preference period
    q = q.filter(Timeframe.preference_startTiming <= today, Timeframe.preference_endTiming >= today)

    # Require that the project is in a timeframe the student is assigned to
    if user_tf_ids:
        q = q.filter(Project.timeframe_id.in_(user_tf_ids))
    else:
        # If student isn't in any timeframe, show none (or you could relax this)
        q = q.filter(False)

    projects = q.order_by(Project.created_at.desc()).all()
    
    # Convert projects to dictionaries for JSON serialization
    projects_data = []
    for project in projects:
        projects_data.append({
            'id': project.id,
            'title': project.title,
            'description': project.description or 'No description provided.',
            'student_capacity': project.student_capacity,
            'created_at': project.created_at.strftime('%Y-%m-%d') if project.created_at else 'Unknown',
            'timeframe': {
                'name': project.timeframe.name if project.timeframe else 'Unscheduled Term'
            }
        })
    
    # Get user's wishlist project IDs for frontend display
    wishlist_project_ids = [w.project_id for w in user.wishlists.all()] if user else []
    
    return render_template("ViewProjectListing.html", projects=projects, projects_data=projects_data, user=user, wishlist_project_ids=wishlist_project_ids)

