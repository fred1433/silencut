#!/usr/bin/env python3
"""
Script de test pour vérifier que l'application web fonctionne correctement
"""

import requests
import time
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_webapp():
    print("🔧 Test de l'application web SilenCut")
    
    # 1. Vérifier que l'API est accessible
    print("\n1. Test de l'API...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    print(f"   ✅ API accessible: {response.json()}")
    
    # 2. Utiliser le fichier de test spécifique
    print("\n2. Utilisation du fichier de test...")
    test_file = Path('test_videos/video1397602886.mp4')
    
    if not test_file.exists():
        print(f"   ❌ Fichier de test non trouvé: {test_file}")
        return
    
    print(f"   ✅ Fichier trouvé: {test_file}")
    
    # 3. Upload du fichier
    print("\n3. Upload du fichier...")
    with open(test_file, 'rb') as f:
        files = {'file': (test_file.name, f, 'video/mp4')}
        response = requests.post(f"{BASE_URL}/upload", files=files)
    
    if response.status_code != 200:
        print(f"   ❌ Erreur upload: {response.text}")
        return
    
    upload_data = response.json()
    job_id = upload_data['job_id']
    print(f"   ✅ Upload réussi: job_id={job_id}")
    
    # 4. Lancer le traitement
    print("\n4. Lancement du traitement...")
    params = {
        "threshold_db": -40.0,
        "min_silence_ms": 270.0,
        "min_noise_ms": 70.0,
        "hysteresis_db": 3.0,
        "margin_ms": 20.0,
        "crf": 18,
        "audio_bitrate": "192k"
    }
    
    response = requests.post(f"{BASE_URL}/process/{job_id}", json=params)
    if response.status_code != 200:
        print(f"   ❌ Erreur traitement: {response.text}")
        return
    
    print(f"   ✅ Traitement lancé")
    
    # 5. Suivre le progrès
    print("\n5. Suivi du progrès...")
    last_progress = -1
    while True:
        response = requests.get(f"{BASE_URL}/status/{job_id}")
        if response.status_code != 200:
            print(f"   ❌ Erreur status: {response.text}")
            break
        
        status = response.json()
        progress = status.get('progress', 0)
        
        if progress != last_progress:
            print(f"   [{status['status']}] {progress:.0f}% - {status.get('message', '')}")
            last_progress = progress
        
        if status['status'] == 'completed':
            print(f"\n   ✅ Traitement terminé!")
            print(f"   📊 Durée originale: {status.get('duration_original', 0):.1f}s")
            print(f"   📊 Durée finale: {status.get('duration_final', 0):.1f}s")
            print(f"   📊 Réduction: {status.get('reduction_percent', 0):.1f}%")
            
            # Télécharger le résultat
            print(f"\n6. URL de téléchargement: {BASE_URL}/download/{job_id}")
            break
        
        elif status['status'] == 'failed':
            print(f"\n   ❌ Échec: {status.get('error', 'Erreur inconnue')}")
            break
        
        time.sleep(1)
    
    print("\n✨ Test terminé!")

if __name__ == "__main__":
    try:
        test_webapp()
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter à l'API. Assurez-vous que l'application est lancée:")
        print("   cd webapp && python app.py")
    except Exception as e:
        print(f"❌ Erreur: {e}")