from flask import Flask, redirect, session
from config import Config
from database import db
from features.login.loginController import login_bp
from features.marketing.marketingController import marketing_bp
from features.editMarketing.editMarketingController import edit_marketing_bp
from flask_cors import CORS



app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

CORS(app)

# Register blueprint
app.register_blueprint(login_bp)

#register blueprint for marketingController
app.register_blueprint(marketing_bp)
app.register_blueprint(edit_marketing_bp)

@app.route('/')
def index():
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    return "Welcome to Dashboard"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
