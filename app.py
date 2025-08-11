from flask import Flask, redirect, session, url_for
from config import Config
from database import db
from features.login.loginController import login_bp
from features.marketing.marketingController import marketing_bp
from features.editMarketing.editMarketingController import edit_marketing_bp
from flask_cors import CORS
from features.createSchool.createSchoolController import create_school_bp
from features.educationAdminDashboard.educationAdminDashboardController import educational_admin_bp

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

CORS(app)

# Register all blueprints
app.register_blueprint(login_bp)
app.register_blueprint(marketing_bp)
app.register_blueprint(edit_marketing_bp)
app.register_blueprint(create_school_bp)
app.register_blueprint(educational_admin_bp)

@app.route('/')
def index():
    return redirect(url_for('marketing_bp.marketing'))


@app.route('/loggin')
def login_redirect():
    return redirect(url_for('login_bp.login'))

@app.route('/create-school')
def setup_school():
    return redirect(url_for('create_school_bp.create_school'))

@app.route('/educational_admin')
def dashboard():
    return redirect(url_for('educational_admin.dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)