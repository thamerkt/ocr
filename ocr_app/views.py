import json
import io
import base64
import uuid
import threading
import logging
import re
import time
import socket
import os
import requests
from time import sleep
import pika

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

from confluent_kafka import Producer, Consumer
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from dotenv import set_key

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException, TimeoutException

import qrcode
import qrcode.image.svg

from .models import DocumentType, Document, IdentityVerification
from .serializars import DocumentSerializer, DocumentTypeSerializer
from .utils import (
    extract_text_from_image, 
    extract_face_from_id, 
    compare_faces, 
    detect_liveness,
    send_verification_email,
    encrypt_aes_ecb,
    get_local_ip
)
from .gemini_helper import GeminiProcessor

# Configure logging
logger = logging.getLogger(__name__)

def get_ip(request):
    if request.method == 'GET':
        ip = get_local_ip()
        return JsonResponse({"ip": ip})
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)



# Utility Functions
def delivery_report(err, msg):
    """Callback for Kafka message delivery confirmation"""
    if err is not None:
        logger.error(f"❌ Message delivery failed: {err}")
    else:
        logger.info(f"✅ Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")



def handle_file_upload(file):
    """Helper function to handle file uploads consistently"""
    file_name = default_storage.save(file.name, ContentFile(file.read()))
    return file_name, default_storage.path(file_name)

def verify_identity(detected_text):
    """Verifies user identity by comparing ID details"""
    try:
        if not detected_text:
            return {"error": "No text detected"}

        processor = GeminiProcessor()
        extracted_data = processor.extract_id_data(detected_text)

        expected_user_details = {
            "last_name": "Al Kathiri",
            "first_name": "Thamer"
        }

        is_data_verified = (
            extracted_data.get('last_name') == expected_user_details["last_name"] and 
            extracted_data.get('first_name') == expected_user_details["first_name"]
        )

        return {
            "status": "success",
            "data_verified": is_data_verified,
            "extracted_data": extracted_data
        }
    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}

def write_to_env():
    """Writes local IP to environment file"""
    local_ip = get_local_ip()
    set_key('.env', 'MY_SETTING', local_ip)

# Kafka Consumer Function
def send_failure_email(email, reason):
    logger.error(f"❌ {reason}")
    send_verification_email(email, False)

# Main event consumption function
import json
import logging
from time import sleep

# Configure logging for better tracking and monitoring
logger = logging.getLogger(__name__)

# Helper function to handle sending verification emails
def send_failure_email(email, reason):
    logger.error(f"❌ {reason}")
    send_verification_email(email, False)





def _verifyy(image_path, keycloak_user):
    """Verifies identity based on saved file paths and keycloak user."""
    try:
        # Extract text from ID image
        detected_text = extract_text_from_image(image_path)
        logger.info(f"Detected text: {detected_text}")

        # Process the extracted text
        processor = GeminiProcessor()
        extracted_data = processor.extract_id_data(detected_text)
        logger.info(f"Extracted data: {extracted_data}")

        # Verify against the provided keycloak_user
        result = verify_data(keycloak_user,extracted_data)
        result_str = result.content.decode('utf-8')
        result_json = json.loads(result_str)

        similarity_score = result_json.get('comparison', {}).get('similarity_score')
        logger.info(f"Similarity score: {similarity_score}")

        status = 'failed'
        if similarity_score is not None and similarity_score >= 60:
            status = 'passed'
            
        else:
            send_verification_email('kthirithamer1@gmail.com', False)

        return {
            'status': status,
            'similarity_score': similarity_score,
            'extracted_data': extracted_data
        }

    except Exception as e:
        logger.warning(f"⚠️ Verification failed: {e}")
        send_failure_email('kthirithamer1@gmail.com', f"Verification failed: {e}")
        raise e  # re-raise exception for handling outside


def _verify(event_data):
    try:
        extracted_data = event_data.get("extracted_data")
        detected_text = event_data.get("detected_text")
        keycloak_user = event_data.get("keycloak_user")

        if not all([extracted_data, detected_text, keycloak_user]):
            raise ValueError("Missing required fields in event")

        if not compare_faces_view(event_data):
            raise ValueError("Face comparison failed")
        print(extracted_data)
        print(keycloak_user)
        result = verify_data(keycloak_user, extracted_data)
        print(result.content) 
        result_content=result.content
        result_str = result_content.decode('utf-8')

