#!/usr/bin/env python3
"""
Système de tracking avec historique journalier persistant
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any

STATS_FILE = Path("webapp/stats_history.json")

def get_today_key():
    """Retourne la clé du jour actuel"""
    return date.today().isoformat()

def load_stats() -> Dict[str, Any]:
    """Charge les stats depuis le fichier"""
    if STATS_FILE.exists():
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_stats(stats: Dict[str, Any]):
    """Sauvegarde les stats dans le fichier"""
    STATS_FILE.parent.mkdir(exist_ok=True)
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

def track_page_view():
    """Enregistre une vue de page"""
    stats = load_stats()
    today = get_today_key()
    
    if today not in stats:
        stats[today] = {
            "page_views": 0,
            "videos_processed": 0,
            "total_seconds_saved": 0,
            "uploads": 0,
            "errors": 0
        }
    
    stats[today]["page_views"] += 1
    save_stats(stats)

def track_video_processed(duration_original: float, duration_final: float):
    """Enregistre une vidéo traitée"""
    stats = load_stats()
    today = get_today_key()
    
    if today not in stats:
        stats[today] = {
            "page_views": 0,
            "videos_processed": 0,
            "total_seconds_saved": 0,
            "uploads": 0,
            "errors": 0
        }
    
    stats[today]["videos_processed"] += 1
    stats[today]["total_seconds_saved"] += (duration_original - duration_final)
    save_stats(stats)

def track_upload():
    """Enregistre un upload"""
    stats = load_stats()
    today = get_today_key()
    
    if today not in stats:
        stats[today] = {
            "page_views": 0,
            "videos_processed": 0,
            "total_seconds_saved": 0,
            "uploads": 0,
            "errors": 0
        }
    
    stats[today]["uploads"] += 1
    save_stats(stats)

def track_error():
    """Enregistre une erreur"""
    stats = load_stats()
    today = get_today_key()
    
    if today not in stats:
        stats[today] = {
            "page_views": 0,
            "videos_processed": 0,
            "total_seconds_saved": 0,
            "uploads": 0,
            "errors": 0
        }
    
    stats[today]["errors"] += 1
    save_stats(stats)

def get_stats_summary():
    """Retourne un résumé des stats"""
    stats = load_stats()
    
    # Stats du jour
    today = get_today_key()
    today_stats = stats.get(today, {
        "page_views": 0,
        "videos_processed": 0,
        "total_seconds_saved": 0,
        "uploads": 0,
        "errors": 0
    })
    
    # Stats totales
    total_views = sum(day.get("page_views", 0) for day in stats.values())
    total_videos = sum(day.get("videos_processed", 0) for day in stats.values())
    total_saved = sum(day.get("total_seconds_saved", 0) for day in stats.values())
    total_uploads = sum(day.get("uploads", 0) for day in stats.values())
    
    # Historique des 7 derniers jours
    from datetime import timedelta
    last_7_days = []
    for i in range(7):
        day = (date.today() - timedelta(days=i)).isoformat()
        if day in stats:
            last_7_days.append({
                "date": day,
                **stats[day]
            })
        else:
            last_7_days.append({
                "date": day,
                "page_views": 0,
                "videos_processed": 0,
                "total_seconds_saved": 0,
                "uploads": 0,
                "errors": 0
            })
    
    return {
        "today": today_stats,
        "totals": {
            "page_views": total_views,
            "videos_processed": total_videos,
            "total_seconds_saved": round(total_saved, 1),
            "total_minutes_saved": round(total_saved / 60, 1),
            "total_hours_saved": round(total_saved / 3600, 1),
            "uploads": total_uploads
        },
        "last_7_days": last_7_days,
        "all_time_data": stats
    }