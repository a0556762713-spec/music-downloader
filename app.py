import os
import re
import glob
import traceback
import requests

from datetime import datetime, timezone
from flask import Flask, request, render_template_string, send_file
import yt_dlp


# ============================================================
# APP
# ============================================================

app = Flask(__name__)


# ============================================================
# FFMPEG
# ============================================================

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
    print("FFmpeg loaded successfully")
except Exception as e:
    print("Warning: static_ffmpeg not loaded:", e)


# ============================================================
# SETTINGS
# ============================================================

DOWNLOAD_FOLDER = os.path.abspath("downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

ERROR_SERVER_URL = "https://merkazia-plus.wuaze.com/wer.php"

PORT = int(os.environ.get("PORT", 10000))


# ============================================================
# STARTUP INFO
# ============================================================

print("=" * 60)
print("SERVER STARTING")
print("=" * 60)
print("PORT:", PORT)
print("ERROR SERVER:", ERROR_SERVER_URL)
print("DOWNLOAD FOLDER:", DOWNLOAD_FOLDER)

try:
    print("yt-dlp version:", yt_dlp.version.__version__)
except Exception:
    print("yt-dlp version: unknown")

print("=" * 60)


# ============================================================
# SEND ERROR TO PHP SERVER
# ============================================================

def send_error_to_remote_server(
    event,
    error_text,
    video_id="",
    youtube_url="",
    title="",
    extra=None
):
    """
    שולח את פרטי השגיאה לשרת PHP.
    אין מפתח ואין אימות מיוחד.
    """

    try:
        payload = {
            "time": datetime.now(timezone.utc).isoformat(),
            "timestamp": int(datetime.now(timezone.utc).timestamp()),

            "event": event,

            "video_id": video_id,
            "youtube_url": youtube_url,
            "title": title,

            "error": str(error_text),

            "traceback": traceback.format_exc(),

            "server": "Render",
            "extra": extra or {}
        }

        response = requests.post(
            ERROR_SERVER_URL,
            json=payload,
            timeout=10,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MusicDownloader/1.0"
            }
        )

        print("ERROR SERVER RESPONSE:", response.status_code)

    except Exception as report_error:
        print("Could not send error to PHP server:")
        print(report_error)


# ============================================================
# HEBREW ERROR TRANSLATION
# ============================================================