# Parse the string to JSON
        result_json = json.loads(result_str)

# Access the similarity score
        similarity_score = result_json['comparison']['similarity_score']

        
        
        send_verification_email('kthirithamer1@gmail.com', False)
        logger.info(f"🎯 Score: {similarity_score}")
        return True

    except Exception as e:
        logger.warning(f"⚠️ Verification failed: {e}")
        send_failure_email('kthirithamer1@gmail.com', f"Verification failed: {e}")
        return False




# ViewSets
class DocumentTypeViewSet(viewsets.ModelViewSet):
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    permission_classes = [AllowAny]

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [AllowAny]

# Views
import logging
from django.http import JsonResponse

# Set up logging
logging.basicConfig(level=logging.INFO)

def validate_and_extract_image_data(request):
    """Validates the request and extracts image data."""
    if request.method != 'POST' or 'image' not in request.FILES:
        logging.warning("Invalid request: Either method is not POST or image is missing.")
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        image = request.FILES['image']
        # Assuming handle_file_upload returns the image name and path
        image_name, image_path = handle_file_upload(image)
        logging.info(f"Image uploaded successfully: {image_name}")

        # Extract text and face from the image
        detected_text = extract_text_from_image(image_path)
        face_detected = extract_face_from_id(image_path)

        # Assuming GeminiProcessor is a valid class for extracting data from the detected text
        processor = GeminiProcessor()
        extracted_data = processor.extract_id_data(detected_text)
        logging.info("Data extracted from image.")

        # Define required fields
        required_fields = [
            'first_name', 'last_name', 'date_of_birth', 'country', 'type',
            'id_number', 'father_name', 'place_of_birth', 'face_detected'
        ]

        # Check for missing fields
        missing_fields = [
            field for field in required_fields 
            if not extracted_data.get('identity_card', {}).get(field) 
            and extracted_data.get('identity_card', {}).get(field) != "null"
        ]

        is_data_verified = not bool(missing_fields)
        logging.info(f"Data verification result: {'Verified' if is_data_verified else 'Not Verified'}")

        # Prepare and return the response
        return JsonResponse({
            "status": "success",
            "data_verified": is_data_verified,
            "missing_fields": missing_fields,
            "extracted_data": extracted_data,
            "detected_text": detected_text,
            "face_detected": face_detected
        })

    except FileNotFoundError as e:
        logging.error(f"Error processing file: {str(e)}")
        return JsonResponse({'error': f'File error: {str(e)}'}, status=500)
    except Exception as e:
        logging.error(f"Unexpected error processing image: {str(e)}")
        return JsonResponse({'error': f'Error processing image: {str(e)}'}, status=500)

import json
import logging
from time import sleep
from confluent_kafka import Producer, Consumer, KafkaException

# Configure logging for better tracking and monitoring
logger = logging.getLogger(__name__)

# Kafka Configuration with optimizations

