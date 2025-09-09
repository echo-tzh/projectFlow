# app.py

from flask import Flask, redirect, url_for
from config import Config
from database import db
from flask_cors import CORS
from flask_migrate import Migrate  # <-- NEW

# Blueprints
from features.authentication.login.loginController import login_bp
from features.systemAdmin.marketing.marketingController import marketing_bp
from features.systemAdmin.marketing.editMarketing.editMarketingController import edit_marketing_bp
from features.createSchool.createSchoolController import create_school_bp
from features.educationAdmin.manageTimeframe.manageTimeframeController import manage_timeframe_bp
from features.educationAdmin.load_data.loadDataController import load_data_bp
from features.dashboard.dashboardController import universal_dashboard_bp
from features.educationAdmin.load_data.sendWelcomeEmailController import send_welcome_email_bp
from features.educationAdmin.setupEmail.setupEmailController import setup_email_bp
from features.viewProfile.viewProfileController import viewProfile_bp
from features.student.viewProjectListing.viewProjectListingController import student_projects_bp
from features.student.viewProjectListing.wishlistController import student_wishlist_bp
from features.authentication.changePassword.changePassword import change_password_bp
from shared.models import create_default_admin_account
from features.systemAdmin.manageSchool.manageSchoolController import manage_school_bp
from features.academicCoordinator.viewCourseTerm.viewCourseTermController import view_course_term_bp
from shared.navigationBar.navigationController import navigation_bp, inject_navigation
from features.educationAdmin.setupAPI.setupAPIController import setup_api_bp
from features.educationAdmin.load_data.loadDataAPIController import load_data_api_bp
from features.student.studentPreferences.studentPreferencesController import student_preferences_bp

from features.academicCoordinator.manageProjects.manageProjectsController import manage_projects_bp

# --- APP SETUP ---
app = Flask(__name__, template_folder='.')
app.config.from_object(Config)
db.init_app(app)
migrate = Migrate(app, db)  # <-- NEW: enable Flask-Migrate
CORS(app)

# --- REGISTER BLUEPRINTS ---
app.register_blueprint(login_bp)
app.register_blueprint(marketing_bp)
app.register_blueprint(edit_marketing_bp)
app.register_blueprint(create_school_bp)
app.register_blueprint(manage_timeframe_bp)
app.register_blueprint(load_data_bp)
app.register_blueprint(universal_dashboard_bp)
app.register_blueprint(send_welcome_email_bp)
app.register_blueprint(setup_email_bp)
app.register_blueprint(student_projects_bp, url_prefix="/student")
app.register_blueprint(student_wishlist_bp, url_prefix="/student")
app.register_blueprint(viewProfile_bp)
app.register_blueprint(change_password_bp)
app.register_blueprint(manage_school_bp, url_prefix='/admin')
app.register_blueprint(view_course_term_bp)
app.register_blueprint(navigation_bp)
app.register_blueprint(setup_api_bp)
app.register_blueprint(load_data_api_bp)
app.register_blueprint(student_preferences_bp)

app.register_blueprint(manage_projects_bp)
# --- CONTEXT PROCESSORS ---
app.context_processor(inject_navigation)

# --- ROUTES ---
@app.route('/')
def index():
    return redirect(url_for('marketing_bp.marketing'))

@app.route('/loggin')
def login_redirect():
    return redirect(url_for('login_bp.login'))

@app.route('/create-school')
def setup_school():
    return redirect(url_for('create_school_bp.create_school'))

@app.route('/educational_admin_dashboard')
def educational_admin_dashboard_redirect():
    return redirect(url_for('educational_admin_bp.dashboard'))

@app.route('/manage-timeframes-redirect')
def manage_timeframes_redirect():
    return redirect(url_for('manage_timeframe_bp.manage_timeframes'))

@app.route('/dashboard')
def dashboard_redirect():
    return redirect(url_for('universal_dashboard_bp.dashboard'))

# --- MAIN ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_admin_account()
    app.run(debug=True)
