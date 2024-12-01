import os
from flask import Flask, render_template, request, jsonify, flash, make_response
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import tempfile

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///threads.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'txt', 'pdf'}

db.init_app(app)

from models import Thread, ThreadPost
from agents import process_document, create_thread
from config import get_config, update_config

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
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
            
            # Save thread to database
            thread = Thread(title=thread_data['title'])
            db.session.add(thread)
            db.session.flush()
            
            for post in thread_data['posts']:
                thread_post = ThreadPost(
                    thread_id=thread.id,
                    content=post['content']
                )
                db.session.add(thread_post)
            
            db.session.commit()
            
            # Clean up
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'thread_id': thread.id
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/thread/<int:thread_id>')
def view_thread(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    return render_template('thread.html', thread=thread)

@app.route('/thread/<int:thread_id>/export', methods=['GET'])
def export_thread(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    
    # Clean and format the thread content for export
    title = thread.title.replace('**', '').replace('*', '').replace('"', '').strip()
    content = f"🧵 {title}\n\n"
    
    for i, post in enumerate(thread.posts, 1):
        # Clean markdown from the post content
        cleaned_content = post.content.replace('**', '').replace('*', '').strip()
        content += f"{cleaned_content}\n\n"
    
    # Create response with the content
    response = make_response(content)
    response.headers['Content-Type'] = 'text/plain'
    response.headers['Content-Disposition'] = f'attachment; filename=thread_{thread_id}.txt'
    
    return response

@app.route('/config', methods=['GET', 'POST'])
def configure():
    if request.method == 'POST':
        try:
            config = update_config(
                model_name=request.form.get('model_name'),
                temperature=float(request.form.get('temperature', 0.7)),
                max_tokens=int(request.form.get('max_tokens', 1000)),
                chunk_size=int(request.form.get('chunk_size', 2000)),
                chunk_overlap=int(request.form.get('chunk_overlap', 100)),
                max_chunks=int(request.form.get('max_chunks', 10)),
                prompts={
                    'title': request.form.get('title_prompt'),
                    'thread': request.form.get('thread_prompt')
                } if request.form.get('title_prompt') and request.form.get('thread_prompt') else None
            )
            flash('Configuration updated successfully!', 'success')
        except (ValueError, TypeError) as e:
            flash(f'Error updating configuration: {str(e)}', 'error')
        
    config = get_config()
    return render_template('config.html', config=config)

with app.app_context():
    db.create_all()
