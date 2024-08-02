from flask import Flask, request, jsonify, send_from_directory
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from pymongo import MongoClient
import logging

app = Flask(__name__)
bcrypt = Bcrypt(app)
CORS(app)

# MongoDB setup
try:
    client = MongoClient('mongodb+srv://anthonyouchprogrammer:skincare123@cluster0.2wl7pco.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
    db = client['skin_type_db']
    users_collection = db['users']
    logging.info("Connected to MongoDB successfully")
except Exception as e:
    logging.error(f"Error connecting to MongoDB: {e}")

@app.route('/')
def home():
    return send_from_directory('templates', 'index.html')

@app.route('/register')
def register_page():
    return send_from_directory('templates', 'register.html')

@app.route('/upload')
def upload_page():
    return send_from_directory('templates', 'upload.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    password = data['password']

    logging.info(f"Received registration request for username: {username}")

    if users_collection.find_one({'username': username}):
        logging.error(f"Username {username} already exists")
        return jsonify({'error': 'Username already exists'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    try:
        users_collection.insert_one({'username': username, 'password': hashed_password})
        logging.info(f"User {username} registered successfully")
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        logging.error(f"Error inserting user into MongoDB: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, port=5000)
