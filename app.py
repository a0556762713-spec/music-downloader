import os
import re
import traceback
import glob
import requests
from datetime import datetime

from flask import Flask, request, render_template_string, send_file
import yt_dlp


# =========================================================
# FFmpeg
# =========================================================

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
    print("FFmpeg loaded successfully")
except Exception as e:
    print(f"Warning: static_ffmpeg not loaded: {e}")


# =========================================================
# Flask
# =========================================================

app = Flask(__name__)


# =========================================================
# Downloads folder
# =========================================================

DOWNLOAD_FOLDER = os.path.abspath("downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# =========================================================
# Remote error server
# =========================================================

ERROR_SERVER_URL = "https://merkazia-plus.wuaze.com/wer.php"


# =========================================================
# Send error to PHP server
# =========================================================

def send_error_to_remote_server(
    event="download_error",
    video_id="",
    youtube_url="",
    title="",
    error="",
    traceback_text="",
    extra=None
):
    try:
        payload = {
            "event": event,
            "video_id": video_id,
            "youtube_url": youtube_url,
            "title": title,
            "error": error,
            "traceback": traceback_text,
            "server": "music-downloader-laf6.onrender.com",
            "time": datetime.utcnow().isoformat(),
            "extra": extra or {}
        }

        print("========================================")
        print("SENDING ERROR TO REMOTE SERVER")
        print("========================================")
        print("URL:", ERROR_SERVER_URL)
        print("EVENT:", event)
        print("VIDEO ID:", video_id)
        print("TITLE:", title)
        print("ERROR:", error)
        print("========================================")

        response = requests.post(
            ERROR_SERVER_URL,
            json=payload,
            timeout=15
        )

        print("========================================")
        print("REMOTE SERVER RESPONSE")
        print("========================================")
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)
        print("========================================")

    except Exception as send_error:
        print("========================================")
        print("FAILED TO SEND ERROR TO REMOTE SERVER")
        print("========================================")
        print("ERROR:", str(send_error))
        print("========================================")


# =========================================================
# Main HTML
# =========================================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>Music Downloader</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #111827, #1f2937);
            color: white;
            min-height: 100vh;
        }

        .container {
            width: 95%;
            max-width: 1100px;
            margin: auto;
            padding: 40px 0;
        }

        h1 {
            text-align: center;
            font-size: 42px;
            margin-bottom: 10px;
        }

        .subtitle {
            text-align: center;
            color: #cbd5e1;
            margin-bottom: 35px;
        }

        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 35px;
        }

        .search-box input {
            flex: 1;
            padding: 17px;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            outline: none;
        }

        .search-box button {
            padding: 17px 28px;
            border: none;
            border-radius: 12px;
            background: #ef4444;
            color: white;
            font-size: 18px;
            cursor: pointer;
            font-weight: bold;
        }

        .search-box button:hover {
            background: #dc2626;
        }

        .results {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }

        .card {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 18px;
            overflow: hidden;
            backdrop-filter: blur(10px);
            transition: 0.2s;
        }

        .card:hover {
            transform: translateY(-4px);
        }

        .thumbnail {
            width: 100%;
            aspect-ratio: 16 / 9;
            object-fit: cover;
            display: block;
        }

        .card-content {
            padding: 18px;
        }

        .title {
            font-size: 19px;
            font-weight: bold;
            line-height: 1.4;
            margin-bottom: 8px;
        }

        .artist {
            color: #cbd5e1;
            margin-bottom: 16px;
        }

        .download {
            display: block;
            width: 100%;
            text-align: center;
            text-decoration: none;
            background: #22c55e;
            color: white;
            padding: 13px;
            border-radius: 10px;
            font-weight: bold;
        }

        .download:hover {
            background: #16a34a;
        }

        .empty {
            text-align: center;
            color: #cbd5e1;
            padding: 40px;
        }

        @media (max-width: 650px) {
            h1 {
                font-size: 32px;
            }

            .search-box {
                flex-direction: column;
            }

            .search-box button {
                width: 100%;
            }
        }
    </style>
</head>

<body>

