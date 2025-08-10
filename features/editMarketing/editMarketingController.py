import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from werkzeug.utils import secure_filename
from shared.models import Plan, Review, MarketingPhoto, db
from functools import wraps

# Set the path to the templates folder inside this feature
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
edit_marketing_bp = Blueprint('edit_marketing_bp', __name__, template_folder=template_dir)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Add your admin authentication logic here
        # For now, assuming you have a way to check if user is admin
        # if not current_user.is_authenticated or current_user.role != 'admin':
        #     flash('Admin access required.', 'error')
        #     return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@edit_marketing_bp.route('/admin/marketing')
@admin_required
def edit_marketing():
    """Main marketing editing dashboard"""
    # Get all content ordered by display_order
    hero_slides = MarketingPhoto.query.filter_by(category='hero').order_by(MarketingPhoto.display_order.asc()).all()
    plans = Plan.query.order_by(Plan.display_order.asc()).all()
    
    # Get all reviews and featured reviews separately
    all_reviews = Review.query.order_by(Review.created_at.desc()).all()
    featured_reviews = Review.query.filter_by(is_featured=True).order_by(Review.display_order.asc()).all()
    
    return render_template('editMarketing.html',
                         hero_slides=hero_slides,
                         plans=plans,
                         all_reviews=all_reviews,
                         featured_reviews=featured_reviews)

# HERO SLIDES MANAGEMENT
@edit_marketing_bp.route('/admin/marketing/hero/add', methods=['GET', 'POST'])
@admin_required
def add_hero_slide():
    """Add new hero slide"""
    if request.method == 'POST':
        slide = MarketingPhoto(
            category='hero',
            eyebrow_text=request.form.get('eyebrow_text'),
            headline=request.form.get('headline'),
            subhead=request.form.get('subhead'),
            primary_cta_text=request.form.get('primary_cta_text'),
            primary_cta_link=request.form.get('primary_cta_link'),
            secondary_cta_text=request.form.get('secondary_cta_text'),
            secondary_cta_link=request.form.get('secondary_cta_link'),
            filename=request.form.get('filename', 'default.jpg'),
            is_active=True,
            display_order=int(request.form.get('display_order', 0))
        )
        
        db.session.add(slide)
        db.session.commit()
        flash('Hero slide added successfully!', 'success')
        return redirect(url_for('edit_marketing_bp.edit_marketing'))
    
    return render_template('add_hero_slide.html')

@edit_marketing_bp.route('/admin/marketing/hero/edit/<int:slide_id>', methods=['GET', 'POST'])
@admin_required
def edit_hero_slide(slide_id):
    """Edit existing hero slide"""
    slide = MarketingPhoto.query.get_or_404(slide_id)
    
    if request.method == 'POST':
        slide.eyebrow_text = request.form.get('eyebrow_text')
        slide.headline = request.form.get('headline')
        slide.subhead = request.form.get('subhead')
        slide.primary_cta_text = request.form.get('primary_cta_text')
        slide.primary_cta_link = request.form.get('primary_cta_link')
        slide.secondary_cta_text = request.form.get('secondary_cta_text')
        slide.secondary_cta_link = request.form.get('secondary_cta_link')
        slide.is_active = 'is_active' in request.form
        slide.display_order = int(request.form.get('display_order', 0))
        
        db.session.commit()
        flash('Hero slide updated successfully!', 'success')
        return redirect(url_for('edit_marketing_bp.edit_marketing'))
    
    return render_template('edit_hero_slide.html', slide=slide)

@edit_marketing_bp.route('/admin/marketing/hero/delete/<int:slide_id>', methods=['POST'])
@admin_required
def delete_hero_slide(slide_id):
    """Delete hero slide"""
    slide = MarketingPhoto.query.get_or_404(slide_id)
    db.session.delete(slide)
    db.session.commit()
    flash('Hero slide deleted successfully!', 'success')
    return redirect(url_for('edit_marketing_bp.edit_marketing'))

# PLANS MANAGEMENT
@edit_marketing_bp.route('/admin/marketing/plan/add', methods=['GET', 'POST'])
@admin_required
def add_plan():
    """Add new plan"""
    if request.method == 'POST':
        # Handle price - if custom pricing, set to None
        price_input = request.form.get('price')
        price = None if price_input == 'custom' or not price_input else float(price_input)
        
        plan = Plan(
            name=request.form.get('name'),
            price=price,
            billing_period=request.form.get('billing_period'),
            is_popular='is_popular' in request.form,
            features=request.form.get('features'),
            cta_text=request.form.get('cta_text'),
            cta_link=request.form.get('cta_link'),
            is_active=True,
            display_order=int(request.form.get('display_order', 0))
        )
        
        db.session.add(plan)
        db.session.commit()
        flash('Plan added successfully!', 'success')
        return redirect(url_for('edit_marketing_bp.edit_marketing'))
    
    return render_template('add_plan.html')

