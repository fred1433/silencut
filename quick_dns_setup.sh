#!/bin/bash

echo "🚀 Configuration rapide DNS + Render"
echo "===================================="
echo ""
echo "Je vais ouvrir 2 pages :"
echo "1. Porkbun DNS (pour configurer les DNS)"
echo "2. Render Settings (pour ajouter le domaine)"
echo ""
echo "Appuie sur ENTER pour continuer..."
read

# Ouvrir la page DNS de Porkbun
echo "📌 Ouverture de Porkbun DNS..."
open "https://porkbun.com/account/domainsSpeedy?return_to=%2Faccount%2Fdomains%2Fsilencut.com"

echo ""
echo "Sur Porkbun, fais ceci :"
echo "1. SUPPRIME les enregistrements ALIAS et CNAME wildcard (*)"
echo "2. AJOUTE :"
echo "   - Type: A, Host: vide, Answer: 75.2.60.5"
echo "   - Type: CNAME, Host: www, Answer: silencut.onrender.com"
echo ""
echo "Appuie sur ENTER quand c'est fait..."
read

# Ouvrir Render pour ajouter le domaine
echo "📌 Ouverture de Render..."
open "https://dashboard.render.com/web/srv-crfktmrtq21c73fmvi10/settings#custom-domains"

echo ""
echo "Sur Render :"
echo "1. Clique 'Add Custom Domain'"
echo "2. Entre: silencut.com"
echo "3. Clique 'Save'"
echo ""
echo "✅ Dans 10-30 minutes, ton site sera accessible sur https://silencut.com !"