from django.apps import AppConfig
import threading
import time

class OcrAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ocr_app'

    def ready(self):
        # Import inside ready() to avoid issues with app registry not ready
        from .tasks import continuous_scraping

        def start_scraping():
            print("Starting continuous scraping task...")
            continuous_scraping.delay()

        # Optional small delay to ensure Django startup is smooth
        time.sleep(1)

        # Start Celery task in a daemon thread (won't block shutdown)
        thread = threading.Thread(target=start_scraping, daemon=True)
        thread.start()
