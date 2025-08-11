FROM python:3.11-slim

# Installer FFmpeg et dépendances système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Créer le répertoire de travail
WORKDIR /app

# Copier les requirements et installer les dépendances Python
COPY requirements.txt webapp/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY cut_silence.py ./
COPY webapp/ ./webapp/

# Créer les dossiers nécessaires
RUN mkdir -p webapp/uploads webapp/outputs webapp/temp webapp/static

# Exposer le port
EXPOSE 8000

# Lancer l'application
CMD ["python", "-m", "uvicorn", "webapp.app:app", "--host", "0.0.0.0", "--port", "8000"]