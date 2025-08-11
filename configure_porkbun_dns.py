#!/usr/bin/env python3
"""
Configure automatiquement les DNS sur Porkbun via leur API
"""

import requests
import json
import time

# Configuration
DOMAIN = "silencut.com"
API_URL = "https://porkbun.com/api/json/v3"

print("🔧 Configuration automatique DNS pour silencut.com")
print("=" * 50)

# D'abord, tu dois créer une clé API
print("\n📝 ÉTAPE 1: Créer une clé API Porkbun")
print("1. Va sur: https://porkbun.com/account/api")
print("2. Clique 'Create API Key'")
print("3. Copie l'API Key et le Secret Key")
print("")

api_key = input("Colle ton API Key ici: ").strip()
secret_key = input("Colle ton Secret Key ici: ").strip()

# Authentification pour toutes les requêtes
auth = {
    "apikey": api_key,
    "secretapikey": secret_key
}

def delete_record(record_id):
    """Supprime un enregistrement DNS"""
    url = f"{API_URL}/dns/delete/{DOMAIN}/{record_id}"
    response = requests.post(url, json=auth)
    return response.json()

def get_records():
    """Récupère tous les enregistrements DNS"""
    url = f"{API_URL}/dns/retrieve/{DOMAIN}"
    response = requests.post(url, json=auth)
    return response.json()

def create_record(record_type, host, answer, ttl=600, priority=None):
    """Crée un nouvel enregistrement DNS"""
    url = f"{API_URL}/dns/create/{DOMAIN}"
    data = {
        **auth,
        "type": record_type,
        "content": answer,
        "ttl": str(ttl)
    }
    
    if host:
        data["name"] = host
    
    if priority:
        data["prio"] = str(priority)
    
    response = requests.post(url, json=data)
    return response.json()

print("\n🔍 Récupération des enregistrements actuels...")
current = get_records()

if current.get("status") == "ERROR":
    print(f"❌ Erreur: {current.get('message')}")
    print("\nVérifie que tu as bien activé l'API sur ton compte Porkbun")
    exit(1)

records = current.get("records", [])
print(f"Trouvé {len(records)} enregistrements")

# Supprimer les enregistrements par défaut
print("\n🗑️ Suppression des enregistrements par défaut...")
for record in records:
    if record["type"] == "ALIAS" and "uixie.porkbun.com" in record["content"]:
        print(f"  Suppression ALIAS -> {record['content']}")
        delete_record(record["id"])
    elif record["type"] == "CNAME" and record["name"] == "*.silencut.com":
        print(f"  Suppression CNAME wildcard -> {record['content']}")
        delete_record(record["id"])

print("\n✅ Ajout des nouveaux enregistrements...")

# Ajouter l'enregistrement A pour le domaine principal
print("  Ajout A record -> 75.2.60.5")
result = create_record("A", "", "75.2.60.5", 600)
if result.get("status") == "SUCCESS":
    print("    ✓ A record créé")
else:
    print(f"    ✗ Erreur: {result.get('message')}")

# Ajouter le CNAME pour www
print("  Ajout CNAME www -> silencut.onrender.com")
result = create_record("CNAME", "www", "silencut.onrender.com", 600)
if result.get("status") == "SUCCESS":
    print("    ✓ CNAME créé")
else:
    print(f"    ✗ Erreur: {result.get('message')}")

print("\n🎉 Configuration DNS terminée!")
print("\nProchaine étape: Ajouter le domaine sur Render")
print("Lance: python3 configure_render_domain.py")