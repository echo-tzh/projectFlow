from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from shared.models import db, School, User, Role  # Added Role import
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
        confirm_password = request.form.get('confirm_password')
        
        if not all([school_name, admin_email, admin_password, confirm_password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('createSchool.create_school'))
        
        if admin_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('createSchool.create_school'))
        
        existing_school = School.query.filter_by(name=school_name).first()
        if existing_school:
            flash('A school with this name already exists. Please choose a different name.', 'error')
            return redirect(url_for('createSchool.create_school'))
        
        existing_admin = User.query.filter_by(email=admin_email).first()
        if existing_admin:
            flash('An admin account with this email already exists. Please use a different email.', 'error')
            return redirect(url_for('createSchool.create_school'))
        
        try:
            # 1. Get or create the educational_admin role
            edu_admin_role = Role.query.filter_by(name='educational_admin').first()
            if not edu_admin_role:
                edu_admin_role = Role(
                    name='educational_admin', 
                    description='Educational Administrator'
                )
                db.session.add(edu_admin_role)
                db.session.flush()  # Ensure role gets an ID
            
            # 2. Create the new School object
            school = School(name=school_name, created_at=datetime.utcnow())
            db.session.add(school)
            # Flush the session to get the school.id
            db.session.flush()
            
            # 3. Create the User object (without role field)
            hashed_password = generate_password_hash(admin_password)
            admin_user = User(
                email=admin_email,
                password_hash=hashed_password,
                school_id=school.id
            )
            db.session.add(admin_user)
            db.session.flush()  # Ensure user gets an ID
            
            # 4. Assign the educational_admin role to the user
            admin_user.roles.append(edu_admin_role)
            
            # 5. Commit all changes
            db.session.commit()
            
            flash('School and admin account created successfully!', 'success')
            return redirect(url_for('login_bp.login'))
            
        except IntegrityError:
            db.session.rollback()
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('createSchool.create_school'))
    
    return render_template('createSchool.html')