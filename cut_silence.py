#!/usr/bin/env python3
"""
SilenCut - Suppression intelligente de silence dans les vidéos
Approche robuste avec détection RMS, hystérésis et morphologie temporelle
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

import numpy as np
import librosa
import soundfile as sf


class SilenceDetector:
    def __init__(
        self,
        threshold_db: float = -40.0,
        min_silence_ms: float = 270.0,
        min_noise_ms: float = 70.0,
        hysteresis_db: float = 3.0,
        margin_ms: float = 20.0,
        window_ms: float = 20.0,
        hop_ms: float = 10.0
    ):
        self.threshold_db = threshold_db
        self.min_silence_ms = min_silence_ms
        self.min_noise_ms = min_noise_ms
        self.hysteresis_db = hysteresis_db
        self.margin_ms = margin_ms
        self.window_ms = window_ms
        self.hop_ms = hop_ms
        
        self.enter_silence_db = threshold_db - hysteresis_db
        self.exit_silence_db = threshold_db + hysteresis_db
    
    def extract_audio(self, input_file: str, temp_wav: str) -> None:
        """Extrait l'audio en mono 48kHz pour la détection."""
        cmd = [
            'ffmpeg', '-i', input_file,
            '-vn', '-ac', '1', '-ar', '48000',
            '-c:a', 'pcm_s16le', temp_wav,
            '-y', '-loglevel', 'error'
        ]
        subprocess.run(cmd, check=True)
    
    def detect_activity(self, audio_path: str, sr: int = 48000) -> np.ndarray:
        """Détecte l'activité vocale avec RMS et hystérésis."""
        print(f"Chargement de l'audio...")
        y, _ = librosa.load(audio_path, sr=sr, mono=True)
        
        win = int(self.window_ms * sr / 1000)
        hop = int(self.hop_ms * sr / 1000)
        
        print(f"Calcul du RMS (fenêtre={win}, hop={hop})...")
        rms = librosa.feature.rms(y=y, frame_length=win, hop_length=hop, center=True)[0]
        db = 20 * np.log10(rms + 1e-9)
        
        print(f"Application de l'hystérésis (entrée={self.enter_silence_db:.1f}dB, sortie={self.exit_silence_db:.1f}dB)...")
        mask_voice = np.zeros_like(db, dtype=bool)
        in_silence = True
        
        for i, d in enumerate(db):
            if in_silence and d > self.exit_silence_db:
                in_silence = False
            elif (not in_silence) and d < self.enter_silence_db:
                in_silence = True
            mask_voice[i] = not in_silence
        
        return mask_voice, hop / sr, len(y) / sr
    
    def apply_morphology(self, mask: np.ndarray, hop_duration: float) -> np.ndarray:
        """Applique la morphologie temporelle (fermeture/ouverture)."""
        min_noise_frames = int(np.ceil(self.min_noise_ms / 1000 / hop_duration))
        min_silence_frames = int(np.ceil(self.min_silence_ms / 1000 / hop_duration))
        
        print(f"Morphologie: suppression bruits <{self.min_noise_ms}ms ({min_noise_frames} frames)")
        print(f"Morphologie: conservation silences <{self.min_silence_ms}ms ({min_silence_frames} frames)")
        
        mask = self._squash_short_runs(mask, min_noise_frames, True)
        mask = self._squash_short_runs(mask, min_silence_frames, False)
        
        return mask
    
    def _squash_short_runs(self, mask: np.ndarray, min_len: int, value: bool) -> np.ndarray:
        """Supprime les runs courts d'une valeur donnée."""
        m = mask.copy()
        n = len(m)
        i = 0
        
        while i < n:
            j = i
            while j < n and m[j] == value:
                j += 1
            
            run_length = j - i
            if run_length > 0 and run_length < min_len:
                m[i:j] = not value
            
            i = j if j > i else i + 1
        
        return m
    
    def mask_to_intervals(
        self, mask: np.ndarray, hop_duration: float, total_duration: float
    ) -> List[Tuple[float, float]]:
        """Convertit le masque binaire en intervalles temporels à garder."""
        times = np.arange(len(mask)) * hop_duration
        intervals = []
        i = 0
        
        while i < len(mask):
            if mask[i]:
                j = i + 1
                while j < len(mask) and mask[j]:
                    j += 1
                
                start = max(0.0, times[i] - self.margin_ms / 1000)
                end = min(times[j-1] + hop_duration + self.margin_ms / 1000, total_duration)
                
                if end > start:
                    intervals.append((start, end))
                i = j
            else:
                i += 1
        
        return intervals
    
    def process(self, input_file: str) -> List[Tuple[float, float]]:
        """Traite un fichier et retourne les intervalles à garder."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            temp_wav = tmp.name
        
        try:
            print(f"Extraction de l'audio de {input_file}...")
            self.extract_audio(input_file, temp_wav)
            
            mask, hop_duration, total_duration = self.detect_activity(temp_wav)
            
            mask = self.apply_morphology(mask, hop_duration)
            
            intervals = self.mask_to_intervals(mask, hop_duration, total_duration)
            
            return intervals
            
        finally:
            Path(temp_wav).unlink(missing_ok=True)


class VideoProcessor:
    def __init__(self, crf: int = 18, audio_bitrate: str = '192k'):
        self.crf = crf
        self.audio_bitrate = audio_bitrate
    
    def generate_filter_complex(self, intervals: List[Tuple[float, float]]) -> str:
        """Génère le filter_complex pour FFmpeg."""
        if not intervals:
            raise ValueError("Aucun intervalle à garder!")
        
        filters = []
        outputs = []
        
        for i, (start, end) in enumerate(intervals):
            duration = end - start
            # Pas de fade vidéo pour éviter les flashs noirs
            # Micro-fades audio (3ms) pour éviter les clics aux transitions
            filters.append(f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{i}]")
            filters.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.003,afade=t=out:st={duration-0.003:.3f}:d=0.003[a{i}]")
            outputs.extend([f"[v{i}]", f"[a{i}]"])
        
        concat = f"{''.join(outputs)}concat=n={len(intervals)}:v=1:a=1[v][a]"
        filters.append(concat)
        
        return ';'.join(filters)
    
    def render(self, input_file: str, output_file: str, intervals: List[Tuple[float, float]]) -> None:
        """Effectue le rendu final avec FFmpeg."""
        if not intervals:
            print("Aucun intervalle à garder - le fichier serait vide!")
            return
        
        filter_complex = self.generate_filter_complex(intervals)
        
        cmd = [
            'ffmpeg', '-i', input_file,
            '-filter_complex', filter_complex,
            '-map', '[v]', '-map', '[a]',
            '-r', '30', '-g', '30',
            '-c:v', 'libx264', '-crf', str(self.crf),
            '-c:a', 'aac', '-b:a', self.audio_bitrate,
            '-movflags', '+faststart',
            output_file,
            '-y'
        ]
        
        print(f"Rendu de la vidéo finale...")
        subprocess.run(cmd, check=True)


def format_time(seconds: float) -> str:
    """Formate un temps en secondes en HH:MM:SS.mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def main():
    parser = argparse.ArgumentParser(
        description="SilenCut - Suppression intelligente de silence dans les vidéos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s input.mp4 output.mp4
  %(prog)s input.mp4 output.mp4 --threshold -30
  %(prog)s input.mp4 output.mp4 --min-silence 500 --min-noise 100
        """
    )
    
    parser.add_argument('input', help='Fichier vidéo d\'entrée')
    parser.add_argument('output', help='Fichier vidéo de sortie')
    
    parser.add_argument(
        '--threshold', '-t',
        type=float, default=-40.0,
        help='Seuil de détection en dBFS (défaut: -40)'
    )
    parser.add_argument(
        '--min-silence', '-s',
        type=float, default=270.0,
        help='Durée minimale de silence à supprimer en ms (défaut: 270)'
    )
    parser.add_argument(
        '--min-noise', '-n',
        type=float, default=70.0,
        help='Durée maximale de bruit à ignorer en ms (défaut: 70)'
    )
    parser.add_argument(
        '--hysteresis',
        type=float, default=3.0,
        help='Hystérésis en dB pour éviter les tremblements (défaut: 3)'
    )
    parser.add_argument(
        '--margin',
        type=float, default=20.0,
        help='Marge de sécurité en ms autour des coupes (défaut: 20)'
    )
    parser.add_argument(
        '--crf',
        type=int, default=18,
        help='CRF pour l\'encodage x264 (défaut: 18, 0=lossless, 51=pire)'
    )
    parser.add_argument(
        '--audio-bitrate',
        type=str, default='192k',
        help='Bitrate audio (défaut: 192k)'
    )
    parser.add_argument(
        '--export-intervals',
        type=str,
        help='Exporter les intervalles dans un fichier texte'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Analyser seulement, sans générer la vidéo'
    )
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Erreur: Le fichier '{args.input}' n'existe pas", file=sys.stderr)
        sys.exit(1)
    
    print("="*60)
    print("SilenCut - Suppression intelligente de silence")
    print("="*60)
    print(f"Entrée:       {args.input}")
    print(f"Sortie:       {args.output}")
    print(f"Seuil:        {args.threshold} dBFS (défaut: -40)")
    print(f"Silence min:  {args.min_silence} ms (défaut: 270)")
    print(f"Bruit max:    {args.min_noise} ms (défaut: 70)")
    print(f"Hystérésis:   {args.hysteresis} dB (défaut: 3)")
    print(f"Marge:        {args.margin} ms (défaut: 20)")
    print("="*60)
    
    detector = SilenceDetector(
        threshold_db=args.threshold,
        min_silence_ms=args.min_silence,
        min_noise_ms=args.min_noise,
        hysteresis_db=args.hysteresis,
        margin_ms=args.margin
    )
    
    try:
        intervals = detector.process(args.input)
        
        if not intervals:
            print("\nAucun segment audio détecté! Vérifiez vos paramètres.")
            sys.exit(1)
        
        print(f"\n{len(intervals)} segments détectés:")
        total_kept = 0
        for i, (start, end) in enumerate(intervals, 1):
            duration = end - start
            total_kept += duration
            print(f"  Segment {i:3d}: {format_time(start)} → {format_time(end)} ({duration:.3f}s)")
        
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
               '-of', 'default=noprint_wrappers=1:nokey=1', args.input]
        original_duration = float(subprocess.check_output(cmd).decode().strip())
        
        reduction = (1 - total_kept / original_duration) * 100
        print(f"\nDurée originale: {format_time(original_duration)}")
        print(f"Durée finale:    {format_time(total_kept)}")
        print(f"Réduction:       {reduction:.1f}%")
        
        if args.export_intervals:
            with open(args.export_intervals, 'w') as f:
                for start, end in intervals:
                    f.write(f"{start:.3f},{end:.3f}\n")
            print(f"\nIntervalles exportés dans: {args.export_intervals}")
        
        if not args.dry_run:
            processor = VideoProcessor(crf=args.crf, audio_bitrate=args.audio_bitrate)
            processor.render(args.input, args.output, intervals)
            print(f"\nVidéo générée: {args.output}")
        else:
            print("\nMode dry-run: aucune vidéo générée")
        
    except subprocess.CalledProcessError as e:
        print(f"\nErreur FFmpeg: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nErreur: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()