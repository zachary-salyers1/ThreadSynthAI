import os
from flask import Flask, render_template, request, jsonify, flash, make_response, redirect, url_for, session
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import tempfile
from functools import wraps
from dotenv import load_dotenv
from supabase_client import sign_up, sign_in, sign_out, get_user, save_thread, get_user_threads, get_thread, delete_thread, update_user_config, get_user_config
from asgiref.sync import async_to_sync

# Load environment variables
load_dotenv()

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-secret-key-here")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///threads.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'txt', 'pdf'}

db.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        user, error = async_to_sync(get_user)(session['access_token'])
        if error or not user:
            session.clear()
            flash('Session expired. Please log in again.', 'error')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        auth_data, error = async_to_sync(sign_in)(email, password)
        if error:
            flash(f'Login failed: {error}', 'error')
            return render_template('login.html')
        
        if auth_data and auth_data.get('session') and auth_data.get('user'):
            session['access_token'] = auth_data['session'].access_token
            session['user_id'] = auth_data['user'].id
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed: Invalid response from authentication server', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')
        
        user, error = async_to_sync(sign_up)(email, password)
        if error:
            flash(f'Registration failed: {error}', 'error')
            return render_template('register.html')
        
        flash('Registration successful! Please check your email to verify your account.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    success, error = async_to_sync(sign_out)(session.get('access_token'))
    session.clear()
    if error:
        flash(f'Logout failed: {error}', 'error')
    else:
        flash('Successfully logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Process document and create thread
            document_content = process_document(filepath)
            thread_data = create_thread(document_content)
            
            # Save thread to Supabase
            thread, error = async_to_sync(save_thread)(
                session['user_id'],
                thread_data['title'],
                [post['content'] for post in thread_data['posts']]
            )
            
            if error:
                return jsonify({'error': str(error)}), 500
            
            # Clean up
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'thread_id': thread['id']
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/thread/<thread_id>')
@login_required
def view_thread(thread_id):
    thread, error = async_to_sync(get_thread)(thread_id)
    if error or not thread:
        flash('Thread not found.', 'error')
        return redirect(url_for('index'))
    
    if thread['user_id'] != session['user_id']:
        flash('You do not have permission to view this thread.', 'error')
        return redirect(url_for('index'))
    
    return render_template('thread.html', thread=thread)

@app.route('/thread/<thread_id>/export', methods=['GET'])
@login_required
def export_thread(thread_id):
    thread, error = async_to_sync(get_thread)(thread_id)
    if error or not thread:
        flash('Thread not found.', 'error')
        return redirect(url_for('index'))
    
    if thread['user_id'] != session['user_id']:
        flash('You do not have permission to export this thread.', 'error')
        return redirect(url_for('index'))
    
    # Clean and format the thread content for export
    title = thread['title'].replace('**', '').replace('*', '').replace('"', '').strip()
    content = f"🧵 {title}\n\n"
    
    for post_content in thread['content']:
        cleaned_content = post_content.replace('**', '').replace('*', '').strip()
        content += f"{cleaned_content}\n\n"
    
    # Create response with the content
    response = make_response(content)
    response.headers['Content-Type'] = 'text/plain'
    response.headers['Content-Disposition'] = f'attachment; filename=thread_{thread_id}.txt'
    
    return response

@app.route('/config', methods=['GET', 'POST'])
@login_required
def configure():
    try:
        if request.method == 'POST':
            try:
                config_data = {
                    'model_name': request.form.get('model_name'),
                    'temperature': float(request.form.get('temperature', 0.7)),
                    'max_tokens': int(request.form.get('max_tokens', 1000)),
                    'chunk_size': int(request.form.get('chunk_size', 2000)),
                    'chunk_overlap': int(request.form.get('chunk_overlap', 100)),
                    'max_chunks': int(request.form.get('max_chunks', 10)),
                    'prompts': {
                        'title': request.form.get('title_prompt'),
                        'thread': request.form.get('thread_prompt')
                    }
                }
                
                print(f"Updating config for user {session['user_id']}")  # Debug log
                config, error = async_to_sync(update_user_config)(session['user_id'], config_data)
                if error:
                    print(f"Error updating config: {error}")  # Debug log
                    flash(f'Error updating configuration: {error}', 'error')
                else:
                    flash('Configuration updated successfully!', 'success')
            except (ValueError, TypeError) as e:
                print(f"Error processing form data: {str(e)}")  # Debug log
                flash(f'Error updating configuration: {str(e)}', 'error')
        
        # Get current config
        print(f"Getting config for user {session['user_id']}")  # Debug log
        config, error = async_to_sync(get_user_config)(session['user_id'])
        if error:
            print(f"Error loading config: {error}")  # Debug log
            flash(f'Error loading configuration: {error}', 'error')
            config = {
                'model_name': 'gpt-3.5-turbo',
                'temperature': 0.7,
                'max_tokens': 1000,
                'chunk_size': 2000,
                'chunk_overlap': 100,
                'max_chunks': 10,
                'prompts': {
                    'title': 'Summarize the following content into a thread title that would grab attention on X (formerly Twitter): {content}',
                    'thread': 'Create a single engaging thread post from this content. Format it as a thread with line breaks between key points, use emojis where appropriate, and make it conversational: {content}'
                }
            }
        
        return render_template('config.html', config=config)
    except Exception as e:
        print(f"Unexpected error in configure route: {str(e)}")  # Debug log
        flash('An unexpected error occurred. Please try again.', 'error')
        return render_template('config.html', config={})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
