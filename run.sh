#!/bin/bash

# Script pour activer l'environnement virtuel et lancer cut_silence.py

# Activer l'environnement virtuel
source venv/bin/activate

# Lancer le script avec les arguments passés
python cut_silence.py "$@"