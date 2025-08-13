FROM python:3.11-slim

# Installer FFmpeg et dépendances système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Créer le répertoire de travail
WORKDIR /app

# Copier les requirements de l'app web et installer les dépendances (sans librosa/numpy)
COPY webapp/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application (incluant la version FFmpeg)
COPY cut_silence.py ./
COPY cut_silence_ffmpeg.py ./
COPY webapp/ ./webapp/

# Créer les dossiers nécessaires
RUN mkdir -p webapp/uploads webapp/outputs webapp/temp webapp/static

# Limiter le parallélisme des libs natives par défaut
ENV OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1

# Exposer le port
EXPOSE 8000

# Lancer l'application
CMD ["python", "-m", "uvicorn", "webapp.app:app", "--host", "0.0.0.0", "--port", "8000"]