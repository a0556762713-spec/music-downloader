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

    print(
        "Warning: static_ffmpeg not loaded:",
        e
    )


# =========================================================
# Flask
# =========================================================

app = Flask(__name__)


# =========================================================
# Downloads folder
# =========================================================

DOWNLOAD_FOLDER = os.path.abspath("downloads")

os.makedirs(
    DOWNLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# PHP ERROR SERVER
# =========================================================

ERROR_SERVER_URL = (
    "https://merkazia-plus.wuaze.com/wer.php"
)


# =========================================================
# SEND ERROR TO PHP SERVER
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

            "server": (
                "music-downloader-laf6.onrender.com"
            ),

            "time": datetime.utcnow().isoformat(),

            "extra": extra or {}
        }


        print()
        print("========================================")
        print("SENDING ERROR TO REMOTE SERVER")
        print("========================================")

        print(
            "URL:",
            ERROR_SERVER_URL
        )

        print(
            "EVENT:",
            event
        )

        print(
            "VIDEO ID:",
            video_id
        )

        print(
            "TITLE:",
            title
        )

        print(
            "ERROR:",
            error
        )

        print("========================================")


        response = requests.post(

            ERROR_SERVER_URL,

            json=payload,

            timeout=15

        )


        print()
        print("========================================")
        print("REMOTE SERVER RESPONSE")
        print("========================================")

        print(
            "STATUS:",
            response.status_code
        )

        print(
            "RESPONSE:",
            response.text
        )

        print("========================================")


    except Exception as send_error:

        print()
        print("========================================")
        print("FAILED TO SEND ERROR TO REMOTE SERVER")
        print("========================================")

        print(
            "ERROR:",
            str(send_error)
        )

        print("========================================")


# =========================================================
# TRANSLATE ERROR TO HEBREW
# =========================================================

def translate_error_to_hebrew(error_text):

    error = str(error_text).lower()


    # Video unavailable
    if (
        "video unavailable" in error
        or "video is unavailable" in error
    ):

        return (
            "הסרטון אינו זמין כרגע ביוטיוב. "
            "ייתכן שהוא נמחק, פרטי או חסום לצפייה."
        )


    # Private video
    if "private video" in error:

        return (
            "הסרטון פרטי ולכן לא ניתן להוריד אותו."
        )


    # Deleted
    if (
        "video has been removed" in error
        or "has been removed" in error
        or "video not found" in error
    ):

        return (
            "הסרטון כנראה נמחק או אינו קיים יותר ביוטיוב."
        )


    # Region restriction
    if (
        "not available in your country" in error
        or "geo" in error
        or "country" in error
    ):

        return (
            "הסרטון אינו זמין באזור שבו השרת נמצא."
        )


    # 403
    if (
        "http error 403" in error
        or "403 forbidden" in error
        or "error 403" in error
    ):

        return (
            "יוטיוב דחה את בקשת ההורדה מהשרת. "
            "ייתכן שיוטיוב חסם זמנית את כתובת השרת "
            "או שהגישה לסרטון מוגבלת."
        )


    # 404
    if (
        "http error 404" in error
        or "404 not found" in error
        or "error 404" in error
    ):

        return (
            "הסרטון או המשאב הנדרש לא נמצאו."
        )


    # 429
    if (
        "http error 429" in error
        or "too many requests" in error
        or "error 429" in error
    ):

        return (
            "נשלחו יותר מדי בקשות ליוטיוב. "
            "יש להמתין מעט ולנסות שוב."
        )


    # Sign in
    if (
        "sign in" in error
        or "login" in error
        or "log in" in error
    ):

        return (
            "יוטיוב דורש התחברות או אימות "
            "כדי לגשת לסרטון הזה."
        )


    # Age restriction
    if (
        "age-restricted" in error
        or "age restricted" in error
    ):

        return (
            "הסרטון מוגבל לפי גיל ולכן לא ניתן "
            "להוריד אותו דרך השרת."
        )


    # Format unavailable
    if (
        "requested format is not available" in error
        or "format is not available" in error
    ):

        return (
            "לא נמצא פורמט שמע מתאים להורדה "
            "עבור הסרטון הזה."
        )


    # FFmpeg
    if "ffmpeg" in error:

        return (
            "השרת נתקל בבעיה בעיבוד קובץ המדיה. "
            "ייתכן שיש בעיה ב־FFmpeg או בפורמט שהתקבל."
        )


    # Network
    if (
        "connection" in error
        or "timed out" in error
        or "timeout" in error
        or "network" in error
    ):

        return (
            "השרת לא הצליח להתחבר ליוטיוב בזמן ההורדה. "
            "ייתכן שמדובר בתקלה זמנית בחיבור."
        )


    # Unsupported URL
    if (
        "unsupported url" in error
        or "unsupported" in error
    ):

        return (
            "הקישור שסופק אינו נתמך או שאינו קישור תקין."
        )


    # Bot / verification
    if (
        "captcha" in error
        or "confirm you are human" in error
        or "sign in to confirm" in error
        or "not a bot" in error
    ):

        return (
            "יוטיוב דורש אימות נוסף לפני שניתן לגשת לסרטון. "
            "השרת לא הצליח להשלים את האימות."
        )


    # Generic
    return (
        "השרת לא הצליח להוריד את הסרטון. "
        "ייתכן שמדובר בתקלה זמנית ביוטיוב "
        "או בשרת."
    )