def translate_error_to_hebrew(error_text):
    """
    הופך שגיאות נפוצות של yt-dlp להסבר ברור בעברית.
    """

    text = str(error_text)
    lower = text.lower()

    # --------------------------------------------------------
    # YouTube BOT / LOGIN
    # --------------------------------------------------------

    if (
        "sign in to confirm" in lower
        or "you're not a bot" in lower
        or "you’re not a bot" in lower
        or "confirm you're not a bot" in lower
    ):
        return (
            "YouTube חסם את ניסיון ההורדה וביקש אימות שהשרת אינו רובוט.\n\n"
            "הבעיה אינה בקובץ או ב־FFmpeg. "
            "YouTube מזהה את השרת של Render ומבקש אימות נוסף.\n\n"
            "המערכת ניסתה להשתמש בלקוח חלופי של YouTube, "
            "אבל YouTube עדיין עלול לחסום הורדות מהשרת."
        )

    # --------------------------------------------------------
    # PRIVATE
    # --------------------------------------------------------

    if "private video" in lower:
        return (
            "הסרטון פרטי ולכן לא ניתן להוריד אותו."
        )

    # --------------------------------------------------------
    # REMOVED
    # --------------------------------------------------------

    if (
        "video unavailable" in lower
        or "video removed" in lower
        or "not found" in lower
    ):
        return (
            "הסרטון אינו זמין כרגע.\n"
            "ייתכן שהוא נמחק, הוסר או שהקישור אינו תקין."
        )

    # --------------------------------------------------------
    # REGION
    # --------------------------------------------------------

    if (
        "not available in your country" in lower
        or "not available in your region" in lower
        or "country" in lower and "available" in lower
    ):
        return (
            "הסרטון אינו זמין באזור שבו נמצא שרת ההורדה."
        )

    # --------------------------------------------------------
    # 403
    # --------------------------------------------------------

    if "403" in lower or "forbidden" in lower:
        return (
            "YouTube דחה את בקשת השרת (HTTP 403).\n\n"
            "ייתכן שהבקשה נחסמה בגלל הגבלות של YouTube "
            "או בגלל אימות של השרת."
        )

    # --------------------------------------------------------
    # 404
    # --------------------------------------------------------

    if "404" in lower:
        return (
            "הסרטון לא נמצא (HTTP 404).\n"
            "ייתכן שהקישור אינו תקין או שהסרטון הוסר."
        )

    # --------------------------------------------------------
    # 429
    # --------------------------------------------------------

    if "429" in lower or "too many requests" in lower:
        return (
            "YouTube קיבל יותר מדי בקשות מהשרת בזמן קצר.\n\n"
            "יש להמתין לפני ניסיון הורדה נוסף."
        )

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    if (
        "login required" in lower
        or "sign in" in lower
        or "authentication" in lower
    ):
        return (
            "YouTube דורש התחברות או אימות כדי לאפשר את ההורדה."
        )

    # --------------------------------------------------------
    # AGE
    # --------------------------------------------------------

    if (
        "age-restricted" in lower
        or "age restricted" in lower
    ):
        return (
            "הסרטון מוגבל לפי גיל ולכן YouTube דורש אימות משתמש."
        )

    # --------------------------------------------------------
    # FORMAT
    # --------------------------------------------------------

    if (
        "requested format is not available" in lower
        or "format is not available" in lower
    ):
        return (
            "YouTube לא סיפק פורמט מתאים להורדה עבור הסרטון הזה."
        )

    # --------------------------------------------------------
    # FFMPEG
    # --------------------------------------------------------

    if "ffmpeg" in lower:
        return (
            "אירעה בעיה בעיבוד קובץ המדיה באמצעות FFmpeg.\n\n"
            "יש לבדוק ש־FFmpeg נטען בהצלחה בשרת."
        )

    # --------------------------------------------------------
    # NETWORK
    # --------------------------------------------------------

    if (
        "timed out" in lower
        or "timeout" in lower
        or "connection reset" in lower
        or "connection refused" in lower
        or "network" in lower
    ):
        return (
            "השרת לא הצליח להשלים את החיבור ל־YouTube.\n"
            "ייתכן שמדובר בבעיה זמנית ברשת או בחסימה מצד YouTube."
        )

    # --------------------------------------------------------
    # CAPTCHA
    # --------------------------------------------------------

    if (
        "captcha" in lower
        or "verify you are human" in lower
        or "verification" in lower
    ):
        return (
            "YouTube דורש אימות אנושי לפני שניתן להמשיך בהורדה."
        )

    # --------------------------------------------------------
    # UNSUPPORTED URL
    # --------------------------------------------------------

    if "unsupported url" in lower:
        return (
            "הקישור שסופק אינו נתמך על ידי מערכת ההורדה."
        )

    # --------------------------------------------------------
    # PO TOKEN
    # --------------------------------------------------------

    if (
        "po token" in lower
        or "potoken" in lower
    ):
        return (
            "YouTube דורש PO Token עבור בקשת ההורדה.\n\n"
            "זהו מנגנון אימות של YouTube מול תוכנות הורדה."
        )

    # --------------------------------------------------------
    # GENERIC
    # --------------------------------------------------------

    return (
        "אירעה שגיאה בזמן ניסיון ההורדה מ־YouTube.\n\n"
        "המערכת לא הצליחה לזהות את סוג השגיאה באופן אוטומטי."
    )


# ============================================================
# CLEAN TITLE
# ============================================================

def clean_filename(name):
    """
    מנקה שם קובץ מתווים בעייתיים.
    """

    name = str(name)

    name = re.sub(
        r'[<>:"/\\|?*\x00-\x1F]',
        '',
        name
    )

    name = re.sub(
        r'\s+',
        ' ',
        name
    ).strip()

    if not name:
        name = "song"

    return name[:180]


# ============================================================
# SEARCH YOUTUBE
# ============================================================

def search_youtube(query):

    try:

        query = query.strip()

        if not query:
            return []

        # אם המשתמש הכניס קישור ישיר
        if re.match(
            r'https?://(www\.)?(youtube\.com|youtu\.be)/',
            query,
            re.IGNORECASE
        ):
            search_query = query
        else:
            search_query = "ytsearch8:" + query

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,

            "extract_flat": True,

            "skip_download": True,

            "noplaylist": True,

            "nocheckcertificate": True,

            # לקוח חלופי
            "extractor_args": {
                "youtube": {
                    "player_client": [
                        "web_safari"
                    ]
                }
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                search_query,
                download=False
            )

        results = []

        if not info:
            return results

        entries = info.get("entries", [])

        for entry in entries:

            if not entry:
                continue

            video_id = entry.get("id")

            if not video_id:
                continue

            title = (
                entry.get("title")
                or "ללא כותרת"
            )

            channel = (
                entry.get("channel")
                or entry.get("uploader")
                or ""
            )

            thumbnail = (
                entry.get("thumbnail")
                or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            )

            results.append({
                "id": video_id,
                "title": title,
                "artist": channel,
                "thumbnail": thumbnail,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            })

        return results

    except Exception as e:

        print("=" * 60)
        print("SEARCH ERROR")
        print("=" * 60)

        traceback.print_exc()

        send_error_to_remote_server(
            event="youtube_search",
            error_text=str(e),
            extra={
                "query": query
            }
        )

        return []


