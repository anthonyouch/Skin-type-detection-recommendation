from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, session
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from pymongo import MongoClient
import logging
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'your_secret_key'
bcrypt = Bcrypt(app)
CORS(app)
login_manager = LoginManager()
login_manager.init_app(app)

# MongoDB setup
try:
    client = MongoClient('mongodb+srv://anthonyouchprogrammer:skincare123@cluster0.2wl7pco.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
    db = client['skin_type_db']
    users_collection = db['users']
    logging.info("Connected to MongoDB successfully")
except Exception as e:
    logging.error(f"Error connecting to MongoDB: {e}")

class User(UserMixin):
    def __init__(self, username):
        self.username = username

    def get_id(self):
        return self.username

@login_manager.user_loader
def load_user(username):
    user = users_collection.find_one({"username": username})
    if user:
        return User(username=user['username'])
    return None

@app.route('/')
def home():
    return send_from_directory('templates', 'index.html')

@app.route('/register')
def register_page():
    return send_from_directory('templates', 'register.html')

@app.route('/upload')
@login_required
def upload_page():
    return send_from_directory('templates', 'upload.html')

@app.route('/login')
def login_page():
    return send_from_directory('templates', 'login.html')

@app.route('/profile')
@login_required
def profile_page():
    return send_from_directory('templates', 'profile.html')

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

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    logging.info(f"Received login request for username: {username}")

    user = users_collection.find_one({'username': username})
    if user and bcrypt.check_password_hash(user['password'], password):
        login_user(User(username=user['username']))
        return jsonify({'message': 'Login successful'}), 200
    else:
        return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, port=5000)
