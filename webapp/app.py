#!/usr/bin/env python3
"""
SilenCut Web API - FastAPI backend pour le service de suppression de silence
"""

import os
import uuid
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import aiofiles

# Import de notre module de traitement
import sys
import gc  # Garbage collector pour optimiser la mémoire
sys.path.append('..')

# Limiter le parallélisme des libs natives (utile même si non utilisées)
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')

# Utiliser la version FFmpeg légère pour économiser la RAM
try:
    from cut_silence_ffmpeg import FFmpegSilenceDetector as SilenceDetector
    from cut_silence_ffmpeg import FFmpegVideoProcessor as VideoProcessor
    print("✅ Using lightweight FFmpeg version")
except ImportError:
    from cut_silence import SilenceDetector, VideoProcessor
    print("⚠️ Using standard librosa version")

# Import local pour la persistance
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
from persist_jobs import save_jobs, load_jobs

app = FastAPI(title="SilenCut API", version="1.1.0")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, limiter aux domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
TEMP_DIR = Path("temp")
MAX_FILE_SIZE = 300 * 1024 * 1024  # 300 MB (optimisé pour 512MB RAM)
CLEANUP_AFTER_HOURS = 2

# Créer les dossiers nécessaires
for dir_path in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    dir_path.mkdir(exist_ok=True)

# Stockage des jobs avec persistance
jobs: Dict[str, Dict[str, Any]] = load_jobs()

# WebSocket connections pour les notifications
websocket_connections: Dict[str, WebSocket] = {}

# Sémaphore globale pour éviter plusieurs encodages simultanés (512MB RAM)
PROCESSING_SEMAPHORE = asyncio.Semaphore(1)


class ProcessRequest(BaseModel):
    """Paramètres de traitement"""
    threshold_db: float = Field(default=-40.0, ge=-60, le=-20)
    min_silence_ms: float = Field(default=270.0, ge=100, le=2000)
    min_noise_ms: float = Field(default=70.0, ge=0, le=500)
    hysteresis_db: float = Field(default=3.0, ge=1, le=10)
    margin_ms: float = Field(default=20.0, ge=0, le=200)
    crf: int = Field(default=20, ge=0, le=51)  # 20 est un bon compromis qualité/taille
    audio_bitrate: str = Field(default="192k")


class JobStatus(BaseModel):
    """Statut d'un job de traitement"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: float = 0.0
    message: str = ""
    input_file: str = ""
    output_file: Optional[str] = None
    created_at: datetime
    duration_original: Optional[float] = None
    duration_final: Optional[float] = None
    reduction_percent: Optional[float] = None
    error: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def home():
    """Page d'accueil avec interface simple"""
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(content=html_path.read_text())


@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict[str, str]:
    """Upload d'une vidéo"""
    
    # Vérifications
    if not file.filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4a', '.mp3', '.wav')):
        raise HTTPException(400, "Format de fichier non supporté")
    
    # Vérifier la taille
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    # Générer un ID unique
    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    
    # Sauvegarder le fichier
    try:
        async with aiofiles.open(input_path, 'wb') as f:
            while chunk := await file.read(chunk_size):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    await f.close()
                    os.remove(input_path)
                    raise HTTPException(413, f"Fichier trop volumineux (max {MAX_FILE_SIZE//1024//1024}MB)")
                await f.write(chunk)
    except Exception as e:
        if input_path.exists():
            input_path.unlink()
        raise HTTPException(500, f"Erreur lors de l'upload: {str(e)}")
    
    # Créer le job
    jobs[job_id] = {
        "job_id": job_id,
        "status": "uploaded",
        "progress": 0.0,
        "message": "Fichier uploadé, prêt pour le traitement",
        "input_file": str(input_path),
        "output_file": None,
        "created_at": datetime.now(),
        "file_size": file_size,
        "original_filename": file.filename
    }
    save_jobs(jobs)  # Persister après création
    
    # Programmer le nettoyage automatique
    background_tasks.add_task(cleanup_old_files)
    
    return {
        "job_id": job_id,
        "message": "Upload réussi",
        "file_size": str(file_size),
        "filename": file.filename
    }


