"""
Persister les jobs sur disque pour survivre aux redémarrages
"""
import json
import os
from pathlib import Path
from datetime import datetime

JOBS_FILE = Path("jobs.json")

def save_jobs(jobs):
    """Sauvegarde les jobs sur disque"""
    jobs_serializable = {}
    for job_id, job in jobs.items():
        job_copy = job.copy()
        if 'created_at' in job_copy and isinstance(job_copy['created_at'], datetime):
            job_copy['created_at'] = job_copy['created_at'].isoformat()
        jobs_serializable[job_id] = job_copy
    
    with open(JOBS_FILE, 'w') as f:
        json.dump(jobs_serializable, f)

def load_jobs():
    """Charge les jobs depuis le disque"""
    if not JOBS_FILE.exists():
        return {}
    
    with open(JOBS_FILE, 'r') as f:
        jobs = json.load(f)
    
    # Reconvertir les dates
    for job_id, job in jobs.items():
        if 'created_at' in job and isinstance(job['created_at'], str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
    
    return jobs