# ============================================================
# MAIN PAGE
# ============================================================

HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="he" dir="rtl">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>מוריד שירים מיוטיוב</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background:
        linear-gradient(
            135deg,
            #111827,
            #1f2937
        );
    color: white;
    min-height: 100vh;
}

.container {
    width: min(1000px, 94%);
    margin: auto;
    padding: 45px 0;
}

.header {
    text-align: center;
    margin-bottom: 35px;
}

.header h1 {
    font-size: 42px;
    margin-bottom: 10px;
}

.header p {
    color: #cbd5e1;
    font-size: 18px;
}

.search-box {
    display: flex;
    gap: 10px;
    margin-bottom: 35px;
}

.search-box input {
    flex: 1;
    padding: 17px;
    border-radius: 12px;
    border: none;
    font-size: 17px;
    direction: rtl;
}

.search-box button {
    padding: 17px 30px;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    background: #ef4444;
    color: white;
    font-size: 17px;
    font-weight: bold;
}

.search-box button:hover {
    background: #dc2626;
}

.results {
    display: grid;
    gap: 15px;
}

.card {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 15px;
    display: flex;
    gap: 18px;
    align-items: center;
}

.card img {
    width: 190px;
    height: 108px;
    object-fit: cover;
    border-radius: 10px;
}

.card-info {
    flex: 1;
}

.card-title {
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 8px;
}

.artist {
    color: #cbd5e1;
    margin-bottom: 15px;
}

.download {
    display: inline-block;
    background: #22c55e;
    color: white;
    text-decoration: none;
    padding: 11px 20px;
    border-radius: 9px;
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

    .search-box {
        flex-direction: column;
    }

    .card {
        flex-direction: column;
        align-items: stretch;
    }

    .card img {
        width: 100%;
        height: auto;
    }

    .header h1 {
        font-size: 30px;
    }
}

</style>

</head>

<body>

<div class="container">

    <div class="header">

        <h1>🎵 מוריד שירים מיוטיוב</h1>

        <p>
            חפש שיר והורד אותו כקובץ שמע
        </p>

    </div>


    <form
        class="search-box"
        method="GET"
        action="/"
    >

        <input
            type="text"
            name="q"
            value="{{ query }}"
            placeholder="כתוב שם של שיר..."
            autocomplete="off"
        >

        <button type="submit">
            🔍 חיפוש
        </button>

    </form>


    {% if query and not results %}

        <div class="empty">

            לא נמצאו תוצאות.

            <br><br>

            נסה לחפש בשם אחר.

        </div>

    {% endif %}


    <div class="results">

        {% for item in results %}

        <div class="card">

            <img
                src="{{ item.thumbnail }}"
                alt=""
            >

            <div class="card-info">

                <div class="card-title">
                    {{ item.title }}
                </div>

                <div class="artist">
                    {{ item.artist }}
                </div>

                <a
                    class="download"
                    href="/download?id={{ item.id }}&title={{ item.title|urlencode }}"
                >
                    ⬇ הורד
                </a>

            </div>

        </div>

        {% endfor %}

    </div>

</div>

</body>
</html>
"""


# ============================================================
# ERROR PAGE
# ============================================================

ERROR_TEMPLATE = r"""
<!DOCTYPE html>

<html lang="he" dir="rtl">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>שגיאה בהורדה</title>

<style>

body {
    margin: 0;
    padding: 30px;
    background: #111827;
    color: white;
    font-family: Arial, sans-serif;
}

.container {
    max-width: 850px;
    margin: 40px auto;
}

.box {
    background: #1f2937;
    border-radius: 18px;
    padding: 30px;
    border: 1px solid #374151;
}

h1 {
    color: #f87171;
}

.message {
    white-space: pre-line;
    background: #111827;
    padding: 20px;
    border-radius: 12px;
    line-height: 1.8;
    font-size: 18px;
}

.code {
    margin-top: 20px;
    color: #9ca3af;
}

details {
    margin-top: 25px;
}

summary {
    cursor: pointer;
    color: #93c5fd;
    font-weight: bold;
}

pre {
    direction: ltr;
    text-align: left;
    white-space: pre-wrap;
    background: #030712;
    color: #d1d5db;
    padding: 20px;
    border-radius: 10px;
    overflow-x: auto;
}

.back {
    display: inline-block;
    margin-top: 25px;
    padding: 13px 22px;
    background: #3b82f6;
    color: white;
    text-decoration: none;
    border-radius: 10px;
}

</style>

</head>

<body>

<div class="container">

<div class="box">

<h1>❌ ההורדה נכשלה</h1>

