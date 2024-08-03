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
from flask_pymongo import PyMongo
import io
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import certifi
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'
bcrypt = Bcrypt(app)
CORS(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

# MongoDB setup
try:
    client = MongoClient(
        'mongodb+srv://anthonyouchprogrammer:skincare123@cluster0.2wl7pco.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0',
        tlsCAFile=certifi.where())
    # client = MongoClient('mongodb+srv://anthonyouchprogrammer:skincare123@cluster0.2wl7pco.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
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

"""EVERYTHING BELOW IS FOR COMMUNITY PAGE /display_posts ONLY"""

# MongoDB configuration
MONGO_URI = 'mongodb+srv://anthonyouchprogrammer:skincare123@cluster0.2wl7pco.mongodb.net/your_database_name?retryWrites=true&w=majority&appName=Cluster0'
app.config["MONGO_URI"] = MONGO_URI

# Initialize PyMongo
mongo = PyMongo(app)

# Collection names
POSTS_COLLECTION = "posts"
COMMENTS_COLLECTION = "comments"

# Set up logging
logging.basicConfig(level=logging.INFO)

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/add_post', methods=['GET', 'POST'])
def add_post():
    print(request)
    if request.method == 'POST':
        try:
            if 'image_file' not in request.files:
                logging.error("No file part in the request")
                return "No file part", 400

            file = request.files['image_file']
            if file.filename == '':
                logging.error("No selected file")
                return "No selected file", 400

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                posts_collection = db[POSTS_COLLECTION]
                description = request.form['description']
                user_id = current_user.get_id()
                mbti = request.form['mbti']
                timestamp = datetime.now()

                post = {
                    'image_url': file_path,
                    'description': description,
                    'user_id': user_id,
                    'mbti': mbti,
                    'timestamp': timestamp
                }
                posts_collection.insert_one(post)
                return redirect(url_for('display_posts'))
            else:
                logging.error("File not allowed")
                return "File not allowed", 400
        except Exception as e:
            logging.error(f"Error adding post: {e}")
            return "Error adding post", 500
    return render_template('add_post.html')

@app.route('/add_comment', methods=['POST'])
def add_comment():
    try:
        post_id = request.form['post_id']
        comment_text = request.form['comment']
        user_id = request.form['user_id']
        mbti = request.form['mbti']
        timestamp = datetime.now()

        comment = {
            'post_id': ObjectId(post_id),
            'comment': comment_text,
            'user_id': user_id,
            'mbti': mbti,
            'timestamp': timestamp
        }

        comments_collection = db[COMMENTS_COLLECTION]
        comments_collection.insert_one(comment)
        return redirect(url_for('display_posts'))
    except Exception as e:
        logging.error(f"Error adding comment: {e}")
        return "Error adding comment", 500

@app.route('/get_comments/<post_id>')
def get_comments(post_id):
    try:
        comments_collection = db[COMMENTS_COLLECTION]
        comments = comments_collection.find({'post_id': ObjectId(post_id)})
        comments_list = list(comments)

        for comment in comments_list:
            comment['_id'] = str(comment['_id'])
            comment['post_id'] = str(comment['post_id'])
            comment['time_stamp'] = comment.get('timestamp', datetime.now())

        return jsonify(comments_list)
    except Exception as e:
        logging.error(f"Error fetching comments: {e}")
        return "Error fetching comments", 500

@app.route('/search', methods=['GET'])
def search():
    keyword = request.args.get('keyword', '')
    try:
        posts_collection = db.get_collection(POSTS_COLLECTION)
        comments_collection = db.get_collection(COMMENTS_COLLECTION)

        if posts_collection is None or comments_collection is None:
            logging.error("Collections do not exist")
            return "Collections not found", 500

        # Search posts by keyword in mbti field
        posts = posts_collection.find({'mbti': {'$regex': keyword, '$options': 'i'}})
        posts_list = []

        for post in posts:
            post_comments = list(comments_collection.find({'post_id': post['_id']}))
            post['comments'] = post_comments
            post['timestamp'] = post.get('timestamp', datetime.now())
            posts_list.append(post)

        return render_template('display_posts.html', posts=posts_list, keyword=keyword)
    except Exception as e:
        logging.error(f"Error during search: {e}")
        return "Error during search", 500


        return render_template('display_posts.html', posts=posts_list, keyword=keyword)
    except Exception as e:
        logging.error(f"Error during search: {e}")
        return "Error during search", 500


@app.route('/display_posts', methods=['GET', 'POST'])
def display_posts():
    print("get request!")
    try:
        keyword = request.args.get('keyword', '')
        if keyword:
            posts = db[POSTS_COLLECTION].find({'mbti': {'$regex': keyword, '$options': 'i'}})
        else:
            posts = db[POSTS_COLLECTION].find()

        posts_list = []
        for post in posts:
            post_comments = list(db[COMMENTS_COLLECTION].find({'post_id': post['_id']}))
            post['comments'] = post_comments
            post['timestamp'] = post.get('timestamp', datetime.now())
            if 'mbti' not in post:
                post['mbti'] = "DRPT"
            post_return = {
                "user_id": post['user_id'],
                'create_time': str(post['timestamp']),
                'post': {
                    "content": post['description']
                },
                "skin_tag": post['mbti']
            }
            posts_list.append(post_return)

        print(posts_list)
        return {
        'statusCode': 200,
        'body': json.dumps(posts_list)
        }
    except Exception as e:
        logging.error(f"Error fetching posts: {e}")
        return "Error fetching posts", 500



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, port=5001)
