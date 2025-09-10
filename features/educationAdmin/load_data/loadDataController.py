from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, session
import pandas as pd
import secrets
import string
import requests
import logging
from werkzeug.security import generate_password_hash
from shared.models import db, User, Role, Timeframe, ExternalAPIConfig, assign_user_role_timeframe, user_role_timeframes  # ADDED IMPORTS
from sqlalchemy import and_  # ADDED IMPORT
import io

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def _get_or_create_role(role_name: str):
    """Helper function to get or create a role - matches API controller"""
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        role = Role(name=role_name, description=role_name, is_active=True)
        db.session.add(role)
        db.session.flush()
    return role

def assign_user_role_timeframe(user, role_name: str, timeframe):
    """
    Ensure user has role `role_name` in `timeframe`. Also ensures legacy link in user_timeframes.
    Accepts model instances or ids for user and timeframe.
    This is the SAME function from the API controller - duplicated here to avoid circular imports.
    """
    user_id = user.id if hasattr(user, "id") else int(user)
    timeframe_id = timeframe.id if hasattr(timeframe, "id") else int(timeframe)
    role = _get_or_create_role(role_name)

    logger.info(f"DEBUG: Excel - Assigning user_id={user_id}, role={role_name} (role_id={role.id}), timeframe_id={timeframe_id}")

    # Insert into role-scoped table if missing
    exists = db.session.query(user_role_timeframes).filter_by(
        user_id=user_id, role_id=role.id, timeframe_id=timeframe_id
    ).first()
    
    if not exists:
        db.session.execute(
            user_role_timeframes.insert().values(
                user_id=user_id, role_id=role.id, timeframe_id=timeframe_id
            )
        )
        logger.info(f"DEBUG: Excel - Inserted into user_role_timeframes - user_id={user_id}, role_id={role.id}, timeframe_id={timeframe_id}")
        db.session.flush()
        
        # Verify the insert worked
        verify = db.session.query(user_role_timeframes).filter_by(
            user_id=user_id, role_id=role.id, timeframe_id=timeframe_id
        ).first()
        if verify:
            logger.info(f"DEBUG: Excel - Verified insert successful in user_role_timeframes")
        else:
            logger.error(f"DEBUG: Excel - Insert failed - record not found after flush")
    else:
        logger.info(f"DEBUG: Excel - Record already exists in user_role_timeframes")

def get_or_create_role(role_name):
    role = Role.query.filter_by(name=role_name.lower()).first()
    if not role:
        role = Role(name=role_name.lower(), description=f"{role_name}")
        db.session.add(role)
        db.session.flush()
    return role

def remove_user_from_timeframe_with_role_cleanup(user, timeframe):
    """
    Remove user from timeframe and clean up role-scoped assignments
    """
    # Remove from legacy timeframe assignment
    if timeframe in user.timeframes:
        user.timeframes.remove(timeframe)
    
    # Remove role-scoped assignments for this timeframe
    db.session.execute(
        user_role_timeframes.delete().where(
            and_(
                user_role_timeframes.c.user_id == user.id,
                user_role_timeframes.c.timeframe_id == timeframe.id
            )
        )
    )
    
    # If user has no more timeframes, clear all roles
    if not user.timeframes:
        user.roles = []

