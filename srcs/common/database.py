from common.constants import MONGO_URL
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime

# client = pymongo.MongoClient(MONGO_URL)
uri = MONGO_URL
client = MongoClient(uri, server_api=ServerApi('1'), tlsAllowInvalidCertificates=True)

db = client.jobs_database
jobs_collection = db.jobs_collection
logs_collection = db.logs

def is_url_in_database(url):
    """Return True if the given URL is already in our MongoDB database."""
    return jobs_collection.find_one({'url': url}) is not None

def add_url_in_database(url):
    """Add an URL into our MongoDB database (minimal entry, will be enriched later)."""
    # Ne rien faire ici - le save_job s'en chargera avec toutes les données
    pass

def save_job(job_data):
    """
    Save a complete job with all details.
    job_data: dict with keys like:
    - url, name, company, location, thumbnail
    - technologies: [], seniority: str, contract_type: str
    - salary: str, remote: bool, posted_date: str
    """
    job_data['date_scraped'] = datetime.now()
    if 'date_added' not in job_data:
        job_data['date_added'] = datetime.now()
    
    # Upsert: met à jour si existe, insère sinon
    existing = jobs_collection.find_one({'url': job_data.get('url')})
    if existing:
        # Met à jour avec les données enrichies
        jobs_collection.update_one(
            {'url': job_data.get('url')},
            {'$set': job_data}
        )
        return True
    else:
        # Insère nouveau
        jobs_collection.insert_one(job_data)
        return True
    return False

def get_jobs(filters=None, limit=100, skip=0):
    """
    Get jobs with optional filters.
    filters: dict with keys like:
    - technologies: ['react', 'javascript']
    - seniority: 'junior'|'mid'|'senior'
    - contract_type: 'cdi'|'cdd'|'freelance'
    - company: str
    - remote: bool
    """
    query = {}
    
    if filters:
        # Filter by technologies (match any)
        if filters.get('technologies'):
            query['technologies'] = {'$in': [t.lower() for t in filters['technologies']]}
        
        # Filter by seniority
        if filters.get('seniority'):
            query['seniority'] = filters['seniority'].lower()
        
        # Filter by contract type
        if filters.get('contract_type'):
            query['contract_type'] = filters['contract_type'].lower()
        
        # Filter by company (partial match)
        if filters.get('company'):
            query['company'] = {'$regex': filters['company'], '$options': 'i'}
        
        # Filter by remote
        if filters.get('remote') is not None:
            query['remote'] = filters['remote']
        
        # Text search in name/description
        if filters.get('search'):
            query['$or'] = [
                {'name': {'$regex': filters['search'], '$options': 'i'}},
                {'description': {'$regex': filters['search'], '$options': 'i'}},
                {'company': {'$regex': filters['search'], '$options': 'i'}}
            ]
    
    cursor = jobs_collection.find(query).sort('date_scraped', -1).skip(skip).limit(limit)
    return list(cursor)

def get_distinct_values(field):
    """Get all distinct values for a field (e.g., technologies, companies)"""
    return jobs_collection.distinct(field)

def get_stats():
    """Get dashboard stats"""
    from datetime import datetime, timedelta
    
    total = jobs_collection.count_documents({})
    last_24h = jobs_collection.count_documents({
        'date_scraped': {'$gte': datetime.now() - timedelta(hours=24)}
    })
    
    # Get unique technologies count
    all_techs = jobs_collection.distinct('technologies')
    
    # Get jobs by seniority
    seniority_stats = {}
    for level in ['junior', 'mid', 'senior', 'lead', 'expert']:
        count = jobs_collection.count_documents({'seniority': level})
        if count > 0:
            seniority_stats[level] = count
    
    return {
        'total': total,
        'last_24h': last_24h,
        'unique_technologies': len(all_techs),
        'seniority_breakdown': seniority_stats
    }

def log_to_db(level, message, website='', extra_data=None):
    """Save a log entry to MongoDB"""
    log_entry = {
        'timestamp': datetime.now(),
        'level': level,
        'message': message,
        'website': website,
        'extra_data': extra_data or {}
    }
    logs_collection.insert_one(log_entry)

def get_logs(limit=100, level=None, website=None):
    """Get recent logs with optional filters"""
    query = {}
    if level:
        query['level'] = level
    if website:
        query['website'] = website
    
    return list(logs_collection.find(query).sort('timestamp', -1).limit(limit))
