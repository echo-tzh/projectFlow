# features/educationAdmin/viewCourseTerm/viewCourseTermController.py

from flask import Blueprint, render_template, session, redirect, url_for, flash
from datetime import datetime
from sqlalchemy import and_

from shared.models import (
    db,
    User,
    Role,
    Timeframe,
    user_role_timeframes,  # new role-scoped junction
)

view_course_term_bp = Blueprint(
    "view_course_term",
    __name__,
    template_folder="templates",
    url_prefix="/academic-coordinator",
)

def _require_login():
    if "user_id" not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("auth.login"))
    return None

def _require_active_role(role_name: str):
    # Optional: enforce currently switched role
    active = session.get("active_role")
    if active and active != role_name:
        flash(f"Switch to '{role_name}' to view this page.", "info")
        return redirect(url_for("universal_dashboard.dashboard"))
    return None

def _user_has_role(user: User, role_name: str) -> bool:
    return any(r.name == role_name for r in user.roles)

@view_course_term_bp.route("/course-terms")
def view_course_terms():
    # Auth checks
    r = _require_login()
    if r:
        return r

    user = User.query.get(session["user_id"])
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("auth.login"))

    # === DEBUG SECTION - START ===
    print(f"\n=== DEBUG: User {user.id} ({user.email}) ===")
    
    # 1. Check user's roles
    user_roles = [role.name for role in user.roles]
    print(f"User roles: {user_roles}")
    
    # 2. Check if academic coordinator role exists
    ac_role = Role.query.filter_by(name="academic coordinator").first()
    print(f"Academic coordinator role exists: {ac_role is not None}")
    if ac_role:
        print(f"Academic coordinator role ID: {ac_role.id}")
    
    # 3. Check legacy timeframe assignments
    legacy_timeframes = user.timeframes.all()
    print(f"Legacy timeframes count: {len(legacy_timeframes)}")
    for tf in legacy_timeframes:
        print(f"  - Legacy timeframe: {tf.id} ({tf.name})")
    
    # 4. Check role-scoped timeframe assignments
    role_assignments = (
        db.session.query(user_role_timeframes)
        .filter_by(user_id=user.id)
        .all()
    )
    print(f"Role-scoped assignments count: {len(role_assignments)}")
    for assignment in role_assignments:
        role_name = Role.query.get(assignment.role_id).name
        timeframe_name = Timeframe.query.get(assignment.timeframe_id).name
        print(f"  - Role assignment: Role '{role_name}' in Timeframe '{timeframe_name}'")
    
    # 5. Check specifically for academic coordinator assignments
    ac_assignments = []
    if ac_role:
        ac_assignments = (
            db.session.query(user_role_timeframes)
            .filter_by(user_id=user.id, role_id=ac_role.id)
            .all()
        )
    print(f"Academic coordinator assignments count: {len(ac_assignments)}")
    for assignment in ac_assignments:
        timeframe_name = Timeframe.query.get(assignment.timeframe_id).name
        print(f"  - AC assignment in timeframe: '{timeframe_name}'")
    
    # 6. Test the exact query that's failing
    assigned_timeframes_debug = (
        db.session.query(Timeframe)
        .join(user_role_timeframes, Timeframe.id == user_role_timeframes.c.timeframe_id)
        .join(Role, user_role_timeframes.c.role_id == Role.id)
        .filter(
            user_role_timeframes.c.user_id == user.id,
            Role.name == "academic coordinator",
        )
        .order_by(Timeframe.start_date)
        .all()
    )
    print(f"Query result count: {len(assigned_timeframes_debug)}")
    for tf in assigned_timeframes_debug:
        print(f"  - Query result: {tf.id} ({tf.name})")
    
    print("=== END DEBUG ===\n")
    # === DEBUG SECTION - END ===

    # Must be an academic coordinator
    if not _user_has_role(user, "academic coordinator"):
        flash("Access denied. Academic coordinator privileges required.", "error")
        return redirect(url_for("universal_dashboard.dashboard"))

    r = _require_active_role("academic coordinator")
    if r:
        return r

    # Only timeframes where this user is assigned AS academic coordinator
    assigned_timeframes = (
        db.session.query(Timeframe)
        .join(user_role_timeframes, Timeframe.id == user_role_timeframes.c.timeframe_id)
        .join(Role, user_role_timeframes.c.role_id == Role.id)
        .filter(
            user_role_timeframes.c.user_id == user.id,
            Role.name == "academic coordinator",
        )
        .order_by(Timeframe.start_date)
        .all()
    )

    current_date = datetime.now().date()
    current_timeframes, upcoming_timeframes, past_timeframes = [], [], []
    for tf in assigned_timeframes:
        if tf.start_date <= current_date <= tf.end_date:
            current_timeframes.append(tf)
        elif tf.start_date > current_date:
            upcoming_timeframes.append(tf)
        else:
            past_timeframes.append(tf)

    current_timeframes.sort(key=lambda x: x.start_date)
    upcoming_timeframes.sort(key=lambda x: x.start_date)
    past_timeframes.sort(key=lambda x: x.start_date, reverse=True)

    return render_template(
        "viewCourseTerm.html",
        user=user,
        current_timeframes=current_timeframes,
        upcoming_timeframes=upcoming_timeframes,
        past_timeframes=past_timeframes,
        total_timeframes=len(assigned_timeframes),
        active_timeframes=len(current_timeframes),
        current_date=current_date,
    )

@view_course_term_bp.route("/course-term/<int:timeframe_id>")
def view_course_term_detail(timeframe_id: int):
    # Auth checks
    r = _require_login()
    if r:
        return r

    user = User.query.get(session["user_id"])
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("auth.login"))

    # Must be an academic coordinator
    if not _user_has_role(user, "academic coordinator"):
        flash("Access denied. Academic coordinator privileges required.", "error")
        return redirect(url_for("universal_dashboard.dashboard"))

    r = _require_active_role("academic coordinator")
    if r:
        return r

    timeframe = Timeframe.query.get_or_404(timeframe_id)

    # Enforce role + timeframe membership
    urt = (
        db.session.query(user_role_timeframes.c.assigned_at)
        .join(Role, user_role_timeframes.c.role_id == Role.id)
        .filter(
            user_role_timeframes.c.user_id == user.id,
            user_role_timeframes.c.timeframe_id == timeframe.id,
            Role.name == "academic coordinator",
        )
        .first()
    )
    if not urt:
        flash("Access denied. You are not assigned to coordinate this course term.", "error")
        return redirect(url_for("view_course_term.view_course_terms"))

    current_date = datetime.now().date()
    if timeframe.start_date <= current_date <= timeframe.end_date:
        status = "current"
    elif timeframe.start_date > current_date:
        status = "upcoming"
    else:
        status = "past"

    duration_days = (timeframe.end_date - timeframe.start_date).days + 1
    assignment_date = urt.assigned_at if hasattr(urt, "assigned_at") else (urt[0] if urt else None)

    # Projects inside this timeframe only
    projects = timeframe.projects

    return render_template(
        "viewCourseTerm.html",
        timeframe=timeframe,
        projects=projects,
        status=status,
        duration_days=duration_days,
        current_date=current_date,
        assignment_date=assignment_date,
    )