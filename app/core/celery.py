from celery.schedules import crontab
from app.celery import app

app.conf.beat_schedule = {
    'generate-qr-codes-every-5-minutes': {
        'task': 'core.tasks.generate_qr_codes_for_upcoming_classes',
        'schedule': crontab(minute='*/5'),  # Chạy mỗi 5 phút
    },
} 