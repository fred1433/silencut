#!/bin/bash

echo "🚀 Upgrade de silencut vers le plan Starter"
echo "=========================================="
echo ""
echo "Service ID: srv-d2d6kcer433s73aqh860"
echo "Plan actuel: free"
echo "Plan cible: starter (7$/mois)"
echo ""

# Malheureusement, le CLI Render ne permet pas d'upgrader directement le plan
# Il faut utiliser l'API REST de Render

echo "Option 1: Via l'interface web (le plus simple)"
echo "-----------------------------------------------"
open "https://dashboard.render.com/web/srv-d2d6kcer433s73aqh860/settings"
echo "1. La page Settings s'est ouverte"
echo "2. Cherche 'Instance Type' ou 'Plan'"
echo "3. Change de 'Free' à 'Starter'"
echo "4. Clique 'Save Changes'"
echo ""

echo "Option 2: Via l'API Render (nécessite un API token)"
echo "----------------------------------------------------"
echo "curl -X PATCH https://api.render.com/v1/services/srv-d2d6kcer433s73aqh860 \\"
echo "  -H 'Authorization: Bearer YOUR_API_KEY' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"plan\": \"starter\"}'"
echo ""
echo "Pour obtenir un API key:"
echo "https://dashboard.render.com/u/settings/api-keys"