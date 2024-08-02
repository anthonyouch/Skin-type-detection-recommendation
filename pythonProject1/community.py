from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_pymongo import PyMongo
from bson import ObjectId
import logging

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
        return render_template('index.html', posts=posts_list)
    except Exception as e:
        logging.error(f"Error fetching posts: {e}")
        return "Error fetching posts", 500


@app.route('/add_post', methods=['POST'])
def add_post():
    try:
        posts_collection = mongo.db.get_collection(POSTS_COLLECTION)
        if posts_collection is None:
            logging.error("Posts collection does not exist")
            return "Posts collection not found", 500

        image_url = request.form['image_url']
        description = request.form['description']
        user_id = request.form['user_id']

        post = {
            'image_url': image_url,
            'description': description,
            'user_id': user_id
        }
        posts_collection.insert_one(post)
        return redirect(url_for('comm_index'))
    except Exception as e:
        logging.error(f"Error adding post: {e}")
        return "Error adding post", 500


@app.route('/add_comment', methods=['POST'])
def add_comment():
    try:
        post_id = request.form['post_id']
        comment_text = request.form['comment']
        user_id = request.form['user_id']  # This can be hardcoded for testing

        comment = {
            'post_id': ObjectId(post_id),
            'comment': comment_text,
            'user_id': user_id
        }

        comments_collection = mongo.db.get_collection(COMMENTS_COLLECTION)
        if comments_collection is None:
            logging.error("Comments collection does not exist")
            return "Comments collection not found", 500

        comments_collection.insert_one(comment)
        return redirect(url_for('comm_index'))
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


if __name__ == '__main__':
    app.run(debug=True)
