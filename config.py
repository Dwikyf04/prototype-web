import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change_this_secret')            
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///default.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CLOUD_NAME = os.getenv('CLOUD_NAME', 'default_cloud')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', 'default_api_key')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', 'default_api_secret')

    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'default_username')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'default_password')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)

    ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin_password')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')

    