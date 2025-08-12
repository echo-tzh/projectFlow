from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
import pandas as pd
import secrets
import string
from werkzeug.security import generate_password_hash
from shared.models import db, User, Role, Timeframe
import io

# Corrected: Add template_folder to tell Flask where to find templates
load_data_bp = Blueprint('load_data', __name__, url_prefix='/load_data', template_folder='templates')

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def get_or_create_role(role_name):
    role = Role.query.filter_by(name=role_name.lower()).first()
    if not role:
        role = Role(name=role_name.lower(), description=f"Auto-created role: {role_name}")
        db.session.add(role)
        db.session.flush()
    return role

@load_data_bp.route('/')
def index():
    latest_timeframe = Timeframe.query.order_by(Timeframe.id.desc()).first()
    if latest_timeframe:
        return redirect(url_for('load_data.select_timeframe', timeframe_id=latest_timeframe.id))
    flash('No timeframes available', 'warning')
    # Corrected: Use relative path
    return render_template('noTimeframes.html')

@load_data_bp.route('/select_timeframe/<int:timeframe_id>')
def select_timeframe(timeframe_id):
    timeframe = Timeframe.query.get_or_404(timeframe_id)
    users_in_timeframe = timeframe.users
    
    # Corrected: Use relative path
    return render_template(
        'loadData.html',
        timeframe=timeframe,
        users=users_in_timeframe
    )

@load_data_bp.route('/upload/<int:timeframe_id>', methods=['POST'])
def upload_excel(timeframe_id):
    timeframe = Timeframe.query.get_or_404(timeframe_id)
    
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('load_data.select_timeframe', timeframe_id=timeframe_id))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('load_data.select_timeframe', timeframe_id=timeframe_id))
    
    if file and allowed_file(file.filename):
        try:
            df = pd.read_excel(file)
            required_columns = ['ID', 'name', 'course studying', 'email', 'role']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                flash(f'Missing required columns: {", ".join(missing_columns)}', 'error')
                return redirect(url_for('load_data.select_timeframe', timeframe_id=timeframe_id))
            
            success_count = 0
            error_count = 0
            error_details = []
            
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
                    
                    allowed_roles = ['assessor', 'supervisor', 'student', 'academic coordinator', 'subject head']
                    if role_name.lower() not in allowed_roles:
                        error_details.append(f'Row {index + 2}: Invalid role "{role_name}"')
                        error_count += 1
                        continue
                    
                    existing_user = User.query.filter_by(email=email).first()
                    if existing_user:
                        existing_user.name = name
                        existing_user.course = course
                        existing_user.student_staff_id = student_staff_id
                        
                        if not any(t.id == timeframe_id for t in existing_user.timeframes):
                            existing_user.timeframes.append(timeframe)
                        
                        role = get_or_create_role(role_name)
                        if not any(r.id == role.id for r in existing_user.roles):
                            existing_user.roles.append(role)
                    else:
                        password = generate_password()
                        password_hash = generate_password_hash(password)
                        new_user = User(
                            name=name,
                            email=email,
                            course=course,
                            student_staff_id=student_staff_id,
                            password_hash=password_hash
                        )
                        db.session.add(new_user)
                        db.session.flush()
                        
                        new_user.timeframes.append(timeframe)
                        role = get_or_create_role(role_name)
                        new_user.roles.append(role)
                        
                        flash(f'New user created: {email} with password: {password}', 'info')
                    
                    success_count += 1
                except Exception as e:
                    error_details.append(f'Row {index + 2}: {str(e)}')
                    error_count += 1
            
            db.session.commit()
            
            flash(f'Successfully processed {success_count} users', 'success')
            if error_count > 0:
                flash(f'{error_count} errors occurred', 'warning')
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
    timeframe = Timeframe.query.get_or_404(timeframe_id)
    users = timeframe.users
    
    users_by_role = {}
    for user in users:
        for role in user.roles:
            users_by_role.setdefault(role.name, []).append(user)
    
    # Corrected: Use relative path
    return render_template(
        'viewUsers.html',
        timeframe=timeframe,
        users=users,
        users_by_role=users_by_role
    )

@load_data_bp.route('/download_template')
def download_template():
    """Generates and serves a blank Excel template for user import."""
    # Define the required column headers
    columns = ['ID', 'name', 'course studying', 'email', 'role']

    # Create an empty DataFrame with the specified columns
    df = pd.DataFrame(columns=columns)

    # Use an in-memory byte stream to save the Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Users')

    # Move the stream position to the beginning before sending
    output.seek(0)

    # Use send_file to serve the file for download
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='user_template.xlsx'
    )