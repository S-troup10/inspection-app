# Picked up automatically by gunicorn when run from the project directory.
# One worker (report generation is memory heavy on a 512MB instance) with
# threads so the page still responds while a report renders.
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
workers = 1
threads = 4
timeout = 300            # PDF generation can take minutes for big inspections
graceful_timeout = 60    # let in-flight email threads finish on redeploy
max_requests = 50        # recycle the worker periodically to cap memory growth
max_requests_jitter = 10
accesslog = "-"
errorlog = "-"
loglevel = "info"
