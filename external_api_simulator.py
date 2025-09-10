from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# Database configuration (points to your external_school_db)
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'external_school_db',
    'user': 'root',
    'password': ''  # Your MySQL password
}

# Simple API key validation
VALID_API_KEYS = {
    'uow_api_key_123': 'UOW_SECRET',
    'test_school_key': 'TEST_SECRET'
}

def validate_api_key():
    api_key = request.headers.get('X-API-Key')
    api_secret = request.headers.get('X-API-Secret')
    
    if not api_key or api_key not in VALID_API_KEYS:
        return False, 'Invalid API key'
    
    if VALID_API_KEYS[api_key] != api_secret:
        return False, 'Invalid API secret'
    
    return True, None

@app.route('/api/students/fyp-eligible', methods=['GET'])
def get_fyp_eligible_students():
    """Simulate external school's API endpoint"""
    
    # Validate API credentials
    is_valid, error = validate_api_key()
    if not is_valid:
        return jsonify({'error': error}), 401
    
    # Optional filters
    academic_period = request.args.get('academic_period')
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT id, name, email, course, fyp_session, 
               fyp_eligible, role, last_updated
        FROM fyp_data
        WHERE fyp_eligible = TRUE AND status = 'active'
        """
        
        params = []
        if academic_period:
            query += " AND fyp_session = %s"
            params.append(academic_period)
            
        query += " ORDER BY fyp_session, name"
        
        cursor.execute(query, params)
        students = cursor.fetchall()
        
        # Convert datetime to string for JSON serialization
        for student in students:
            if student['last_updated']:
                student['last_updated'] = student['last_updated'].isoformat()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'students': students,
            'total_count': len(students),
            'school_code': 'UOW',
            'sync_timestamp': datetime.now().isoformat()
        })
        
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/students/by-period/<period>', methods=['GET'])
def get_students_by_period(period):
    """Get students for specific academic period"""
    
    is_valid, error = validate_api_key()
    if not is_valid:
        return jsonify({'error': error}), 401
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
        SELECT id, name, email, course, fyp_session, 
               fyp_eligible, role, last_updated
        FROM fyp_data 
        WHERE fyp_session = %s AND fyp_eligible = TRUE AND status = 'active'
        ORDER BY name
        """, (period,))
        
        students = cursor.fetchall()
        
        for student in students:
            if student['last_updated']:
                student['last_updated'] = student['last_updated'].isoformat()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'academic_period': period,
            'students': students,
            'count': len(students)
        })
        
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'External School API Simulator'
    })

if __name__ == '__main__':
    app.run(port=5002, debug=True)  # Different port from your main app