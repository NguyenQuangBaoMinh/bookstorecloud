import os

from flask_jwt_extended import JWTManager

from bookstore import app, build_sample_db
from bookstore.api import api_bp

# Cấu hình JWT
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Đổi thành một key bảo mật mạnh
jwt = JWTManager(app)

# Đăng ký blueprint API
app.register_blueprint(api_bp)
# It Allows You to Execute Code When the File Runs as a Script
if __name__ == '__main__':
    
    # Build a sample db on the fly, if one does not exist yet.
    # app_dir = os.path.realpath(os.path.dirname(__file__))
    # database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    # if not os.path.exists(database_path):
    with app.app_context():
        build_sample_db()

    # Start app
    app.run(debug=True)  