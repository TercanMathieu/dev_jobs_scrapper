# Script pour nettoyer la base de données des jobs incomplets
# et optionnellement rescrapper depuis le début

from pymongo import MongoClient
from datetime import datetime
import os
import sys

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/')

def clean_incomplete_jobs():
    """Remove jobs that only have URL but no name/company"""
    client = MongoClient(MONGO_URL)
    db = client.jobs_database
    jobs_collection = db.jobs_collection
    
    # Find incomplete jobs (only have url field or missing name/company)
    incomplete_query = {
        '$or': [
            {'name': {'$exists': False}},
            {'name': None},
            {'name': ''},
            {'company': {'$exists': False}},
            {'company': None},
            {'company': ''}
        ]
    }
    
    incomplete_count = jobs_collection.count_documents(incomplete_query)
    print(f"Found {incomplete_count} incomplete jobs")
    
    if incomplete_count > 0:
        result = jobs_collection.delete_many(incomplete_query)
        print(f"Deleted {result.deleted_count} incomplete jobs")
    
    # Show stats after cleanup
    total = jobs_collection.count_documents({})
    print(f"\nTotal jobs in database now: {total}")
    
    if total > 0:
        sample = jobs_collection.find_one()
        print(f"\nSample job structure:")
        for key in ['name', 'company', 'location', 'technologies', 'seniority']:
            print(f"  {key}: {sample.get(key, 'N/A')}")
    
    client.close()

def reset_database():
    """WARNING: Delete ALL jobs from database"""
    client = MongoClient(MONGO_URL)
    db = client.jobs_database
    
    print("⚠️  WARNING: This will delete ALL jobs from the database!")
    print("Type 'yes' to confirm: ")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        confirm = 'yes'
    else:
        confirm = input().strip().lower()
    
    if confirm == 'yes':
        result = db.jobs_collection.delete_many({})
        print(f"Deleted {result.deleted_count} jobs from database")
    else:
        print("Cancelled")
    
    client.close()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        reset_database()
    else:
        clean_incomplete_jobs()
        print("\nUsage:")
        print("  python clean_database.py          # Clean incomplete jobs")
        print("  python clean_database.py --reset  # Reset all jobs (interactive)")
        print("  python clean_database.py --reset --force  # Reset without prompt")
