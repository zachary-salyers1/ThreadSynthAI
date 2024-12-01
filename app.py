import os
from flask import Flask, render_template, request, jsonify, flash
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

with app.app_context():
    db.create_all()
