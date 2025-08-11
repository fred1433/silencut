# SilenCut - Suppression intelligente de silence dans les vidéos

Un outil CLI robuste pour supprimer automatiquement les silences dans les vidéos, avec détection RMS, hystérésis et morphologie temporelle.

## Caractéristiques

- **Détection RMS avec hystérésis** : Évite les tremblements aux frontières silence/parole
- **Morphologie temporelle** : 
  - Supprime les bruits courts (<70ms par défaut)
  - Conserve les silences courts (<270ms par défaut)
- **Marges de sécurité** : Ajoute 15ms autour des coupes pour éviter de couper les syllabes
- **Micro-fades audio** : Évite les clics audibles aux transitions
- **Ré-encodage propre** : Utilise x264 avec GOP court pour des coupes nettes

## Installation

### Prérequis

- Python 3.8+
- FFmpeg installé et accessible dans le PATH

### Installation des dépendances Python

```bash
pip install -r requirements.txt
```

## Utilisation

### Commande de base

```bash
python cut_silence.py input.mp4 output.mp4
```

### Paramètres par défaut

- Seuil de détection : **-35 dBFS**
- Silence minimum à supprimer : **270 ms**
- Bruit maximum à ignorer : **70 ms**
- Hystérésis : **3 dB**
- Marge autour des coupes : **15 ms**

### Options avancées

```bash
# Ajuster le seuil de détection (plus négatif = plus sensible)
python cut_silence.py input.mp4 output.mp4 --threshold -30

# Changer les durées minimales
python cut_silence.py input.mp4 output.mp4 --min-silence 500 --min-noise 100

# Qualité vidéo (CRF: 0=lossless, 18=très bien, 23=défaut x264, 51=pire)
python cut_silence.py input.mp4 output.mp4 --crf 23

# Mode analyse seule (sans générer la vidéo)
python cut_silence.py input.mp4 output.mp4 --dry-run

# Exporter les intervalles détectés
python cut_silence.py input.mp4 output.mp4 --export-intervals intervals.txt
```

### Toutes les options

```
Options:
  -h, --help            Affiche l'aide
  --threshold -35       Seuil de détection en dBFS (défaut: -35)
  --min-silence 270     Durée min de silence à supprimer en ms (défaut: 270)
  --min-noise 70        Durée max de bruit à ignorer en ms (défaut: 70)
  --hysteresis 3        Hystérésis en dB pour éviter tremblements (défaut: 3)
  --margin 15           Marge de sécurité en ms autour des coupes (défaut: 15)
  --crf 18              CRF pour l'encodage x264 (défaut: 18)
  --audio-bitrate 192k  Bitrate audio (défaut: 192k)
  --export-intervals    Exporter les intervalles dans un fichier
  --dry-run             Analyser seulement, sans générer la vidéo
```

## Algorithme détaillé

1. **Extraction audio** : Convertit en mono 48kHz pour l'analyse
2. **Calcul RMS** : Fenêtre de 20ms, hop de 10ms
3. **Hystérésis** : 
   - Entre en silence si < seuil - 3dB
   - Sort du silence si > seuil + 3dB
4. **Morphologie temporelle** :
   - Fermeture : supprime les sons courts (<70ms)
   - Ouverture : conserve les silences courts (<270ms)
5. **Génération des intervalles** : Avec marges de 15ms
6. **Rendu FFmpeg** : Trim + concat avec micro-fades

## Exemples d'utilisation

### Podcast avec peu de bruit de fond
```bash
python cut_silence.py podcast.mp4 podcast_cut.mp4 --threshold -38
```

### Vidéo bruitée (moins sensible)
```bash
python cut_silence.py noisy.mp4 clean.mp4 --threshold -25 --min-noise 100
```

### Conférence (garder les pauses naturelles)
```bash
python cut_silence.py conference.mp4 conference_cut.mp4 --min-silence 500
```

## Format du fichier d'intervalles

Si vous utilisez `--export-intervals`, le format est :
```
start1,end1
start2,end2
...
```
Temps en secondes avec 3 décimales de précision.

## Troubleshooting

### "Aucun segment audio détecté"
- Le seuil est trop élevé, essayez `--threshold -25` ou `-20`

### Coupe des syllabes
- Augmentez la marge : `--margin 30`
- Ou augmentez le bruit ignoré : `--min-noise 100`

### Trop de petites coupes
- Augmentez le silence minimum : `--min-silence 500`

### FFmpeg error
- Vérifiez que FFmpeg est installé : `ffmpeg -version`
- Vérifiez que le fichier d'entrée est valide

## Performance

- Traitement audio : ~10x temps réel sur CPU moderne
- Rendu vidéo : Dépend de la résolution et du CRF (1-5x temps réel typiquement)

## Limitations

- Ré-encode toujours la vidéo (pas de copie directe des streams)
- Détection basée sur le volume uniquement (pas de VAD sophistiqué)
- Pas de traitement multi-pistes audio

## Licence

MIT