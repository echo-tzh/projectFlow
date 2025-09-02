from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
from shared.models import MarketingPhoto, Plan, Review
from database import db
import os
from datetime import datetime

edit_marketing_bp = Blueprint('edit_marketing_bp', __name__, 
                              template_folder='templates')

# Configuration for file uploads
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@edit_marketing_bp.route('/edit-marketing')
def edit_marketing():
    """Display the marketing content editing interface"""
    try:
        # Get all hero slides (both active and inactive)
        hero_slides = MarketingPhoto.query.filter_by(
            category='hero', 
        ).order_by(MarketingPhoto.display_order).all()
        
        # The rest of your function remains the same
        plans = Plan.query.filter_by(is_active=True).order_by(Plan.display_order).all()
        reviews = Review.query.order_by(Review.display_order).all()
        
        return render_template('editMarketing.html', 
                             hero_slides=hero_slides,
                             plans=plans, 
                             reviews=reviews)
    except Exception as e:
        flash(f'Error loading marketing content: {str(e)}')
        return redirect(url_for('main.index'))
    
    
@edit_marketing_bp.route('/edit-marketing/hero', methods=['POST'])
def save_hero_slides():
    """Save hero slides data"""
    try:
        slides_data = request.get_json()
        
        if not slides_data:
            return jsonify({'success': False, 'error': 'No slide data provided'}), 400
        
        created_slides = []
        
        for i, slide_data in enumerate(slides_data):
            slide_id = slide_data.get('id')

            # Check if this is a new slide (ID is 'new', None, empty, or starts with 'temp_')
            if (slide_id == 'new' or slide_id is None or slide_id == '' or 
                (isinstance(slide_id, str) and slide_id.startswith('temp_'))):
                
                # Create new slide
                new_slide = MarketingPhoto(
                    filename=slide_data.get('filename', 'default.jpg'),
                    category='hero',
                    eyebrow_text=slide_data.get('eyebrow_text', ''),
                    headline=slide_data.get('headline', ''),
                    subhead=slide_data.get('subhead', ''),
                    primary_cta_text=slide_data.get('primary_cta_text', ''),
                    primary_cta_link=slide_data.get('primary_cta_link', ''),
                    secondary_cta_text=slide_data.get('secondary_cta_text', ''),
                    secondary_cta_link=slide_data.get('secondary_cta_link', ''),
                    display_order=slide_data.get('display_order', 0),
                    is_active=slide_data.get('is_active', True),
                    uploaded_at=datetime.utcnow()
                )
                db.session.add(new_slide)
                db.session.flush()  # Get the ID immediately
                created_slides.append({
                    'index': i, 
                    'new_id': new_slide.id,
                    'temp_id': slide_id  # Include the temp ID for frontend mapping
                })
            else:
                # Update existing slide
                try:
                    slide_id_int = int(slide_id)
                    slide = MarketingPhoto.query.get(slide_id_int)
                    
                    if not slide:
                        return jsonify({'success': False, 'error': f'Slide with ID {slide_id} not found'}), 404

                    slide.eyebrow_text = slide_data.get('eyebrow_text', '')
                    slide.headline = slide_data.get('headline', '')
                    slide.subhead = slide_data.get('subhead', '')
                    slide.primary_cta_text = slide_data.get('primary_cta_text', '')
                    slide.primary_cta_link = slide_data.get('primary_cta_link', '')
                    slide.secondary_cta_text = slide_data.get('secondary_cta_text', '')
                    slide.secondary_cta_link = slide_data.get('secondary_cta_link', '')
                    slide.display_order = slide_data.get('display_order', 0)
                    slide.is_active = slide_data.get('is_active', True)
                    
                    if slide_data.get('filename') and slide_data.get('filename') != 'default.jpg':
                        slide.filename = slide_data.get('filename')
                        
                except ValueError:
                    return jsonify({'success': False, 'error': f'Invalid slide ID: {slide_id}'}), 400

        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Hero slides saved successfully',
            'created_slides': created_slides
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@edit_marketing_bp.route('/edit-marketing/upload-image', methods=['POST'])
def upload_image():
    """Handle image uploads for hero slides"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to prevent filename conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            
            # Ensure upload directory exists
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            return jsonify({
                'success': True, 
                'filename': filename,
                'url': f'/static/images/{filename}'
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@edit_marketing_bp.route('/edit-marketing/plans', methods=['POST'])
def save_plans():
    """Save plans data"""
    try:
        plans_data = request.get_json()
        
        created_plans = []
        
        for i, plan_data in enumerate(plans_data):
            plan_id = plan_data.get('id')
            
            # Check if this is a new plan (ID is 'new', None, empty, or starts with 'temp_')
            if (plan_id == 'new' or plan_id is None or plan_id == '' or 
                (isinstance(plan_id, str) and plan_id.startswith('temp_'))):
                
                # Create new plan
                new_plan = Plan(
                    name=plan_data.get('name', ''),
                    price=plan_data.get('price'),
                    billing_period=plan_data.get('billing_period', ''),
                    features=plan_data.get('features', ''),
                    cta_text=plan_data.get('cta_text', 'Get Started'),
                    cta_link=plan_data.get('cta_link', '#'),
                    is_popular=plan_data.get('is_popular', False),
                    display_order=plan_data.get('display_order', 0),
                    is_active=plan_data.get('is_active', True)
                )
                db.session.add(new_plan)
                db.session.flush()  # Get the ID immediately
                created_plans.append({
                    'index': i, 
                    'new_id': new_plan.id,
                    'temp_id': plan_id
                })
            else:
                # Update existing plan
                try:
                    plan_id_int = int(plan_id)
                    plan = Plan.query.get(plan_id_int)
                    if plan:
                        plan.name = plan_data.get('name', '')
                        plan.price = plan_data.get('price')
                        plan.billing_period = plan_data.get('billing_period', '')
                        plan.features = plan_data.get('features', '')
                        plan.cta_text = plan_data.get('cta_text', 'Get Started')
                        plan.cta_link = plan_data.get('cta_link', '#')
                        plan.is_popular = plan_data.get('is_popular', False)
                        plan.display_order = plan_data.get('display_order', 0)
                        plan.is_active = plan_data.get('is_active', True)
                except ValueError:
                    return jsonify({'success': False, 'error': f'Invalid plan ID: {plan_id}'}), 400
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Plans saved successfully',
            'created_plans': created_plans
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@edit_marketing_bp.route('/edit-marketing/reviews/featured', methods=['POST'])
def update_featured_reviews():
    """Update which reviews are featured on homepage"""
    try:
        data = request.get_json()
        featured_ids = data.get('featured_reviews', [])
        
        # Reset all reviews to not featured
        Review.query.update({'is_featured': False})
        
        # Set selected reviews as featured
        if featured_ids:
            # Filter out any invalid IDs
            valid_ids = []
            for review_id in featured_ids:
                try:
                    valid_ids.append(int(review_id))
                except (ValueError, TypeError):
                    continue  # Skip invalid IDs
            
            if valid_ids:
                Review.query.filter(Review.id.in_(valid_ids)).update(
                    {'is_featured': True}, 
                    synchronize_session=False
                )
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Featured reviews updated'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@edit_marketing_bp.route('/edit-marketing/reviews/order', methods=['POST'])
def update_review_order():
    """Update display order of reviews via drag & drop"""
    try:
        data = request.get_json()
        review_orders = data.get('review_orders', [])
        
        for item in review_orders:
            review_id = item.get('id')
            new_order = item.get('order')
            
            try:
                review_id_int = int(review_id)
                review = Review.query.get(review_id_int)
                if review:
                    review.display_order = new_order
            except (ValueError, TypeError):
                continue  # Skip invalid IDs
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Review order updated'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@edit_marketing_bp.route('/edit-marketing/slide/<int:slide_id>', methods=['DELETE'])
def delete_slide(slide_id):
    """Delete a hero slide"""
    try:
        slide = MarketingPhoto.query.get_or_404(slide_id)
        
        # Optionally delete the image file
        if slide.filename and slide.filename != 'default.jpg':
            try:
                file_path = os.path.join(UPLOAD_FOLDER, slide.filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass  # Don't fail if file deletion fails
        
        db.session.delete(slide)
        db.session.flush()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Slide deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@edit_marketing_bp.route('/edit-marketing/plan/<int:plan_id>', methods=['DELETE'])
def delete_plan(plan_id):
    """Delete a plan"""
    try:
        plan = Plan.query.get_or_404(plan_id)
        db.session.delete(plan)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Plan deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500