<div class="container">

    <h1>🎵 Music Downloader</h1>

    <div class="subtitle">
        חפש שירים והורד אותם
    </div>

    <form class="search-box" method="GET" action="/">
        <input
            type="text"
            name="q"
            value="{{ search_query }}"
            placeholder="חפש שיר או הדבק קישור מיוטיוב..."
            autocomplete="off"
            required
        >

        <button type="submit">
            🔍 חיפוש
        </button>
    </form>

    {% if search_query and not results %}

        <div class="empty">
            ❌ לא נמצאו תוצאות
        </div>

    {% elif results %}

        <div class="results">

            {% for item in results %}

                <div class="card">

                    <img
                        class="thumbnail"
                        src="{{ item.thumbnail }}"
                        alt="thumbnail"
                    >

                    <div class="card-content">

                        <div class="title">
                            {{ item.title }}
                        </div>

                        <div class="artist">
                            {{ item.artist }}
                        </div>

                        <a
                            class="download"
                            href="/download?id={{ item.id }}&title={{ item.url_title }}"
                        >
                            ⬇️ הורדה
                        </a>

                    </div>

                </div>

            {% endfor %}

        </div>

    {% endif %}

</div>

</body>
</html>
"""


# =========================================================
# Error HTML
# =========================================================

ERROR_TEMPLATE = """
<!DOCTYPE html>
<html lang="he" dir="rtl">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>שגיאה בהורדה</title>

    <style>
        body {
            margin: 0;
            padding: 30px;
            background: #111827;
            color: white;
            font-family: Arial, sans-serif;
        }

        .box {
            max-width: 1000px;
            margin: auto;
            background: #1f2937;
            padding: 30px;
            border-radius: 18px;
        }

        h1 {
            color: #ef4444;
        }

        pre {
            direction: ltr;
            text-align: left;
            white-space: pre-wrap;
            word-break: break-word;
            background: #000;
            padding: 20px;
            border-radius: 12px;
            overflow-x: auto;
        }

        a {
            display: inline-block;
            margin-top: 20px;
            background: #3b82f6;
            color: white;
            text-decoration: none;
            padding: 12px 20px;
            border-radius: 10px;
        }
    </style>
</head>

<body>

<div class="box">

    <h1>❌ אירעה שגיאה בהורדה</h1>

    <p>
        פרטי השגיאה:
    </p>

    <pre>{{ error_details }}</pre>

    <a href="/">
        ← חזרה לחיפוש
    </a>

</div>

