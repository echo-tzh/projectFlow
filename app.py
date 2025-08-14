from flask import Flask, redirect, url_for
from config import Config
from database import db
from features.login.loginController import login_bp
from features.marketing.marketingController import marketing_bp
from features.editMarketing.editMarketingController import edit_marketing_bp
from flask_cors import CORS
from features.createSchool.createSchoolController import create_school_bp
#from features.educationAdmin.educationAdminDashboard.educationAdminDashboardController import educational_admin_bp
from features.educationAdmin.manageTimeframe.manageTimeframeController import manage_timeframe_bp

from features.educationAdmin.load_data.loadDataController import load_data_bp

from features.dashboard.dashboardController import universal_dashboard_bp

#


app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
CORS(app)

# Register all blueprints
app.register_blueprint(login_bp)
app.register_blueprint(marketing_bp)
app.register_blueprint(edit_marketing_bp)
app.register_blueprint(create_school_bp)
#app.register_blueprint(educational_admin_bp)
app.register_blueprint(manage_timeframe_bp)
app.register_blueprint(load_data_bp)
app.register_blueprint(universal_dashboard_bp)
@app.route('/')
def index():
    return redirect(url_for('marketing_bp.marketing'))

@app.route('/loggin')
def login_redirect():
    return redirect(url_for('login_bp.login'))

@app.route('/create-school')
def setup_school():
    return redirect(url_for('create_school_bp.create_school'))

#@app.route('/educational_admin')
#def dashboard():
 #   return redirect(url_for('educational_admin.dashboard'))

# Renamed the route to prevent a conflict with the blueprint's route
@app.route('/manage-timeframes-redirect')
def manage_timeframes_redirect():
    return redirect(url_for('manage_timeframe_bp.manage_timeframes'))

@app.route('/dashboard')
def dashboard_redirect():
    return redirect(url_for('universal_dashboard.dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)