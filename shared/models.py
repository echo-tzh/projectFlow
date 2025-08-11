from database import db
from datetime import datetime

# ------------------------
# Existing Models
# ------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)  # Added for better identification
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(700), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # e.g., student, supervisor, admin, coordinator
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to School
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True)

    # Relationships
    photos = db.relationship('MarketingPhoto', backref='uploader', lazy=True)
    projects = db.relationship('Project', backref='creator', lazy=True)  # For coordinators

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
# New Models for Project Flow
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

class Timeframe(db.Model):
    __tablename__ = 'timeframes'
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)

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
