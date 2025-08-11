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
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import aiofiles

# Import de notre module de traitement
import sys
sys.path.append('..')
from cut_silence import SilenceDetector, VideoProcessor

app = FastAPI(title="SilenCut API", version="1.0.0")

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
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
CLEANUP_AFTER_HOURS = 2

# Créer les dossiers nécessaires
for dir_path in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    dir_path.mkdir(exist_ok=True)

# Stockage des jobs en mémoire (utiliser Redis en production)
jobs: Dict[str, Dict[str, Any]] = {}

# WebSocket connections pour les notifications
websocket_connections: Dict[str, WebSocket] = {}


class ProcessRequest(BaseModel):
    """Paramètres de traitement"""
    threshold_db: float = Field(default=-40.0, ge=-60, le=-20)
    min_silence_ms: float = Field(default=270.0, ge=100, le=2000)
    min_noise_ms: float = Field(default=70.0, ge=0, le=500)
    hysteresis_db: float = Field(default=3.0, ge=1, le=10)
    margin_ms: float = Field(default=20.0, ge=0, le=200)
    crf: int = Field(default=18, ge=0, le=51)
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
    
    try:
        # Mettre à jour le statut
        job["status"] = "processing"
        job["progress"] = 10.0
        job["message"] = "Analyse de l'audio en cours..."
        await notify_progress(job_id, job)
        
        # Créer le détecteur avec les paramètres
        detector = SilenceDetector(
            threshold_db=params.threshold_db,
            min_silence_ms=params.min_silence_ms,
            min_noise_ms=params.min_noise_ms,
            hysteresis_db=params.hysteresis_db,
            margin_ms=params.margin_ms
        )
        
        # Traitement
        job["progress"] = 30.0
        job["message"] = "Détection des silences..."
        await notify_progress(job_id, job)
        
        intervals = detector.process(str(input_path))
        
        if not intervals:
            raise ValueError("Aucun segment audio détecté")
        
        job["progress"] = 60.0
        job["message"] = f"Génération de la vidéo ({len(intervals)} segments)..."
        await notify_progress(job_id, job)
        
        # Rendu vidéo
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
        
        await notify_progress(job_id, job)
        
    except Exception as e:
        job["status"] = "failed"
        job["progress"] = 0.0
        job["message"] = "Échec du traitement"
        job["error"] = str(e)
        await notify_progress(job_id, job)
        print(f"Erreur traitement {job_id}: {e}")


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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "jobs_count": len(jobs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)