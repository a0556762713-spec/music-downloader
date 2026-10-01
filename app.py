import os
import re
import traceback
import glob
import requests
from datetime import datetime

from flask import Flask, request, render_template_string, send_file
import yt_dlp


# ==========================================
# ניסיון להפעיל FFmpeg אם קיים
# ==========================================

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception as e:
    print(f"Warning: static_ffmpeg not loaded: {e}")


# ==========================================
# הגדרות
# ==========================================

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.abspath("downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# כתובת שרת שמקבל את השגיאות
ERROR_SERVER_URL = "https://merkazia-plus.wuaze.com/wer.php"


# ==========================================
# שליחת שגיאה לשרת החיצוני
# ==========================================

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

        response = requests.post(
            ERROR_SERVER_URL,
            json=payload,
            timeout=10
        )

        print(
            "Remote error server response:",
            response.status_code,
            response.text
        )

    except Exception as send_error:

        # אם wer.php לא עובד,
        # לא להפיל את שרת ההורדות
        print(
            "Could not send error to remote server:",
            send_error
        )


# ==========================================
# HTML ראשי
# ==========================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="he" dir="rtl">

<head>

    <meta charset="UTF-8">

    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>דביר מיוזיק - הורדת שירים מיוטיוב</title>

    <style>

        body {
            font-family: sans-serif;
            background-color: #f4f4f9;
            padding: 20px;
            direction: rtl;
        }

        .container {
            max-width: 800px;
            margin: auto;
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            text-align: center;
        }

        input[type="text"] {
            width: 60%;
            padding: 12px;
            border: 1px solid #ccc;
            border-radius: 20px;
            font-size: 16px;
            outline: none;
        }

        button {
            padding: 12px 25px;
            background: #ffcc00;
            border: none;
            border-radius: 20px;
            font-weight: bold;
            cursor: pointer;
            font-size: 16px;
        }

        button:hover {
            background: #e6b800;
        }

        .results {
            display: grid;
            grid-template-columns:
                repeat(auto-fill, minmax(220px, 1fr));

            gap: 20px;
            margin-top: 30px;
        }

        .card {
            border: 1px solid #eee;
            padding: 15px;
            border-radius: 10px;
            background: #fafafa;
            text-align: center;
        }

        .card img {
            width: 100%;
            height: 140px;
            object-fit: cover;
            border-radius: 8px;
        }

        .card h4 {
            margin: 10px 0 5px 0;
            font-size: 15px;
            height: 38px;
            overflow: hidden;
        }

        .card p {
            margin: 0 0 10px 0;
            color: #666;
            font-size: 13px;
        }

        .download-btn {
            display: block;
            background: #28a745;
            color: white;
            text-decoration: none;
            padding: 10px;
            margin-top: 10px;
            border-radius: 5px;
            font-weight: bold;
        }

        .download-btn:hover {
            background: #218838;
        }

        .info-text {
            font-size: 14px;
            color: #666;
            margin-top: 15px;
        }

    </style>

</head>

<body>

<div class="container">

    <h1>🎵 דביר מיוזיק - הורדת שירים מיוטיוב</h1>

    <form method="GET" action="/">

        <input
            type="text"
            name="q"
            placeholder="הקלד שם שיר או הדבק קישור מיוטיוב..."
            value="{{ search_query }}"
            required
        >

        <button type="submit">
            חפש
        </button>

    </form>


    {% if search_query %}

        <p class="info-text">

            תוצאות חיפוש עבור:

            <strong>
                {{ search_query }}
            </strong>

        </p>

    {% endif %}


    <div class="results">

        {% for song in results %}

            <div class="card">

                <img
                    src="{{ song.thumbnail }}"
                    alt="תמונה"
                >

                <h4>
                    {{ song.title }}
                </h4>

                <p>
                    {{ song.artist }}
                </p>

                <a
                    href="/download?id={{ song.id }}&title={{ song.url_title }}"
                    class="download-btn"
                >
                    ⬇ הורד שיר למחשב
                </a>

            </div>

        {% endfor %}

    </div>

</div>

</body>

</html>
"""


# ==========================================
# HTML שגיאה
# ==========================================

ERROR_TEMPLATE = """
<!DOCTYPE html>

<html lang="he" dir="rtl">

<head>

    <meta charset="UTF-8">

    <title>שגיאה בהורדה</title>

    <style>

        body {
            font-family: sans-serif;
            background-color: #fce8e6;
            padding: 30px;
            direction: rtl;
        }

        .box {
            background: white;
            padding: 25px;
            border-radius: 10px;
            max-width: 800px;
            margin: auto;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }

        h2 {
            color: #d93025;
        }

        pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            direction: ltr;
            text-align: left;
            font-size: 13px;
        }

        a {
            display: inline-block;
            margin-top: 15px;
            background: #007bff;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            text-decoration: none;
        }

    </style>

