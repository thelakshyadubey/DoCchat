from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
import os
import traceback
from pathlib import Path
import stat
from auth import User
from database import get_db, init_db, get_user_documents, add_document, get_document_path, delete_document
from document_processor import process_document
from chatbot import DocumentChatbot
from config import Config
from dotenv import load_dotenv
from google_drive_integration import GoogleDriveManager
from drive_utils import init_drive_manager, get_drive_file_id, get_drive_manager
from concurrent.futures import ThreadPoolExecutor
import threading
from werkzeug.middleware.profiler import ProfilerMiddleware

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
load_dotenv()

# Add this before app.run()
if os.getenv('FLASK_ENV') == 'development':
    app.wsgi_app = ProfilerMiddleware(
        app.wsgi_app,
        profile_dir='./profiler'
    )

# Add at the top of your app.py
executor = ThreadPoolExecutor(4)  # Adjust based on your server capacity

# Configuration
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['EMBEDDING_FOLDER'] = os.path.join(os.getcwd(), 'embeddings')
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['EXPLAIN_TEMPLATE_LOADING'] = False

# Initialize Google Drive
# Initialize Google Drive - add error handling
try:
    if not init_drive_manager(app):
        print("WARNING: Failed to initialize Google Drive. Continuing without it.")
        drive_manager = None
    else:
        drive_manager = GoogleDriveManager(
            app.config['GOOGLE_DRIVE_CREDENTIALS_FILE'],
            app.config['GOOGLE_DRIVE_TOKEN_FILE']
        )
except Exception as e:
    print(f"WARNING: Google Drive initialization failed: {e}")
    drive_manager = None

def setup_directories():
    """Create required directories with proper permissions"""
    try:
        for folder in [app.config['UPLOAD_FOLDER'], app.config['EMBEDDING_FOLDER']]:
            os.makedirs(folder, exist_ok=True)
            os.chmod(folder, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            
            test_file = os.path.join(folder, 'permission_test.txt')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
        print("✓ Directories initialized successfully")
        return True
    except Exception as e:
        print(f"🚨 Directory setup failed: {str(e)}")
        traceback.print_exc()
        return False

# Initialize directories
try:
    if not setup_directories():
        print("WARNING: Directory setup failed. May need persistent volumes on Railway.")
except Exception as e:
    print(f"WARNING: Directory initialization skipped: {e}")

# Initialize database
init_db()

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT * FROM users WHERE username = %s", (username,)
            )
            user = cur.fetchone()
            
            if user and check_password_hash(user[3], password):
                user_obj = User(id_=user[0], username=user[1], email=user[2])
                login_user(user_obj)
                return redirect(url_for('dashboard'))
        finally:
            cur.close()
            conn.close()
        
        return render_template('login.html', error="Invalid username or password")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        try:
            User.create(username, email, password)
            return redirect(url_for('login'))
        except Exception as e:
            return render_template('register.html', error=str(e))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    documents = get_user_documents(current_user.id)
    return render_template('dashboard.html', documents=documents)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    files = request.files.getlist('file')
    uploaded_files = []
    
    def process_upload(file):
        try:
            filename = secure_filename(file.filename)
            user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
            os.makedirs(user_upload_dir, exist_ok=True)
            filepath = os.path.join(user_upload_dir, filename)
            file.save(filepath)
            
            # Offload Drive upload to separate thread
            future = executor.submit(
                upload_to_drive_and_db,
                filepath, filename, current_user.id
            )
            return future.result(timeout=300)  # 5 minute timeout
            
        except Exception as e:
            print(f"Upload failed: {str(e)}")
            traceback.print_exc()
            return None

    # Process files in parallel
    results = list(executor.map(process_upload, files))
    uploaded_files = [r for r in results if r is not None]
    
    return jsonify({
        'success': bool(uploaded_files), 
        'files': uploaded_files,
        'message': f"Uploaded {len(uploaded_files)} files"
    })

def upload_to_drive_and_db(filepath, filename, user_id):
    """Separate function for Drive and DB operations"""
    drive_manager = get_drive_manager()
    folder_id = drive_manager.get_or_create_user_folder(user_id)
    if not folder_id:
        raise Exception("Failed to create Google Drive folder")
    
    drive_file_id = drive_manager.upload_file(filepath, filename, folder_id)
    if not drive_file_id:
        raise Exception("Failed to upload to Google Drive")
    
    doc_id = add_document(user_id, filename, filepath, drive_file_id)
    
    # Process document in background
    executor.submit(
        process_document_background,
        filepath, user_id, doc_id
    )
    
    return filename

def process_document_background(filepath, user_id, doc_id):
    """Background processing of documents"""
    try:
        process_document_func = get_process_document()
        if not process_document_func(filepath, user_id, doc_id):
            print(f"Background processing failed for doc {doc_id}")
    except Exception as e:
        print(f"Background processing error: {str(e)}")

@app.route('/preview/<int:doc_id>')
@login_required
def preview(doc_id):
    drive_file_id = get_drive_file_id(current_user.id, doc_id)
    if not drive_file_id:
        return "Document not found", 404
    return redirect(f"https://drive.google.com/file/d/{drive_file_id}/preview")

@app.route('/delete/<int:doc_id>', methods=['DELETE'])
@login_required
def delete_file(doc_id):
    try:
        filepath = get_document_path(current_user.id, doc_id)
        if not filepath:
            return jsonify({'success': False, 'error': 'Document not found'}), 404

        deleted_filepath = delete_document(current_user.id, doc_id)
        if not deleted_filepath:
            return jsonify({'success': False, 'error': 'Failed to delete from database'}), 500

        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Failed to delete file {filepath}: {str(e)}")
                return jsonify({'success': False, 'error': f'File deletion failed: {str(e)}'}), 500

        try:
            delete_embeddings_func = get_delete_document_embeddings()
            delete_embeddings_func(current_user.id, doc_id)
        except Exception as e:
            print(f"Failed to delete embeddings for doc {doc_id}: {str(e)}")

        return jsonify({'success': True, 'message': 'Document deleted successfully'})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
def get_delete_document_embeddings():
    from document_processor import delete_document_embeddings
    return delete_document_embeddings

@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'POST':
        doc_ids = request.form.getlist('documents')
        if not doc_ids:
            return redirect(url_for('dashboard'))
        return render_template('chat.html', doc_ids=doc_ids)
    return redirect(url_for('dashboard'))

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json()
    try:
        chatbot = DocumentChatbot(current_user.id, data.get('doc_ids', []))
        response = chatbot.generate_response(data.get('query'))
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<int:doc_id>')
@login_required
def download(doc_id):
    filepath = get_document_path(current_user.id, doc_id)
    if filepath and os.path.exists(filepath):
        return send_from_directory(
            os.path.dirname(filepath), 
            os.path.basename(filepath), 
            as_attachment=True
        )
    return "Document not found", 404

def get_process_document():
    from document_processor import process_document
    return process_document

def get_delete_document_embeddings():
    from document_processor import delete_document_embeddings
    return delete_document_embeddings

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    
    if not setup_directories():
        print("Warning: Directory setup failed, continuing anyway for cloud deployment")
    
    app.run(debug=debug, host='0.0.0.0', port=port)