# models.py
import sys
import os

# Fix encoding issues on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from datetime import datetime, date
from werkzeug.security import generate_password_hash
from sqlalchemy import and_, Index, UniqueConstraint
from database import db

# ------------------------
# Association tables
# ------------------------

# Many-to-many: User ↔ Role
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow)
)

# Many-to-many: User ↔ Timeframe (role-agnostic legacy link)
user_timeframes = db.Table(
    'user_timeframes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('timeframe_id', db.Integer, db.ForeignKey('timeframes.id'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow)
)

# Role-scoped assignment: User ↔ Role ↔ Timeframe
user_role_timeframes = db.Table(
    'user_role_timeframes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('timeframe_id', db.Integer, db.ForeignKey('timeframes.id'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow)
)

# ------------------------
# Core models
# ------------------------

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # e.g. student, supervisor, academic coordinator, system admin
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Users (role-agnostic)
    users = db.relationship('User', secondary=user_roles, back_populates='roles', lazy='dynamic')

    def __repr__(self):
        return f"<Role {self.name}>"


class EmailConfig(db.Model):
    __tablename__ = 'email_configs'
    id = db.Column(db.Integer, primary_key=True)
    smtp_server = db.Column(db.String(255), nullable=False, default='smtp.gmail.com')
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    smtp_username = db.Column(db.String(255), nullable=False)
    smtp_password = db.Column(db.String(500), nullable=False)  # encrypt in production
    from_email = db.Column(db.String(255), nullable=False)
    from_name = db.Column(db.String(100), nullable=True, default='ProjectFlow Team')

    use_tls = db.Column(db.Boolean, default=True)
    use_ssl = db.Column(db.Boolean, default=False)

    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def __repr__(self):
        return f'<EmailConfig {self.from_email}>'


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(700), nullable=False)
    course = db.Column(db.String(200), nullable=True)
    student_staff_id = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    email_sent = db.Column(db.Boolean, default=False, nullable=False)

    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True)

    # Role-agnostic links
    roles = db.relationship('Role', secondary=user_roles, back_populates='users', lazy='dynamic')
    timeframes = db.relationship('Timeframe', secondary=user_timeframes, backref='users', lazy='dynamic')

    # Other rels
    photos = db.relationship('MarketingPhoto', backref='uploader', lazy=True)
    projects = db.relationship('Project', backref='creator', lazy=True)  # created as coordinator
    email_configs = db.relationship('EmailConfig', backref='creator', lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"


class MarketingPhoto(db.Model):
    __tablename__ = 'marketing_photos'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    alt_text = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category = db.Column(db.String(100))  # hero, slide, review

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


class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

    location = db.Column(db.String(255), nullable=True)  # UOW, SIM, etc.
    delivery_type = db.Column(db.Enum('on campus', 'off campus', name='delivery_type_enum'), nullable=False)

    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    preference_limit = db.Column(db.Integer, nullable=False, default=3)
    preference_startTiming = db.Column(db.Date, nullable=False)
    preference_endTiming = db.Column(db.Date, nullable=False)

    projects = db.relationship('Project', backref='timeframe', lazy=True)

    def __repr__(self):
        return f"<Timeframe {self.name}>"


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student_capacity = db.Column(db.Integer)
    assessor_capacity = db.Column(db.Integer)
    supervisor_capacity = db.Column(db.Integer)

    timeframe_id = db.Column(db.Integer, db.ForeignKey('timeframes.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # coordinator


class Wishlist(db.Model):
    __tablename__ = 'wishlists'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('wishlists', lazy='dynamic', cascade='all, delete-orphan'))
    project = db.relationship('Project', backref=db.backref('wishlisted_by', lazy='dynamic'))


class Preference(db.Model):
    __tablename__ = 'preferences'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    timeframe_id = db.Column(db.Integer, db.ForeignKey('timeframes.id'), nullable=False, index=True)

    preference_rank = db.Column(db.Integer, nullable=False, index=True)

    selected_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    notes = db.Column(db.Text, nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'project_id', 'timeframe_id', name='unique_user_project_timeframe_preference'),
        UniqueConstraint('user_id', 'timeframe_id', 'preference_rank', name='unique_user_timeframe_rank'),
        Index('idx_user_timeframe_rank', 'user_id', 'timeframe_id', 'preference_rank'),
        Index('idx_timeframe_rank', 'timeframe_id', 'preference_rank'),
    )

    user = db.relationship('User', backref=db.backref('preferences', lazy='dynamic', cascade='all, delete-orphan'))
    project = db.relationship('Project', backref=db.backref('preferred_by', lazy='dynamic'))
    timeframe = db.relationship('Timeframe', backref=db.backref('user_preferences', lazy='dynamic'))


class AllocationResult(db.Model):
    __tablename__ = 'allocation_results'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    timeframe_id = db.Column(db.Integer, db.ForeignKey('timeframes.id'), nullable=False)
    role_type = db.Column(db.Enum('student', 'supervisor', 'assessor', name='allocation_role_enum'), nullable=False)

    preference_rank_fulfilled = db.Column(db.Integer, nullable=True)
    allocation_batch_id = db.Column(db.String(100), nullable=False)
    allocation_method = db.Column(db.String(50), nullable=False)  # automatic, manual, override

    status = db.Column(db.Enum('pending', 'confirmed', 'rejected', 'withdrawn', name='allocation_status_enum'),
                       default='pending', nullable=False)

    allocated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    status_updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    allocated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'timeframe_id', 'role_type', name='unique_user_timeframe_role_allocation'),
        Index('idx_allocation_batch', 'allocation_batch_id'),
        Index('idx_timeframe_role', 'timeframe_id', 'role_type'),
        Index('idx_user_timeframe', 'user_id', 'timeframe_id'),
    )

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('allocations', lazy='dynamic'))
    project = db.relationship('Project', backref=db.backref('allocated_users', lazy='dynamic'))
    timeframe = db.relationship('Timeframe', backref=db.backref('allocations', lazy='dynamic'))
    allocator = db.relationship('User', foreign_keys=[allocated_by], backref=db.backref('allocations_made', lazy='dynamic'))


