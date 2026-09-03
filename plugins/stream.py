import time
import json
import base64
import hmac
import hashlib
import re
import mimetypes
from aiohttp import web

SECRET_KEY = b"84b6f10c7931c890e0e1a967f6515f40192ea62f25608d0f7a75932598be6f2d"
DUMP_CHANNEL_ID = -1003946902565
TELEGRAM_CHUNK_ALIGNMENT = 4096

routes = web.RouteTableDef()

def verify_token(request):
    """Helper to verify URL signatures."""
    data = request.query.get("data")
    sig = request.query.get("sig")

    if not data or not sig:
        return None, web.Response(text="Missing required parameters.", status=400)

    expected_sig = hmac.new(SECRET_KEY, data.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, sig):
        return None, web.Response(text="Invalid or tampered link signature.", status=403)

    try:
        padding = "=" * (4 - len(data) % 4)
        decoded_json = base64.urlsafe_b64decode(data + padding).decode("utf-8")
        payload = json.loads(decoded_json)

        if int(time.time()) > payload["exp"]:
            return None, web.Response(text="⚠️ This link expired. Please search again in the bot.", status=403)

        return int(payload["mid"]), None
    except Exception:
        return None, web.Response(text="Malformed token.", status=400)


def get_media_from_message(message):
    """Extract media object and resolve proper filename and MIME type."""
    if not message:
        return None, None, 0, "video/mp4"

    media = message.video or message.document or message.animation or message.video_note
    if not media:
        return None, None, 0, "video/mp4"

    file_name = getattr(media, "file_name", None) or f"video_{message.id}.mp4"
    file_size = getattr(media, "file_size", 0)
    
    # Auto-detect accurate mime type if Telegram gives generic application/octet-stream
    mime_type = getattr(media, "mime_type", None)
    if not mime_type or mime_type == "application/octet-stream":
        guessed_type, _ = mimetypes.guess_type(file_name)
        mime_type = guessed_type or "video/mp4"

    return media, file_name, file_size, mime_type


