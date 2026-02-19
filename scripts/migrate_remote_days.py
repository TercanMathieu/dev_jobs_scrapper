"""
Script de migration pour mettre à jour les jobs existants avec les nouvelles informations de télétravail.
À exécuter après le déploiement du nouveau système de détection des jours de TT.
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime

# Import des fonctions d'analyse
sys.path.insert(0, '/app/srcs')
from common.job_analyzer import extract_remote_days
from common.database import fetch_job_page

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://mongodb:27017/')

def migrate_existing_jobs():
    """
    Met à jour tous les jobs existants pour ajouter le champ remote_days.
"""
    client = MongoClient(MONGO_URL)
    db = client.jobs_database
    jobs_collection = db.jobs_collection
    
    # Récupérer tous les jobs qui n'ont pas encore remote_days
    jobs_to_update = list(jobs_collection.find({
        '$or': [
            {'remote_days': {'$exists': False}},
            {'remote_days': None}
        ]
    }))
    
    total = len(jobs_to_update)
    print(f"📊 Trouvé {total} jobs à mettre à jour")
    
    if total == 0:
        print("✅ Tous les jobs sont déjà à jour !")
        return
    
    updated = 0
    failed = 0
    
    for i, job in enumerate(jobs_to_update, 1):
        try:
            job_id = job['_id']
            job_url = job.get('url', '')
            job_name = job.get('name', 'Unknown')
            
            print(f"\n[{i}/{total}] Analyse de: {job_name[:50]}...")
            
            if not job_url:
                print(f"  ⚠️ Pas d'URL, skip")
                failed += 1
                continue
            
            # Scraper la fiche de poste
            html_content = fetch_job_page(job_url)
            
            if html_content is None:
                # Si on ne peut pas scraper, essayer de déduire du champ 'remote' existant
                if job.get('remote', False):
                    # Job marqué comme remote mais sans détail → hybrid
                    jobs_collection.update_one(
                        {'_id': job_id},
                        {'$set': {
                            'remote_days': 'hybrid',
                            'migrated_at': datetime.now()
                        }}
                    )
                    print(f"  ✅ Défini comme 'hybrid' (basé sur remote=True)")
                else:
                    # Pas remote → None
                    jobs_collection.update_one(
                        {'_id': job_id},
                        {'$set': {
                            'remote_days': None,
                            'migrated_at': datetime.now()
                        }}
                    )
                    print(f"  ✅ Défini comme None (pas de remote)")
                updated += 1
                continue
            
            # Parser le HTML et extraire le texte
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Supprimer scripts et styles
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            text = ' '.join(text.split())  # Normaliser les espaces
            
            # Extraire les jours de télétravail
            remote_days = extract_remote_days(text)
            
            # Mettre à jour le job
            jobs_collection.update_one(
                {'_id': job_id},
                {'$set': {
                    'remote_days': remote_days,
                    'migrated_at': datetime.now(),
                    'remote': remote_days is not None  # Assurer la cohérence
                }}
            )
            
            # Log du résultat
            if remote_days == 'full':
                print(f"  ✅ Full Remote (100%)")
            elif isinstance(remote_days, int):
                print(f"  ✅ {remote_days} jours/semaine")
            elif remote_days == 'hybrid':
                print(f"  ✅ Hybride (non précisé)")
            else:
                print(f"  ✅ Pas de télétravail")
            
            updated += 1
            
            # Petite pause pour ne pas surcharger
            if i % 10 == 0:
                print(f"\n⏳ Pause de 2 secondes...")
                import time
                time.sleep(2)
                
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            failed += 1
            continue
    
    print(f"\n{'='*50}")
    print(f"📊 Migration terminée:")
    print(f"  ✅ Mis à jour: {updated}")
    print(f"  ❌ Échecs: {failed}")
    print(f"{'='*50}")
    
    # Stats finales
    stats = jobs_collection.aggregate([
        {'$match': {'remote_days': {'$exists': True}}},
        {'$group': {'_id': '$remote_days', 'count': {'$sum': 1}}}
    ])
    
    print("\n📈 Répartition du télétravail après migration:")
    for stat in stats:
        label = stat['_id'] if stat['_id'] is not None else 'Pas de remote'
        print(f"  {label}: {stat['count']} jobs")
    
    client.close()

if __name__ == '__main__':
    print("🚀 Démarrage de la migration des jobs existants...")
    print(f"🔗 Connexion à MongoDB: {MONGO_URL}")
    print()
    
    migrate_existing_jobs()