</head>

<body>

    <div class="box">

        <h2>
            ❌ אירעה שגיאה בעת ניסיון ההורדה מיוטיוב
        </h2>

        <p>
            להלן פירוט השגיאה המדויק מהשרת:
        </p>

        <pre>{{ error_details }}</pre>

        <br>

        <a href="/">
            חזרה לעמוד הראשי
        </a>

    </div>

</body>

</html>
"""


# ==========================================
# חיפוש ביוטיוב
# ==========================================

def search_youtube(query):

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
    }

    results = []

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            target = query.strip()

            if not (
                "youtube.com" in target
                or
                "youtu.be" in target
            ):

                target = f"ytsearch8:{target}"

            info = ydl.extract_info(
                target,
                download=False
            )

            if "entries" in info:
                entries = info.get("entries", [])
            else:
                entries = [info]

            for entry in entries:

                if not entry:
                    continue

                v_id = entry.get("id")

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

                    "id": v_id,

                    "title": title,

                    "artist":
                        entry.get("uploader")
                        or
                        entry.get("channel")
                        or
                        "יוטיוב",

                    "thumbnail":
                        f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg",

                    "url_title": clean_title
                })

    except Exception as e:

        full_error = traceback.format_exc()

        print("SEARCH ERROR:")
        print(full_error)

        # גם שגיאות חיפוש נשלחות לשרת
        send_error_to_remote_server(

            event="youtube_search_error",

            error=str(e),

            traceback_text=full_error,

            extra={
                "query": query,
                "user_agent":
                    request.headers.get(
                        "User-Agent",
                        ""
                    )
            }
        )

    return results


# ==========================================
# דף הבית
# ==========================================

@app.route("/")
def home():

    query = request.args.get(
        "q",
        ""
    ).strip()

    results = []

    if query:
        results = search_youtube(query)

    return render_template_string(

        HTML_PAGE,

        search_query=query,

        results=results
    )


# ==========================================
# הורדה
# ==========================================

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

    url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )


    # ======================================
    # בדיקה אם הקובץ כבר קיים
    # ======================================

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

        return send_file(

            filepath,

            as_attachment=True,

            download_name=
                f"{clean_title}.{ext}"
        )


    # ======================================
    # הגדרות yt-dlp
    # ======================================

    ydl_opts = {

        "format":
            "bestaudio/best",

        "outtmpl":
            os.path.join(
                DOWNLOAD_FOLDER,
                f"{video_id}.%(ext)s"
            ),

        "nocheckcertificate":
            True,

        "noplaylist":
            True,

        "quiet":
            True,

        "no_warnings":
            True,
    }


    # ======================================
    # ניסיון הורדה
    # ======================================

    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.download([url])


        # ==================================
        # חיפוש הקובץ שהורד
        # ==================================

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

            return send_file(

                filepath,

                as_attachment=True,

                download_name=
                    f"{clean_title}.{ext}"
            )

        else:

            raise Exception(
                "ההורדה הסתיימה אך הקובץ "
                "לא נמצא בתיקיית downloads."
            )


    # ======================================
    # טיפול בשגיאה
    # ======================================

    except Exception as e:

        full_error = traceback.format_exc()

        print("")
        print("========================================")
        print("DOWNLOAD ERROR")
        print("========================================")
        print(full_error)
        print("========================================")
        print("")


        # ==================================
        # שליחת השגיאה ל־wer.php
        # ==================================

        send_error_to_remote_server(

            event="youtube_download_error",

            video_id=video_id,

            youtube_url=url,

            title=clean_title,

            error=str(e),

            traceback_text=full_error,

            extra={

                "request_args":
                    dict(request.args),

                "user_agent":
                    request.headers.get(
                        "User-Agent",
                        ""
                    ),

                "host":
                    request.host
            }
        )


        # ==================================
        # הצגת השגיאה למשתמש
        # ==================================

        return render_template_string(

            ERROR_TEMPLATE,

            error_details=full_error

        ), 500


# ==========================================
# הפעלת השרת
# ==========================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            7860
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
