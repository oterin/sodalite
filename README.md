# 🌊 sodalite

a friendly media downloader for the web ✨

## 💭 what is it?

sodalite is an open-source, no-fuss downloader with real-time stats and a clean interface. paste a link from a supported service, choose your quality and format, receive the file download. that's it. 🎯

## ✨ features

### 🎨 simple & intuitive
- paste any supported link and get download options instantly
- clean, mobile-friendly interface with cozy brown cottage theme 🏡
- no accounts, no ads, no tracking - just downloads

### 📊 real-time statistics
- live server status with heartbeat monitoring 💓
- connected clients counter via websockets
- total downloads and bandwidth tracking
- persistent stats that survive server restarts

### ⚙️ advanced options
- video, audio-only, or muted download modes
- multiple quality options for both video and audio
- format selection (mp4, webm, mkv, mp3, m4a)
- background processing with download queue

### 📱 mobile-first design
- responsive dialog and interface
- touch-friendly controls
- works seamlessly on all devices

## 🌐 supported services

- **tiktok** → videos and audio extraction
- ~~**youtube** → videos, shorts, and music~~ Youtube is unsupported by Sodalight for the time being
- **instagram reels** → full quality downloads
- ... more coming soon! 🚀

## 🚀 how to use

1. copy a link from any supported service
2. paste it into sodalite
3. choose your preferred quality and format
4. download your file

the download manager shows real-time progress and you can queue multiple downloads.

## 🔌 api endpoints

> **Base URL**: `https://backend.otter.llc:1335/`

### 📥 main endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sodalite/download` | Get media metadata and available formats |
| `POST` | `/sodalite/process` | Start download processing job |
| `GET` | `/sodalite/task/{task_id}` | Check task status and progress |
| `GET` | `/sodalite/download/{task_id}/file` | Download the processed file |

### 🔧 system endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sodalite/health` | Server health check and status |
| `GET` | `/sodalite/git-info` | Git repository information |
| `GET` | `/sodalite/services` | List all supported services |
| `WS` | `/sodalite/ws/stats` | Real-time statistics websocket |

## 💻 tech stack

### frontend
- **next.js 15** with react 19
- **tailwindcss 4** with a custom cozy theme 🎨
- **framer-motion** for smooth animations
- **radix-ui** components
- **axios** for api communication
- **websockets** for real-time updates

### backend
- **fastapi** with async/await
- **yt-dlp** for youtube downloads
- **aiohttp** for http requests
- **ffmpeg** for media processing
- **websockets** for live statistics
- **file-based persistence** for statistics

## ⚠️ disclaimer

this project is provided for demonstration and educational purposes only. its use may be subject to legal considerations depending on your location. the author(s) and contributors are not responsible for any outcomes from using, sharing, or modifying this software. users should ensure they follow applicable laws and regulations. proceed at your own discretion.

## 📦 installation

### 🛠️ development setup

1. clone the repository
```bash
git clone https://github.com/oterin/sodalite.git
cd sodalite
```

2. set up the backend
```bash
cd server
pip install -r requirements.txt
python run.py
```

3. set up the frontend
```bash
cd frontend
npm install
npm run dev
```

### 🚀 production deployment

the project is designed to be deployed on:
- **backend** → any python hosting service
- **frontend** → vercel (or similar)
- **requirements** → ffmpeg installed on server

## 🤝 contributing

pull requests welcome! please:
- check existing issues before opening new ones
- follow the existing code style
- test your changes thoroughly
- update documentation as needed

## 💖 special thanks

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) → youtube download backend
- [fastapi](https://fastapi.tiangolo.com/) → modern python api framework
- [next.js](https://nextjs.org/) → react framework
- [tailwindcss](https://tailwindcss.com/) → utility-first css

## use of artificial intelligence
this project primarily relies on traditional programming approaches. artificial intelligence tools have been utilized in various supporting capacities throughout the development process. all core functionality is human-authored.
models used: claude opus 4, gemini 2.5 pro.

## 📄 license

MIT License

Copyright (c) 2025 Milan Oterin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
