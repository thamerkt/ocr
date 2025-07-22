from django.apps import AppConfig
import threading
import time

class OcrAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ocr_app'

    def ready(self):
        