<div class="message">
{{ error_message }}
</div>

<div class="code">
קוד שגיאה: {{ error_code }}
</div>

{% if raw_error %}

<details>

<summary>
🔧 פרטי השגיאה הטכניים מהשרת
</summary>

<pre>{{ raw_error }}</pre>

</details>

{% endif %}

<a
    class="back"
    href="/"
>
    ← חזרה לחיפוש
</a>

</div>

</div>

</body>

</html>
"""


# ============================================================
# HOME
# ============================================================

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
        query=query,
        results=results
    )


# ============================================================
# DOWNLOAD
# ============================================================

@app.route("/download")
def download():

    video_id = request.args.get(
        "id",
        ""
    ).strip()

    title = request.args.get(
        "title",
        "song"
    ).strip()

    if not video_id:

        return render_template_string(
            ERROR_TEMPLATE,
            error_message="לא סופק מזהה של הסרטון.",
            raw_error="Missing video ID",
            error_code="MISSING-ID"
        ), 400


    youtube_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )


    # --------------------------------------------------------
    # בדיקת קבצים קיימים
    # --------------------------------------------------------

    existing_files = glob.glob(
        os.path.join(
            DOWNLOAD_FOLDER,
            video_id + ".*"
        )
    )

    if existing_files:

        existing_file = existing_files[0]

        try:

            return send_file(
                existing_file,
                as_attachment=True,
                download_name=(
                    clean_filename(title)
                    + os.path.splitext(existing_file)[1]
                )
            )

        except Exception as e:

            print("=" * 60)
            print("EXISTING FILE SEND ERROR")
            print("=" * 60)

            traceback.print_exc()

            send_error_to_remote_server(
                event="send_existing_file",
                error_text=str(e),
                video_id=video_id,
                youtube_url=youtube_url,
                title=title
            )

            return render_template_string(
                ERROR_TEMPLATE,
                error_message=translate_error_to_hebrew(e),
                raw_error=str(e),
                error_code="SEND-FILE"
            ), 500


    # --------------------------------------------------------
    # שם קובץ
    # --------------------------------------------------------

    output_template = os.path.join(
        DOWNLOAD_FOLDER,
        video_id + ".%(ext)s"
    )


    # --------------------------------------------------------
    # yt-dlp options
    # --------------------------------------------------------

    ydl_opts = {

        # אודיו / פורמט איכותי
        "format": "bestaudio/best",

        "outtmpl": output_template,

        "noplaylist": True,

        "quiet": False,

        "no_warnings": False,

        "nocheckcertificate": True,

        "retries": 2,

        "fragment_retries": 2,

        "socket_timeout": 30,

        "continuedl": True,

        # ניסיון עם לקוח YouTube חלופי
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "web_safari"
                ]
            }
        }
    }


    # --------------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------------

    try:

        print("=" * 60)
        print("DOWNLOAD START")
        print("=" * 60)

        print("VIDEO ID:", video_id)
        print("TITLE:", title)
        print("URL:", youtube_url)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            ydl.download([
                youtube_url
            ])


        # ----------------------------------------------------
        # איתור הקובץ
        # ----------------------------------------------------

        files = glob.glob(
            os.path.join(
                DOWNLOAD_FOLDER,
                video_id + ".*"
            )
        )

        if not files:

            raise Exception(
                "ההורדה הסתיימה ללא יצירת קובץ."
            )


        file_path = files[0]

        extension = os.path.splitext(
            file_path
        )[1]


        filename = (
            clean_filename(title)
            + extension
        )


        print("DOWNLOAD SUCCESS:", file_path)


        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )


    except Exception as e:

        # ----------------------------------------------------
        # שמירת שגיאה
        # ----------------------------------------------------

        print("=" * 60)
        print("DOWNLOAD ERROR")
        print("=" * 60)

        print("VIDEO ID:", video_id)
        print("TITLE:", title)
        print("URL:", youtube_url)

        print("ERROR:")
        print(str(e))

        print("TRACEBACK:")

        traceback.print_exc()

        # ----------------------------------------------------
        # שליחה לשרת PHP
        # ----------------------------------------------------

        send_error_to_remote_server(
            event="youtube_download",
            error_text=str(e),
            video_id=video_id,
            youtube_url=youtube_url,
            title=title
        )

        # ----------------------------------------------------
        # תרגום לעברית
        # ----------------------------------------------------

        hebrew_message = translate_error_to_hebrew(
            str(e)
        )


        return render_template_string(

            ERROR_TEMPLATE,

            error_message=hebrew_message,

            raw_error=str(e),

            error_code="YTDLP-DOWNLOAD"

        ), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "service": "music-downloader",
        "yt_dlp": getattr(
            yt_dlp.version,
            "__version__",
            "unknown"
        ),
        "time": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
