from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, 
                static_folder='static',  # Añade esta línea
                static_url_path='/static')  # Añade esta línea
    
    app.config.from_object(Config)
    
    db.init_app(app)
    
    from app.routes import bp
    app.register_blueprint(bp)
    
    with app.app_context():
        db.create_all()
    
    return app