# =========================================================
# MAIN HTML
# =========================================================

HTML_PAGE = """
<!DOCTYPE html>

<html lang="he" dir="rtl">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Music Downloader</title>


<style>

* {
    box-sizing: border-box;
}


body {

    margin: 0;

    padding: 0;

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

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(280px, 1fr)
        );

    gap: 20px;
}


.card {

    background:
        rgba(
            255,
            255,
            255,
            0.08
        );

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.1
        );

    border-radius: 18px;

    overflow: hidden;

    backdrop-filter: blur(10px);

    transition: 0.2s;
}


.card:hover {

    transform:
        translateY(-4px);
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


<h1>
    🎵 Music Downloader
</h1>


<div class="subtitle">

    חפש שירים והורד אותם

</div>


<form
    class="search-box"
    method="GET"
    action="/"
>


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
# ERROR HTML
# =========================================================

ERROR_TEMPLATE = """
<!DOCTYPE html>

<html lang="he" dir="rtl">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>שגיאה בהורדה</title>


<style>

* {
    box-sizing: border-box;
}


body {

    margin: 0;

    padding: 30px;

    background: #111827;

    color: white;

    font-family: Arial, sans-serif;
}


.box {

    max-width: 800px;

    margin: 50px auto;

    background: #1f2937;

    padding: 35px;

    border-radius: 20px;

    box-shadow:
        0 15px 40px
        rgba(
            0,
            0,
            0,
            0.35
        );
}


.icon {

    font-size: 60px;

    text-align: center;
}


h1 {

    text-align: center;

    color: #ef4444;

    margin-bottom: 25px;
}


.message {

    background: #374151;

    padding: 20px;

    border-radius: 14px;

    font-size: 20px;

    line-height: 1.7;

    margin-bottom: 20px;
}


.details {

    background: #111827;

    padding: 15px;

    border-radius: 12px;

    color: #9ca3af;

    font-size: 14px;
}


a {

    display: block;

    text-align: center;

    margin-top: 25px;

    background: #3b82f6;

    color: white;

    text-decoration: none;

    padding: 14px 20px;

    border-radius: 12px;

    font-weight: bold;
}


a:hover {

    background: #2563eb;
}

</style>

</head>


<body>


<div class="box">


<div class="icon">

    ⚠️

</div>


<h1>

    ההורדה לא הצליחה

</h1>


<div class="message">

    {{ error_message }}

</div>


<div class="details">

    מספר שגיאה:
    {{ error_code }}

</div>


<a href="/">

    ← חזרה לחיפוש

</a>


</div>


</body>

