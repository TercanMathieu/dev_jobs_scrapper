# Script pour corriger les jobs existants dans la base de données

from pymongo import MongoClient
from datetime import datetime
import os

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/')

def fix_existing_jobs():
    """Fix jobs that have missing or N/A fields"""
    client = MongoClient(MONGO_URL)
    db = client.jobs_database
    jobs_collection = db.jobs_collection
    
    print("Checking for jobs with missing fields...")
    
    # Find jobs with missing or empty fields
    problematic_query = {
        '$or': [
            {'name': {'$in': [None, '', 'N/A', 'Unknown']}},
            {'company': {'$in': [None, '', 'N/A', 'Unknown']}},
            {'name': {'$exists': False}},
            {'company': {'$exists': False}},
        ]
    }
    
    problematic_jobs = list(jobs_collection.find(problematic_query))
    print(f"Found {len(problematic_jobs)} problematic jobs")
    
    if problematic_jobs:
        print("\nSample of problematic jobs:")
        for job in problematic_jobs[:3]:
            print(f"  ID: {job['_id']}")
            print(f"  URL: {job.get('url', 'N/A')[:80]}...")
            print(f"  Name: {job.get('name', 'MISSING')}")
            print(f"  Company: {job.get('company', 'MISSING')}")
            print()
        
        # Delete problematic jobs (they'll be re-scrapped properly)
        result = jobs_collection.delete_many(problematic_query)
        print(f"Deleted {result.deleted_count} problematic jobs")
    
    # Show final stats
    total = jobs_collection.count_documents({})
    print(f"\nTotal jobs in database: {total}")
    
    if total > 0:
        sample = jobs_collection.find_one()
        print("\nSample job:")
        print(f"  Name: {sample.get('name', 'N/A')}")
        print(f"  Company: {sample.get('company', 'N/A')}")
        print(f"  Technologies: {sample.get('technologies', [])}")
        print(f"  Seniority: {sample.get('seniority', 'N/A')}")
    
    client.close()

if __name__ == '__main__':
    fix_existing_jobs()
