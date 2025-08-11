#!/bin/bash

# Script pour acheter et configurer un domaine automatiquement

echo "🔍 Vérification de la disponibilité de silencut.com..."

# Option 1: Avec Namecheap API (nécessite une clé API)
check_namecheap() {
    curl -s "https://api.namecheap.com/xml.response?ApiUser=YOUR_USERNAME&ApiKey=YOUR_API_KEY&UserName=YOUR_USERNAME&Command=namecheap.domains.check&ClientIp=YOUR_IP&DomainList=silencut.com"
}

# Option 2: Avec Porkbun API (plus simple, moins cher)
check_porkbun() {
    curl -X POST https://porkbun.com/api/json/v3/domain/check \
        -H "Content-Type: application/json" \
        -d '{
            "secretapikey": "YOUR_SECRET_KEY",
            "apikey": "YOUR_API_KEY",
            "domain": "silencut.com"
        }'
}

# Option 3: Avec Cloudflare Registrar (si tu as déjà un compte)
check_cloudflare() {
    curl -X GET "https://api.cloudflare.com/client/v4/registrar/domains/silencut.com/available" \
        -H "Authorization: Bearer YOUR_API_TOKEN" \
        -H "Content-Type: application/json"
}

echo ""
echo "📝 Options pour acheter le domaine via CLI :"
echo ""
echo "1. PORKBUN (Recommandé - ~10€/an)"
echo "   - Va sur: https://porkbun.com/account/api"
echo "   - Génère une clé API"
echo "   - Utilise leur API pour acheter"
echo ""
echo "2. CLOUDFLARE (Si tu as un compte - ~9€/an)"
echo "   - Le moins cher du marché"
echo "   - API très simple"
echo "   - Protection DDoS incluse"
echo ""
echo "3. GANDI CLI (Installation facile)"
echo "   brew install gandi-cli"
echo "   gandi domain buy silencut.com"
echo ""

# Configuration DNS automatique pour Render
configure_dns_for_render() {
    echo "Configuration DNS pour Render:"
    echo "A     @     75.2.60.5"
    echo "CNAME www   silencut.onrender.com"
}

configure_dns_for_render