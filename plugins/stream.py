import time
import hmac
import hashlib
import base64
import json
import re
from aiohttp import web
from pyrogram.errors import FloodWait

# --- CONFIGURATION ---
SECRET_KEY = b"84b6f10c7931c890e0e1a967f6515f40192ea62f25608d0f7a75932598be6f2d"
DUMP_CHANNEL_ID = -1004478362115

class StreamServer:
    def __init__(self, bot):
        self.bot = bot 
        self.app = web.Application()
        self.app.router.add_get('/watch', self.html_player_handler)
        self.app.router.add_get('/stream', self.stream_handler)

    # ==========================================
    # 1. HTML WEB PLAYER (Sci-Fi / Neon UI)
    # ==========================================
    async def html_player_handler(self, request):
        data_param = request.query.get("data")
        sig_param = request.query.get("sig")

        if not data_param or not sig_param:
            return web.Response(text="Missing parameters", status=400)

        stream_url = f"/stream?data={data_param}&sig={sig_param}"

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Voltaic Network | Secure Stream</title>
            <!-- Tailwind CSS -->
            <script src="https://cdn.tailwindcss.com"></script>
            <!-- Plyr CSS -->
            <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
            <!-- Google Fonts -->
            <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --neon-purple: #a855f7;
                    --bg-dark: #050508;
                    --panel-bg: rgba(20, 20, 30, 0.6);
                }}
                body {{
                    background-color: var(--bg-dark);
                    background-image:
                        radial-gradient(circle at 50% 0%, rgba(168, 85, 247, 0.15) 0%, transparent 50%),
                        linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
                    background-size: 100% 100%, 30px 30px, 30px 30px;
                    color: #e2e8f0;
                    font-family: 'Space Mono', monospace;
                }}
                .neon-text {{
                    color: var(--neon-purple);
                    text-shadow: 0 0 15px rgba(168, 85, 247, 0.6), 0 0 30px rgba(168, 85, 247, 0.4);
                }}
                .glass-panel {{
                    background: var(--panel-bg);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(168, 85, 247, 0.15);
                    box-shadow: 0 0 30px rgba(0, 0, 0, 0.8), inset 0 0 20px rgba(168, 85, 247, 0.05);
                }}
                .plyr {{
                    --plyr-color-main: var(--neon-purple);
                    --plyr-video-background: transparent;
                    border-radius: 0.5rem;
                }}
                .status-dot {{
                    width: 8px;
                    height: 8px;
                    background-color: var(--neon-purple);
                    border-radius: 50%;
                    box-shadow: 0 0 8px var(--neon-purple);
                    display: inline-block;
                    animation: pulse 2s infinite;
                }}
                @keyframes pulse {{
                    0% {{ opacity: 1; box-shadow: 0 0 12px var(--neon-purple); }}
                    50% {{ opacity: 0.4; box-shadow: 0 0 2px var(--neon-purple); }}
                    100% {{ opacity: 1; box-shadow: 0 0 12px var(--neon-purple); }}
                }}
            </style>
        </head>
        <body class="min-h-screen flex flex-col items-center p-4 md:p-8">

            <!-- Top Navigation -->
            <nav class="w-full max-w-6xl flex justify-between items-center text-xs tracking-widest text-gray-400 z-50 uppercase mb-12 mt-4">
                <div class="flex items-center gap-3">
                    <span class="status-dot"></span>
                    <span class="text-white font-bold tracking-[0.2em]">VOLTAIC NETWORK</span>
                </div>
                <div class="hidden md:flex gap-8">
                    <span class="hover:text-purple-400 cursor-pointer transition">INDEX</span>
                    <span class="hover:text-purple-400 cursor-pointer transition">SYLLABUS</span>
                    <span class="hover:text-purple-400 cursor-pointer transition">RESOURCES</span>
                </div>
            </nav>

            <!-- Main Content -->
            <main class="w-full max-w-4xl flex flex-col items-center">
                
                <h1 class="text-3xl md:text-5xl font-black tracking-widest neon-text mb-4 uppercase text-center">
                    SECURE STREAM
                </h1>
                <p class="text-gray-500 text-xs md:text-sm mb-10 tracking-[0.1em]">
                    // LOC_SYS: <span id="clock"></span>
                </p>

                <!-- Video Player Container -->
                <div class="glass-panel w-full rounded-xl p-2 relative shadow-2xl mb-8">
                    <div class="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-purple-500/50 rounded-tl-xl"></div>
                    <div class="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-purple-500/50 rounded-tr-xl"></div>
                    <div class="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-purple-500/50 rounded-bl-xl"></div>
                    <div class="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-purple-500/50 rounded-br-xl"></div>

                    <video id="player" playsinline controls class="w-full rounded-lg">
                        <source src="{stream_url}" type="video/mp4" />
                    </video>
                </div>

                <!-- Bottom Data Metrics -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 w-full">
                    <div class="glass-panel rounded-lg p-5 flex flex-col items-center justify-center text-center">
                        <p class="text-[10px] text-gray-500 tracking-widest mb-2 uppercase">Target Metric</p>
                        <p class="text-sm font-bold text-gray-200">Active Connection</p>
                    </div>
                    <div class="glass-panel rounded-lg p-5 flex flex-col items-center justify-center text-center">
                        <p class="text-[10px] text-gray-500 tracking-widest mb-2 uppercase">Evaluation Mode</p>
                        <p class="text-sm font-bold text-purple-400">Encrypted Relay</p>
                    </div>
                    <div class="glass-panel rounded-lg p-5 flex flex-col items-center justify-center text-center">
                        <p class="text-[10px] text-gray-500 tracking-widest mb-2 uppercase">Time Window</p>
                        <p class="text-sm font-bold text-gray-200">15 Minutes</p>
                    </div>
                </div>
            </main>

            <script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
            <script>
                document.addEventListener('DOMContentLoaded', () => {{
                    const player = new Plyr('#player', {{
                        controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'mute', 'volume', 'captions', 'settings', 'pip', 'airplay', 'fullscreen'],
                        settings: ['quality', 'speed', 'loop']
                    }});

                    function updateClock() {{
                        const now = new Date();
                        const options = {{ day: 'numeric', month: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }};
                        document.getElementById('clock').innerText = now.toLocaleString('en-GB', options).replace(',', ' @') + ' am';
                    }}
                    setInterval(updateClock, 1000);
                    updateClock();
                }});
            </script>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type='text/html')

    # ==========================================
    # 2. RAW VIDEO STREAMING (Backend Data)
    # ==========================================
    async def stream_handler(self, request):
        data_param = request.query.get("data")
        sig_param = request.query.get("sig")

        if not data_param or not sig_param:
            return web.Response(text="Missing parameters", status=400)

        expected_sig = hmac.new(SECRET_KEY, data_param.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, sig_param):
            return web.Response(text="Invalid or tampered signature", status=403)

        try:
            padding = len(data_param) % 4
            if padding:
                data_param += "=" * (4 - padding)
            payload_bytes = base64.urlsafe_b64decode(data_param)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return web.Response(text="Malformed payload", status=400)

        if int(time.time()) > payload.get("exp", 0):
            return web.Response(text="Link Expired. Please request a new one from the bot.", status=410)

        message_id = payload.get("mid")
        if not message_id:
            return web.Response(text="Invalid video ID", status=400)

        try:
            msg = await self.bot.get_messages(DUMP_CHANNEL_ID, message_id)
            media = msg.video or msg.document or msg.animation
            if not media:
                return web.Response(text="Media not found", status=404)
        except Exception as e:
            return web.Response(text=f"Telegram Error: {e}", status=500)

        file_size = media.file_size
        mime_type = getattr(media, "mime_type", "video/mp4")
        file_name = getattr(media, "file_name", f"video_{message_id}.mp4")

        range_header = request.headers.get("Range")
        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = match.group(2)
                end = int(end) if end else file_size - 1
            else:
                start = 0
                end = file_size - 1
        else:
            start = 0
            end = file_size - 1

        if start >= file_size or end >= file_size or start > end:
            return web.Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})

        length = end - start + 1

        # --- ALIGNMENT FIX FOR TELEGRAM API ---
        CHUNK_SIZE = 1048576  # 1 MB chunks
        aligned_offset = start - (start % CHUNK_SIZE)
        first_part_cut = start - aligned_offset
        aligned_limit = length + first_part_cut

        headers = {
            "Content-Type": mime_type,
            "Accept-Ranges": "bytes",
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(length),
            "Content-Disposition": f'inline; filename="{file_name}"'
        }

        response = web.StreamResponse(status=206 if range_header else 200, headers=headers)
        await response.prepare(request)

        try:
            first_chunk = True
            async for chunk in self.bot.stream_media(msg, offset=aligned_offset, limit=aligned_limit):
                if first_chunk:
                    chunk = chunk[first_part_cut:]
                    first_chunk = False
                
                await response.write(chunk)
                
        except (ConnectionResetError, web.HTTPProcessingError):
            pass
        except FloodWait as e:
            print(f"Stream interrupted by FloodWait: {e}")
        except Exception as e:
            print(f"Streaming error: {e}")

        return response

# ==========================================
# 3. EXPORT TO BOT.PY
# ==========================================
async def web_server(bot):
    """
    Called by bot.py to get the web application instance.
    """
    server = StreamServer(bot)
    return server.app
