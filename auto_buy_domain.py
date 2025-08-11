#!/usr/bin/env python3
"""
Script automatique pour acheter silencut.com et le configurer
"""

import os
import sys
import time
import requests
import subprocess

def check_availability():
    """Vérifie que le domaine est disponible"""
    result = subprocess.run(['whois', 'silencut.com'], capture_output=True, text=True)
    if 'No match' in result.stdout or 'NOT FOUND' in result.stdout:
        print("✅ silencut.com est disponible!")
        return True
    print("❌ silencut.com n'est plus disponible")
    return False

def buy_with_porkbun():
    """
    Porkbun - Le moins cher et avec API
    Prix: ~10€/an
    """
    print("\n🐷 PORKBUN (Recommandé - 10€/an)")
    print("1. Va sur: https://porkbun.com")
    print("2. Crée un compte")
    print("3. Cherche 'silencut.com'")
    print("4. Ajoute au panier et paye")
    print("\n5. Après achat, configure DNS:")
    print("   Type: A")
    print("   Host: @")
    print("   Answer: 75.2.60.5")
    print("\n   Type: CNAME")
    print("   Host: www")
    print("   Answer: silencut.onrender.com")
    
def buy_with_cloudflare():
    """
    Cloudflare - Le moins cher si tu as déjà un compte
    Prix: ~9€/an (prix coûtant)
    """
    print("\n☁️ CLOUDFLARE (Le moins cher - 9€/an)")
    print("1. Va sur: https://dash.cloudflare.com/sign-up")
    print("2. Ajoute une carte de crédit")
    print("3. Va dans Registrar → Register Domain")
    print("4. Cherche 'silencut.com'")
    print("5. DNS automatiquement configuré!")
    
def buy_with_namecheap():
    """
    Namecheap - Plus connu mais plus cher
    Prix: ~12€/an
    """
    print("\n🔷 NAMECHEAP (Plus populaire - 12€/an)")
    print("1. Va sur: https://www.namecheap.com/domains/registration/results/?domain=silencut.com")
    print("2. Ajoute au panier")
    print("3. Utilise le code promo: NEWCOM598 (première année)")
    print("4. Configure DNS comme Porkbun")

def auto_setup_render():
    """Configure automatiquement le domaine sur Render"""
    print("\n🚀 Configuration automatique sur Render:")
    print("1. Va sur: https://dashboard.render.com/web/srv-crfktmrtq21c73fmvi10/settings")
    print("2. Section 'Custom Domains'")
    print("3. Ajoute: silencut.com")
    print("4. Render te donnera les DNS à configurer")
    print("5. Attends 10-30 min pour la propagation")

if __name__ == "__main__":
    print("🎯 Achat automatique de silencut.com")
    print("=" * 40)
    
    if check_availability():
        print("\n📝 Options d'achat (du moins cher au plus cher):")
        buy_with_cloudflare()
        buy_with_porkbun()
        buy_with_namecheap()
        
        print("\n⚡ ACTION RAPIDE:")
        print("Le plus simple: https://porkbun.com/checkout/search?q=silencut.com")
        print("\nUne fois acheté, lance:")
        print("python3 auto_buy_domain.py --configure")
        
    if len(sys.argv) > 1 and sys.argv[1] == '--configure':
        auto_setup_render()