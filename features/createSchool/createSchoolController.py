from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from shared.models import db, School, User
from datetime import datetime
from sqlalchemy.exc import IntegrityError

create_school_bp = Blueprint(
    'createSchool',
    __name__,
    template_folder='templates'
)

@create_school_bp.route('/createSchool', methods=['GET', 'POST'])
def create_school():
    if request.method == 'POST':
        school_name = request.form.get('school_name')
        admin_email = request.form.get('admin_email')
        admin_password = request.form.get('admin_password')

        # Basic form validation
        if not school_name or not admin_email or not admin_password:
            flash('All fields are required.', 'error')
            return redirect(url_for('createSchool.create_school'))

        # Check for existing school name
        existing_school = School.query.filter_by(name=school_name).first()
        if existing_school:
            flash('A school with this name already exists. Please choose a different name.', 'error')
            return redirect(url_for('createSchool.create_school'))

        # Check for existing admin email
        existing_admin = User.query.filter_by(email=admin_email).first()
        if existing_admin:
            flash('An admin account with this email already exists. Please use a different email.', 'error')
            return redirect(url_for('createSchool.create_school'))

        # If all checks pass, create the school and admin user
        try:
            # Create school
            school = School(name=school_name, created_at=datetime.utcnow())
            db.session.add(school)
            db.session.flush()  # Use flush to get the school ID before committing

            # Create educational admin user
            hashed_password = generate_password_hash(admin_password)
            admin_user = User(
                email=admin_email,
                password_hash=hashed_password,
                role='educational_admin'
            )
            db.session.add(admin_user)
            db.session.commit()

            flash('School and admin account created successfully!', 'success')
            return redirect(url_for('login'))

        except IntegrityError:
            # This is a fallback to catch any unexpected database integrity errors,
            # such as a race condition where another user creates the same school
            # or admin email between our check and the commit.
            db.session.rollback()
            flash('An error occurred while creating the school. Please try again.', 'error')
            return redirect(url_for('createSchool.create_school'))

    # Render the form on GET requests
    return render_template('createSchool.html')