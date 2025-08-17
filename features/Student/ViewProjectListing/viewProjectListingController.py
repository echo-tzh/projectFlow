# features/Student/ViewProjectListing/viewProjectListingController.py
from flask import Blueprint, render_template, session, redirect, url_for, flash
from functools import wraps
from shared.models import User, Project, Timeframe  # uses your models
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
    """List available projects for the logged-in student's school."""
    user = User.query.get(session["user_id"])

    q = Project.query.join(Timeframe, Project.timeframe_id == Timeframe.id)
    # scope to the student's school if present
    if user and user.school_id:
        q = q.filter(Timeframe.school_id == user.school_id)

    projects = q.order_by(Project.created_at.desc()).all()
    return render_template("ViewProjectListing.html", projects=projects, user=user)
