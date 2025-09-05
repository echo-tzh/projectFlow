from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, session
import pandas as pd
import secrets
import string
from werkzeug.security import generate_password_hash
from shared.models import db, User, Role, Timeframe
import io

# Corrected: Add template_folder to tell Flask where to find templates
load_data_bp = Blueprint('load_data', __name__, url_prefix='/load_data', template_folder='templates')

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# Define all possible roles that can be selected
ALL_POSSIBLE_ROLES = ['assessor', 'supervisor', 'student', 'academic coordinator', 'subject head']

# 🔑 Global dictionary to temporarily hold passwords for new users
# This is a security compromise to meet the workflow requirement.
# Passwords are only stored here after upload and are cleared after sending emails.
passwords_for_email = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# This is the single, secure function for generating passwords.
def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))

def get_or_create_role(role_name):
    role = Role.query.filter_by(name=role_name.lower()).first()
    if not role:
        role = Role(name=role_name.lower(), description=f"{role_name}")
        db.session.add(role)
        db.session.flush()
    return role

def get_current_user():
    """Get current user from session"""
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])

@load_data_bp.route('/')
def index():
    # Check if user is educational admin and has a school
    current_user = get_current_user()
    if not current_user:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login_bp.login'))
    
    # Check if user has educational admin role
    admin_role = current_user.roles.filter_by(name='educational_admin').first()
    if not admin_role:
        flash('Access denied. Educational admin privileges required.', 'error')
        return redirect(url_for('universal_dashboard_bp.dashboard'))
    
    # Check if user has a school assigned
    if not current_user.school_id:
        flash('You must be assigned to a school to load user data.', 'error')
        return redirect(url_for('universal_dashboard_bp.dashboard'))
    
    # Get timeframes for the user's school
    latest_timeframe = Timeframe.query.filter_by(school_id=current_user.school_id).order_by(Timeframe.id.desc()).first()
    if latest_timeframe:
        return redirect(url_for('load_data.select_timeframe', timeframe_id=latest_timeframe.id))
    flash('No timeframes available for your school', 'warning')
    return render_template('noTimeframes.html')

@load_data_bp.route('/select_timeframe/<int:timeframe_id>')
def select_timeframe(timeframe_id):
    current_user = get_current_user()
    if not current_user:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login_bp.login'))
    
    timeframe = Timeframe.query.get_or_404(timeframe_id)
    
    # Ensure the timeframe belongs to the admin's school
    if timeframe.school_id != current_user.school_id:
        flash('Access denied. You can only manage course terms for your school.', 'error')
        return redirect(url_for('load_data.index'))
    
    users_in_timeframe = timeframe.users
    
    return render_template(
        'loadData.html',
        timeframe=timeframe,
        users=users_in_timeframe,
        available_roles=ALL_POSSIBLE_ROLES
    )

