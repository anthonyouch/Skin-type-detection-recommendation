from flask import Flask, request, jsonify, send_file, send_from_directory, redirect, url_for
from flask_cors import CORS
from transformers import AutoModelForImageClassification, AutoFeatureExtractor
import torch
from PIL import Image
import io
from pymongo import MongoClient
import gridfs
from bson import ObjectId
import logging
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'your_secret_key'
CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)

# MongoDB setup
client = MongoClient('mongodb+srv://anthonyouchprogrammer:skincare123@cluster0.2wl7pco.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['skin_type_db']
fs = gridfs.GridFS(db)
image_collection = db['images']

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

class User(UserMixin):
    def __init__(self, username):
        self.username = username

    def get_id(self):
        return self.username

@login_manager.user_loader
def load_user(username):
    user = db['users'].find_one({"username": username})
    if user:
        return User(username=user['username'])
    return None

def preprocess_image(image):
    inputs = feature_extractor(images=image, return_tensors="pt")
    return inputs

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

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, port=5001)
