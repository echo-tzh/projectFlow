import requests
from flask import Blueprint, request, jsonify, flash, redirect, url_for, session, render_template
from database import db
from shared.models import User, ExternalAPIConfig, School, Timeframe
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

setup_api_bp = Blueprint('setup_api', __name__)

@setup_api_bp.route('/setup_api')
def index():
    """
    Main setup page for external API configuration
    """
    try:
        # Get current user's school
        current_user_id = session.get('user_id')
        if not current_user_id:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('auth.login'))
        
        current_user = User.query.get(current_user_id)
        if not current_user or not current_user.school_id:
            flash('User school not found. Please contact administrator.', 'error')
            return redirect(url_for('dashboard_redirect'))
        
        # Get existing API configuration for the school
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=current_user.school_id,
            is_active=True
        ).first()
        
        return render_template('features/educationAdmin/setupAPI/templates/setupAPI.html',
                     api_config=api_config,
                     school=current_user.school)
        
    except Exception as e:
        logger.error(f"Error loading setup API page: {e}")
        flash(f'Error loading page: {str(e)}', 'error')
        return redirect(url_for('dashboard_redirect'))

@setup_api_bp.route('/api_config/save', methods=['POST'])
def save_api_config():
    """
    Save or update API configuration including credentials and field mappings
    """
    try:
        # Get current user's school
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        
        current_user = User.query.get(current_user_id)
        if not current_user or not current_user.school_id:
            return jsonify({'success': False, 'message': 'User school not found.'}), 400
        
        data = request.get_json()
        
        # Validate required fields
        api_key = data.get('api_key', '').strip()
        api_secret = data.get('api_secret', '').strip()
        
        if not api_key:
            return jsonify({'success': False, 'message': 'API Key is required'}), 400
        
        # Get field mappings with defaults (including timeframe)
        field_mappings = data.get('field_mappings', {})
        email_field = field_mappings.get('email', 'email').strip()
        name_field = field_mappings.get('name', 'name').strip()
        course_field = field_mappings.get('course', 'course').strip()
        id_field = field_mappings.get('id', 'id').strip()
        role_field = field_mappings.get('role', 'role').strip()
        timeframe_field = field_mappings.get('timeframe', 'fyp_session').strip()
        
        # Validate field mappings are not empty
        if not all([email_field, name_field, course_field, id_field, role_field, timeframe_field]):
            return jsonify({'success': False, 'message': 'All field mappings are required'}), 400
        
        # Check if API config already exists for this school
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=current_user.school_id,
            is_active=True
        ).first()
        
        if api_config:
            # Update existing configuration
            api_config.api_key = api_key
            api_config.api_secret = api_secret if api_secret else api_config.api_secret
            api_config.email_field = email_field
            api_config.name_field = name_field
            api_config.course_field = course_field
            api_config.id_field = id_field
            api_config.role_field = role_field
            api_config.timeframe_field = timeframe_field
            
            action = "updated"
        else:
            # Create new configuration
            if not api_secret:
                return jsonify({'success': False, 'message': 'API Secret is required for new configuration'}), 400
            
            api_config = ExternalAPIConfig(
                api_key=api_key,
                api_secret=api_secret,
                email_field=email_field,
                name_field=name_field,
                course_field=course_field,
                id_field=id_field,
                role_field=role_field,
                timeframe_field=timeframe_field,
                school_id=current_user.school_id,
                created_by=current_user_id,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(api_config)
            action = "created"
        
        db.session.commit()
        
        logger.info(f"API configuration {action} for school {current_user.school_id} by user {current_user_id}")
        flash(f'API configuration {action} successfully!', 'success')
        
        return jsonify({
            'success': True,
            'message': f'API configuration {action} successfully',
            'config_id': api_config.id,
            'field_mappings': api_config.get_field_mappings()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving API configuration: {e}")
        return jsonify({
            'success': False,
            'message': f'Error saving configuration: {str(e)}'
        }), 500

@setup_api_bp.route('/api_config/get/<int:school_id>')
def get_api_config(school_id):
    """
    Get current API configuration for a school
    """
    try:
        # Get current user for authorization
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        
        current_user = User.query.get(current_user_id)
        if not current_user or current_user.school_id != school_id:
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
        
        # Get API configuration
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=school_id,
            is_active=True
        ).first()
        
        if not api_config:
            return jsonify({
                'success': True,
                'config_exists': False,
                'message': 'No API configuration found'
            })
        
        # Return configuration (without sensitive data like api_secret)
        config_data = {
            'id': api_config.id,
            'api_key': api_config.api_key,
            'api_secret_exists': bool(api_config.api_secret),
            'field_mappings': api_config.get_field_mappings(),
            'is_active': api_config.is_active,
            'created_at': api_config.created_at.isoformat() if api_config.created_at else None
        }
        
        return jsonify({
            'success': True,
            'config_exists': True,
            'config': config_data
        })
        
    except Exception as e:
        logger.error(f"Error getting API configuration: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@setup_api_bp.route('/api_config/test_connection', methods=['POST'])
def test_api_connection():
    """
    Test connection to external API using current configuration
    """
    try:
        data = request.get_json()
        school_id = data.get('school_id')
        
        # Get current user for authorization
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        
        current_user = User.query.get(current_user_id)
        if not current_user or current_user.school_id != school_id:
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
        
        # Get API configuration
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=school_id,
            is_active=True
        ).first()
        
        if not api_config:
            return jsonify({
                'success': False,
                'message': 'API configuration not found. Please save configuration first.'
            }), 404
        
        # Test connection using the configuration
        success, message = test_external_api_connection(api_config)
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error testing API connection: {e}")
        return jsonify({
            'success': False,
            'message': f'Error testing connection: {str(e)}'
        }), 500

def test_external_api_connection(api_config):
    """
    Test connection to external API
    Returns (success, message)
    """
    try:
        # Read configuration
        api_key = api_config.api_key
        api_secret = api_config.api_secret
        base_url = "http://localhost:5002"  # You can make this configurable too
        
        if not api_key or not api_secret:
            return False, "API key or secret is missing"
        
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
            return False, f"API returned status {response.status_code}: {response.text}"
            
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

@setup_api_bp.route('/api_config/test_field_mappings', methods=['POST'])
def test_field_mappings():
    """
    Test field mappings by fetching sample data from external API
    """
    try:
        data = request.get_json()
        school_id = data.get('school_id')
        
        # Get current user for authorization
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        
        current_user = User.query.get(current_user_id)
        if not current_user or current_user.school_id != school_id:
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
        
        # Get API configuration
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=school_id,
            is_active=True
        ).first()
        
        if not api_config:
            return jsonify({
                'success': False,
                'message': 'API configuration not found. Please save configuration first.'
            }), 404
        
        # Just use a simple test period to get any available data
        external_data = fetch_sample_external_data(api_config, '2025-Sem1')
        
        if external_data is None:
            return jsonify({
                'success': False,
                'message': 'Failed to connect to external API'
            }), 500
        
        if not external_data:
            return jsonify({
                'success': True,
                'message': 'No sample data available from external API',
                'field_mappings': api_config.get_field_mappings(),
                'total_records': 0,
                'all_fields_valid': False
            })
        
        # Get field mappings
        field_mappings = api_config.get_field_mappings()
        
        # Check field validation across all records
        total_records = len(external_data)
        field_validation = {
            'email': 0,
            'name': 0,
            'course': 0,
            'id': 0,
            'role': 0,
            'timeframe': 0
        }
        
        # Count how many records have each field
        for record in external_data:
            for field_name, column_name in field_mappings.items():
                if column_name in record and record[column_name] is not None:
                    field_validation[field_name] += 1
        
        # Calculate field status
        field_status = {}
        for field_name, count in field_validation.items():
            field_status[field_name] = {
                'column_exists': field_mappings[field_name] in (external_data[0].keys() if external_data else []),
                'records_with_data': count,
                'percentage': round((count / total_records * 100), 1) if total_records > 0 else 0,
                'status': 'valid' if count > 0 else 'invalid'
            }
        
        # Check if all required fields are present and have data
        all_fields_valid = all(status['status'] == 'valid' for status in field_status.values())
        
        # Get available columns from first record for reference
        available_columns = list(external_data[0].keys()) if external_data else []
        
        return jsonify({
            'success': True,
            'total_records': total_records,
            'field_mappings': field_mappings,
            'field_status': field_status,
            'all_fields_valid': all_fields_valid,
            'available_columns': available_columns,
            'message': f'Found {total_records} records. ' + ('All field mappings are valid.' if all_fields_valid else 'Some field mappings need correction.')
        })
        
    except Exception as e:
        logger.error(f"Error testing field mappings: {e}")
        return jsonify({
            'success': False,
            'message': f'Error testing field mappings: {str(e)}'
        }), 500
        
        
def fetch_sample_external_data(api_config, academic_period):
    """
    Fetch sample data from external API for testing field mappings
    """
    try:
        # Read configuration
        api_key = api_config.api_key
        api_secret = api_config.api_secret
        base_url = "http://localhost:5002"
        
        if not api_key or not api_secret:
            logger.error("API key or secret is missing")
            return None
        
        # Prepare headers for API request
        headers = {
            'X-API-Key': api_key,
            'X-API-Secret': api_secret,
            'Content-Type': 'application/json'
        }
        
        # Make API request
        api_url = f"{base_url}/api/students/by-period/{academic_period}"
        logger.info(f"Making test API request to: {api_url}")
        
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                students = data.get('students', [])
                logger.info(f"Successfully fetched {len(students)} students for testing")
                return students
            else:
                logger.error(f"API returned success=False: {data}")
                return []
        else:
            logger.error(f"API request failed with status {response.status_code}: {response.text}")
            return []
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error when calling external API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching from external API: {e}")
        return None

@setup_api_bp.route('/api_config/delete/<int:config_id>', methods=['DELETE'])
def delete_api_config(config_id):
    """
    Delete API configuration
    """
    try:
        # Get current user for authorization
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        
        current_user = User.query.get(current_user_id)
        if not current_user:
            return jsonify({'success': False, 'message': 'User not found.'}), 400
        
        # Get API configuration
        api_config = ExternalAPIConfig.query.get_or_404(config_id)
        
        # Check authorization
        if api_config.school_id != current_user.school_id:
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
        
        # Soft delete by setting is_active to False
        api_config.is_active = False
        db.session.commit()
        
        logger.info(f"API configuration {config_id} deactivated by user {current_user_id}")
        flash('API configuration deleted successfully!', 'success')
        
        return jsonify({
            'success': True,
            'message': 'API configuration deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting API configuration: {e}")
        return jsonify({
            'success': False,
            'message': f'Error deleting configuration: {str(e)}'
        }), 500

@setup_api_bp.route('/api_config/field_mappings/save', methods=['POST'])
def save_field_mappings():
    """
    Save custom field mappings for API data processing
    """
    try:
        data = request.get_json()
        school_id = data.get('school_id')
        mappings = data.get('mappings', {})
        
        # Get current user for authorization
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        
        current_user = User.query.get(current_user_id)
        if not current_user or current_user.school_id != school_id:
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
        
        # Get API configuration
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=school_id,
            is_active=True
        ).first()
        
        if not api_config:
            return jsonify({'success': False, 'message': 'API config not found'}), 404
        
        # Validate mappings (including timeframe)
        required_fields = ['email', 'name', 'course', 'id', 'role', 'timeframe']
        for field in required_fields:
            if field not in mappings or not mappings[field].strip():
                return jsonify({
                    'success': False, 
                    'message': f'Field mapping for {field} is required'
                }), 400
        
        # Update field mappings
        api_config.set_field_mappings(mappings)
        db.session.commit()
        
        logger.info(f"Field mappings updated for school {school_id} by user {current_user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Field mappings saved successfully',
            'field_mappings': api_config.get_field_mappings()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving field mappings: {e}")
        return jsonify({
            'success': False,
            'message': f'Error saving field mappings: {str(e)}'
        }), 500

@setup_api_bp.route('/api_config/export/<int:school_id>')
def export_api_config(school_id):
    """
    Export API configuration (without sensitive data) for backup
    """
    try:
        # Get current user for authorization
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({'success': False, 'message': 'Please log in to continue.'}), 401
        
        current_user = User.query.get(current_user_id)
        if not current_user or current_user.school_id != school_id:
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
        
        # Get API configuration
        api_config = ExternalAPIConfig.query.filter_by(
            school_id=school_id,
            is_active=True
        ).first()
        
        if not api_config:
            return jsonify({
                'success': False,
                'message': 'No API configuration found'
            }), 404
        
        # Export configuration (excluding sensitive data)
        export_data = {
            'school_id': school_id,
            'field_mappings': api_config.get_field_mappings(),
            'api_key': api_config.api_key[:8] + "..." if api_config.api_key else None,  # Partial for reference
            'has_api_secret': bool(api_config.api_secret),
            'created_at': api_config.created_at.isoformat() if api_config.created_at else None,
            'export_date': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'export_data': export_data
        })
        
    except Exception as e:
        logger.error(f"Error exporting API configuration: {e}")
        return jsonify({
            'success': False,
            'message': f'Error exporting configuration: {str(e)}'
        }), 500