@app.post("/process/{job_id}")
async def process_video(
    job_id: str,
    params: ProcessRequest,
    background_tasks: BackgroundTasks
) -> JobStatus:
    """Lance le traitement d'une vidéo"""
    
    if job_id not in jobs:
        raise HTTPException(404, "Job non trouvé")
    
    job = jobs[job_id]
    if job["status"] != "uploaded":
        raise HTTPException(400, f"Job déjà en cours ou terminé (status: {job['status']})")
    
    # Mettre à jour le statut
    job["status"] = "pending"
    job["message"] = "Traitement en file d'attente..."
    job["params"] = params.dict()
    save_jobs(jobs)  # Persister après mise à jour
    
    # Lancer le traitement en arrière-plan
    background_tasks.add_task(process_video_task, job_id, params)
    
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        input_file=job["original_filename"],
        created_at=job["created_at"]
    )


async def process_video_task(job_id: str, params: ProcessRequest):
    """Tâche de traitement vidéo en arrière-plan"""
    job = jobs[job_id]
    input_path = Path(job["input_file"])
    output_filename = f"{job_id}_processed.mp4"
    output_path = OUTPUT_DIR / output_filename
    
    # S'assurer qu'un seul traitement FFmpeg tourne à la fois
    await PROCESSING_SEMAPHORE.acquire()

    try:
        # Mettre à jour le statut
        job["status"] = "processing"
        job["progress"] = 10.0
        job["message"] = "Analyse de l'audio en cours..."
        save_jobs(jobs)  # Persister après mise à jour
        await notify_progress(job_id, job)
        
        # Libérer la mémoire après chaque étape
        gc.collect()
        
        # Créer le détecteur avec les paramètres adaptés
        # La version FFmpeg a des paramètres différents
        try:
            # Version FFmpeg légère
            detector = SilenceDetector(
                threshold_db=params.threshold_db,
                min_silence_duration=params.min_silence_ms / 1000.0,
                margin_ms=params.margin_ms
            )
            intervals = detector.get_audio_segments(str(input_path))
        except TypeError:
            # Version librosa standard
            detector = SilenceDetector(
                threshold_db=params.threshold_db,
                min_silence_ms=params.min_silence_ms,
                min_noise_ms=params.min_noise_ms,
                hysteresis_db=params.hysteresis_db,
                margin_ms=params.margin_ms
            )
            intervals = detector.process(str(input_path))
        
        # Traitement
        job["progress"] = 30.0
        job["message"] = "Détection des silences..."
        save_jobs(jobs)
        await notify_progress(job_id, job)
        gc.collect()
        
        if not intervals:
            raise ValueError("Aucun segment audio détecté")
        
        job["progress"] = 60.0
        job["message"] = f"Génération de la vidéo ({len(intervals)} segments)..."
        save_jobs(jobs)
        await notify_progress(job_id, job)
        gc.collect()
        
        # Rendu vidéo (fixer les threads FFmpeg via env pour plus de sécurité)
        os.environ.setdefault('FFMPEG_THREADS', '1')
        processor = VideoProcessor(crf=params.crf, audio_bitrate=params.audio_bitrate)
        processor.render(str(input_path), str(output_path), intervals)
        
        # Calculer les statistiques
        import subprocess
        def get_duration(file_path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)]
            return float(subprocess.check_output(cmd).decode().strip())
        
        duration_original = get_duration(input_path)
        duration_final = get_duration(output_path)
        reduction = (1 - duration_final / duration_original) * 100
        
        # Succès !
        job["status"] = "completed"
        job["progress"] = 100.0
        job["message"] = f"Traitement terminé ! Réduction de {reduction:.1f}%"
        job["output_file"] = str(output_path)
        job["duration_original"] = duration_original
        job["duration_final"] = duration_final
        job["reduction_percent"] = reduction
        save_jobs(jobs)
        
        await notify_progress(job_id, job)
        gc.collect()
        
    except MemoryError:
        job["status"] = "failed"
        job["progress"] = 0.0
        job["message"] = "Fichier trop volumineux pour le plan actuel"
        job["error"] = "Mémoire insuffisante. Essayez un fichier plus petit (max 50MB)."
        save_jobs(jobs)
        await notify_progress(job_id, job)
        print(f"Erreur mémoire {job_id}")
        gc.collect()
    except Exception as e:
        job["status"] = "failed"
        job["progress"] = 0.0
        job["message"] = "Échec du traitement"
        job["error"] = str(e)
        save_jobs(jobs)
        await notify_progress(job_id, job)
        print(f"Erreur traitement {job_id}: {e}")
        gc.collect()
    finally:
        # Libérer le sémaphore quoi qu'il arrive
        try:
            PROCESSING_SEMAPHORE.release()
        except Exception:
            pass