async def stream_media_aligned(bot, message, offset_bytes: int, length_bytes: int):
    """
    Aligns the Pyrogram stream offset to Telegram's 4096-byte boundaries to prevent OFFSET_INVALID (400),
    while stripping excess padding bytes so the browser receives exactly what it requested.
    """
    aligned_offset = (offset_bytes // TELEGRAM_CHUNK_ALIGNMENT) * TELEGRAM_CHUNK_ALIGNMENT
    skip_bytes = offset_bytes - aligned_offset
    bytes_to_read = length_bytes

    async for chunk in bot.stream_media(message, offset=aligned_offset):
        if not chunk:
            break
        
        # Skip leading padding bytes that the browser didn't ask for
        if skip_bytes > 0:
            if len(chunk) <= skip_bytes:
                skip_bytes -= len(chunk)
                continue
            chunk = chunk[skip_bytes:]
            skip_bytes = 0
        
        # Stop yielding once we've fulfilled the requested length
        if bytes_to_read is not None:
            if len(chunk) > bytes_to_read:
                yield chunk[:bytes_to_read]
                break
            else:
                bytes_to_read -= len(chunk)
                
        yield chunk


# --- THE CUSTOM HTML PLAYER ---
@routes.get("/watch")
async def render_player(request):
    message_id, error_response = verify_token(request)
    if error_response:
        return error_response

    # Reconstruct query strings and absolute URLs for external app handlers
    raw_query = request.query_string
    host = request.host
    scheme = request.scheme
    
    stream_url = f"/play?{raw_query}"
    full_stream_url = f"{scheme}://{host}{stream_url}"

    # Custom intents for external player apps
    vlc_url = f"vlc://{full_stream_url}"
    mx_url = f"intent:{full_stream_url}#Intent;package=com.mxtech.videoplayer.ad;type=video/*;end"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Voltaic Network // Stream</title>
        
        <!-- Tailwind CSS & Google Fonts -->
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;700&family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        
        <!-- Plyr Video Player -->
        <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
        
        <style>
            :root {{
                --plyr-color-main: #a855f7; /* Tailwind Purple 500 */
                --plyr-video-background: #000;
            }}
            body {{
                font-family: 'Inter', sans-serif;
                background-color: #09090b;
                background-image: radial-gradient(circle at 50% 0%, rgba(168, 85, 247, 0.15), transparent 50%);
                color: #e4e4e7;
            }}
            .font-mono {{ font-family: 'Fira Code', monospace; }}
            .plyr {{ border-radius: 0.5rem; overflow: hidden; }}
        </style>
    </head>
    <body class="min-h-screen flex flex-col items-center justify-center p-4 md:p-8" oncontextmenu="return false;">
        
        <!-- Header -->
        <div class="w-full max-w-5xl flex justify-between items-center mb-6 px-2">
            <div class="flex items-center gap-3">
                <div class="w-3 h-3 rounded-full bg-purple-500 animate-pulse"></div>
                <h1 class="text-sm font-bold tracking-[0.2em] text-gray-300">VOLTAIC NETWORK</h1>
            </div>
            <div class="text-xs font-mono text-gray-500">
                // SYS_STATUS: SECURE_STREAM
            </div>
        </div>

        <!-- Video Container -->
        <div class="w-full max-w-5xl glass-card rounded-xl p-2 md:p-4 relative">
            <video id="player" playsinline controls class="w-full h-auto rounded-lg shadow-2xl">
                <source src="{stream_url}" />
            </video>
        </div>

        <!-- External Player Fallback Buttons -->
        <div class="w-full max-w-5xl mt-4 glass-card rounded-xl p-4">
            <div class="text-xs font-mono text-gray-400 mb-3 flex items-center gap-2">
                <svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <span>Having playback or audio issues (e.g. MKV format)? Open in external player:</span>
            </div>
            <div class="flex flex-wrap gap-3">
                <a href="{vlc_url}" class="px-4 py-2 rounded-lg bg-orange-600/20 hover:bg-orange-600/30 border border-orange-500/30 text-orange-300 text-xs font-semibold transition-all">
                    Open in VLC
                </a>
                <a href="{mx_url}" class="px-4 py-2 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-blue-300 text-xs font-semibold transition-all">
                    Open in MX Player
                </a>
            </div>
        </div>

        <!-- Footer Info -->
        <div class="w-full max-w-5xl mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 text-center md:text-left text-sm font-mono text-gray-400">
            <div class="glass-card p-4 rounded-lg">
                <span class="block text-xs text-gray-600 mb-1">NETWORK</span>
                <a href="https://t.me/voltaic_network" target="_blank" class="text-purple-400 hover:text-purple-300 transition-colors">@voltaic_network</a>
            </div>
            <div class="glass-card p-4 rounded-lg flex items-center justify-center">
                <span class="text-gray-500">ENCRYPTED // EXPIRING LINK</span>
            </div>
            <div class="glass-card p-4 rounded-lg md:text-right">
                <span class="block text-xs text-gray-600 mb-1">DEVELOPER</span>
                Made with ❤️ by <a href="https://t.me/a3xarva" target="_blank" class="text-purple-400 hover:text-purple-300 transition-colors">@a3xarva</a>
            </div>
        </div>

        <!-- Initialize Plyr -->
        <script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', () => {{
                const player = new Plyr('#player', {{
                    controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'mute', 'volume', 'settings', 'pip', 'fullscreen'],
                    settings: ['speed', 'quality'],
                    speed: {{ selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] }},
                    keyboard: {{ focused: true, global: true }},
                }});
            }});
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

# --- THE RAW VIDEO BYTE STREAMER ---
@routes.get("/play")
async def stream_video(request):
    message_id, error_response = verify_token(request)
    if error_response:
        return error_response

    bot = request.app["bot"]

    try:
        message = await bot.get_messages(DUMP_CHANNEL_ID, message_id)
        media, file_name, file_size, mime_type = get_media_from_message(message)

        if not media or file_size == 0:
            return web.Response(text="Video file not found in database channel.", status=404)

        range_header = request.headers.get("Range", "")
        offset = 0
        limit = file_size

        if range_header:
            match = re.search(r"bytes=(\d+)-(\d*)", range_header)
            if match:
                offset = int(match.group(1))
                end = match.group(2)
                limit = (int(end) + 1) if end else file_size

        chunk_size = limit - offset
        response = web.StreamResponse(
            status=206 if range_header else 200,
            headers={
                "Content-Type": mime_type,
                "Content-Range": f"bytes {offset}-{limit-1}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
                "Content-Disposition": f'inline; filename="{file_name}"',
                "Access-Control-Allow-Origin": "*"
            }
        )

        await response.prepare(request)
        
        try:
            async for chunk in stream_media_aligned(bot, message, offset, chunk_size):
                await response.write(chunk)
        except ConnectionResetError:
            # Browser closed the connection (e.g. user skipped forward or closed page)
            pass
        except Exception as streaming_err:
            print(f"Error during video chunk write: {streaming_err}")
            
        return response

    except Exception as e:
        print(f"Streaming Error: {e}")
        return web.Response(text="Error streaming from Telegram.", status=500)

async def web_server(bot_client):
    web_app = web.Application(client_max_size=30000000)
    web_app["bot"] = bot_client
    web_app.add_routes(routes)
    return web_app
