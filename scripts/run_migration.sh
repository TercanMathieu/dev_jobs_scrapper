#!/bin/bash
# Script pour exécuter la migration des jobs existants
# Usage: ./run_migration.sh

echo "🚀 Exécution de la migration des jobs existants..."
echo ""

# Vérifier si le conteneur tourne
if ! docker compose ps | grep -q "scrapper"; then
    echo "❌ Le conteneur scrapper n'est pas en cours d'exécution"
    echo "Démarrage des services..."
    docker compose up -d
    sleep 5
fi

# Exécuter le script de migration dans le conteneur
echo "📦 Exécution du script de migration dans le conteneur..."
docker compose exec scrapper python scripts/migrate_remote_days.py

echo ""
echo "✅ Migration terminée !"
echo ""
echo "Vous pouvez maintenant utiliser les nouveaux filtres de télétravail."
