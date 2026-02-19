from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# MongoDB connection
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URL)
db = client.jobs_database
jobs_collection = db.jobs_collection
logs_collection = db.logs

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/jobs')
def jobs_page():
    return render_template('jobs.html')

@app.route('/api/stats')
def get_stats():
    """Get dashboard stats"""
    total_jobs = jobs_collection.count_documents({})
    
    # Jobs des dernières 24h
    last_24h = datetime.now() - timedelta(hours=24)
    jobs_24h = jobs_collection.count_documents({'date_scraped': {'$gte': last_24h}})
    
    # Dernière mise à jour
    last_job = jobs_collection.find_one(sort=[('date_scraped', -1)])
    last_update = last_job['date_scraped'].strftime('%Y-%m-%d %H:%M:%S') if last_job and 'date_scraped' in last_job else 'Jamais'
    
    # Stats avancées
    all_techs = jobs_collection.distinct('technologies')
    companies = jobs_collection.distinct('company')
    
    # Répartition par seniorité
    seniority_stats = {}
    for level in ['junior', 'mid', 'senior', 'lead', 'expert', 'not_specified']:
        count = jobs_collection.count_documents({'seniority': level})
        if count > 0:
            seniority_stats[level] = count
    
    # Répartition par type de contrat
    contract_stats = {}
    for ctype in ['cdi', 'cdd', 'freelance', 'internship', 'apprenticeship', 'not_specified']:
        count = jobs_collection.count_documents({'contract_type': ctype})
        if count > 0:
            contract_stats[ctype] = count
    
    # Jobs remote
    remote_count = jobs_collection.count_documents({'remote': True})
    
    return jsonify({
        'total_jobs': total_jobs,
        'jobs_24h': jobs_24h,
        'last_update': last_update,
        'unique_technologies': len(all_techs),
        'unique_companies': len(companies),
        'seniority_breakdown': seniority_stats,
        'contract_breakdown': contract_stats,
        'remote_jobs': remote_count
    })

@app.route('/api/jobs')
def get_jobs():
    """Get jobs with advanced filters"""
    # Pagination
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    skip = (page - 1) * per_page
    
    # Build query from filters
    query = {}
    
    # Technologies filter (AND logic - must have all selected)
    techs = request.args.getlist('technologies')
    if techs:
        query['technologies'] = {'$all': [t.lower() for t in techs]}
    
    # Seniority filter
    seniority = request.args.getlist('seniority')
    if seniority:
        query['seniority'] = {'$in': [s.lower() for s in seniority]}
    
    # Contract type filter
    contracts = request.args.getlist('contract_type')
    if contracts:
        query['contract_type'] = {'$in': [c.lower() for c in contracts]}
    
    # Remote filter
    remote = request.args.get('remote')
    if remote is not None:
        query['remote'] = remote.lower() == 'true'
    
    # Company filter
    company = request.args.get('company')
    if company:
        query['company'] = {'$regex': company, '$options': 'i'}
    
    # Search text
    search = request.args.get('search')
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}},
            {'company': {'$regex': search, '$options': 'i'}}
        ]
    
    # Date range
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query['$gte'] = datetime.fromisoformat(date_from)
        if date_to:
            date_query['$lte'] = datetime.fromisoformat(date_to)
        query['date_scraped'] = date_query
    
    # Get total count for pagination
    total = jobs_collection.count_documents(query)
    
    # Get jobs
    jobs = list(jobs_collection.find(query).sort('date_scraped', -1).skip(skip).limit(per_page))
    
    result = []
    for job in jobs:
        result.append({
            'id': str(job['_id']),
            'name': job.get('name', 'N/A'),
            'company': job.get('company', 'N/A'),
            'location': job.get('location', 'N/A'),
            'link': job.get('url', '#'),
            'thumbnail': job.get('thumbnail', ''),
            'technologies': job.get('technologies', []),
            'seniority': job.get('seniority', 'not_specified'),
            'contract_type': job.get('contract_type', 'not_specified'),
            'remote': job.get('remote', False),
            'source': job.get('source', 'Unknown'),
            'date': job.get('date_scraped', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({
        'jobs': result,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@app.route('/api/filters/options')
def get_filter_options():
    """Get all available filter options"""
    return jsonify({
        'technologies': sorted(jobs_collection.distinct('technologies')),
        'companies': sorted(jobs_collection.distinct('company')),
        'seniority_levels': ['junior', 'mid', 'senior', 'lead', 'expert'],
        'contract_types': ['cdi', 'cdd', 'freelance', 'internship', 'apprenticeship'],
        'locations': sorted(jobs_collection.distinct('location'))
    })

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
