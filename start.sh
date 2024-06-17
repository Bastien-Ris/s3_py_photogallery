#!/bin/sh 
#
celery -A s3_pygallery:celery worker >> celery.log &
gunicorn s3_pygallery:app >> gunicorn.log & 
