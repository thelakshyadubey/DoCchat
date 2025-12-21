import os
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

class GoogleDriveManager:
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(self, credentials_file, token_file):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        
        # Check for base64 encoded credentials in environment (for cloud deployment)
        if os.getenv('GOOGLE_CREDENTIALS_BASE64'):
            import base64
            import json
            try:
                creds_json = base64.b64decode(os.getenv('GOOGLE_CREDENTIALS_BASE64'))
                creds_info = json.loads(creds_json)
                creds = Credentials.from_authorized_user_info(creds_info, self.SCOPES)
            except Exception as e:
                print(f'Error loading credentials from environment: {e}')
        
        # Fallback to file-based authentication (for local development)
        if not creds and os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Only use local server flow if not in production
                if not os.getenv('RAILWAY_ENVIRONMENT'):
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                    
                    with open(self.token_file, 'w') as token:
                        token.write(creds.to_json())
                else:
                    raise Exception("Cannot authenticate in production without valid credentials")
        
        return build('drive', 'v3', credentials=creds)
    
    def get_or_create_user_folder(self, user_id):
        """Get or create a user-specific folder in Google Drive"""
        folder_name = f'User_{user_id}_Documents'
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        try:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields="files(id, name)"
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                return items[0]['id']
            else:
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.service.files().create(
                    body=file_metadata,
                    fields='id'
                ).execute()
                return folder['id']
        except HttpError as error:
            print(f'Google Drive folder operation failed: {error}')
            return None
    
    def upload_file(self, file_path, file_name, folder_id):
        """Upload with timeout and retry logic"""
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                file_metadata = {
                    'name': file_name,
                    'parents': [folder_id]
                }
                
                media = MediaFileUpload(
                    file_path, 
                    mimetype='application/pdf',
                    chunksize=1024*1024,  # 1MB chunks
                    resumable=True
                )
                
                request = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                )
                
                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        print(f"Upload progress: {int(status.progress() * 100)}%")
                
                return response.get('id')
                
            except HttpError as error:
                if attempt == max_retries - 1:
                    print(f'Final upload attempt failed: {error}')
                    return None
                print(f'Attempt {attempt + 1} failed, retrying...')
                time.sleep(retry_delay)
            except Exception as e:
                print(f'Unexpected upload error: {str(e)}')
                return None
    
    def download_file(self, file_id, destination_path):
        """Download a file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            with open(destination_path, 'wb') as file:
                file.write(request.execute())
            return True
        except HttpError as error:
            print(f'Google Drive download failed: {error}')
            return False