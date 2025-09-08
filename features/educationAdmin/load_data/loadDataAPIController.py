import requests
from flask import Blueprint, request, jsonify, flash, redirect, url_for, session
from database import db
from shared.models import User, Role, Timeframe, ExternalAPIConfig, School
from werkzeug.security import generate_password_hash
from datetime import datetime
import logging
import secrets
import string

# Import the passwords dictionary from loadDataController
from features.educationAdmin.load_data.loadDataController import passwords_for_email

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_data_api_bp = Blueprint('load_data_api', __name__)

def generate_random_password(length=12):
    """Generate a secure random password"""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))

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

def create_or_update_user(user_data, school_id, timeframe_id):
    """
    Create new user or update existing user with external data
    Returns (user, created_flag)
    """
    try:
        # Check if user already exists by email
        existing_user = User.query.filter_by(email=user_data['email']).first()
        
        if existing_user:
            # Update existing user - NO password generation for existing users
            existing_user.name = user_data['name']
            existing_user.course = user_data['course']
            existing_user.student_staff_id = user_data['id']
            existing_user.school_id = school_id
            
            # Update role if needed
            role_name = user_data['role']
            role = Role.query.filter_by(name=role_name).first()
            if role and role not in existing_user.roles:
                # Clear existing roles and add new one
                existing_user.roles = [role]
            
            logger.info(f"Updated existing user (no password generated): {existing_user.email}")
            return existing_user, False
        else:
            # Create NEW user - ONLY generate password for truly new users
            temp_password = generate_random_password()
            passwords_for_email[user_data['email']] = temp_password
            
            # Generate hash for database storage
            password_hash = generate_password_hash(temp_password)
            
            new_user = User(
                name=user_data['name'],
                email=user_data['email'],
                password_hash=password_hash,
                course=user_data['course'],
                student_staff_id=user_data['id'],
                school_id=school_id,
                created_at=datetime.utcnow()
            )
            
            # Assign role
            role_name = user_data['role']
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                # Create role if it doesn't exist
                role = Role(
                    name=role_name,
                    description=f"{role_name}",
                    created_at=datetime.utcnow()
                )
                db.session.add(role)
                db.session.flush()  # Get the role ID
            
            new_user.roles.append(role)
            
            db.session.add(new_user)
            logger.info(f"Created NEW user with generated password: {new_user.email}")
            return new_user, True
            
    except Exception as e:
        logger.error(f"Error creating/updating user {user_data['email']}: {e}")
        return None, False

def sync_users_with_timeframe(external_data, school_id, timeframe_id):
    """
    Synchronize users with timeframe - add/update/remove users based on external data
    Returns (created, updated, removed, assigned, errors)
    """
    try:
        timeframe = Timeframe.query.get(timeframe_id)
        if not timeframe:
            raise ValueError(f"Timeframe {timeframe_id} not found")
        
        # Get emails from external data
        external_emails = {user_data['email'].lower() for user_data in external_data}
        
        # Get current users assigned to this timeframe from the same school
        current_users_in_timeframe = User.query.join(User.timeframes).filter(
            Timeframe.id == timeframe_id,
            User.school_id == school_id
        ).all()
        
        current_emails = {user.email.lower() for user in current_users_in_timeframe}
        
        # Track changes
        created_count = 0
        updated_count = 0
        removed_count = 0
        assigned_count = 0
        error_count = 0
        
        # 1. Process users from external data (create/update/assign)
        for user_data in external_data:
            try:
                user, created = create_or_update_user(user_data, school_id, timeframe_id)
                
                if user:
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    # Assign user to timeframe if not already assigned
                    if timeframe not in user.timeframes:
                        user.timeframes.append(timeframe)
                        assigned_count += 1
                        logger.info(f"Assigned user {user.email} to timeframe {timeframe.name}")
                else:
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing user data: {e}")
                error_count += 1
                continue
        
        # 2. Remove users who are no longer in external data
        emails_to_remove = current_emails - external_emails
        
        for email in emails_to_remove:
            try:
                user = User.query.filter(
                    User.email.ilike(email),
                    User.school_id == school_id
                ).first()
                
                if user and timeframe in user.timeframes:
                    # Remove user from timeframe
                    user.timeframes.remove(timeframe)
                    removed_count += 1
                    logger.info(f"Removed user {user.email} from timeframe {timeframe.name}")
                    
                    # Optional: If user is not in any other timeframes, you might want to 
                    # deactivate or delete the user entirely
                    if not user.timeframes:
                        logger.info(f"User {user.email} is no longer in any timeframes")
                        # Uncomment the next line if you want to delete users completely
                        db.session.delete(user)
                        
            except Exception as e:
                logger.error(f"Error removing user {email}: {e}")
                error_count += 1
                continue
        
        return created_count, updated_count, removed_count, assigned_count, error_count
        
    except Exception as e:
        logger.error(f"Error in sync_users_with_timeframe: {e}")
        raise

@load_data_api_bp.route('/load_data/load_external/<int:timeframe_id>', methods=['POST'])
def load_from_external_database(timeframe_id):
    """
    Load and synchronize data from external API for a specific timeframe
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
        
        # Synchronize users with timeframe
        created_count, updated_count, removed_count, assigned_count, error_count = sync_users_with_timeframe(
            external_data, 
            current_user.school_id, 
            timeframe_id
        )
        
        # Commit all changes
        db.session.commit()
        
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
        
        if not message_parts:
            message_parts.append("No changes needed - data already synchronized")
        
        success_message = "Sync completed: " + ", ".join(message_parts)
        
        if error_count > 0:
            success_message += f" ({error_count} errors occurred)"
            flash(success_message, 'warning')
        else:
            flash(success_message, 'success')
        
        logger.info(f"Data sync completed for timeframe {timeframe_id}: {success_message}")
        
        # Return JSON response for the JavaScript
        return jsonify({
            'success': True,
            'message': success_message,
            'total_external': len(external_data),
            'created': created_count,
            'updated': updated_count,
            'assigned': assigned_count,
            'removed': removed_count,
            'errors': error_count
        })
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error synchronizing data from external API: {e}")
        flash(f'Error synchronizing data: {str(e)}', 'error')
        return jsonify({
            'success': False,
            'message': f'Error synchronizing data: {str(e)}'
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
        
        return jsonify({
            'configured': api_config is not None,
            'config_exists': api_config is not None
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