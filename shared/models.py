from database import db
from datetime import datetime
from werkzeug.security import generate_password_hash

# ------------------------
# Association Table for Many-to-Many User-Role Relationship
# ------------------------
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow)
)

# ------------------------
# Association Table for Many-to-Many User-Timeframe Relationship
# ------------------------
user_timeframes = db.Table('user_timeframes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('timeframe_id', db.Integer, db.ForeignKey('timeframes.id'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow)
)

# ------------------------
# New Role Model
# ------------------------
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # e.g., 'student', 'supervisor', 'admin', 'coordinator'
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship back to users
    users = db.relationship('User', secondary=user_roles, back_populates='roles', lazy='dynamic')

# ------------------------
# Email Configuration Model
# ------------------------
class EmailConfig(db.Model):
    __tablename__ = 'email_configs'
    id = db.Column(db.Integer, primary_key=True)
    smtp_server = db.Column(db.String(255), nullable=False, default='smtp.gmail.com')
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    smtp_username = db.Column(db.String(255), nullable=False)
    smtp_password = db.Column(db.String(500), nullable=False)  # Should be encrypted in production
    from_email = db.Column(db.String(255), nullable=False)
    from_name = db.Column(db.String(100), nullable=True, default='ProjectFlow Team')
    
    # Additional settings
    use_tls = db.Column(db.Boolean, default=True)
    use_ssl = db.Column(db.Boolean, default=False)
    
    # Tie to school
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def __repr__(self):
        return f'<EmailConfig {self.from_email} - {self.school.name if self.school else "No School"}>'

# ------------------------
# Updated Models
# ------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)  # Added for better identification
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(700), nullable=False)
    course = db.Column(db.String(200), nullable=True)  # Course studying
    student_staff_id = db.Column(db.String(50), nullable=True)  # Student/Staff ID (not primary key)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to School
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True)

    # Many-to-Many relationship with roles
    roles = db.relationship('Role', secondary=user_roles, back_populates='users', lazy='dynamic')
    
    # Many-to-Many relationship with timeframes
    timeframes = db.relationship('Timeframe', secondary=user_timeframes, backref='users', lazy='dynamic')

    # Other relationships
    photos = db.relationship('MarketingPhoto', backref='uploader', lazy=True)
    projects = db.relationship('Project', backref='creator', lazy=True)  # For coordinators
    email_configs = db.relationship('EmailConfig', backref='creator', lazy=True)

class MarketingPhoto(db.Model):
    __tablename__ = 'marketing_photos'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    alt_text = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category = db.Column(db.String(100))  # e.g., 'hero', 'slide', 'review'

    # Hero slide text content
    eyebrow_text = db.Column(db.String(100))
    headline = db.Column(db.String(200))
    subhead = db.Column(db.Text)
    primary_cta_text = db.Column(db.String(50))
    primary_cta_link = db.Column(db.String(255))
    secondary_cta_text = db.Column(db.String(50))
    secondary_cta_link = db.Column(db.String(255))

    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)

class Plan(db.Model):
    __tablename__ = 'plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=True)
    billing_period = db.Column(db.String(50), nullable=False)
    is_popular = db.Column(db.Boolean, default=False)
    features = db.Column(db.Text)
    cta_text = db.Column(db.String(50), default='Get Started')
    cta_link = db.Column(db.String(255), default='#')

    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    author_name = db.Column(db.String(100), nullable=False)
    author_role = db.Column(db.String(100), nullable=False)
    university = db.Column(db.String(100), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    is_featured = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)

# ------------------------
# Project Flow Models
# ------------------------
class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    users = db.relationship('User', backref='school', lazy=True)
    timeframes = db.relationship('Timeframe', backref='school', lazy=True)
    email_config = db.relationship('EmailConfig', backref='school', lazy=True)

class Timeframe(db.Model):
    __tablename__ = 'timeframes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    location = db.Column(db.String(255), nullable=True)  # the location will be like UOW or SIM etc.
    delivery_type = db.Column(db.Enum('on campus', 'off campus', name='delivery_type_enum'), nullable=False)

    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    preference_limit = db.Column(db.Integer, nullable=False, default=3)
    preference_startTiming = db.Column(db.Date, nullable=False)
    preference_endTiming = db.Column(db.Date, nullable=False)
    
    
    # Relationships
    projects = db.relationship('Project', backref='timeframe', lazy=True)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    timeframe_id = db.Column(db.Integer, db.ForeignKey('timeframes.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Academic Coordinator

# ------------------------
# Default Data Creation Function
# ------------------------
def create_default_admin_account():
    """
    Creates a default system admin account if it doesn't exist.
    Call this function after creating your database tables.
    
    Login credentials:
    - Email: projectFlowAdminAccount
    - Password: 12345678
    """
    
    try:
        # Check if system admin role exists, create if not
        admin_role = Role.query.filter_by(name='system admin').first()
        if not admin_role:
            admin_role = Role(
                name='system admin',
                description='system admin',
                created_at=datetime.utcnow(),
                is_active=True
            )
            db.session.add(admin_role)
            print("✅ Created 'system admin' role")
        else:
            print("ℹ️  'system admin' role already exists")

        # Check if admin user exists, create if not
        admin_user = User.query.filter_by(email='projectFlowAdminAccount').first()
        if not admin_user:
            # Hash the password '12345678'
            hashed_password = generate_password_hash('12345678')
            
            admin_user = User(
                name='System Administrator',
                email='projectFlowAdminAccount',
                password_hash=hashed_password,
                course=None,  # Not applicable for admin
                student_staff_id='ADMIN001',
                created_at=datetime.utcnow(),
                school_id=None  # Can be assigned to a school later if needed
            )
            
            db.session.add(admin_user)
            db.session.flush()  # To get the user ID before adding role
            
            # Assign the admin role to the user
            admin_user.roles.append(admin_role)
            
            print("✅ Created default admin user: projectFlowAdminAccount")
            print("🔑 Login credentials:")
            print("   Email: projectFlowAdminAccount")
            print("   Password: 12345678")
            print("⚠️  IMPORTANT: Change this password after first login!")
        else:
            print("ℹ️  Admin user 'projectFlowAdminAccount' already exists")
            # Ensure the user has admin role
            if admin_role not in admin_user.roles:
                admin_user.roles.append(admin_role)
                print("✅ Added 'system admin' role to existing user")

        db.session.commit()
        print("✅ Default admin account setup completed successfully!")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating admin account: {str(e)}")
        return False
# ------------------------
# Usage Example (add to your app initialization)
# ------------------------
"""
To use this in your Flask app, add this to your main app file after creating tables:

from models import create_default_admin_account

# After db.create_all()
with app.app_context():
    db.create_all()  # Create tables first
    create_default_admin_account()  # Then create default admin
"""