import os
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
DUMP_CHANNEL_ID = -1003946902565
PORT = int(os.environ.get("PORT", 8080)) 

class StreamServer:
    def __init__(self, bot):
        self.bot = bot 
        self.app = web.Application()
        # Two routes now: One for the UI, one for the raw video data
        self.app.router.add_get('/watch', self.html_player_handler)
        self.app.router.add_get('/stream', self.stream_handler)

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        print(f"🌐 Koyeb Streaming Server started on port {PORT}")

    # ==========================================
    # 1. HTML WEB PLAYER (User Interface)
    # ==========================================
    async def html_player_handler(self, request):
        data_param = request.query.get("data")
        sig_param = request.query.get("sig")

        if not data_param or not sig_param:
            return web.Response(text="Missing parameters", status=400)

        # Build the URL for the raw video stream
        stream_url = f"/stream?data={data_param}&sig={sig_param}"

        # Modern, dark-themed HTML video player
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Voltaic Network Player</title>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background-color: #0f0f0f;
                    color: white;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }}
                .player-container {{
                    width: 100%;
                    max-width: 900px;
                    background: #000;
                    box-shadow: 0 4px 20px rgba(0,255,255,0.1);
                    border-radius: 10px;
                    overflow: hidden;
                }}
                video {{
                    width: 100%;
                    height: auto;
                    outline: none;
                }}
                .branding {{
                    padding: 15px;
                    background: #111;
                    text-align: center;
                    font-weight: bold;
                    color: #00ffff;
                    letter-spacing: 1px;
                }}
            </style>
        </head>
        <body>
            <div class="player-container">
                <video controls autoplay playsinline>
                    <source src="{stream_url}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
                <div class="branding">⚡ VOLTAIC NETWORK STREAM ⚡</div>
            </div>
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

        # Validate the Signature
        expected_sig = hmac.new(SECRET_KEY, data_param.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, sig_param):
            return web.Response(text="Invalid or tampered signature", status=403)

        # Decode the Payload
        try:
            padding = len(data_param) % 4
            if padding:
                data_param += "=" * (4 - padding)
            payload_bytes = base64.urlsafe_b64decode(data_param)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return web.Response(text="Malformed payload", status=400)

        # Check Expiration Time
        if int(time.time()) > payload.get("exp", 0):
            return web.Response(text="Link Expired. Please request a new one from the bot.", status=410)

        message_id = payload.get("mid")
        if not message_id:
            return web.Response(text="Invalid video ID", status=400)

        # Fetch Message from Telegram using Pyrogram MTProto
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

        # Parse HTTP Range Headers (Allows users to skip forward/backward in the HTML player)
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

        # Setup Response Headers
        headers = {
            "Content-Type": mime_type,
            "Accept-Ranges": "bytes",
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(length),
            "Content-Disposition": f'inline; filename="{file_name}"'
        }

        response = web.StreamResponse(status=206 if range_header else 200, headers=headers)
        await response.prepare(request)

        # Stream Data directly from Telegram's servers to the Web Player
        try:
            async for chunk in self.bot.stream_media(msg, offset=start, limit=length):
                await response.write(chunk)
        except (ConnectionResetError, web.HTTPProcessingError):
            # Normal behavior when a user skips forward in the video player
            pass
        except FloodWait as e:
            print(f"Stream interrupted by FloodWait: {e}")
        except Exception as e:
            print(f"Streaming error: {e}")

        return response

# ==========================================
# 3. WEB SERVER LAUNCHER (Resolves your ImportError)
# ==========================================
async def web_server(bot):
    """Initializes and starts the streaming server."""
    server = StreamServer(bot)
    await server.start()
