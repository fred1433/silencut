#!/usr/bin/env python3
"""
Version optimisée de FFmpeg pour petits fichiers (<50MB)
Utilise des paramètres plus agressifs pour la vitesse
"""

import subprocess
import re
from pathlib import Path
from typing import List, Tuple

class FFmpegSilenceDetectorFast:
    def __init__(
        self,
        threshold_db: float = -40.0,
        min_silence_duration: float = 0.3,
        margin_ms: float = 20.0
    ):
        self.threshold_db = threshold_db
        self.min_silence_duration = min_silence_duration
        self.margin_s = margin_ms / 1000.0
    
    def detect_silence(self, input_file: str) -> List[Tuple[float, float]]:
        """Détecte les silences avec FFmpeg - version rapide"""
        cmd = [
            'ffmpeg',
            '-hide_banner', '-nostats',
            # Analyse minimale pour vitesse max
            '-analyzeduration', '0', '-probesize', '32k',
            '-threads', '1',
            '-vn', '-sn', '-dn',
            '-i', input_file,
            '-af', f'silencedetect=noise={self.threshold_db}dB:d={self.min_silence_duration}',
            '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parser la sortie pour extraire les segments de silence
        silence_starts = re.findall(r'silence_start: ([\d.]+)', result.stderr)
        silence_ends = re.findall(r'silence_end: ([\d.]+)', result.stderr)
        
        silences = []
        for start, end in zip(silence_starts, silence_ends):
            silences.append((float(start), float(end)))
        
        return silences
    
    def get_audio_segments(self, input_file: str) -> List[Tuple[float, float]]:
        """Retourne les segments audio (inverse des silences)"""
        # Obtenir la durée totale
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
               '-of', 'default=noprint_wrappers=1:nokey=1', input_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        
        # Obtenir les silences
        silences = self.detect_silence(input_file)
        
        if not silences:
            return [(0, duration)]
        
        # Calculer les segments audio
        segments = []
        
        # Premier segment
        if silences[0][0] > 0:
            segments.append((0, silences[0][0] + self.margin_s))
        
        # Segments intermédiaires
        for i in range(len(silences) - 1):
            start = max(0, silences[i][1] - self.margin_s)
            end = min(duration, silences[i + 1][0] + self.margin_s)
            if end - start > 0.1:  # Garder seulement les segments > 100ms
                segments.append((start, end))
        
        # Dernier segment
        if silences[-1][1] < duration:
            segments.append((max(0, silences[-1][1] - self.margin_s), duration))
        
        return segments


class FFmpegVideoProcessorFast:
    def __init__(self, crf: int = 23, audio_bitrate: str = '128k'):
        self.crf = crf  # CRF plus élevé pour vitesse
        self.audio_bitrate = audio_bitrate  # Bitrate audio réduit
    
    def render(self, input_file: str, output_file: str, segments: List[Tuple[float, float]]):
        """Génère la vidéo finale avec FFmpeg - version rapide"""
        if not segments:
            raise ValueError("Aucun segment à traiter")
        
        # Construire le filtre complexe
        filter_parts = []
        concat_inputs = []
        
        for i, (start, end) in enumerate(segments):
            # Trim video
            filter_parts.append(f'[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]')
            # Trim audio
            filter_parts.append(f'[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]')
            concat_inputs.append(f'[v{i}][a{i}]')
        
        # Concatenation
        filter_complex = ';'.join(filter_parts) + ';'
        filter_complex += ''.join(concat_inputs) + f'concat=n={len(segments)}:v=1:a=1[outv][outa]'
        
        # Commande FFmpeg optimisée pour la vitesse
        cmd = [
            'ffmpeg',
            # Analyse réduite pour vitesse max
            '-analyzeduration', '10M', '-probesize', '10M',  # Réduit de 100M/50M
            # Entrée
            '-i', input_file,
            # Pas de parallélisme pour économiser la RAM
            '-filter_threads', '1', '-filter_complex_threads', '1',
            '-filter_complex', filter_complex,
            '-map', '[outv]', '-map', '[outa]',
            # Preset ultrafast pour vitesse maximale
            '-c:v', 'libx264', '-preset', 'ultrafast', '-threads', '1', '-crf', str(self.crf),
            '-c:a', 'aac', '-b:a', self.audio_bitrate,
            '-movflags', '+faststart',
            '-y', output_file
        ]
        
        subprocess.run(cmd, check=True)


# Fonction principale pour compatibilité
def process_video_fast(input_file: str, output_file: str, **kwargs):
    """Interface simple pour traiter une vidéo rapidement"""
    detector = FFmpegSilenceDetectorFast(
        threshold_db=kwargs.get('threshold_db', -40.0),
        min_silence_duration=kwargs.get('min_silence_duration', 0.3),
        margin_ms=kwargs.get('margin_ms', 20.0)
    )
    
    segments = detector.get_audio_segments(input_file)
    
    if not segments:
        raise ValueError("Aucun segment audio détecté")
    
    processor = FFmpegVideoProcessorFast(crf=kwargs.get('crf', 23))
    processor.render(input_file, output_file, segments)
    
    return segments