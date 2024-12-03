from flask import Flask, render_template, request, jsonify
from model import ForgettingLLM
import json
import os

app = Flask(__name__)
llm = ForgettingLLM()

# Store chat history
CHATS_FILE = 'chats.json'

def load_chats():
    if os.path.exists(CHATS_FILE):
        with open(CHATS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_chats(chats):
    with open(CHATS_FILE, 'w') as f:
        json.dump(chats, f)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    chat_id = data.get('chat_id', '')
    
    response = llm.generate_response(message)
    
    return jsonify({
        'response': response,
        'chat_id': chat_id
    })

@app.route('/update-config', methods=['POST'])
def update_config():
    data = request.json
    llm.config.update_config(
        check_before_llm=data.get('check_before_llm'),
        similarity_threshold=data.get('similarity_threshold'),
        model_name=data.get('model_name')
    )
    return jsonify({'status': 'success'})

@app.route('/chats', methods=['GET'])
def get_chats():
    chats = load_chats()
    return jsonify(chats)

if __name__ == '__main__':
    app.run(debug=True) 