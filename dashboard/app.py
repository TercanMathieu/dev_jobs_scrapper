from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
from datetime import datetime, timedelta
from collections import Counter
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

@app.route('/analytics')
def analytics_page():
    return render_template('analytics.html')

@app.route('/api/debug')
def debug_data():
    """Debug endpoint to check data"""
    try:
        total = jobs_collection.count_documents({})
        sample = list(jobs_collection.find().limit(3))
        
        for doc in sample:
            doc['_id'] = str(doc['_id'])
            if 'date_scraped' in doc:
                doc['date_scraped'] = doc['date_scraped'].isoformat()
            if 'date_added' in doc:
                doc['date_added'] = doc['date_added'].isoformat()
        
        return jsonify({
            'mongo_url': MONGO_URL,
            'database_name': db.name,
            'collection_name': jobs_collection.name,
            'total_documents': total,
            'sample_documents': sample
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get dashboard stats"""
    total_jobs = jobs_collection.count_documents({})
    
    last_24h = datetime.now() - timedelta(hours=24)
    jobs_24h = jobs_collection.count_documents({'date_scraped': {'$gte': last_24h}})
    
    last_job = jobs_collection.find_one(sort=[('date_scraped', -1)])
    last_update = last_job['date_scraped'].strftime('%Y-%m-%d %H:%M:%S') if last_job and 'date_scraped' in last_job else 'Jamais'
    
    all_techs = jobs_collection.distinct('technologies')
    companies = jobs_collection.distinct('company')
    
    seniority_stats = {}
    for level in ['junior', 'mid', 'senior', 'lead', 'expert', 'not_specified']:
        count = jobs_collection.count_documents({'seniority': level})
        if count > 0:
            seniority_stats[level] = count
    
    contract_stats = {}
    for ctype in ['cdi', 'cdd', 'freelance', 'internship', 'apprenticeship', 'not_specified']:
        count = jobs_collection.count_documents({'contract_type': ctype})
        if count > 0:
            contract_stats[ctype] = count
    
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

@app.route('/api/analytics/technologies')
def get_tech_analytics():
    """Get technology demand analytics"""
    # Get all jobs
    jobs = list(jobs_collection.find({}, {'technologies': 1}))
    
    # Count all technologies
    all_techs = []
    for job in jobs:
        all_techs.extend(job.get('technologies', []))
    
    tech_counts = Counter(all_techs)
    top_techs = tech_counts.most_common(20)
    
    return jsonify({
        'labels': [tech[0] for tech in top_techs],
        'data': [tech[1] for tech in top_techs]
    })

@app.route('/api/analytics/tech-by-seniority')
def get_tech_by_seniority():
    """Get technology demand by seniority level"""
    seniority_levels = ['junior', 'mid', 'senior', 'lead']
    tech_by_level = {}
    
    for level in seniority_levels:
        jobs = list(jobs_collection.find({'seniority': level}, {'technologies': 1}))
        all_techs = []
        for job in jobs:
            all_techs.extend(job.get('technologies', []))
        
        tech_counts = Counter(all_techs)
        tech_by_level[level] = dict(tech_counts.most_common(10))
    
    return jsonify(tech_by_level)

@app.route('/api/analytics/seniority')
def get_seniority_distribution():
    """Get seniority distribution"""
    seniority_counts = {}
    for level in ['junior', 'mid', 'senior', 'lead', 'expert']:
        count = jobs_collection.count_documents({'seniority': level})
        if count > 0:
            seniority_counts[level] = count
    
    return jsonify(seniority_counts)

@app.route('/api/analytics/contracts')
def get_contract_distribution():
    """Get contract type distribution"""
    contract_counts = {}
    for ctype in ['cdi', 'cdd', 'freelance', 'internship', 'apprenticeship']:
        count = jobs_collection.count_documents({'contract_type': ctype})
        if count > 0:
            contract_counts[ctype] = count
    
    return jsonify(contract_counts)

@app.route('/api/analytics/remote')
def get_remote_stats():
    """Get remote vs on-site stats"""
    remote_count = jobs_collection.count_documents({'remote': True})
    onsite_count = jobs_collection.count_documents({'remote': False})
    unknown_count = jobs_collection.count_documents({'remote': {'$exists': False}})
    
    return jsonify({
        'remote': remote_count,
        'onsite': onsite_count,
        'unknown': unknown_count
    })

@app.route('/api/analytics/top-companies')
def get_top_companies():
    """Get top hiring companies"""
    limit = int(request.args.get('limit', 15))
    
    pipeline = [
        {'$group': {'_id': '$company', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': limit}
    ]
    
    results = list(jobs_collection.aggregate(pipeline))
    
    return jsonify({
        'companies': [r['_id'] for r in results if r['_id']],
        'counts': [r['count'] for r in results if r['_id']]
    })

@app.route('/api/analytics/timeline')
def get_jobs_timeline():
    """Get jobs posted over time (last 30 days)"""
    days = int(request.args.get('days', 30))
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    pipeline = [
        {
            '$match': {
                'date_scraped': {'$gte': start_date, '$lte': end_date}
            }
        },
        {
            '$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$date_scraped'}},
                'count': {'$sum': 1}
            }
        },
        {'$sort': {'_id': 1}}
    ]
    
    results = list(jobs_collection.aggregate(pipeline))
    
    # Fill missing dates with 0
    date_counts = {r['_id']: r['count'] for r in results}
    all_dates = []
    all_counts = []
    
    current = start_date
    while current <= end_date:
        date_str = current.strftime('%Y-%m-%d')
        all_dates.append(date_str)
        all_counts.append(date_counts.get(date_str, 0))
        current += timedelta(days=1)
    
    return jsonify({
        'dates': all_dates,
        'counts': all_counts
    })

@app.route('/api/analytics/tech-correlation')
def get_tech_correlation():
    """Get which technologies are often requested together"""
    # Get pairs of technologies that appear together
    jobs = list(jobs_collection.find({'technologies': {'$exists': True, '$ne': []}}))
    
    from itertools import combinations
    
    pair_counts = Counter()
    for job in jobs:
        techs = job.get('technologies', [])
        if len(techs) >= 2:
            for pair in combinations(sorted(techs), 2):
                pair_counts[pair] += 1
    
    # Get top pairs
    top_pairs = pair_counts.most_common(15)
    
    return jsonify({
        'pairs': [{'tech1': p[0][0], 'tech2': p[0][1], 'count': p[1]} for p in top_pairs]
    })

@app.route('/api/jobs')
def get_jobs():
    """Get jobs with advanced filters"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    skip = (page - 1) * per_page
    
    query = {}
    
    techs = request.args.getlist('technologies')
    if techs:
        query['technologies'] = {'$all': [t.lower() for t in techs]}
    
    seniority = request.args.getlist('seniority')
    if seniority:
        query['seniority'] = {'$in': [s.lower() for s in seniority]}
    
    contracts = request.args.getlist('contract_type')
    if contracts:
        query['contract_type'] = {'$in': [c.lower() for c in contracts]}
    
    remote = request.args.get('remote')
    if remote is not None:
        query['remote'] = remote.lower() == 'true'
    
    # Location filter (paris or all)
    location = request.args.get('location', 'all')
    if location == 'paris':
        # Match Paris and Ile-de-France locations
        query['location'] = {'$regex': 'paris|île-de-france|idf|75|77|78|91|92|93|94|95', '$options': 'i'}
    # if 'all', don't add location filter (show all France)
    
    # Remote days filter (1, 2, 3, 4, 'full', 'hybrid')
    remote_days = request.args.getlist('remote_days')
    if remote_days:
        # Convert string numbers to int, keep 'full' and 'hybrid' as strings
        days_values = []
        for day in remote_days:
            if day.isdigit():
                days_values.append(int(day))
            else:
                days_values.append(day)
        query['remote_days'] = {'$in': days_values}
    
    company = request.args.get('company')
    if company:
        query['company'] = {'$regex': company, '$options': 'i'}
    
    search = request.args.get('search')
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}},
            {'company': {'$regex': search, '$options': 'i'}}
        ]
    
    total = jobs_collection.count_documents(query)
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
            'remote_days': job.get('remote_days'),
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
        'locations': sorted(jobs_collection.distinct('location')),
        'remote_options': [
            {'value': 'full', 'label': 'Full Remote (100%)'},
            {'value': '4', 'label': '4 jours / semaine'},
            {'value': '3', 'label': '3 jours / semaine'},
            {'value': '2', 'label': '2 jours / semaine'},
            {'value': '1', 'label': '1 jour / semaine'},
            {'value': 'hybrid', 'label': 'Hybride (non précisé)'},
        ]
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
