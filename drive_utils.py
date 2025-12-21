from google_drive_integration import GoogleDriveManager
from flask import current_app

drive_manager = None

def init_drive_manager(app):
    global drive_manager
    try:
        drive_manager = GoogleDriveManager(
            app.config['GOOGLE_DRIVE_CREDENTIALS_FILE'],
            app.config['GOOGLE_DRIVE_TOKEN_FILE']
        )
        # Test authentication
        if not drive_manager.service:
            raise RuntimeError("Google Drive authentication failed")
        return True
    except Exception as e:
        print(f"Google Drive initialization failed: {str(e)}")
        return False

def get_drive_manager():
    if not drive_manager:
        raise RuntimeError("Google Drive manager not initialized")
    return drive_manager

def get_drive_file_id(user_id, doc_id):
    from database import get_drive_file_id as db_get_drive_file_id
    return db_get_drive_file_id(user_id, doc_id)

def download_from_drive(drive_file_id, destination_path):
    return get_drive_manager().download_file(drive_file_id, destination_path)