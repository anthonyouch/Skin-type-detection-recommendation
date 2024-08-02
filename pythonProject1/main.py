# pip install Flask Flask-CORS transformers torch torchvision torchaudio Pillow
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import AutoModelForImageClassification, AutoFeatureExtractor
import torch
from PIL import Image

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire app

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

    return jsonify({'skin_type': skin_type, 'recommendations': skincare_recommendations})


if __name__ == '__main__':
    app.run(debug=True)