def publish_identity_verification_event(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method. Only POST is allowed.'}, status=405)

    if 'image' not in request.FILES or 'selfie' not in request.FILES:
        return JsonResponse({'error': 'Missing required files: image and/or selfie'}, status=402)

    keycloak_user = request.POST.get('keycloak_user')
    if not keycloak_user:
        return JsonResponse({'error': 'Missing keycloak_user in request data'}, status=402)

    image_name = selfie_name = None
    try:
        image = request.FILES['image']
        selfie = request.FILES['selfie']
        image_name, image_path = handle_file_upload(image)
        selfie_name, selfie_path = handle_file_upload(selfie)

        verification_result = _verifyy(image_path, keycloak_user)
        if verification_result.get('status') == 'failed':
            return JsonResponse({
                'status': 'failed',
                'step': 'identity_verification',
                'message': 'Identity verification failed',
                'similarity_score': verification_result.get('similarity_score')
            }, status=400)

        face_comparison_result = compare_faces_view({'image_path': image_path, 'selfie_path': selfie_path})
        if 'error' in face_comparison_result:
            return JsonResponse({
                'status': 'failed',
                'step': 'face_comparison',
                'message': 'Face comparison failed',
                'details': face_comparison_result['error']
            }, status=400)

        match_score = face_comparison_result.get('match_score')
        detected_text = extract_text_from_image(image_path)
        processor = GeminiProcessor()
        extracted_data = processor.extract_id_data(detected_text)

        event_data = {
            "image_name": image_name,
            "image_path": image_path,
            "selfie_name": selfie_name,
            "selfie_path": selfie_path,
            "detected_text": detected_text,
            "extracted_data": extracted_data,
            "keycloak_user": keycloak_user,
            "similarity_score": verification_result.get('similarity_score'),
            "face_match_score": match_score
        }

        # ======== Publish to RabbitMQ ============
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='host.docker.internal',
                    port=5672,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue='identity_verification_queue', durable=True)

            message = json.dumps(event_data)
            channel.basic_publish(
                exchange='',
                routing_key='identity_verification_queue',
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                )
            )
            connection.close()
            print("Message published to RabbitMQ.")
        except Exception as e:
            logger.error(f"Failed to publish message to RabbitMQ: {str(e)}")
            return JsonResponse({'error': f'Failed to publish to RabbitMQ: {str(e)}'}, status=500)

        # Optional: Send a success email
        send_verification_email('kthirithamer1@gmail.com', True)

        return JsonResponse({
            'status': 'success',
            'message': 'Identity verified and event published successfully',
            'image_path': image_path,
            'selfie_path': selfie_path,
            'similarity_score': verification_result.get('similarity_score'),
            'face_match_score': match_score
        }, status=200)

    except Exception as e:
        logger.error(f"Error in identity verification process: {str(e)}")
        if image_name and default_storage.exists(image_name):
            default_storage.delete(image_name)
        if selfie_name and default_storage.exists(selfie_name):
            default_storage.delete(selfie_name)
        return JsonResponse({'error': f'Error publishing event: {str(e)}'}, status=500)

def compare_faces_view(data):
    """Compares the face detected on the ID with the selfie uploaded (Kafka-friendly)."""
    try:
        selfie_path = data.get('selfie_path')
        image_path = data.get('image_path')

        if not selfie_path or not image_path:
            return {"error": "Missing selfie_path or image_path"}

        id_face = extract_face_from_id(image_path)
        selfie_face = extract_face_from_id(selfie_path)

        if not id_face or not selfie_face:
            return {"error": "Face not detected in one or both images"}

        match_score = compare_faces(image_path, selfie_path)

        return {
            "status": "success",
            "match_score": match_score,
            "match": match_score 
        }
    except Exception as e:
        return {"error": f"Face comparison failed: {str(e)}"}

def liveness_detection_view(request):
    """Performs liveness detection on the selfie."""
    if request.method != 'POST' or 'selfie' not in request.FILES:
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        selfie = request.FILES['selfie']
        selfie_name, selfie_path = handle_file_upload(selfie)
        is_live = detect_liveness(selfie_path)
        default_storage.delete(selfie_name)
        
        return JsonResponse({
            "status": "success",
            "liveness_detected": is_live
        })
    except Exception as e:
        return JsonResponse({"error": f"Liveness detection failed: {str(e)}"}, status=500)

