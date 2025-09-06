from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from shared.models import db, User, ExternalAPIConfig, Timeframe
import mysql.connector
from mysql.connector import Error

# Create blueprint for API setup
setup_api_bp = Blueprint('setup_api', __name__, 
                        url_prefix='/education-admin/setup-api', 
                        template_folder='templates')

def get_current_user():
    """Get current user from session"""
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])

def check_educational_admin():
    """Check if user has educational admin privileges"""
    current_user = get_current_user()
    if not current_user:
        return False, None
    
    admin_role = current_user.roles.filter_by(name='educational_admin').first()
    if not admin_role or not current_user.school_id:
        return False, current_user
    
    return True, current_user

@setup_api_bp.route('/')
def index():
    """Main API setup page"""
    is_admin, current_user = check_educational_admin()
    
    if not is_admin:
        flash('Access denied. Educational admin privileges required.', 'error')
        return redirect(url_for('universal_dashboard_bp.dashboard'))
    
    # Get existing API config for this school
    existing_config = ExternalAPIConfig.query.filter_by(school_id=current_user.school_id).first()
    
    return render_template('setupAPI.html', 
                         existing_config=existing_config,
                         current_user=current_user)

@setup_api_bp.route('/save-config', methods=['POST'])
def save_config():
    """Save external API configuration"""
    is_admin, current_user = check_educational_admin()
    
    if not is_admin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        # Get form data
        api_key = request.form.get('api_key', '').strip()
        api_secret = request.form.get('api_secret', '').strip()
        
        # Validate required fields
        if not api_key:
            flash('API Key is required', 'error')
            return redirect(url_for('setup_api.index'))
        
        # Check if config already exists
        existing_config = ExternalAPIConfig.query.filter_by(school_id=current_user.school_id).first()
        
        if existing_config:
            # Update existing
            existing_config.api_key = api_key
            existing_config.api_secret = api_secret if api_secret else None
            db.session.commit()
        else:
            # Create new
            new_config = ExternalAPIConfig(
                api_key=api_key,
                api_secret=api_secret if api_secret else None,
                school_id=current_user.school_id,
                created_by=current_user.id
            )
            db.session.add(new_config)
            db.session.commit()
        
        flash('API configuration saved successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving configuration: {str(e)}', 'error')
    
    return redirect(url_for('setup_api.index'))


@setup_api_bp.route('/add-mapping', methods=['POST'])
def add_mapping():
    """Add academic period mapping"""
    is_admin, current_user = check_educational_admin()
    
    if not is_admin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        external_period = request.form.get('external_period', '').strip()
        timeframe_id = int(request.form.get('timeframe_id'))
        
        if not external_period:
            flash('External period name is required', 'error')
            return redirect(url_for('setup_api.index'))
        
        # Check if mapping already exists
        existing = AcademicPeriodMapping.query.filter_by(
            external_period=external_period,
            school_id=current_user.school_id
        ).first()
        
        if existing:
            flash(f'Mapping for "{external_period}" already exists', 'warning')
            return redirect(url_for('setup_api.index'))
        
        # Verify timeframe belongs to this school
        timeframe = Timeframe.query.filter_by(
            id=timeframe_id,
            school_id=current_user.school_id
        ).first()
        
        if not timeframe:
            flash('Invalid timeframe selected', 'error')
            return redirect(url_for('setup_api.index'))
        
        # Create mapping
        mapping = AcademicPeriodMapping(
            external_period=external_period,
            timeframe_id=timeframe_id,
            school_id=current_user.school_id,
            created_by=current_user.id
        )
        
        db.session.add(mapping)
        db.session.commit()
        
        flash(f'Mapping added: "{external_period}" → {timeframe.name}', 'success')
        
    except ValueError:
        flash('Invalid timeframe selection', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding mapping: {str(e)}', 'error')
    
    return redirect(url_for('setup_api.index'))

@setup_api_bp.route('/delete-mapping/<int:mapping_id>', methods=['POST'])
def delete_mapping(mapping_id):
    """Delete academic period mapping"""
    is_admin, current_user = check_educational_admin()
    
    if not is_admin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        mapping = AcademicPeriodMapping.query.filter_by(
            id=mapping_id,
            school_id=current_user.school_id
        ).first()
        
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404
        
        db.session.delete(mapping)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Mapping deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500