@edit_marketing_bp.route('/admin/marketing/plan/edit/<int:plan_id>', methods=['GET', 'POST'])
@admin_required
def edit_plan(plan_id):
    """Edit existing plan"""
    plan = Plan.query.get_or_404(plan_id)
    
    if request.method == 'POST':
        plan.name = request.form.get('name')
        
        # Handle price
        price_input = request.form.get('price')
        plan.price = None if price_input == 'custom' or not price_input else float(price_input)
        
        plan.billing_period = request.form.get('billing_period')
        plan.is_popular = 'is_popular' in request.form
        plan.features = request.form.get('features')
        plan.cta_text = request.form.get('cta_text')
        plan.cta_link = request.form.get('cta_link')
        plan.is_active = 'is_active' in request.form
        plan.display_order = int(request.form.get('display_order', 0))
        
        db.session.commit()
        flash('Plan updated successfully!', 'success')
        return redirect(url_for('edit_marketing_bp.edit_marketing'))
    
    return render_template('edit_plan.html', plan=plan)

@edit_marketing_bp.route('/admin/marketing/plan/delete/<int:plan_id>', methods=['POST'])
@admin_required
def delete_plan(plan_id):
    """Delete plan"""
    plan = Plan.query.get_or_404(plan_id)
    db.session.delete(plan)
    db.session.commit()
    flash('Plan deleted successfully!', 'success')
    return redirect(url_for('edit_marketing_bp.edit_marketing'))

# REVIEWS MANAGEMENT
@edit_marketing_bp.route('/admin/marketing/review/add', methods=['GET', 'POST'])
@admin_required
def add_review():
    """Add new review"""
    if request.method == 'POST':
        review = Review(
            author_name=request.form.get('author_name'),
            author_role=request.form.get('author_role'),
            university=request.form.get('university'),
            rating=int(request.form.get('rating', 5)),
            content=request.form.get('content'),
            is_featured='is_featured' in request.form,
            display_order=int(request.form.get('display_order', 0))
        )
        
        db.session.add(review)
        db.session.commit()
        flash('Review added successfully!', 'success')
        return redirect(url_for('edit_marketing_bp.edit_marketing'))
    
    return render_template('add_review.html')

@edit_marketing_bp.route('/admin/marketing/review/edit/<int:review_id>', methods=['GET', 'POST'])
@admin_required
def edit_review(review_id):
    """Edit existing review"""
    review = Review.query.get_or_404(review_id)
    
    if request.method == 'POST':
        review.author_name = request.form.get('author_name')
        review.author_role = request.form.get('author_role')
        review.university = request.form.get('university')
        review.rating = int(request.form.get('rating', 5))
        review.content = request.form.get('content')
        review.is_featured = 'is_featured' in request.form
        review.display_order = int(request.form.get('display_order', 0))
        
        db.session.commit()
        flash('Review updated successfully!', 'success')
        return redirect(url_for('edit_marketing_bp.edit_marketing'))
    
    return render_template('edit_review.html', review=review)

@edit_marketing_bp.route('/admin/marketing/review/toggle-featured/<int:review_id>', methods=['POST'])
@admin_required
def toggle_review_featured(review_id):
    """Toggle review featured status"""
    review = Review.query.get_or_404(review_id)
    review.is_featured = not review.is_featured
    db.session.commit()
    
    status = 'featured' if review.is_featured else 'unfeatured'
    flash(f'Review {status} successfully!', 'success')
    return redirect(url_for('edit_marketing_bp.edit_marketing'))

@edit_marketing_bp.route('/admin/marketing/review/delete/<int:review_id>', methods=['POST'])
@admin_required
def delete_review(review_id):
    """Delete review"""
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted successfully!', 'success')
    return redirect(url_for('edit_marketing_bp.edit_marketing'))

# AJAX ENDPOINTS FOR REORDERING
@edit_marketing_bp.route('/admin/marketing/reorder', methods=['POST'])
@admin_required
def reorder_items():
    """Handle drag-and-drop reordering"""
    data = request.get_json()
    item_type = data.get('type')  # 'hero', 'plan', or 'review'
    items = data.get('items')  # list of {id: x, order: y}
    
    try:
        if item_type == 'hero':
            for item in items:
                slide = MarketingPhoto.query.get(item['id'])
                if slide:
                    slide.display_order = item['order']
        elif item_type == 'plan':
            for item in items:
                plan = Plan.query.get(item['id'])
                if plan:
                    plan.display_order = item['order']
        elif item_type == 'review':
            for item in items:
                review = Review.query.get(item['id'])
                if review:
                    review.display_order = item['order']
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})