@api_view(['POST'])
def generate_qr(request):
    """Generates a QR code for identity verification."""
    try:
        body = json.loads(request.body)
        user = body.get('user')
        local_ip = get_local_ip()  # Assuming this returns something like '192.168.1.120'

        if not user:
            return JsonResponse({"error": "User ID is required."}, status=400)

        write_to_env()

        # Correctly format the link using the actual user and IP values
        verification_link = f"frontendd-5mig.vercel.app/register/identity-verification/verification/document-type/{user}/{local_ip}"

        qr = qrcode.make(verification_link)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        buffer.seek(0)

        qr_data = base64.b64encode(buffer.getvalue()).decode()

        return JsonResponse({
            "qr_code": f"data:image/png;base64,{qr_data}",
            "link": verification_link
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)
    except Exception as e:
        logger.error(f"Failed to generate QR code: {e}")
        return JsonResponse(
            {"error": "Failed to generate QR code. Please try again later."},
            status=500
        )

def verify_face(request):
    """Verifies face match between ID and selfie"""
    if request.method != 'POST' or 'id_image' not in request.FILES or 'selfie' not in request.FILES:
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        id_image = request.FILES['id_image']
        selfie = request.FILES['selfie']
        
        id_image_name, id_image_path = handle_file_upload(id_image)
        selfie_name, selfie_path = handle_file_upload(selfie)
        
        face_match_result = compare_faces(id_image_path, selfie_path)
        
        default_storage.delete(id_image_name)
        default_storage.delete(selfie_name)
        
        return JsonResponse({'face_match_result': face_match_result})
    except Exception as e:
        return JsonResponse({'error': f'Error processing images: {str(e)}'}, status=500)


from django.http import JsonResponse
import requests
import logging

logger = logging.getLogger(__name__)

def verify_data(keycloak_user, input_data):
    """Verifies user data against profile"""
    if not keycloak_user:
        return JsonResponse({'error': 'keycloak_user not provided'}, status=400)

    if not input_data:
        return JsonResponse({'error': 'input_data not provided'}, status=400)

    try:
        response = requests.get(
            'https://kong-7e283b39dauspilq0.kongcloud.dev/profile/profil/', 
            params={'user': keycloak_user}
        )

        if response.status_code != 200:
            return JsonResponse(
                {'error': 'Failed to fetch profile data'}, 
                status=response.status_code
            )

        real_profile_data = response.json()

        processor = GeminiProcessor()
        comparison_result = processor.compare_input_with_profile(input_data,real_profile_data)

        logger.info("Comparison Result: %s", comparison_result)  # better than print

        return JsonResponse({"comparison": comparison_result})

    except Exception as e:
        logger.exception("Error during data verification")
        return JsonResponse({'error': str(e)}, status=500)


import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException, TimeoutException
from django.http import JsonResponse
from bs4 import BeautifulSoup



from django.views.decorators.csrf import csrf_exempt
import os
import csv
from django.http import JsonResponse
import requests
from io import StringIO
import unicodedata

def normalize(text):
    """Normalize text: lowercase, remove accents, unify spacing and punctuation."""
    if not text:
        return ''
    # Normalize Unicode (accents)
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    text = text.replace('-', ' ').replace('_', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

@csrf_exempt
def verify_company(request):
    """Verifies company from Google Sheets CSV export by region and company name."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method. Only POST requests are allowed.'})

    region_input = normalize(request.POST.get('region', ''))
    company_name_input = normalize(request.POST.get('company_name', ''))
    print("INPUT:")
    print(f"company_name_input: '{company_name_input}'")
    print(f"region_input: '{region_input}'")

    if not region_input or not company_name_input:
        return JsonResponse({'success': False, 'error': 'Region and company name are required.'})

    csv_url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTtbFiXn_42JNL8OX2KrvvL_CmRDn7F1UKyyswLukoIr_4yGv_7EheaUh0rUAeKEY77dSBNcohkXaab/pub?gid=1015846341&single=true&output=csv'

    try:
        response = requests.get(csv_url)
        if response.status_code != 200:
            return JsonResponse({'success': False, 'error': f'Failed to fetch Google Sheet CSV. Status: {response.status_code}'})

        csv_content = response.content.decode('utf-8')
        reader = csv.DictReader(StringIO(csv_content))

        matches = []
        for index, row in enumerate(reader):
            row_region = normalize(row.get('region', ''))

            # Check region match
            if region_input not in row_region:
                continue

            # Check company name in any of the relevant fields
            raw_names = [
                row.get('company_name_commercial', ''),
                row.get('company_name_arabic', ''),
                row.get('company_name_arabic_full', '')
            ]
            name_fields = [normalize(name) for name in raw_names if name]

            print(f"[Row {index}] Normalized names: {name_fields} | Region: '{row_region}'")

            if any(company_name_input in name for name in name_fields):
                matches.append(row)

        if matches:
            print(f"✅ Match found: {matches[0]}")
            return JsonResponse({'success': True, 'result': matches[0]})
        else:
            return JsonResponse({'success': False, 'error': f'Company \"{company_name_input}\" not found in region \"{region_input}\".'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error fetching or parsing Google Sheet: {str(e)}'})




# Verification API Views
def generate_qr_code(verification):
    """Generates QR code for verification"""
    verification_url = f"https://yourdomain.com/verify/{verification.id}/{verification.secret_code}/"
    img = qrcode.make(verification_url, image_factory=qrcode.image.svg.SvgImage)
    stream = io.BytesIO()
    img.save(stream)
    return base64.b64encode(stream.getvalue()).decode()

@api_view(['POST'])
def start_verification(request):
    """Starts a new identity verification session"""
    verification = IdentityVerification.objects.create(
        secret_code=str(uuid.uuid4()),
        expires_at=timezone.now() + timezone.timedelta(minutes=15)
    )
    
    return Response({
        'verification_id': str(verification.id),
        'qr_code': generate_qr_code(verification),
        'expires_at': verification.expires_at,
        'secret_code': verification.secret_code
    })

@api_view(['POST'])
def upload_documents(request, verification_id):
    """Handles document upload for verification"""
    try:
        verification = IdentityVerification.objects.get(
            id=verification_id,
            status__in=['pending', 'under_review']
        )
    except IdentityVerification.DoesNotExist:
        return Response({'error': 'Invalid verification session'}, status=status.HTTP_400_BAD_REQUEST)
    
    if verification.expires_at < timezone.now():
        verification.status = 'expired'
        verification.save()
        return Response({'error': 'Verification session expired'}, status=status.HTTP_400_BAD_REQUEST)
    
    document_front = request.FILES.get('document_front')
    document_back = request.FILES.get('document_back')
    selfie = request.FILES.get('selfie')
    
    if not document_front or not selfie:
        return Response({'error': 'Document front and selfie are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    verification.document_type = request.data.get('document_type', 'id_card')
    verification.document_number = request.data.get('document_number', '')
    verification.document_front.save(document_front.name, ContentFile(document_front.read()))
    
    if document_back:
        verification.document_back.save(document_back.name, ContentFile(document_back.read()))
    
    verification.selfie.save(selfie.name, ContentFile(selfie.read()))
    verification.status = 'under_review'
    verification.save()
    
    return Response({
        'status': verification.status,
        'verification_id': str(verification.id),
        'message': 'Documents uploaded successfully. Verification in progress.'
    })

@api_view(['POST'])
def verify_qr_code(request, verification_id, secret_code):
    """Verifies QR code for identity verification"""
    try:
        verification = IdentityVerification.objects.get(
            id=verification_id,
            secret_code=secret_code
        )
    except IdentityVerification.DoesNotExist:
        return Response({'error': 'Invalid verification code'}, status=status.HTTP_400_BAD_REQUEST)
    
    if verification.status == 'under_review':
        verification.status = 'approved'
        verification.verified_at = timezone.now()
        verification.save()
    
    return Response({
        'status': verification.status,
        'verification_id': str(verification.id),
        'verified_at': verification.verified_at
    })

@api_view(['GET'])
def check_status(request, verification_id):
    """Checks verification status"""
    try:
        verification = IdentityVerification.objects.get(id=verification_id)
    except IdentityVerification.DoesNotExist:
        return Response({'error': 'Verification not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'status': verification.status,
        'document_type': verification.document_type,
        'created_at': verification.created_at,
        'expires_at': verification.expires_at,
        'verified_at': verification.verified_at
    })

@api_view(['POST'])
def admin_update_status(request, verification_id):
    """Allows admin to update verification status"""
    try:
        verification = IdentityVerification.objects.get(id=verification_id)
    except IdentityVerification.DoesNotExist:
        return Response({'error': 'Verification not found'}, status=status.HTTP_404_NOT_FOUND)
    
    new_status = request.data.get('status')
    if new_status not in dict(IdentityVerification.VERIFICATION_STATUS).keys():
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    verification.status = new_status
    if new_status == 'approved':
        verification.verified_at = timezone.now()
    elif new_status == 'rejected':
        verification.rejection_reason = request.data.get('rejection_reason', '')
    verification.save()
    
    return Response({
        'status': verification.status,
        'verification_id': str(verification.id),
        'updated_at': timezone.now()
    })