</html>
"""


# =========================================================
# YOUTUBE SEARCH
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

            target = (
                f"ytsearch8:{target}"
            )


        print(
            "SEARCHING:",
            target
        )


        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            info = ydl.extract_info(
                target,
                download=False
            )


        entries = (

            info.get(
                "entries",
                []
            )

            if "entries" in info

            else [info]

        )


        for entry in entries:

            if not entry:
                continue


            video_id = entry.get(
                "id"
            )


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

                "id":
                    video_id,

                "title":
                    title,

                "artist":
                    (
                        entry.get(
                            "uploader"
                        )

                        or entry.get(
                            "channel"
                        )

                        or "יוטיוב"
                    ),

                "thumbnail":
                    (
                        "https://i.ytimg.com/vi/"
                        f"{video_id}/hqdefault.jpg"
                    ),

                "url_title":
                    clean_title
            })


        print(
            "SEARCH RESULTS:",
            len(results)
        )


    except Exception as e:

        full_error = (
            traceback.format_exc()
        )


        print()
        print("========================================")
        print("SEARCH ERROR")
        print("========================================")

        print(
            full_error
        )

        print("========================================")


        send_error_to_remote_server(

            event="youtube_search_error",

            error=str(e),

            traceback_text=full_error,

            extra={

                "query":
                    query,

                "user_agent":
                    request.headers.get(
                        "User-Agent",
                        ""
                    ),

                "host":
                    request.host
            }
        )


    return results


# =========================================================
# HOME
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
# DOWNLOAD
# =========================================================

@app.route("/download")
def download():

    video_id = request.args.get(
        "id"
    )


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

        "https://www.youtube.com/watch?v="

        + video_id

    )


    # =====================================================
    # CHECK EXISTING FILE
    # =====================================================

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

            download_name=(
                f"{clean_title}.{ext}"
            )

        )


    # =====================================================
    # YT-DLP SETTINGS
    # =====================================================

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
            True
    }


    # =====================================================
    # DOWNLOAD
    # =====================================================

    try:

        print()
        print("========================================")
        print("STARTING DOWNLOAD")
        print("========================================")

        print(
            "VIDEO ID:",
            video_id
        )

        print(
            "URL:",
            youtube_url
        )

        print(
            "TITLE:",
            clean_title
        )

        print("========================================")


        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.download([
                youtube_url
            ])


        # =================================================
        # FIND DOWNLOADED FILE
        # =================================================

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


            print()
            print(
                "DOWNLOAD SUCCESS"
            )

            print(
                "FILE:",
                filepath
            )


            return send_file(

                filepath,

                as_attachment=True,

                download_name=(
                    f"{clean_title}.{ext}"
                )

            )


        else:

            raise Exception(

                "ההורדה הסתיימה אך "
                "הקובץ לא נמצא בתיקיית downloads."

            )


    # =====================================================
    # DOWNLOAD ERROR
    # =====================================================

    except Exception as e:

        full_error = (
            traceback.format_exc()
        )


        print()
        print("========================================")
        print("DOWNLOAD ERROR")
        print("========================================")

        print(
            "VIDEO ID:",
            video_id
        )

        print(
            "URL:",
            youtube_url
        )

        print(
            "TITLE:",
            clean_title
        )

        print(
            "ERROR:",
            str(e)
        )

        print()

        print(
            full_error
        )

        print("========================================")


        # =================================================
        # SEND FULL TECHNICAL ERROR TO PHP
        # =================================================

        send_error_to_remote_server(

            event=
                "youtube_download_error",

            video_id=
                video_id,

            youtube_url=
                youtube_url,

            title=
                clean_title,

            error=
                str(e),

            traceback_text=
                full_error,

            extra={

                "request_args":
                    dict(
                        request.args
                    ),

                "user_agent":
                    request.headers.get(
                        "User-Agent",
                        ""
                    ),

                "host":
                    request.host
            }

        )


        # =================================================
        # CREATE HEBREW ERROR
        # =================================================

        hebrew_error = (
            translate_error_to_hebrew(
                str(e)
            )
        )


        # =================================================
        # SHOW USER-FRIENDLY ERROR
        # =================================================

        return render_template_string(

            ERROR_TEMPLATE,

            error_message=
                hebrew_error,

            error_code=
                "YTDLP-DOWNLOAD"

        ), 500


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    port = int(

        os.environ.get(
            "PORT",
            7860
        )

    )


    print()
    print("========================================")
    print("SERVER STARTING")
    print("========================================")

    print(
        "PORT:",
        port
    )

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
