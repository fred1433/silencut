#!/bin/bash

# Script pour lancer l'application web SilenCut

echo "🚀 Lancement de SilenCut Web..."

# Activer l'environnement virtuel si il existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Installer les dépendances si nécessaire
pip install fastapi uvicorn python-multipart aiofiles websockets 2>/dev/null || true

# Créer les dossiers nécessaires
mkdir -p webapp/uploads webapp/outputs webapp/temp

# Lancer l'application
echo "✅ Application disponible sur http://localhost:8000"
echo "📝 API docs disponibles sur http://localhost:8000/docs"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter le serveur"

python3 -m uvicorn webapp.app:app --reload --port 8000