@load_data_bp.route('/upload/<int:timeframe_id>', methods=['POST'])
def upload_excel(timeframe_id):
    current_user = get_current_user()
    if not current_user:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login_bp.login'))
    
    timeframe = Timeframe.query.get_or_404(timeframe_id)
    
    # Ensure the timeframe belongs to the admin's school
    if timeframe.school_id != current_user.school_id:
        flash('Access denied. You can only upload users for your school.', 'error')
        return redirect(url_for('load_data.index'))
    
    selected_roles = request.form.getlist('allowed_roles')
    
    if not selected_roles:
        flash('Please select at least one role to allow in the upload', 'error')
        return redirect(url_for('load_data.select_timeframe', timeframe_id=timeframe_id))
    
    allowed_roles = [role.lower() for role in selected_roles]
    
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('load_data.select_timeframe', timeframe_id=timeframe_id))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('load_data.select_timeframe', timeframe_id=timeframe_id))
    
    if file and allowed_file(file.filename):
        try:
            # Read Excel file and ensure ID column is treated as string to avoid .0 issues
            df = pd.read_excel(file, dtype={'ID': str})
            required_columns = ['ID', 'name', 'course studying', 'email', 'role']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                flash(f'Missing required columns: {", ".join(missing_columns)}', 'error')
                return redirect(url_for('load_data.select_timeframe', timeframe_id=timeframe_id))
            
            success_count = 0
            error_count = 0
            error_details = []
            role_skipped_count = 0
            role_skip_details = []

            # ➡️ Clear any old passwords from the dictionary
            passwords_for_email.clear()
            
            for index, row in df.iterrows():
                try:
                    student_staff_id = str(row['ID']).strip() if pd.notna(row['ID']) else ''
                    name = str(row['name']).strip() if pd.notna(row['name']) else ''
                    course = str(row['course studying']).strip() if pd.notna(row['course studying']) else ''
                    email = str(row['email']).strip().lower() if pd.notna(row['email']) else ''
                    role_name = str(row['role']).strip() if pd.notna(row['role']) else ''
                    
                    if not email or '@' not in email:
                        error_details.append(f'Row {index + 2}: Invalid email')
                        error_count += 1
                        continue
                    
                    if role_name.lower() not in allowed_roles:
                        role_skip_details.append(f'Row {index + 2}: Skipped role "{role_name}" for {email} (not in allowed roles)')
                        role_skipped_count += 1
                        continue
                    
                    existing_user = User.query.filter_by(email=email).first()
                    if existing_user:
                        # Update existing user info
                        existing_user.name = name
                        existing_user.course = course
                        existing_user.student_staff_id = student_staff_id
                        
                        # IMPORTANT: Assign user to the educational admin's school if not already assigned
                        if not existing_user.school_id:
                            existing_user.school_id = current_user.school_id
                        
                        # Add to timeframe if not already added
                        if not any(t.id == timeframe_id for t in existing_user.timeframes):
                            existing_user.timeframes.append(timeframe)
                        
                        # Add role if not already assigned
                        role = get_or_create_role(role_name)
                        if not any(r.id == role.id for r in existing_user.roles):
                            existing_user.roles.append(role)
                    else:
                        # 🔑 Generate password ONCE and store it
                        temp_password = generate_random_password()
                        passwords_for_email[email] = temp_password
                        
                        password_hash = generate_password_hash(temp_password)
                        new_user = User(
                            name=name,
                            email=email,
                            course=course,
                            student_staff_id=student_staff_id,
                            password_hash=password_hash,
                            school_id=current_user.school_id  # ASSIGN TO ADMIN'S SCHOOL
                        )
                        db.session.add(new_user)
                        db.session.flush()
                        
                        # Add to timeframe and role
                        new_user.timeframes.append(timeframe)
                        role = get_or_create_role(role_name)
                        new_user.roles.append(role)
                        
                        flash(f'New user created for {current_user.school.name}: {email}', 'info')
                    
                    success_count += 1
                except Exception as e:
                    error_details.append(f'Row {index + 2}: {str(e)}')
                    error_count += 1
            
            db.session.commit()
            
            flash(f'Successfully processed {success_count} users for {current_user.school.name} with roles: {", ".join(selected_roles)}', 'success')
            
            if role_skipped_count > 0:
                flash(f'{role_skipped_count} role assignments were skipped (roles not allowed)', 'warning')
                for skip in role_skip_details[:5]:
                    flash(skip, 'warning')
                if len(role_skip_details) > 5:
                    flash(f'... and {len(role_skip_details) - 5} more roles skipped', 'warning')
            
            if error_count > 0:
                flash(f'{error_count} rows had errors and were not processed', 'error')
                for err in error_details[:5]:
                    flash(err, 'error')
                if len(error_details) > 5:
                    flash(f'... and {len(error_details) - 5} more errors', 'error')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing file: {str(e)}', 'error')
    else:
        flash('Invalid file type. Please upload an Excel file (.xlsx or .xls)', 'error')
    
    return redirect(url_for('load_data.select_timeframe', timeframe_id=timeframe_id))

@load_data_bp.route('/view/<int:timeframe_id>')
def view_users(timeframe_id):
    current_user = get_current_user()
    if not current_user:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login_bp.login'))
    
    timeframe = Timeframe.query.get_or_404(timeframe_id)
    
    # Ensure the timeframe belongs to the admin's school
    if timeframe.school_id != current_user.school_id:
        flash('Access denied. You can only view users for your school.', 'error')
        return redirect(url_for('load_data.index'))
    
    users = timeframe.users
    
    users_by_role = {}
    for user in users:
        for role in user.roles:
            users_by_role.setdefault(role.name, []).append(user)
    
    return render_template(
        'viewUsers.html',
        timeframe=timeframe,
        users=users,
        users_by_role=users_by_role
    )

@load_data_bp.route('/download_template')
def download_template():
    """Generates and serves a blank Excel template for user import."""
    columns = ['ID', 'name', 'course studying', 'email', 'role']

    df = pd.DataFrame(columns=columns)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Users')

    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='user_template.xlsx'
    )