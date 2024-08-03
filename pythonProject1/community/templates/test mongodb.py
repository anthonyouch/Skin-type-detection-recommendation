from pymongo import MongoClient

# MongoDB connection string
MONGO_URI = 'mongodb+srv://anthonyouchprogrammer:skincare123@cluster0.2wl7pco.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
DATABASE_NAME = 'skin_care'  # Replace with your actual database name

try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]  # Specify the database name
    # Test the connection
    db.command('ping')
    print("MongoDB connection successful!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
