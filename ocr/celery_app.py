from celery import Celery

app = Celery('scraper_app', broker='redis://host.docker.internal:6379/0')

# Optional: If you want to schedule tasks
app.conf.beat_schedule = {
    'scrape-every-30-minutes': {
        'task': 'tasks.scrape_rne',
        'schedule': 30 * 60,  # 30 minutes in seconds
    },
}
app.conf.timezone = 'UTC'
