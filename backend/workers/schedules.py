from __future__ import annotations

from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    "crawl-all-sources-every-1h": {
        "task": "workers.tasks.crawl.crawl_all_sources",
        "schedule": crontab(minute=0),  # top of every hour
    },
    "rebuild-feeds-every-30min": {
        "task": "workers.tasks.feeds.rebuild_all_feeds",
        "schedule": crontab(minute="*/30"),
    },
    "expire-past-events-daily": {
        "task": "workers.tasks.crawl.expire_past_events",
        "schedule": crontab(hour=3, minute=0),
    },
}

