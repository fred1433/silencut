"""
Version optimisée pour économiser la mémoire
"""

# Dans process_video_task, ajouter :

import gc  # Garbage collector

async def process_video_task(job_id: str, params: ProcessRequest):
    """Version optimisée pour la mémoire"""
    job = jobs[job_id]
    
    try:
        # Limiter la mémoire utilisée par librosa
        import os
        os.environ['LIBROSA_CACHE_DIR'] = '/tmp/librosa_cache'
        
        # ... traitement ...
        
        # Forcer le nettoyage mémoire après chaque étape
        gc.collect()
        
        # Option : Traiter par chunks au lieu de charger toute la vidéo
        # Option : Utiliser ffmpeg directement sans librosa
        
    except MemoryError:
        job["status"] = "failed"
        job["error"] = "File too large for current plan. Please try a smaller file (max 50MB)."