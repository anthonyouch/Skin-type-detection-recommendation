from flask import Flask, request, jsonify, send_file, send_from_directory, render_template, redirect, url_for, session
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from pymongo import MongoClient
import gridfs
from bson import ObjectId
import logging
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from transformers import AutoModelForImageClassification, AutoFeatureExtractor
import torch
from PIL import Image
import io

app = Flask(__name__)
app.secret_key = 'your_secret_key'
bcrypt = Bcrypt(app)
CORS(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'  # Add this line

# MongoDB setup
try:
    client = MongoClient('mongodb+srv://anthonyouchprogrammer:skincare123@cluster0.2wl7pco.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
    db = client['skin_type_db']
    users_collection = db['users']
    fs = gridfs.GridFS(db)
    image_collection = db['images']
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

# Image classification setup
model_name = "dima806/skin_types_image_detection"
model = AutoModelForImageClassification.from_pretrained(model_name)
feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)

class_labels = {
    0: "Oily",
    1: "Dry",
    2: "Combination",
    3: "Normal"
}

recommendations = {
    "Oily": [
        "Use oil-free moisturizers",
        "Look for products with salicylic acid",
        "Avoid heavy creams"
    ],
    "Dry": [
        "Use rich, hydrating creams",
        "Look for products with hyaluronic acid",
        "Avoid alcohol-based products"
    ],
    "Combination": [
        "Use light moisturizers",
        "Look for balanced skincare products",
        "Avoid heavy oils"
    ],
    "Normal": [
        "Maintain a regular cleansing routine",
        "Use balanced moisturizers",
        "Avoid over-exfoliation"
    ]
}

def preprocess_image(image):
    inputs = feature_extractor(images=image, return_tensors="pt")
    return inputs

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    image = Image.open(file.stream)
    inputs = preprocess_image(image)

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits

    predicted_class = logits.argmax(-1).item()
    skin_type = class_labels[predicted_class]
    skincare_recommendations = recommendations[skin_type]

    # Save the image in MongoDB using GridFS
    file_id = fs.put(file.stream, filename=file.filename, content_type=file.content_type)

    # Save the record in MongoDB
    image_record = {
        'file_id': file_id,
        'filename': file.filename,
        'skin_type': skin_type
    }
    image_collection.insert_one(image_record)

    logging.info(f"Stored file with ID: {file_id}")

    return jsonify({'skin_type': skin_type, 'recommendations': skincare_recommendations, 'image_url': f"/uploads/{file_id}"})

@app.route('/uploads/<file_id>')
def uploaded_file(file_id):
    try:
        logging.info(f"Fetching file with ID: {file_id}")
        grid_out = fs.get(ObjectId(file_id))
        return send_file(grid_out, mimetype=grid_out.content_type)
    except Exception as e:
        logging.error(f"Error fetching file: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/all_images', methods=['GET'])
@login_required
def all_images():
    images = image_collection.find()
    image_list = []
    for image in images:
        image_list.append({
            'file_id': str(image['file_id']),
            'filename': image['filename'],
            'skin_type': image['skin_type'],
            'image_url': f"/uploads/{image['file_id']}"
        })
    return jsonify(image_list)

@app.route('/user_info', methods=['GET'])
@login_required
def user_info():
    user = users_collection.find_one({"username": current_user.username})
    if user:
        return jsonify({'username': user['username']})
    return jsonify({'error': 'User not found'}), 404

@app.route('/user_images', methods=['GET'])
@login_required
def user_images():
    images = image_collection.find({"username": current_user.username})
    image_list = []
    for image in images:
        image_list.append({
            'file_id': str(image['file_id']),
            'filename': image['filename'],
            'skin_type': image['skin_type'],
            'image_url': f"/uploads/{image['file_id']}"
        })
    return jsonify(image_list)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, port=5001)
