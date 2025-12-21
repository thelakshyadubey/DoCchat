import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key')
    
    # Google Drive API settings
    GOOGLE_DRIVE_CREDENTIALS_FILE = 'credentials.json'  # Your credentials file
    GOOGLE_DRIVE_TOKEN_FILE = 'token.json'  # Will be generated
    
    # GROQ API settings
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama3-70b-8192')
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {'pdf'}