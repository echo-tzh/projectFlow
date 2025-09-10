import requests
from flask import Blueprint, request, jsonify, flash, redirect, url_for, session
from database import db
from shared.models import User, Role, Timeframe, ExternalAPIConfig, School
from werkzeug.security import generate_password_hash
from datetime import datetime
import logging
import secrets
import string

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the tables we need for role-scoped assignments
from shared.models import user_role_timeframes, user_timeframes
from sqlalchemy import and_

load_data_api_bp = Blueprint('load_data_api', __name__)

# Import the passwords dictionary from the main controller - now no circular import
from features.educationAdmin.load_data.loadDataController import passwords_for_email

def generate_random_password(length=12):
    """Generate a secure random password"""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))

def _get_or_create_role(role_name: str):
    """Helper function to get or create a role"""
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
    """
    user_id = user.id if hasattr(user, "id") else int(user)
    timeframe_id = timeframe.id if hasattr(timeframe, "id") else int(timeframe)
    role = _get_or_create_role(role_name)

    logger.info(f"DEBUG: Assigning user_id={user_id}, role={role_name} (role_id={role.id}), timeframe_id={timeframe_id}")

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
        logger.info(f"DEBUG: Inserted into user_role_timeframes - user_id={user_id}, role_id={role.id}, timeframe_id={timeframe_id}")
        db.session.flush()
        
        # Verify the insert worked
        verify = db.session.query(user_role_timeframes).filter_by(
            user_id=user_id, role_id=role.id, timeframe_id=timeframe_id
        ).first()
        if verify:
            logger.info(f"DEBUG: Verified insert successful in user_role_timeframes")
        else:
            logger.error(f"DEBUG: Insert failed - record not found after flush")
    else:
        logger.info(f"DEBUG: Record already exists in user_role_timeframes")

    # Keep legacy user_timeframes in sync for general queries
    legacy = db.session.query(user_timeframes).filter_by(
        user_id=user_id, timeframe_id=timeframe_id
    ).first()
    if not legacy:
        db.session.execute(
            user_timeframes.insert().values(
                user_id=user_id, timeframe_id=timeframe_id
            )
        )
        logger.info(f"DEBUG: Inserted into legacy user_timeframes - user_id={user_id}, timeframe_id={timeframe_id}")
        db.session.flush()
    else:
        logger.info(f"DEBUG: Legacy record already exists in user_timeframes")

def get_external_api_config(api_config):
    """
    Parse API configuration for HTTP API calls
    Expected: api_key and api_secret in separate columns, base_url needs to be added
    """
    try:
        # Read from separate columns
        api_key = api_config.api_key  # uow_api_key_123
        api_secret = api_config.api_secret  # UOW_SECRET
        base_url = "http://localhost:5002"  # You can hardcode this or add it to the database
        
        if not api_key or not api_secret:
            logger.error("API key or secret is missing")
            return None
        
        logger.info(f"Successfully parsed API config for base URL: {base_url}")
        return api_key, api_secret, base_url
        
    except Exception as e:
        logger.error(f"Error parsing API configuration: {e}")
        return None

def get_field_mappings_from_config(api_config):
    """
    Extract field mappings from API configuration with multi-role support
    """
    try:
        # Use the model's built-in method
        if hasattr(api_config, 'get_field_mappings'):
            mappings = api_config.get_field_mappings()
        else:
            # Fallback to manual mapping
            mappings = {
                'email': getattr(api_config, 'email_field', 'email'),
                'name': getattr(api_config, 'name_field', 'name'),
                'course': getattr(api_config, 'course_field', 'course'),
                'id': getattr(api_config, 'id_field', 'id'),
                'role': getattr(api_config, 'role_field', 'role'),
                'timeframe': getattr(api_config, 'timeframe_field', 'fyp_session')
            }
        
        # Add support for multiple roles field if not present
        if 'roles' not in mappings:
            mappings['roles'] = getattr(api_config, 'roles_field', 'roles')
        
        return mappings
        
    except Exception as e:
        logger.error(f"Error parsing field mappings: {e}")
        # Return defaults if parsing fails
        return {
            'email': 'email',
            'name': 'name',
            'course': 'course',
            'id': 'id', 
            'role': 'role',
            'roles': 'roles',
            'timeframe': 'fyp_session'
        }

def fetch_external_data_via_api(api_config, academic_period):
    """
    Fetch eligible students from external API for specific academic period
    """
    try:
        # Parse API configuration
        config = get_external_api_config(api_config)
        if not config:
            return []
        
        api_key, api_secret, base_url = config
        
        # Prepare headers for API request
        headers = {
            'X-API-Key': api_key,
            'X-API-Secret': api_secret,
            'Content-Type': 'application/json'
        }
        
        # Make API request
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

def test_external_api_connection(api_config):
    """
    Test connection to external API
    Returns (success, message)
    """
    try:
        config = get_external_api_config(api_config)
        if not config:
            return False, "Invalid API configuration format"
        
        api_key, api_secret, base_url = config
        
        headers = {
            'X-API-Key': api_key,
            'X-API-Secret': api_secret,
            'Content-Type': 'application/json'
        }
        
        # Test with health check endpoint
        response = requests.get(f"{base_url}/api/health", headers=headers, timeout=10)
        
        if response.status_code == 200:
            return True, "Connection successful"
        else:
            return False, f"API returned status {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def create_or_update_user_multi_role(user_data, school_id, timeframe_id, field_mappings=None):
    """
    Create new user or update existing user with external data supporting multiple roles
    This mirrors the Excel controller's ability to handle multiple roles per user
    Returns (user, created_flag, roles_processed)
    """
    try:
        # Default field mappings
        default_mappings = {
            'email': 'email',
            'name': 'name', 
            'course': 'course',
            'id': 'id',
            'roles': 'roles',  # Primary field for multiple roles
            'role': 'role'     # Fallback for single role
        }
        
        # Use provided mappings or defaults
        mappings = field_mappings or default_mappings
        
        # Extract data using configurable field names
        email = user_data.get(mappings['email'])
        name = user_data.get(mappings['name'])
        course = user_data.get(mappings['course'])
        student_id = user_data.get(mappings['id'])
        
        # Handle both single role and multiple roles formats
        roles_data = user_data.get(mappings.get('roles', 'roles')) or user_data.get(mappings.get('role', 'role'))
        
        # Parse roles - support multiple formats
        user_roles = []
        if roles_data:
            if isinstance(roles_data, str):
                # Handle comma-separated roles or single role
                user_roles = [role.strip().lower() for role in roles_data.split(',')]
            elif isinstance(roles_data, list):
                # Handle list of roles
                user_roles = [str(role).strip().lower() for role in roles_data]
            else:
                # Handle single role
                user_roles = [str(roles_data).strip().lower()]
        
        # Remove empty roles
        user_roles = [role for role in user_roles if role]
        
        # Validate required fields
        if not email:
            raise ValueError(f"Email field '{mappings['email']}' not found or empty in data: {user_data}")
        if not user_roles:
            raise ValueError(f"No valid roles found in data: {user_data}")
        
        # Clean email
        email = email.strip().lower()
        
        # Check if user already exists by email
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            # Update existing user - NO password generation for existing users
            if name:
                existing_user.name = name.strip()
            if course:
                existing_user.course = course.strip()
            if student_id:
                existing_user.student_staff_id = str(student_id).strip()
            existing_user.school_id = school_id
            
            # MULTI-ROLE HANDLING: Process each role for this timeframe
            timeframe = Timeframe.query.get(timeframe_id)
            
            # Get roles this user should have in other timeframes
            roles_needed_in_other_timeframes = get_user_roles_in_other_timeframes(
                existing_user, timeframe, school_id
            )
            
            # Start with roles needed in other timeframes
            updated_roles = list(roles_needed_in_other_timeframes)
            
            # Add all new roles for this timeframe
            roles_processed = []
            for role_name in user_roles:
                new_role = Role.query.filter_by(name=role_name).first()
                if not new_role:
                    new_role = Role(
                        name=role_name,
                        description=f"{role_name}",
                        created_at=datetime.utcnow()
                    )
                    db.session.add(new_role)
                    db.session.flush()
                
                if new_role not in updated_roles:
                    updated_roles.append(new_role)
                    roles_processed.append(role_name)
                else:
                    # Role already exists, but still count as processed
                    roles_processed.append(role_name)
            
            # Update user's roles
            existing_user.roles = updated_roles
            
            logger.info(f"Synchronized multiple roles for existing user {existing_user.email}: now has {[r.name for r in updated_roles]}")
            return existing_user, False, roles_processed
            
        else:
            # Create NEW user - ONLY generate password for truly new users
            temp_password = generate_random_password()
            passwords_for_email[email] = temp_password
            
            # Generate hash for database storage
            password_hash = generate_password_hash(temp_password)
            
            new_user = User(
                name=name.strip() if name else '',
                email=email,
                password_hash=password_hash,
                course=course.strip() if course else '',
                student_staff_id=str(student_id).strip() if student_id else '',
                school_id=school_id,
                email_sent=False,
                created_at=datetime.utcnow()
            )
            
            # Assign all roles to the new user
            roles_processed = []
            for role_name in user_roles:
                role = Role.query.filter_by(name=role_name).first()
                if not role:
                    # Create role if it doesn't exist
                    role = Role(
                        name=role_name,
                        description=f"{role_name}",
                        created_at=datetime.utcnow()
                    )
                    db.session.add(role)
                    db.session.flush()
                
                new_user.roles.append(role)
                roles_processed.append(role_name)
            
            db.session.add(new_user)
            logger.info(f"Created NEW user with multiple roles {roles_processed}: {new_user.email}")
            return new_user, True, roles_processed
            
    except Exception as e:
        logger.error(f"Error creating/updating user with multi-role data {user_data}: {e}")
        return None, False, []

def create_or_update_user(user_data, school_id, timeframe_id, field_mappings=None):
    """
    Legacy function for backward compatibility - now uses multi-role function
    """
    user, created, roles_processed = create_or_update_user_multi_role(user_data, school_id, timeframe_id, field_mappings)
    return user, created

def get_user_roles_in_other_timeframes(user, current_timeframe, school_id):
    """
    Get roles that this user needs in their other timeframes (not the current one being processed)
    """
    try:
        # Get API config to fetch external data
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=school_id,
            is_active=True
        ).first()
        
        if not api_config:
            # If no API config, return current roles as fallback
            return user.roles
        
        field_mappings = get_field_mappings_from_config(api_config)
        
        # Get all other timeframes this user is in (excluding current one)
        other_timeframes = [tf for tf in user.timeframes if tf.id != current_timeframe.id]
        
        required_roles = set()
        
        for timeframe in other_timeframes:
            # Fetch external data for this timeframe
            external_data = fetch_external_data_via_api(api_config, timeframe.name)
            
            # Find this user's role in this timeframe
            user_roles_in_timeframe = get_user_roles_for_specific_timeframe_multi_role(
                user.email, timeframe.name, external_data, field_mappings
            )
            
            # Add these roles to required set
            for role_name in user_roles_in_timeframe:
                role = Role.query.filter_by(name=role_name.lower().strip()).first()
                if role:
                    required_roles.add(role)
        
        return list(required_roles)
        
    except Exception as e:
        logger.error(f"Error getting user roles in other timeframes: {e}")
        # Fallback: return current roles to avoid data loss
        return user.roles

def cleanup_user_roles_after_timeframe_removal(user, removed_timeframe, external_data, field_mappings):
    """
    Clean up user roles after removing them from a timeframe.
    Only removes roles that are not needed in other timeframes.
    """
    try:
        # Get all timeframes this user is still in
        remaining_timeframes = user.timeframes
        
        if not remaining_timeframes:
            # User is not in any timeframes, clear all roles
            user.roles = []
            logger.info(f"Cleared all roles for {user.email} - not in any timeframes")
            return
        
        # Get field mappings
        email_field = field_mappings.get('email', 'email')
        roles_field = field_mappings.get('roles', 'roles')
        role_field = field_mappings.get('role', 'role')
        timeframe_field = field_mappings.get('timeframe', 'fyp_session')
        
        # Find what roles this user should have in their remaining timeframes
        required_roles = set()
        
        for user_data in external_data:
            user_email = user_data.get(email_field)
            user_timeframe = user_data.get(timeframe_field)
            
            if (user_email and user_email.lower().strip() == user.email.lower() and
                user_timeframe):
                
                # Check if this role is for one of the user's remaining timeframes
                for remaining_tf in remaining_timeframes:
                    if remaining_tf.name == user_timeframe:
                        # Extract roles for this timeframe
                        roles_data = user_data.get(roles_field) or user_data.get(role_field)
                        if roles_data:
                            if isinstance(roles_data, str):
                                roles = [role.strip().lower() for role in roles_data.split(',')]
                            elif isinstance(roles_data, list):
                                roles = [str(role).strip().lower() for role in roles_data]
                            else:
                                roles = [str(roles_data).strip().lower()]
                            
                            for role in roles:
                                if role:
                                    required_roles.add(role)
                        break
        
        # Remove roles that are no longer required
        current_role_names = {role.name.lower() for role in user.roles}
        roles_to_remove = current_role_names - required_roles
        
        if roles_to_remove:
            # Remove the specific roles that are no longer needed
            roles_to_keep = []
            for role in user.roles:
                if role.name.lower() not in roles_to_remove:
                    roles_to_keep.append(role)
            
            user.roles = roles_to_keep
            logger.info(f"Removed roles {roles_to_remove} from {user.email} after timeframe removal")
        else:
            logger.info(f"No role cleanup needed for {user.email} - all roles still required")
            
    except Exception as e:
        logger.error(f"Error cleaning up roles for user {user.email}: {e}")

def get_user_roles_for_specific_timeframe_multi_role(user_email, timeframe_name, external_data, field_mappings):
    """
    Enhanced version that supports multiple roles per user per timeframe
    """
    try:
        email_field = field_mappings.get('email', 'email')
        roles_field = field_mappings.get('roles', 'roles')
        role_field = field_mappings.get('role', 'role')  # Fallback
        timeframe_field = field_mappings.get('timeframe', 'fyp_session')
        
        all_roles_for_timeframe = []
        
        for user_data in external_data:
            external_email = user_data.get(email_field)
            external_timeframe = user_data.get(timeframe_field)
            
            if (external_email and external_email.lower().strip() == user_email.lower() and
                external_timeframe == timeframe_name):
                
                # Try to get roles from multiple role field first, then single role
                roles_data = user_data.get(roles_field) or user_data.get(role_field)
                
                if roles_data:
                    if isinstance(roles_data, str):
                        roles = [role.strip() for role in roles_data.split(',')]
                    elif isinstance(roles_data, list):
                        roles = [str(role).strip() for role in roles_data]
                    else:
                        roles = [str(roles_data).strip()]
                    
                    for role in roles:
                        if role and role not in all_roles_for_timeframe:
                            all_roles_for_timeframe.append(role)
        
        return all_roles_for_timeframe
        
    except Exception as e:
        logger.error(f"Error getting multi-roles for user {user_email} in timeframe {timeframe_name}: {e}")
        return []

def get_user_roles_for_specific_timeframe(user_email, timeframe_name, external_data, field_mappings):
    """
    Legacy function for backward compatibility - now uses multi-role function
    """
    return get_user_roles_for_specific_timeframe_multi_role(user_email, timeframe_name, external_data, field_mappings)

def sync_users_with_timeframe_multi_role(external_data, school_id, timeframe_id, field_mappings=None):
    """
    Enhanced synchronization supporting multiple roles per user
    This mirrors the Excel controller's multi-role functionality
    NOW ALSO CREATES ROLE-SCOPED ASSIGNMENTS in user_role_timeframes
    Returns (created, updated, removed, assigned, errors, total_roles_processed)
    """
    try:
        timeframe = Timeframe.query.get(timeframe_id)
        if not timeframe:
            raise ValueError(f"Timeframe {timeframe_id} not found")
        
        logger.info(f"DEBUG: Starting sync for timeframe {timeframe.name} (id={timeframe_id})")
        
        # Default field mappings with support for both single and multiple roles
        mappings = field_mappings or {
            'email': 'email',
            'name': 'name', 
            'course': 'course',
            'id': 'id',
            'roles': 'roles',  # Primary field for multiple roles
            'role': 'role',    # Fallback for single role
            'timeframe': 'fyp_session'
        }
        
        # Group external data by email for this timeframe
        external_users = {}
        timeframe_field = mappings.get('timeframe', 'fyp_session')
        
        for user_data in external_data:
            # Check if this record belongs to the current timeframe
            user_timeframe = user_data.get(timeframe_field)
            if user_timeframe and user_timeframe == timeframe.name:
                email_field = mappings['email']
                if email_field in user_data and user_data[email_field]:
                    email = user_data[email_field].lower().strip()
                    
                    # Aggregate multiple role entries for the same user
                    if email not in external_users:
                        external_users[email] = {
                            'user_data': user_data.copy(),
                            'all_roles': []
                        }
                    
                    # Extract roles from this record
                    roles_data = user_data.get(mappings.get('roles', 'roles')) or user_data.get(mappings.get('role', 'role'))
                    if roles_data:
                        if isinstance(roles_data, str):
                            roles = [role.strip().lower() for role in roles_data.split(',')]
                        elif isinstance(roles_data, list):
                            roles = [str(role).strip().lower() for role in roles_data]
                        else:
                            roles = [str(roles_data).strip().lower()]
                        
                        # Add roles to the user's total roles
                        for role in roles:
                            if role and role not in external_users[email]['all_roles']:
                                external_users[email]['all_roles'].append(role)
        
        # Create consolidated user data with all roles
        consolidated_external_users = {}
        for email, user_info in external_users.items():
            consolidated_data = user_info['user_data'].copy()
            # Set the consolidated roles
            consolidated_data[mappings.get('roles', 'roles')] = user_info['all_roles']
            consolidated_external_users[email] = consolidated_data
        
        external_emails = set(consolidated_external_users.keys())
        logger.info(f"DEBUG: Found {len(external_emails)} unique users in external data for timeframe {timeframe.name}")
        
        # Get current users assigned to this timeframe from the same school
        current_users_in_timeframe = User.query.join(User.timeframes).filter(
            Timeframe.id == timeframe_id,
            User.school_id == school_id
        ).all()
        
        current_emails = {user.email.lower() for user in current_users_in_timeframe}
        logger.info(f"DEBUG: Found {len(current_emails)} current users in timeframe {timeframe.name}")
        
        # Track changes
        created_count = 0
        updated_count = 0
        removed_count = 0
        assigned_count = 0
        error_count = 0
        total_roles_processed = 0
        
        # 1. Process users from external data (create/update/assign)
        for email, user_data in consolidated_external_users.items():
            try:
                logger.info(f"DEBUG: Processing user {email} with roles {user_data.get(mappings.get('roles', 'roles'))}")
                
                user, created, roles_processed = create_or_update_user_multi_role(
                    user_data, school_id, timeframe_id, field_mappings
                )
                
                if user:
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    total_roles_processed += len(roles_processed)
                    
                    # LEGACY: Assign user to timeframe if not already assigned
                    if timeframe not in user.timeframes:
                        user.timeframes.append(timeframe)
                        assigned_count += 1
                        logger.info(f"Assigned user {user.email} to timeframe {timeframe.name}")
                    
                    # NEW: Also create role-scoped assignments for EACH role
                    for role_name in roles_processed:
                        logger.info(f"DEBUG: About to call assign_user_role_timeframe for {user.email}, role={role_name}, timeframe={timeframe.name}")
                        assign_user_role_timeframe(user, role_name, timeframe)
                        logger.info(f"Created role-scoped assignment: {user.email} as {role_name} in {timeframe.name}")
                    
                    logger.info(f"Processed {len(roles_processed)} roles for user {user.email}: {roles_processed}")
                else:
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing user data: {e}")
                error_count += 1
                continue
        
        # Check what's in the user_role_timeframes table before commit
        role_assignments_count = db.session.query(user_role_timeframes).count()
        logger.info(f"DEBUG: Total role assignments in user_role_timeframes table before commit: {role_assignments_count}")
        
        # 2. Handle users who are no longer in external data for this timeframe
        emails_to_remove = current_emails - external_emails
        
        for email in emails_to_remove:
            try:
                user = User.query.filter(
                    User.email.ilike(email),
                    User.school_id == school_id
                ).first()
                
                if user and timeframe in user.timeframes:
                    # Remove user from this timeframe (legacy)
                    user.timeframes.remove(timeframe)
                    removed_count += 1
                    logger.info(f"Removed user {user.email} from timeframe {timeframe.name}")
                    
                    # ALSO remove role-scoped assignments for this timeframe
                    db.session.execute(
                        user_role_timeframes.delete().where(
                            and_(
                                user_role_timeframes.c.user_id == user.id,
                                user_role_timeframes.c.timeframe_id == timeframe.id
                            )
                        )
                    )
                    logger.info(f"Removed role-scoped assignments for {user.email} in {timeframe.name}")
                    
                    # SMART ROLE CLEANUP: Remove roles that are no longer needed
                    cleanup_user_roles_after_timeframe_removal(user, timeframe, external_data, mappings)
                    
                    # If user is not in any timeframes anymore, clear all roles
                    if not user.timeframes:
                        user.roles = []
                        logger.info(f"Cleared all roles for user {user.email} (no longer in any timeframes)")
                        
            except Exception as e:
                logger.error(f"Error removing user {email}: {e}")
                error_count += 1
                continue
        
        return created_count, updated_count, removed_count, assigned_count, error_count, total_roles_processed
        
    except Exception as e:
        logger.error(f"Error in sync_users_with_timeframe_multi_role: {e}")
        raise

def sync_users_with_timeframe_smart(external_data, school_id, timeframe_id, field_mappings=None):
    """
    Legacy function for backward compatibility - now uses multi-role function
    """
    created, updated, removed, assigned, errors, total_roles = sync_users_with_timeframe_multi_role(
        external_data, school_id, timeframe_id, field_mappings
    )
    return created, updated, removed, assigned, errors

@load_data_api_bp.route('/load_data/load_external/<int:timeframe_id>', methods=['POST'])
def load_from_external_database(timeframe_id):
    """
    Load and synchronize data from external API for a specific timeframe with multi-role support
    """
    try:
        # Get current user's school
        current_user_id = session.get('user_id')
        if not current_user_id:
            flash('Please log in to continue.', 'error')
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        
        current_user = User.query.get(current_user_id)
        if not current_user or not current_user.school_id:
            flash('User school not found. Please contact administrator.', 'error')
            return jsonify({'success': False, 'message': 'User school not found.'}), 400
        
        # Get timeframe
        timeframe = Timeframe.query.get_or_404(timeframe_id)
        if timeframe.school_id != current_user.school_id:
            flash('Unauthorized access to timeframe.', 'error')
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
        
        # Get API configuration for the school
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=current_user.school_id,
            is_active=True
        ).first()
        
        if not api_config:
            flash('External API not configured. Please set up API configuration first.', 'warning')
            return jsonify({'success': False, 'message': 'API not configured.'}), 400
        
        # Extract field mappings from config with multi-role support
        field_mappings = get_field_mappings_from_config(api_config)
        logger.info(f"Using field mappings with multi-role support: {field_mappings}")
        
        # Use timeframe name as academic period for matching
        academic_period = timeframe.name
        
        # Fetch data from external API
        external_data = fetch_external_data_via_api(api_config, academic_period)
        
        if external_data is None:
            flash('Failed to connect to external API. Please check configuration.', 'error')
            return jsonify({
                'success': False,
                'message': 'Failed to connect to external API'
            }), 500
        
        if not external_data:
            # Even if no data, we still want to sync (remove users who shouldn't be there)
            logger.info(f'No data found for academic period: {academic_period}, proceeding with cleanup')
        
        logger.info(f"DEBUG: About to start sync with {len(external_data)} external records")
        
        # Synchronize users with timeframe using multi-role handling
        created_count, updated_count, removed_count, assigned_count, error_count, total_roles_processed = sync_users_with_timeframe_multi_role(
            external_data, 
            current_user.school_id, 
            timeframe_id,
            field_mappings
        )
        
        # Check what's in the table before commit
        role_assignments_count = db.session.query(user_role_timeframes).count()
        logger.info(f"DEBUG: About to commit transaction with {total_roles_processed} roles processed")
        logger.info(f"DEBUG: Role assignments in user_role_timeframes before commit: {role_assignments_count}")
        
        # Commit all changes
        db.session.commit()
        logger.info("DEBUG: Transaction committed successfully")
        
        # Check what's in the table after commit
        role_assignments_count_after = db.session.query(user_role_timeframes).count()
        logger.info(f"DEBUG: Role assignments in user_role_timeframes after commit: {role_assignments_count_after}")
        
        # Prepare success message
        message_parts = []
        if created_count > 0:
            message_parts.append(f"{created_count} new users created")
        if updated_count > 0:
            message_parts.append(f"{updated_count} users updated")
        if assigned_count > 0:
            message_parts.append(f"{assigned_count} users assigned to timeframe")
        if removed_count > 0:
            message_parts.append(f"{removed_count} users removed from timeframe")
        if total_roles_processed > 0:
            message_parts.append(f"{total_roles_processed} total roles processed")
        
        if not message_parts:
            message_parts.append("No changes needed - data already synchronized")
        
        success_message = "Multi-role sync completed: " + ", ".join(message_parts)
        
        if error_count > 0:
            success_message += f" ({error_count} errors occurred)"
            flash(success_message, 'warning')
        else:
            flash(success_message, 'success')
        
        logger.info(f"Multi-role data sync completed for timeframe {timeframe_id}: {success_message}")
        
        # Return JSON response for the JavaScript
        return jsonify({
            'success': True,
            'message': success_message,
            'total_external': len(external_data),
            'created': created_count,
            'updated': updated_count,
            'assigned': assigned_count,
            'removed': removed_count,
            'errors': error_count,
            'total_roles_processed': total_roles_processed,
            'field_mappings_used': field_mappings
        })
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error synchronizing multi-role data from external API: {e}")
        flash(f'Error synchronizing data: {str(e)}', 'error')
        return jsonify({
            'success': False,
            'message': f'Error synchronizing data: {str(e)}'
        }), 500

@load_data_api_bp.route('/users/roles_summary/<int:school_id>')
def get_users_roles_summary(school_id):
    """
    Get summary of users and their roles across different timeframes
    """
    try:
        # Get current user's school for authorization
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        
        current_user = User.query.get(current_user_id)
        if not current_user or current_user.school_id != school_id:
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
        
        # Get all users for this school with their roles and timeframes
        users = User.query.filter_by(school_id=school_id).all()
        
        users_summary = []
        for user in users:
            user_info = {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'student_staff_id': user.student_staff_id,
                'course': user.course,
                'roles': [role.name for role in user.roles],
                'timeframes': [
                    {
                        'id': tf.id,
                        'name': tf.name,
                        'description': tf.description
                    } for tf in user.timeframes
                ],
                'role_count': len(user.roles),
                'timeframe_count': len(user.timeframes)
            }
            users_summary.append(user_info)
        
        # Sort by name for easier viewing
        users_summary.sort(key=lambda x: x['name'])
        
        return jsonify({
            'success': True,
            'users': users_summary,
            'total_users': len(users_summary)
        })
        
    except Exception as e:
        logger.error(f"Error getting users roles summary: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@load_data_api_bp.route('/check_api_status/<int:school_id>')
def check_api_status(school_id):
    """
    Check if API is configured for the school
    """
    try:
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=school_id,
            is_active=True
        ).first()
        
        field_mappings = None
        if api_config:
            field_mappings = get_field_mappings_from_config(api_config)
        
        return jsonify({
            'configured': api_config is not None,
            'config_exists': api_config is not None,
            'field_mappings': field_mappings
        })
        
    except Exception as e:
        logger.error(f"Error checking API status: {e}")
        return jsonify({
            'configured': False,
            'config_exists': False,
            'error': str(e)
        }), 500

@load_data_api_bp.route('/test_connection', methods=['POST'])
def test_external_connection():
    """
    Test connection to external API
    """
    try:
        data = request.get_json()
        school_id = data.get('school_id')
        
        if not school_id:
            return jsonify({'success': False, 'message': 'School ID required'}), 400
        
        # Get API configuration
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=school_id,
            is_active=True
        ).first()
        
        if not api_config:
            return jsonify({
                'success': False, 
                'message': 'API configuration not found'
            }), 404
        
        # Test connection
        success, message = test_external_api_connection(api_config)
        return jsonify({
            'success': success, 
            'message': message
        })
            
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        return jsonify({
            'success': False, 
            'message': f'Error: {str(e)}'
        }), 500

@load_data_api_bp.route('/cleanup_orphaned_roles/<int:school_id>', methods=['POST'])
def cleanup_orphaned_roles(school_id):
    """
    Clean up roles for users who are no longer in any timeframes
    This is a manual cleanup utility for administrators
    """
    try:
        # Get current user's school for authorization
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        
        current_user = User.query.get(current_user_id)
        if not current_user or current_user.school_id != school_id:
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
        
        # Find users with no timeframes but still have roles
        orphaned_users = User.query.filter(
            User.school_id == school_id,
            ~User.timeframes.any()  # Users with no timeframes
        ).all()
        
        cleaned_count = 0
        for user in orphaned_users:
            if user.roles:  # If user has roles but no timeframes
                user.roles = []  # Clear all roles
                cleaned_count += 1
                logger.info(f"Cleared roles for orphaned user: {user.email}")
        
        db.session.commit()
        
        message = f"Cleaned up roles for {cleaned_count} orphaned users"
        flash(message, 'success')
        
        return jsonify({
            'success': True,
            'message': message,
            'cleaned_count': cleaned_count
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cleaning orphaned roles: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@load_data_api_bp.route('/preview_external_data/<int:timeframe_id>', methods=['GET'])
def preview_external_data(timeframe_id):
    """
    Preview external data without importing it - useful for testing field mappings
    Enhanced to show multi-role data processing
    """
    try:
        # Get current user's school
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        
        current_user = User.query.get(current_user_id)
        if not current_user or not current_user.school_id:
            return jsonify({'success': False, 'message': 'User school not found.'}), 400
        
        # Get timeframe
        timeframe = Timeframe.query.get_or_404(timeframe_id)
        if timeframe.school_id != current_user.school_id:
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
        
        # Get API configuration for the school
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=current_user.school_id,
            is_active=True
        ).first()
        
        if not api_config:
            return jsonify({'success': False, 'message': 'API not configured.'}), 400
        
        # Get field mappings
        field_mappings = get_field_mappings_from_config(api_config)
        
        # Fetch data from external API
        external_data = fetch_external_data_via_api(api_config, timeframe.name)
        
        if external_data is None:
            return jsonify({
                'success': False,
                'message': 'Failed to connect to external API'
            }), 500
        
        # Preview first 5 records with field mapping applied and multi-role processing
        preview_data = []
        for i, record in enumerate(external_data[:5]):
            # Process roles like the actual sync function would
            roles_data = record.get(field_mappings.get('roles', 'roles')) or record.get(field_mappings.get('role', 'role'))
            processed_roles = []
            
            if roles_data:
                if isinstance(roles_data, str):
                    processed_roles = [role.strip().lower() for role in roles_data.split(',')]
                elif isinstance(roles_data, list):
                    processed_roles = [str(role).strip().lower() for role in roles_data]
                else:
                    processed_roles = [str(roles_data).strip().lower()]
            
            mapped_record = {
                'original': record,
                'mapped': {
                    'email': record.get(field_mappings['email']),
                    'name': record.get(field_mappings['name']),
                    'course': record.get(field_mappings['course']),
                    'id': record.get(field_mappings['id']),
                    'role': record.get(field_mappings['role']),
                    'roles': record.get(field_mappings.get('roles', 'roles')),
                    'processed_roles': processed_roles,
                    'timeframe': record.get(field_mappings['timeframe'])
                }
            }
            preview_data.append(mapped_record)
        
        # Analyze role distribution in the data
        all_roles = set()
        user_role_counts = {}
        
        for record in external_data:
            if record.get(field_mappings['timeframe']) == timeframe.name:
                email = record.get(field_mappings['email'])
                roles_data = record.get(field_mappings.get('roles', 'roles')) or record.get(field_mappings.get('role', 'role'))
                
                if email and roles_data:
                    if isinstance(roles_data, str):
                        roles = [role.strip().lower() for role in roles_data.split(',')]
                    elif isinstance(roles_data, list):
                        roles = [str(role).strip().lower() for role in roles_data]
                    else:
                        roles = [str(roles_data).strip().lower()]
                    
                    for role in roles:
                        if role:
                            all_roles.add(role)
                            if email not in user_role_counts:
                                user_role_counts[email] = set()
                            user_role_counts[email].add(role)
        
        # Calculate statistics
        multi_role_users = sum(1 for roles in user_role_counts.values() if len(roles) > 1)
        
        return jsonify({
            'success': True,
            'total_records': len(external_data),
            'records_for_timeframe': len([r for r in external_data if r.get(field_mappings['timeframe']) == timeframe.name]),
            'preview_records': preview_data,
            'field_mappings': field_mappings,
            'timeframe': timeframe.name,
            'analysis': {
                'unique_roles': sorted(list(all_roles)),
                'total_unique_users': len(user_role_counts),
                'users_with_multiple_roles': multi_role_users,
                'total_unique_roles': len(all_roles)
            }
        })
        
    except Exception as e:
        logger.error(f"Error previewing external data: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500