# 🛎️ Dev Jobs Scrapper - Dashboard

Dashboard web moderne pour visualiser les jobs trouvés et les logs en temps réel.

## ✨ Features

- 📊 **Stats temps réel** — Total jobs, jobs des dernières 24h, dernière mise à jour
- 📋 **Liste des jobs** — 50 derniers jobs avec liens directs vers les offres
- 📝 **Logs en direct** — Logs colorés par niveau (info, success, warning, error)
- 🔄 **Auto-refresh** — Mise à jour automatique toutes les 5 secondes
- 🎨 **Dark theme** — Interface moderne et élégante

## 🚀 Installation rapide

### 1. Copier les fichiers dans ton projet

```bash
cp -r dashboard/ /chemin/vers/dev_jobs_scrapper/
cp docker-compose.full.yml /chemin/vers/dev_jobs_scrapper/
```

### 2. Configurer les variables d'environnement

Crée un fichier `.env` à la racine du projet :

```env
# Discord Webhooks
WEBHOOK_URL=https://discord.com/api/webhooks/...
LOG_WEBHOOK_URL=https://discord.com/api/webhooks/...

# MongoDB (optionnel, valeur par défaut fonctionne)
MONGO_URL=mongodb://mongodb:27017/
```

### 3. Lancer la stack complète

```bash
cd /chemin/vers/dev_jobs_scrapper
docker-compose -f docker-compose.full.yml up -d
```

### 4. Ouvrir le dashboard

Rends-toi sur : http://localhost:8080

## 📁 Structure

```
dashboard/
├── Dockerfile              # Image Docker
├── app.py                  # Serveur Flask
├── requirements.txt        # Dépendances Python
├── static/
│   ├── style.css          # Dark theme 🎨
│   └── app.js             # Frontend avec auto-refresh
├── templates/
│   └── index.html         # Interface principale
└── README.md              # Ce fichier
```

## 🐳 Commandes utiles

```bash
# Démarrer
docker-compose -f docker-compose.full.yml up -d

# Arrêter
docker-compose -f docker-compose.full.yml down

# Voir les logs
docker-compose -f docker-compose.full.yml logs -f dashboard

# Rebuild après modification
docker-compose -f docker-compose.full.yml up -d --build dashboard
```

## 🔌 API Endpoints

- `GET /` — Dashboard web
- `GET /api/stats` — Statistiques globales
- `GET /api/jobs` — Liste des 50 derniers jobs
- `GET /api/logs` — Logs récents (100 entrées)
- `GET /api/logs/live` — Logs des 5 dernières minutes

## 📝 Prérequis

- Docker & Docker Compose
- MongoDB (inclus dans docker-compose.full.yml)
- Les webhooks Discord configurés (optionnel pour les logs)

## 🎨 Personnalisation

Le CSS utilise des variables pour faciliter la personnalisation :

```css
:root {
    --bg-primary: #0f0f23;      /* Fond principal */
    --bg-secondary: #1a1a2e;    /* Fond secondaire */
    --accent: #e94560;          /* Couleur d'accent */
    --success: #2ecc71;         /* Succès */
    --error: #e74c3c;           /* Erreur */
    /* ... */
}
```

Modifie `dashboard/static/style.css` pour changer les couleurs.

## 🐛 Dépannage

**Le dashboard ne se connecte pas à MongoDB ?**
- Vérifie que le conteneur `mongodb` est démarré : `docker-compose ps`
- Vérifie les logs : `docker-compose logs mongodb`

**Pas de données dans le dashboard ?**
- Assure-toi que le scrapper a tourné au moins une fois
- Vérifie que les jobs sont bien enregistrés dans MongoDB

**Port 8080 déjà utilisé ?**
- Change le port dans `docker-compose.full.yml` : `ports: - "8081:8080"`

## 📜 Licence

Ce projet fait partie de Dev Jobs Scrapper.