class UnallocatedUser(db.Model):
    __tablename__ = 'unallocated_users'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timeframe_id = db.Column(db.Integer, db.ForeignKey('timeframes.id'), nullable=False)
    allocation_batch_id = db.Column(db.String(100), nullable=False)
    expected_role = db.Column(db.Enum('student', 'supervisor', 'assessor', name='expected_role_enum'), nullable=False)

    reason = db.Column(db.Enum(
        'no_preferences', 'all_preferences_full', 'capacity_exceeded',
        'manual_hold', 'eligibility_issue', 'insufficient_projects',
        name='unallocated_reason_enum'
    ), nullable=False)
    details = db.Column(db.Text, nullable=True)

    manual_intervention_required = db.Column(db.Boolean, default=True)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])
    timeframe = db.relationship('Timeframe')
    resolver = db.relationship('User', foreign_keys=[resolved_by])


class ExternalAPIConfig(db.Model):
    __tablename__ = 'external_api_configs'
    id = db.Column(db.Integer, primary_key=True)

    api_key = db.Column(db.String(255), nullable=False)
    api_secret = db.Column(db.String(255), nullable=True)

    email_field = db.Column(db.String(100), nullable=False, default='email')
    name_field = db.Column(db.String(100), nullable=False, default='name')
    course_field = db.Column(db.String(100), nullable=False, default='course')
    id_field = db.Column(db.String(100), nullable=False, default='id')
    role_field = db.Column(db.String(100), nullable=False, default='role')
    timeframe_field = db.Column(db.String(100), nullable=False, default='fyp_session')

    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def get_field_mappings(self):
        return {
            'email': self.email_field,
            'name': self.name_field,
            'course': self.course_field,
            'id': self.id_field,
            'role': self.role_field,
            'timeframe': self.timeframe_field
        }

    def set_field_mappings(self, mappings: dict):
        self.email_field = mappings.get('email', 'email')
        self.name_field = mappings.get('name', 'name')
        self.course_field = mappings.get('course', 'course')
        self.id_field = mappings.get('id', 'id')
        self.role_field = mappings.get('role', 'role')
        self.timeframe_field = mappings.get('timeframe', 'fyp_session')

# ------------------------
# Helpers for role-scoped assignments
# ------------------------

def _get_or_create_role(role_name: str) -> Role:
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

def user_has_role_in_timeframe(user, role_name: str, timeframe) -> bool:
    user_id = user.id if hasattr(user, "id") else int(user)
    timeframe_id = timeframe.id if hasattr(timeframe, "id") else int(timeframe)
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return False
    row = db.session.query(user_role_timeframes).filter_by(
        user_id=user_id, role_id=role.id, timeframe_id=timeframe_id
    ).first()
    return bool(row)

def get_timeframes_for_user_and_role(user, role_name: str):
    """
    Return Timeframes where user holds role_name.
    """
    user_id = user.id if hasattr(user, "id") else int(user)
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return []
    return (
        db.session.query(Timeframe)
        .join(user_role_timeframes, Timeframe.id == user_role_timeframes.c.timeframe_id)
        .filter(
            user_role_timeframes.c.user_id == user_id,
            user_role_timeframes.c.role_id == role.id
        )
        .order_by(Timeframe.start_date)
        .all()
    )

# ------------------------
# Default admin bootstrap
# ------------------------

def create_default_admin_account():
    """
    Creates a default system admin account if it doesn't exist.
    Email: projectFlowAdminAccount
    Password: 12345678
    """
    try:
        admin_role = Role.query.filter_by(name='system admin').first()
        if not admin_role:
            admin_role = Role(
                name='system admin',
                description='system admin',
                created_at=datetime.utcnow(),
                is_active=True
            )
            db.session.add(admin_role)

        admin_user = User.query.filter_by(email='projectFlowAdminAccount').first()
        if not admin_user:
            hashed_password = generate_password_hash('12345678')
            admin_user = User(
                name='System Administrator',
                email='projectFlowAdminAccount',
                password_hash=hashed_password,
                student_staff_id='ADMIN001',
                created_at=datetime.utcnow(),
                school_id=None
            )
            db.session.add(admin_user)
            db.session.flush()
            admin_user.roles.append(admin_role)
        else:
            if admin_role not in admin_user.roles:
                admin_user.roles.append(admin_role)

        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error creating admin account: {str(e)}")
        return False
