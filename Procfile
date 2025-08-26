# Heroku Procfile for TFT Webapp
# Defines how Heroku should run the application

# Web dyno: Run the Streamlit app
web: streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false

# Worker dyno (optional): For background data processing tasks
# worker: python -m celery worker --app=data_collection:app --loglevel=info

# Release phase: Run database migrations before deploying new version
release: python deployment/migrate_to_production.py

# Scheduler (optional): For periodic data collection tasks
# scheduler: python -c "import schedule; import time; import data_collection; schedule.every(6).hours.do(data_collection.collect_recent_matches); while True: schedule.run_pending(); time.sleep(60)"