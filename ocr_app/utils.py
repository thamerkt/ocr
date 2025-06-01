import boto3
import os
from dotenv import load_dotenv
from PIL import Image
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import hashlib
import socket
from django.core.mail import send_mail
from django.conf import settings

# Load credentials


import os

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')  # Default region fallback


# Safe Rekognition client
rekognition_client = boto3.client(
    'rekognition',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        return f"Error while getting local IP: {e}"

def pad(s):
    try:
        pad_len = 16 - (len(s) % 16)
        return s + chr(pad_len) * pad_len
    except Exception as e:
        return f"Error in padding: {e}"

def encrypt_aes_ecb():
    try:
        secret_key = "mySecretKey123"
        ip = get_local_ip()
        key = hashlib.sha256(secret_key.encode()).digest()[:16]
        cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
        encryptor = cipher.encryptor()
        padded_text = pad(ip)
        ct = encryptor.update(padded_text.encode()) + encryptor.finalize()
        return base64.b64encode(ct).decode()
    except Exception as e:
        return f"Encryption error: {e}"

def extract_text_from_image(image_path):
    try:
        with open(image_path, 'rb') as image_file:
            image_bytes = image_file.read()

        response = rekognition_client.detect_text(Image={'Bytes': image_bytes})
        extracted_text = [item['DetectedText'] for item in response['TextDetections']]
        return extracted_text if extracted_text else "No text detected"
    except Exception as e:
        return f"Error extracting text from image: {e}"

def extract_face_from_id(image_path):
    try:
        with open(image_path, 'rb') as image_file:
            image_bytes = image_file.read()

        response = rekognition_client.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )

        return "Face detected" if response['FaceDetails'] else "No face found"
    except Exception as e:
        return f"Error detecting face in image: {e}"

def compare_faces(id_image_path, selfie_path):
    try:
        with open(id_image_path, 'rb') as id_file:
            id_image_bytes = id_file.read()
        with open(selfie_path, 'rb') as selfie_file:
            selfie_bytes = selfie_file.read()

        response = rekognition_client.compare_faces(
            SourceImage={'Bytes': id_image_bytes},
            TargetImage={'Bytes': selfie_bytes},
            SimilarityThreshold=85
        )

        if response['FaceMatches']:
            return f"Match Confidence: {response['FaceMatches'][0]['Similarity']}%"
        else:
            return "No match found"
    except Exception as e:
        return f"Error comparing faces: {e}"

def detect_liveness(image_path):
    try:
        with open(image_path, 'rb') as img:
            image_bytes = img.read()

        response = rekognition_client.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )

        if response['FaceDetails']:
            confidence = response['FaceDetails'][0].get('Confidence', 0)
            return confidence > 80

        return False
    except Exception as e:
        return f"Liveness detection error: {str(e)}"

def send_verification_email(to_email, state):
    try:
        subject = 'Your Account is Verified' if state else 'Your Verification Failed'
        message = 'Hello, your verification is successful' if state else 'Your data was not verified successfully'
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email])
        return "Email sent successfully"
    except Exception as e:
        return f"Error sending email: {str(e)}"