def get_user_roles_for_other_timeframes(user, current_timeframe_id, school_id):
    """
    Get the roles this user should have in timeframes OTHER than the current one being processed.
    This ensures we preserve their roles in other timeframes when updating roles for the current timeframe.
    """
    try:
        # Get API config for external data lookup
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=school_id,
            is_active=True
        ).first()
        
        if not api_config:
            # WITHOUT EXTERNAL API: We cannot determine timeframe-specific roles
            # For Excel uploads, we should do a complete override for this timeframe
            # and return empty list (this means Excel completely controls the user's roles)
            logger.warning(f"No external API config found. Excel upload will completely override roles for user {user.email}")
            return []  # Empty list means no roles preserved from other timeframes
        
        # If we have external API, preserve roles from other timeframes
        field_mappings = get_field_mappings_from_config(api_config)
        preserved_roles = set()
        
        # Check each of the user's other timeframes
        other_timeframes = [tf for tf in user.timeframes if tf.id != current_timeframe_id]
        
        for timeframe in other_timeframes:
            # Fetch external data for this other timeframe
            external_data = fetch_external_data_via_api(api_config, timeframe.name)
            
            if external_data:
                email_field = field_mappings.get('email', 'email')
                role_field = field_mappings.get('role', 'role')
                timeframe_field = field_mappings.get('timeframe', 'fyp_session')
                
                # Find this user's role in this specific timeframe
                for external_user in external_data:
                    if (email_field in external_user and 
                        role_field in external_user and
                        timeframe_field in external_user and
                        external_user[email_field] and
                        external_user[email_field].lower().strip() == user.email.lower() and
                        external_user[timeframe_field] == timeframe.name):
                        
                        # Found the user's role for this timeframe
                        role_name = external_user[role_field].lower().strip()
                        role = Role.query.filter_by(name=role_name).first()
                        if role:
                            preserved_roles.add(role)
                            logger.info(f"Preserving role '{role_name}' for user {user.email} in timeframe {timeframe.name}")
        
        return list(preserved_roles)
        
    except Exception as e:
        logger.error(f"Error getting roles for other timeframes for user {user.email}: {e}")
        # Fallback: return empty list to allow complete override
        return []

def get_current_user():
    """Get current user from session"""
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])

def get_field_mappings_from_config(api_config):
    """
    Extract field mappings from API configuration
    """
    try:
        if hasattr(api_config, 'get_field_mappings'):
            return api_config.get_field_mappings()
        
        return {
            'email': getattr(api_config, 'email_field', 'email'),
            'name': getattr(api_config, 'name_field', 'name'),
            'course': getattr(api_config, 'course_field', 'course'),
            'id': getattr(api_config, 'id_field', 'id'),
            'role': getattr(api_config, 'role_field', 'role'),
            'timeframe': getattr(api_config, 'timeframe_field', 'fyp_session')
        }
    except Exception as e:
        logger.error(f"Error parsing field mappings: {e}")
        return {
            'email': 'email',
            'name': 'name',
            'course': 'course',
            'id': 'id', 
            'role': 'role',
            'timeframe': 'fyp_session'
        }

def fetch_external_data_via_api(api_config, academic_period):
    """
    Fetch eligible students from external API for specific academic period
    """
    try:
        api_key = api_config.api_key
        api_secret = api_config.api_secret
        base_url = "http://localhost:5002"  # You can hardcode this or add it to the database
        
        if not api_key or not api_secret:
            logger.error("API key or secret is missing")
            return []
        
        headers = {
            'X-API-Key': api_key,
            'X-API-Secret': api_secret,
            'Content-Type': 'application/json'
        }
        
        api_url = f"{base_url}/api/students/by-period/{academic_period}"
        logger.info(f"Making API request to: {api_url}")
        
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                students = data.get('students', [])
                logger.info(f"Successfully fetched {len(students)} students from external API")
                return students
            else:
                logger.error(f"API returned success=False: {data}")
                return []
        else:
            logger.error(f"API request failed with status {response.status_code}: {response.text}")
            return []
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error when calling external API: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching from external API: {e}")
        return []

