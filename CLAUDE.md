# Configuration Claude Code pour Dev Jobs Scrapper

Ce fichier donne le contexte à Claude Code quand tu travailles sur ce projet.

## 🎯 Projet

**Nom:** Dev Jobs Scrapper  
**Type:** Scraper de jobs tech avec dashboard web  
**Stack:** Python, Flask, MongoDB, Docker, Selenium

## 📁 Structure

```
├── srcs/                      # Code source du scrapper
│   ├── common/               # Modules partagés
│   │   ├── database.py       # Connexion MongoDB
│   │   ├── discord_logger.py # Logging Discord
│   │   ├── job_analyzer.py   # Analyse des fiches de poste
│   │   ├── webhook.py        # Envoi Discord
│   │   └── website.py        # Classe base pour les scrapers
│   ├── websites/             # Scrapers spécifiques
│   │   ├── wttj.py          # Welcome to the Jungle
│   │   ├── jobteaser.py     # Job Teaser
│   │   └── stationf.py      # Station F
│   └── main.py              # Point d'entrée
├── dashboard/               # Interface web (Flask)
│   ├── app.py              # API REST
│   ├── templates/          # HTML
│   └── static/             # CSS, JS
├── scripts/                # Scripts utilitaires
│   ├── migrate_remote_days.py
│   └── fix_database.py
├── docker-compose.yml      # Orchestration
└── .env                    # Variables d'environnement
```

## 🐳 Docker

```bash
# Démarrer tout
docker-compose up -d

# Voir les logs
docker-compose logs -f scrapper
docker-compose logs -f dashboard

# Rebuild
docker-compose up -d --build

# Exécuter un script
docker compose exec scrapper python scripts/migrate_remote_days.py
```

## 🔌 API Endpoints (Dashboard)

- `GET /` - Dashboard
- `GET /jobs` - Liste des jobs avec filtres
- `GET /analytics` - Graphiques et stats
- `GET /api/jobs` - API jobs (JSON)
- `GET /api/analytics/*` - Stats pour les graphiques

## 💾 MongoDB

**Database:** `jobs_database`  
**Collections:**
- `jobs_collection` - Les offres d'emploi
- `logs` - Logs du système

## 📝 Conventions de code

- Python 3.11+
- Type hints quand pertinent
- Docstrings en français
- Variables en snake_case

## 🚨 Points d'attention

1. **Scrapers:** Peuvent casser si les sites changent leur HTML
2. **Selenium:** Nécessite Chrome/Chromium dans le conteneur
3. **Rate limiting:** Délai de 4s entre chaque job pour éviter le blocage
4. **MongoDB:** Connexion via `mongodb://mongodb:27017/`

## 🛠️ Tâches communes

### Ajouter un nouveau site de scraping
1. Créer `srcs/websites/nomdujob.py`
2. Hériter de `Website` dans `common.website`
3. Implémenter la méthode `scrap()`
4. Ajouter à `main.py`

### Modifier le dashboard
1. Éditer `dashboard/app.py` pour l'API
2. Éditer `dashboard/templates/` pour l'HTML
3. Éditer `dashboard/static/` pour CSS/JS
4. Rebuild: `docker-compose up -d --build dashboard`

### Migrer des données
```bash
docker compose exec scrapper python scripts/NOM_DU_SCRIPT.py
```

## 🔗 Liens utiles

- Dashboard: http://localhost:8080
- Dashboard jobs: http://localhost:8080/jobs
- Dashboard analytics: http://localhost:8080/analytics
- MongoDB: localhost:27017

## 📦 Dépendances principales

**Scrapper:**
- selenium (web scraping)
- beautifulsoup4 (parsing HTML)
- pymongo (base de données)
- discord-webhook (notifications)
- requests (HTTP)

**Dashboard:**
- flask (serveur web)
- pymongo
- chart.js (graphiques, via CDN)
