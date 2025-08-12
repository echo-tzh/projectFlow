from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from datetime import datetime
from shared.models import db, User, Timeframe

create_timeframe_bp = Blueprint('create_timeframe', __name__, template_folder='templates')

# Reuse your admin login restriction
def educational_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "error")
            return redirect(url_for('login_bp.login'))

        user = User.query.get(session['user_id'])
        if not user or not any(role.name == 'educational_admin' for role in user.roles):
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for('login_bp.login'))

        return f(*args, **kwargs)
    return decorated_function

@create_timeframe_bp.route('/create-timeframe', methods=['GET', 'POST'])
@educational_admin_required
def create_timeframe():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        try:
            start_date_str = request.form['start_date']
            end_date_str = request.form['end_date']
            name = request.form['name']

            # Convert string to date
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            # Validation
            if end_date < start_date:
                flash("End date cannot be earlier than start date.", "error")
                return redirect(url_for('create_timeframe.create_timeframe'))

            # Create timeframe
            new_timeframe = Timeframe(
                start_date=start_date,
                end_date=end_date,
                name = name,
                school_id=user.school_id
                
            )

            db.session.add(new_timeframe)
            db.session.commit()

            flash("Timeframe created successfully.", "success")
            return redirect(url_for('educational_admin.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error creating timeframe: {str(e)}", "error")
            return redirect(url_for('create_timeframe.create_timeframe'))

    return render_template('create_timeframe.html')
