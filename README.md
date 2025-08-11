# SilenCut 🎬

Remove silence from videos automatically - Suppression intelligente des silences

[\![Deploy on Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/fred1433/silencut)

## Features

- 🚀 **Automatic silence detection** with adjustable threshold
- ✂️ **Smart cutting** preserving speech flow
- 📊 **70% average reduction** in video duration
- 🎯 **Web interface** - no software installation required
- 🐳 **Docker ready** for easy deployment

## Quick Start

### Web Application

```bash
cd webapp
pip install -r requirements.txt
python app.py
```

Open http://localhost:8000

### Docker

```bash
docker build -t silencut .
docker run -p 8000:8000 silencut
```

### Command Line

```bash
python cut_silence.py input.mp4 output.mp4
```

## Parameters

- **Threshold**: -40 dBFS (silence level)
- **Min silence**: 270ms (minimum silence duration to cut)
- **Min noise**: 70ms (ignore short noises)
- **Margin**: 20ms (safety margin around cuts)

## Use Cases

- 📹 **YouTube videos** - Remove awkward pauses
- 🎙️ **Podcasts** - Tighten up conversations
- 📚 **Online courses** - Make lessons more dynamic
- 🎬 **Vlogs** - Professional editing in seconds

## Tech Stack

- Python (FastAPI, librosa, numpy)
- FFmpeg for video processing
- WebSocket for real-time progress
- Docker for deployment

## License

MIT

---

Built with ❤️ for content creators
