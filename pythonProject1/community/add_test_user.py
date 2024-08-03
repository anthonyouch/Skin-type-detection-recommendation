from pymongo import MongoClient
from bson import ObjectId

client = MongoClient('mongodb+srv://anthonyouchprogrammer:skincare123@cluster0.2wl7pco.mongodb.net/your_database_name?retryWrites=true&w=majority&appName=Cluster0')
db = client['your_database_name']
users_collection = db['users']

# Insert a sample user
sample_user = {
    '_id': ObjectId('60d5c496f3e2f74b9b5a92e2'),
    'username': 'test_user'
}

users_collection.insert_one(sample_user)
print("Sample user inserted")