</body>
</html>
"""


# =========================================================
# YouTube search
# =========================================================

def search_youtube(query):

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True
    }

    results = []

    try:

        target = query.strip()

        if not (
            "youtube.com" in target
            or "youtu.be" in target
        ):
            target = f"ytsearch8:{target}"

        print("SEARCHING:", target)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                target,
                download=False
            )

        entries = (
            info.get("entries", [])
            if "entries" in info
            else [info]
        )

        for entry in entries:

            if not entry:
                continue

            video_id = entry.get("id")

            if not video_id:
                continue

            title = entry.get(
                "title",
                "שיר"
            )

            clean_title = re.sub(
                r"[^\w\s\d\-_~.-]",
                "",
                title
            ) or "song"

            results.append({
                "id": video_id,
                "title": title,
                "artist": (
                    entry.get("uploader")
                    or entry.get("channel")
                    or "יוטיוב"
                ),
                "thumbnail": (
                    f"https://i.ytimg.com/vi/"
                    f"{video_id}/hqdefault.jpg"
                ),
                "url_title": clean_title
            })

        print("SEARCH RESULTS:", len(results))

    except Exception as e:

        full_error = traceback.format_exc()

        print("========================================")
        print("SEARCH ERROR")
        print("========================================")
        print(full_error)
        print("========================================")

        send_error_to_remote_server(
            event="youtube_search_error",
            error=str(e),
            traceback_text=full_error,
            extra={
                "query": query,
                "user_agent": request.headers.get(
                    "User-Agent",
                    ""
                ),
                "host": request.host
            }
        )

    return results


# =========================================================
# Home
# =========================================================

@app.route("/")
def home():

    query = request.args.get(
        "q",
        ""
    ).strip()

    results = (
        search_youtube(query)
        if query
        else []
    )

    return render_template_string(
        HTML_PAGE,
        search_query=query,
        results=results
    )


# =========================================================
# Download
# =========================================================

@app.route("/download")
def download():

    video_id = request.args.get("id")

    title = request.args.get(
        "title",
        "song"
    )

    if not video_id:

        return (
            "חסר מזהה סרטון (Video ID)",
            400
        )

    clean_title = re.sub(
        r"[^\w\s\d\-_~.-]",
        "",
        title
    ) or "song"

    youtube_url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    # -----------------------------------------------------
    # Check existing file
    # -----------------------------------------------------

    existing_files = glob.glob(
        os.path.join(
            DOWNLOAD_FOLDER,
            f"{video_id}.*"
        )
    )

    if existing_files:

        filepath = existing_files[0]

        ext = filepath.rsplit(
            ".",
            1
        )[-1]

        print(
            "USING EXISTING FILE:",
            filepath
        )

        return send_file(
            filepath,
            as_attachment=True,
            download_name=f"{clean_title}.{ext}"
        )

    # -----------------------------------------------------
    # yt-dlp settings
    # -----------------------------------------------------

    ydl_opts = {

        "format": "bestaudio/best",

        "outtmpl": os.path.join(
            DOWNLOAD_FOLDER,
            f"{video_id}.%(ext)s"
        ),

        "nocheckcertificate": True,

        "noplaylist": True,

        "quiet": True,

        "no_warnings": True
    }

    # -----------------------------------------------------
    # Download
    # -----------------------------------------------------

    try:

        print("========================================")
        print("STARTING DOWNLOAD")
        print("========================================")
        print("VIDEO ID:", video_id)
        print("URL:", youtube_url)
        print("TITLE:", clean_title)
        print("========================================")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            ydl.download([
                youtube_url
            ])

        # -------------------------------------------------
        # Find downloaded file
        # -------------------------------------------------

        downloaded = glob.glob(
            os.path.join(
                DOWNLOAD_FOLDER,
                f"{video_id}.*"
            )
        )

        if downloaded:

            filepath = downloaded[0]

            ext = filepath.rsplit(
                ".",
                1
            )[-1]

            print("DOWNLOAD SUCCESS")
            print("FILE:", filepath)

            return send_file(
                filepath,
                as_attachment=True,
                download_name=f"{clean_title}.{ext}"
            )

        else:

            raise Exception(
                "ההורדה הסתיימה אך הקובץ לא נמצא "
                "בתיקיית downloads."
            )

    except Exception as e:

        full_error = traceback.format_exc()

        # -------------------------------------------------
        # Print error to Render
        # -------------------------------------------------

        print("========================================")
        print("DOWNLOAD ERROR")
        print("========================================")
        print("VIDEO ID:", video_id)
        print("URL:", youtube_url)
        print("TITLE:", clean_title)
        print("ERROR:", str(e))
        print("")
        print(full_error)
        print("========================================")

        # -------------------------------------------------
        # Send error to PHP server
        # -------------------------------------------------

        send_error_to_remote_server(

            event="youtube_download_error",

            video_id=video_id,

            youtube_url=youtube_url,

            title=clean_title,

            error=str(e),

            traceback_text=full_error,

            extra={

                "request_args": dict(
                    request.args
                ),

                "user_agent": request.headers.get(
                    "User-Agent",
                    ""
                ),

                "host": request.host
            }
        )

        # -------------------------------------------------
        # Show error to user
        # -------------------------------------------------

        return render_template_string(
            ERROR_TEMPLATE,
            error_details=full_error
        ), 500


# =========================================================
# Start server
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            7860
        )
    )

    print("========================================")
    print("SERVER STARTING")
    print("========================================")
    print("PORT:", port)
    print(
        "ERROR SERVER:",
        ERROR_SERVER_URL
    )
    print(
        "DOWNLOAD FOLDER:",
        DOWNLOAD_FOLDER
    )
    print("========================================")

    app.run(
        host="0.0.0.0",
        port=port
    )
