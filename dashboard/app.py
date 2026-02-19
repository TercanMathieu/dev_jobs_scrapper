from flask import Flask, render_template, jsonify
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# MongoDB connection
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URL)
db = client['job_scrapper']
jobs_collection = db['jobs']
logs_collection = db['logs']  # Collection pour les logs

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """Get dashboard stats"""
    total_jobs = jobs_collection.count_documents({})
    
    # Jobs des dernières 24h
    last_24h = datetime.now() - timedelta(hours=24)
    jobs_24h = jobs_collection.count_documents({'date': {'$gte': last_24h}})
    
    # Dernière mise à jour
    last_job = jobs_collection.find_one(sort=[('date', -1)])
    last_update = last_job['date'].strftime('%Y-%m-%d %H:%M:%S') if last_job else 'Jamais'
    
    return jsonify({
        'total_jobs': total_jobs,
        'jobs_24h': jobs_24h,
        'last_update': last_update
    })

@app.route('/api/jobs')
def get_jobs():
    """Get recent jobs"""
    jobs = list(jobs_collection.find().sort('date', -1).limit(50))
    
    result = []
    for job in jobs:
        result.append({
            'id': str(job['_id']),
            'name': job.get('name', 'N/A'),
            'company': job.get('company', 'N/A'),
            'location': job.get('location', 'N/A'),
            'link': job.get('link', '#'),
            'date': job.get('date', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify(result)

@app.route('/api/logs')
def get_logs():
    """Get recent logs from MongoDB"""
    logs = list(logs_collection.find().sort('timestamp', -1).limit(100))
    
    result = []
    for log in logs:
        result.append({
            'timestamp': log.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            'level': log.get('level', 'INFO'),
            'message': log.get('message', ''),
            'website': log.get('website', '')
        })
    
    return jsonify(result)

@app.route('/api/logs/live')
def get_live_logs():
    """Get only new logs for live updates"""
    # Logs des 5 dernières minutes
    last_5min = datetime.now() - timedelta(minutes=5)
    logs = list(logs_collection.find({'timestamp': {'$gte': last_5min}}).sort('timestamp', -1))
    
    result = []
    for log in logs:
        result.append({
            'timestamp': log.get('timestamp', datetime.now()).strftime('%H:%M:%S'),
            'level': log.get('level', 'INFO'),
            'message': log.get('message', ''),
            'website': log.get('website', '')
        })
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