@app.get("/status/{job_id}")
async def get_job_status(job_id: str) -> JobStatus:
    """Récupère le statut d'un job"""
    
    if job_id not in jobs:
        raise HTTPException(404, "Job non trouvé")
    
    job = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress", 0),
        message=job.get("message", ""),
        input_file=job.get("original_filename", ""),
        output_file=job.get("output_file"),
        created_at=job["created_at"],
        duration_original=job.get("duration_original"),
        duration_final=job.get("duration_final"),
        reduction_percent=job.get("reduction_percent"),
        error=job.get("error")
    )


@app.get("/download/{job_id}")
async def download_result(job_id: str):
    """Télécharge le résultat traité"""
    
    if job_id not in jobs:
        raise HTTPException(404, "Job non trouvé")
    
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, f"Le traitement n'est pas terminé (status: {job['status']})")
    
    output_path = Path(job["output_file"])
    if not output_path.exists():
        raise HTTPException(404, "Fichier de sortie non trouvé")
    
    original_name = Path(job["original_filename"]).stem
    download_name = f"{original_name}_silencut.mp4"
    
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=download_name
    )


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket pour les notifications en temps réel"""
    await websocket.accept()
    websocket_connections[job_id] = websocket
    
    try:
        # Envoyer le statut initial
        if job_id in jobs:
            job_data = jobs[job_id].copy()
            job_data["created_at"] = job_data["created_at"].isoformat() if "created_at" in job_data else None
            await websocket.send_json(job_data)
        
        # Garder la connexion ouverte
        while True:
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        del websocket_connections[job_id]


async def notify_progress(job_id: str, job_data: dict):
    """Notifie les clients WebSocket du progrès"""
    if job_id in websocket_connections:
        try:
            # Convertir les datetime en string pour la sérialisation JSON
            safe_data = job_data.copy()
            if "created_at" in safe_data and hasattr(safe_data["created_at"], "isoformat"):
                safe_data["created_at"] = safe_data["created_at"].isoformat()
            await websocket_connections[job_id].send_json(safe_data)
        except Exception as e:
            print(f"Erreur WebSocket pour job {job_id}: {e}")
            del websocket_connections[job_id]


async def cleanup_old_files():
    """Nettoie les vieux fichiers"""
    cutoff = datetime.now() - timedelta(hours=CLEANUP_AFTER_HOURS)
    
    for job_id, job in list(jobs.items()):
        if job["created_at"] < cutoff:
            # Supprimer les fichiers
            for file_key in ["input_file", "output_file"]:
                if file_key in job and job[file_key]:
                    path = Path(job[file_key])
                    if path.exists():
                        path.unlink()
            
            # Supprimer le job
            del jobs[job_id]
    
    save_jobs(jobs)  # Persister après nettoyage
    gc.collect()  # Libérer la mémoire


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "jobs_count": len(jobs)}


@app.get("/sitemap.xml", response_class=PlainTextResponse)
async def sitemap():
    """Serve sitemap.xml for SEO"""
    sitemap_path = Path(__file__).parent / "static" / "sitemap.xml"
    if sitemap_path.exists():
        return PlainTextResponse(content=sitemap_path.read_text(), media_type="application/xml")
    raise HTTPException(404, "Sitemap not found")


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    """Serve robots.txt for SEO"""
    robots_path = Path(__file__).parent / "static" / "robots.txt"
    if robots_path.exists():
        return PlainTextResponse(content=robots_path.read_text())
    raise HTTPException(404, "Robots.txt not found")


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Optimisations mémoire pour l'environnement de production
    os.environ['LIBROSA_CACHE_DIR'] = '/tmp/librosa_cache'
    os.environ['NUMBA_CACHE_DIR'] = '/tmp/numba_cache'
    
    # Forcer un garbage collection au démarrage
    gc.collect()
    
    print(f"🚀 Démarrage de SilenCut avec {len(jobs)} jobs restaurés")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)