def get_users_with_timeframe_roles(timeframe_id, school_id):
    """
    Get users for a timeframe with their roles specific to that timeframe
    """
    try:
        # Get all users in the timeframe
        users = User.query.join(User.timeframes).filter(
            Timeframe.id == timeframe_id,
            User.school_id == school_id
        ).all()
        
        # Get the external API config to fetch current data for this timeframe
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=school_id,
            is_active=True
        ).first()
        
        timeframe = Timeframe.query.get(timeframe_id)
        users_with_roles = []
        
        if api_config and timeframe:
            # Get field mappings and fetch external data for this timeframe
            field_mappings = get_field_mappings_from_config(api_config)
            external_data = fetch_external_data_via_api(api_config, timeframe.name)
            
            # Create a lookup dictionary for faster access
            external_user_roles = {}
            if external_data:
                email_field = field_mappings.get('email', 'email')
                role_field = field_mappings.get('role', 'role')
                timeframe_field = field_mappings.get('timeframe', 'fyp_session')
                
                for external_user in external_data:
                    if (email_field in external_user and 
                        role_field in external_user and
                        timeframe_field in external_user and
                        external_user[timeframe_field] == timeframe.name):
                        
                        email = external_user[email_field].lower().strip()
                        role_name = external_user[role_field].lower().strip()
                        
                        if email not in external_user_roles:
                            external_user_roles[email] = []
                        external_user_roles[email].append(role_name)
        
        # Process each user
        for user in users:
            user_timeframe_roles = []
            
            if api_config and timeframe:
                # Get roles from external data for this specific timeframe
                user_email = user.email.lower()
                if user_email in external_user_roles:
                    for role_name in external_user_roles[user_email]:
                        role = Role.query.filter_by(name=role_name).first()
                        if role:
                            user_timeframe_roles.append(role)
            
            # Fallback if no timeframe-specific roles found
            if not user_timeframe_roles:
                logger.warning(f"Could not determine timeframe-specific roles for user {user.email} from external data, using all roles as fallback")
                user_timeframe_roles = list(user.roles)
            
            # Create user data structure
            user_with_timeframe_roles = {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'student_staff_id': user.student_staff_id,
                'course': user.course,
                'timeframe_roles': user_timeframe_roles,
                'all_roles': list(user.roles)
            }
            users_with_roles.append(user_with_timeframe_roles)
        
        return users_with_roles
        
    except Exception as e:
        logger.error(f"Error getting users with timeframe roles: {e}")
        # Fallback
        users = User.query.join(User.timeframes).filter(
            Timeframe.id == timeframe_id,
            User.school_id == school_id
        ).all()
        
        fallback_users = []
        for user in users:
            user_data = {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'student_staff_id': user.student_staff_id,
                'course': user.course,
                'timeframe_roles': list(user.roles),
                'all_roles': list(user.roles)
            }
            fallback_users.append(user_data)
        
        return fallback_users

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
    
    # Get users with their timeframe-specific roles
    users_with_timeframe_roles = get_users_with_timeframe_roles(timeframe_id, current_user.school_id)
    
    return render_template(
        'loadData.html',
        timeframe=timeframe,
        users=users_with_timeframe_roles,
        available_roles=ALL_POSSIBLE_ROLES
    )

