from celery import Celery

app = Celery('scraper_app', broker='redis://red-d1miasidbo4c73fbugg0:6379)

# Optional: If you want to schedule tasks
app.conf.beat_schedule = {
    'scrape-every-30-minutes': {
        'task': 'tasks.scrape_rne',
        'schedule': 30 * 60,  # 30 minutes in seconds
    },
}
app.conf.timezone = 'UTC'
