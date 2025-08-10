from database import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # e.g., student, supervisor, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    photos = db.relationship('MarketingPhoto', backref='uploader', lazy=True)

class MarketingPhoto(db.Model):
    __tablename__ = 'marketing_photos'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    alt_text = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key to track which user uploaded it
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Category for section grouping
    category = db.Column(db.String(100))  # e.g., 'hero', 'slide', 'review'
    
    # Hero slide text content fields
    eyebrow_text = db.Column(db.String(100))
    headline = db.Column(db.String(200))
    subhead = db.Column(db.Text)
    primary_cta_text = db.Column(db.String(50))
    primary_cta_link = db.Column(db.String(255))
    secondary_cta_text = db.Column(db.String(50))
    secondary_cta_link = db.Column(db.String(255))
    
    # Display control
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
    
    # Display control
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
    
    # Display control - whether to show on marketing page
    is_featured = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)