@load_data_bp.route('/upload/<int:timeframe_id>', methods=['POST'])
def upload_excel(timeframe_id):
    print(f"\n" + "="*50)
    print(f"DEBUG: Starting upload for timeframe {timeframe_id}")
    print(f"="*50)
    
    current_user = get_current_user()
    if not current_user:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login_bp.login'))
    
    timeframe = Timeframe.query.get_or_404(timeframe_id)
    
    # Ensure the timeframe belongs to the admin's school
    if timeframe.school_id != current_user.school_id:
        flash('Access denied. You can only upload users for your school.', 'error')
        return redirect(url_for('load_data.index'))
    
    # DEBUG: Check what the form actually sent
    print(f"DEBUG: Raw form data: {dict(request.form)}")
    print(f"DEBUG: Form lists: {request.form.lists()}")
    
    selected_roles = request.form.getlist('allowed_roles')
    print(f"DEBUG: Selected roles from form: {selected_roles}")
    
    if not selected_roles:
        flash('Please select at least one role to allow in the upload', 'error')
        return redirect(url_for('load_data.select_timeframe', timeframe_id=timeframe_id))
    
    allowed_roles = [role.lower().strip() for role in selected_roles]
    print(f"DEBUG: Processed allowed_roles: {allowed_roles}")
    
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
            
            # DEBUG: Check Excel file contents
            print(f"DEBUG: Excel columns: {list(df.columns)}")
            if 'role' in df.columns:
                unique_roles = df['role'].unique()
                print(f"DEBUG: Unique roles in Excel file: {unique_roles}")
                for i, role_val in enumerate(df['role'].head(10)):  # Check first 10 rows
                    print(f"DEBUG: Row {i+2} role: '{role_val}' (type: {type(role_val)})")
            
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

            # Clear any old passwords from the dictionary
            passwords_for_email.clear()
            
            # DEBUG: Check existing roles in database before processing
            existing_roles_before = Role.query.all()
            print(f"DEBUG: Existing roles in DB before processing: {[r.name for r in existing_roles_before]}")
            
            for index, row in df.iterrows():
                try:
                    print(f"\nDEBUG: --- Processing row {index + 2} ---")
                    
                    student_staff_id = str(row['ID']).strip() if pd.notna(row['ID']) else ''
                    name = str(row['name']).strip() if pd.notna(row['name']) else ''
                    course = str(row['course studying']).strip() if pd.notna(row['course studying']) else ''
                    email = str(row['email']).strip().lower() if pd.notna(row['email']) else ''
                    
                    # DEBUG: Detailed role processing
                    raw_role = row['role']
                    print(f"DEBUG: Raw role from Excel: '{raw_role}' (type: {type(raw_role)}, pd.notna: {pd.notna(raw_role)})")
                    
                    role_name = str(row['role']).strip().lower() if pd.notna(row['role']) else ''
                    print(f"DEBUG: Processed role_name: '{role_name}'")
                    print(f"DEBUG: Email: {email}")
                    print(f"DEBUG: Allowed roles: {allowed_roles}")
                    print(f"DEBUG: Is role_name in allowed_roles? {role_name in allowed_roles}")
                    
                    if not email or '@' not in email:
                        error_details.append(f'Row {index + 2}: Invalid email')
                        error_count += 1
                        continue
                    
                    if role_name not in allowed_roles:
                        role_skip_details.append(f'Row {index + 2}: Skipped role "{role_name}" for {email} (not in allowed roles)')
                        role_skipped_count += 1
                        print(f"DEBUG: SKIPPING row {index + 2} - role not allowed")
                        continue
                    
                    print(f"DEBUG: PROCESSING row {index + 2} - role is allowed")
                    
                    existing_user = User.query.filter_by(email=email).first()
                    if existing_user:
                        print(f"DEBUG: Updating existing user: {email}")
                        # Update existing user info
                        existing_user.name = name
                        existing_user.course = course
                        existing_user.student_staff_id = student_staff_id
                        
                        # IMPORTANT: Assign user to the educational admin's school if not already assigned
                        if not existing_user.school_id:
                            existing_user.school_id = current_user.school_id
                        
                        # FIXED: Add role-scoped assignment for Excel upload
                        assign_user_role_timeframe(existing_user, role_name, timeframe)
                        print(f"DEBUG: Excel - Created role-scoped assignment: {email} as {role_name} in {timeframe.name}")
                        
                        # Add user to timeframe if not already there (legacy)
                        if timeframe not in existing_user.timeframes:
                            existing_user.timeframes.append(timeframe)
                            print(f"DEBUG: Excel - Added user to timeframe: {email} in {timeframe.name}")
                        
                        # Get the new role from the Excel file
                        new_role = get_or_create_role(role_name)
                        
                        # Add the new role if the user doesn't already have it
                        if new_role not in existing_user.roles:
                            existing_user.roles.append(new_role)
                            print(f"DEBUG: Excel - ADDED new role '{new_role.name}' to existing user {email}.")
                        else:
                            print(f"DEBUG: Excel - User {email} already has role '{new_role.name}'. No change needed.")
                            
                    else:
                        print(f"DEBUG: Creating new user: {email}")
                        # Generate password ONCE and store it
                        temp_password = generate_random_password()
                        passwords_for_email[email] = temp_password
                        
                        password_hash = generate_password_hash(temp_password)
                        new_user = User(
                            name=name,
                            email=email,
                            course=course,
                            student_staff_id=student_staff_id,
                            password_hash=password_hash,
                            school_id=current_user.school_id,# ASSIGN TO ADMIN'S SCHOOL
                            email_sent=False
                        )
                        db.session.add(new_user)
                        db.session.flush()
                        
                        # FIXED: Add role-scoped assignment for Excel upload
                        print(f"DEBUG: Excel - About to get_or_create_role for new user with: '{role_name}'")
                        role = get_or_create_role(role_name)
                        print(f"DEBUG: Excel - Got role: {role.name} (ID: {role.id})")
                        
                        # Create role-scoped assignment FIRST
                        assign_user_role_timeframe(new_user, role_name, timeframe)
                        print(f"DEBUG: Excel - Created role-scoped assignment: {email} as {role_name} in {timeframe.name}")
                        
                        # Add user to timeframe (legacy)
                        new_user.timeframes.append(timeframe)
                        print(f"DEBUG: Excel - Added new user to timeframe: {email} in {timeframe.name}")
                        
                        # Also add the role to user.roles for general queries
                        new_user.roles.append(role)
                        print(f"DEBUG: Excel - Added role '{role.name}' to new user {email}")
                    
                    success_count += 1
                    
                    # DEBUG: Check roles after each user
                    all_roles_now = Role.query.all()
                    print(f"DEBUG: All roles in DB after processing user: {[r.name for r in all_roles_now]}")
                    
                except Exception as e:
                    print(f"DEBUG: Error processing row {index + 2}: {str(e)}")
                    error_details.append(f'Row {index + 2}: {str(e)}')
                    error_count += 1
            
            # DEBUG: Final role check before commit
            final_roles = Role.query.all()
            print(f"DEBUG: Final roles in DB before commit: {[r.name for r in final_roles]}")
            
            # Check what's in the user_role_timeframes table before commit
            role_assignments_count = db.session.query(user_role_timeframes).count()
            print(f"DEBUG: Excel - Total role assignments in user_role_timeframes table before commit: {role_assignments_count}")
            
            db.session.commit()
            
            # DEBUG: Final role check after commit
            committed_roles = Role.query.all()
            print(f"DEBUG: Final roles in DB after commit: {[r.name for r in committed_roles]}")
            
            # Check what's in the table after commit
            role_assignments_count_after = db.session.query(user_role_timeframes).count()
            print(f"DEBUG: Excel - Role assignments in user_role_timeframes after commit: {role_assignments_count_after}")
            
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
            print(f"DEBUG: File processing error: {str(e)}")
            flash(f'Error processing file: {str(e)}', 'error')
    else:
        flash('Invalid file type. Please upload an Excel file (.xlsx or .xls)', 'error')
    
    print(f"DEBUG: Upload process completed")
    print(f"="*50 + "\n")
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
    
    # Get users with their timeframe-specific roles
    users_with_timeframe_roles = get_users_with_timeframe_roles(timeframe_id, current_user.school_id)
    
    # Group users by their timeframe-specific roles
    users_by_role = {}
    for user_data in users_with_timeframe_roles:
        for role in user_data['timeframe_roles']:
            role_name = role.name if hasattr(role, 'name') else role
            if role_name not in users_by_role:
                users_by_role[role_name] = []
            users_by_role[role_name].append(user_data)
    
    return render_template(
        'viewUsers.html',
        timeframe=timeframe,
        users=users_with_timeframe_roles,
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