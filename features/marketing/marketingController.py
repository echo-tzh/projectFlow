import os
from flask import Blueprint, render_template
from datetime import datetime
from shared.models import Plan, Review, MarketingPhoto
  # Import new models

# Set the path to the templates folder inside this feature
template_dir = os.path.join(os.path.dirname(__file__), 'templates')

marketing_bp = Blueprint('marketing_bp', __name__, template_folder=template_dir)

@marketing_bp.route('/marketing')
def marketing():
    # Fetch dynamic content from database
    hero_slides = MarketingPhoto.query.filter_by(category='hero').order_by(MarketingPhoto.uploaded_at.desc()).all()
    plans = Plan.query.order_by(Plan.id.asc()).all()
    reviews = Review.query.order_by(Review.id.asc()).all()
    
    current_year = datetime.now().year

    return render_template('marketing.html',
                           hero_slides=hero_slides,
                           plans=plans,
                           reviews=reviews,
                           current_year=current_year)
