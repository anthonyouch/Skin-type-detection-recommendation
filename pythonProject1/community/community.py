from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_pymongo import PyMongo
from bson import ObjectId
import logging
import os
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__)

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

@app.route('/')
def index():
    try:
        posts_collection = mongo.db.get_collection(POSTS_COLLECTION)
        if posts_collection is None:
            logging.error("Posts collection does not exist")
            return "Posts collection not found", 500

        posts = posts_collection.find()
        posts_list = list(posts)  # Convert cursor to list
        if not posts_list:
            logging.info("No posts found in the collection.")

        # Attach comments to posts
        for post in posts_list:
            post_comments = mongo.db.get_collection(COMMENTS_COLLECTION).find({'post_id': post['_id']})
            post['comments'] = list(post_comments)

        return render_template('comm_index.html', posts=posts_list)
    except Exception as e:
        logging.error(f"Error fetching posts: {e}")
        return "Error fetching posts", 500

@app.route('/add_post', methods=['POST'])
def add_post():
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

            posts_collection = mongo.db.get_collection(POSTS_COLLECTION)
            if posts_collection is None:
                logging.error("Posts collection does not exist")
                return "Posts collection not found", 500

            description = request.form['description']
            user_id = request.form['user_id']
            mbti = get_user_mbti(user_id)
            avatar_url = get_user_avatar(user_id)

            post = {
                'image_url': filename,  # Save only the filename
                'description': description,
                'user_id': user_id,
                'mbti': mbti,
                'avatar_url': avatar_url
            }
            posts_collection.insert_one(post)
            return redirect(url_for('index'))
        else:
            logging.error("File not allowed")
            return "File not allowed", 400
    except Exception as e:
        logging.error(f"Error adding post: {e}")
        return "Error adding post", 500

@app.route('/add_comment', methods=['POST'])
def add_comment():
    try:
        post_id = request.form['post_id']
        comment_text = request.form['comment']
        user_id = request.form['user_id']
        mbti = get_user_mbti(user_id)
        avatar_url = get_user_avatar(user_id)

        comment = {
            'post_id': ObjectId(post_id),
            'comment': comment_text,
            'user_id': user_id,
            'mbti': mbti,
            'avatar_url': avatar_url
        }

        comments_collection = mongo.db.get_collection(COMMENTS_COLLECTION)
        if comments_collection is None:
            logging.error("Comments collection does not exist")
            return "Comments collection not found", 500

        comments_collection.insert_one(comment)
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error adding comment: {e}")
        return "Error adding comment", 500

@app.route('/get_comments/<post_id>')
def get_comments(post_id):
    try:
        comments_collection = mongo.db.get_collection(COMMENTS_COLLECTION)
        if comments_collection is None:
            logging.error("Comments collection does not exist")
            return "Comments collection not found", 500

        comments = comments_collection.find({'post_id': ObjectId(post_id)})
        comments_list = list(comments)

        # Convert ObjectId to string for JSON serialization
        for comment in comments_list:
            comment['_id'] = str(comment['_id'])
            comment['post_id'] = str(comment['post_id'])

        return jsonify(comments_list)
    except Exception as e:
        logging.error(f"Error fetching comments: {e}")
        return "Error fetching comments", 500

@app.route('/search', methods=['GET'])
def search():
    keyword = request.args.get('keyword', '')
    try:
        posts_collection = mongo.db.get_collection(POSTS_COLLECTION)
        comments_collection = mongo.db.get_collection(COMMENTS_COLLECTION)

        if posts_collection is None or comments_collection is None:
            logging.error("Collections do not exist")
            return "Collections not found", 500

        # Search posts
        posts = posts_collection.find({'description': {'$regex': keyword, '$options': 'i'}})
        posts_list = list(posts)

        # Search comments
        comments = comments_collection.find({'comment': {'$regex': keyword, '$options': 'i'}})
        comments_list = list(comments)

        # Attach comments to posts
        for post in posts_list:
            post_comments = comments_collection.find({'post_id': post['_id']})
            post['comments'] = list(post_comments)

        return render_template('search_results.html', posts=posts_list, comments=comments_list, keyword=keyword)
    except Exception as e:
        logging.error(f"Error during search: {e}")
        return "Error during search", 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
