from flask import Flask, render_template, request, jsonify, send_from_directory
from model import ForgettingLLM
import json
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
llm = ForgettingLLM()

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Store chat history
CHATS_FILE = 'chats.json'

ALLOWED_EXTENSIONS = {'txt', 'csv', 'xlsx'}

def load_chats():
    if os.path.exists(CHATS_FILE):
        with open(CHATS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_chats(chats):
    with open(CHATS_FILE, 'w') as f:
        json.dump(chats, f)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    chat_id = data.get('chat_id', '')
    
    # Capture debug logs
    debug_logs = []
    
    def log_callback(message, type='info'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = {
            'message': message,
            'type': type,
            'timestamp': timestamp
        }
        debug_logs.append(log_entry)
        # Also print to server console
        color_map = {
            'info': '\033[94m',  # Blue
            'warning': '\033[93m',  # Yellow
            'error': '\033[91m'  # Red
        }
        end_color = '\033[0m'
        print(f"{color_map.get(type, '')}{timestamp} [{type.upper()}] {message}{end_color}")
    
    response = llm.generate_response(message, log_callback=log_callback)
    
    return jsonify({
        'response': response,
        'chat_id': chat_id,
        'debug_logs': debug_logs
    })

@app.route('/update-config', methods=['POST'])
def update_config():
    data = request.json
    llm.config.update_config(
        retain_mode=data.get('retain_mode'),
        check_before_llm=data.get('check_before_llm'),
        similarity_threshold=data.get('similarity_threshold'),
        model_name=data.get('model_name')
    )
    return jsonify({'status': 'success'})

@app.route('/chats', methods=['GET'])
def get_chats():
    chats = load_chats()
    return jsonify(chats)

@app.route('/upload-forgetting-set', methods=['POST'])
def upload_forgetting_set():
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'No files provided'})
    
    files = request.files.getlist('files')
    uploaded_items = []
    errors = []
    
    for file in files:
        if file.filename:
            try:
                filename = file.filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Save the file
                file.save(filepath)
                
                # Read the content and add to forgetting set
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Only process non-empty files
                        if llm.add_to_forgetting_set(content, filename):
                            uploaded_items.append(filename)
                        else:
                            errors.append(f"Failed to process {filename}")
                    else:
                        errors.append(f"Empty file: {filename}")
                
            except Exception as e:
                errors.append(f"Error processing {file.filename}: {str(e)}")
                # Try to clean up the file if it was saved
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except:
                        pass
    
    if uploaded_items:
        return jsonify({
            'success': True, 
            'uploaded': uploaded_items,
            'errors': errors if errors else None
        })
    else:
        return jsonify({
            'success': False, 
            'error': 'No files were uploaded successfully',
            'errors': errors
        })

@app.route('/get-forgetting-set')
def get_forgetting_set():
    try:
        # Ensure uploaded_files exists
        if not hasattr(llm, 'uploaded_files'):
            llm.uploaded_files = []
            
        # Verify files still exist and update list if needed
        valid_files = []
        for file in llm.uploaded_files:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file['filename'])
            if os.path.exists(filepath):
                valid_files.append(file)
            
        # If files are missing, try to reload from directory
        if len(valid_files) < len(llm.uploaded_files):
            load_existing_files()
            
        return jsonify({'items': llm.uploaded_files})
    except Exception as e:
        print(f"Error in get_forgetting_set: {e}")
        return jsonify({'items': []})

@app.route('/delete-forgetting-item/<int:item_id>', methods=['DELETE'])
def delete_forgetting_item(item_id):
    try:
        # Remove item from forgetting set
        llm.remove_from_forgetting_set(item_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Load existing files from uploads folder
def load_existing_files():
    if not hasattr(llm, 'uploaded_files'):
        llm.uploaded_files = []
    
    # Get list of files in uploads folder
    files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
             if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f))]
    
    # Add each file to the forgetting set if not already present
    for filename in files:
        # Check if file is already in uploaded_files
        if not any(item['filename'] == filename for item in llm.uploaded_files):
            try:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Only process non-empty files
                        success = llm.add_to_forgetting_set(content, filename)
                        if success:
                            print(f"Loaded existing file: {filename}")
                        else:
                            print(f"Failed to load file: {filename}")
            except Exception as e:
                print(f"Error loading existing file {filename}: {e}")

# Load existing files on startup
load_existing_files()

@app.route('/get-config', methods=['GET'])
def get_config():
    return jsonify({
        'retain_mode': llm.config.retain_mode,
        'check_before_llm': llm.config.check_before_llm,
        'similarity_threshold': llm.config.similarity_threshold,
        'model_name': llm.config.model_name
    })

if __name__ == '__main__':
    app.run(debug=True) 