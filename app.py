import os
import re
import glob
import traceback

from flask import Flask, request, render_template_string, send_file
import yt_dlp

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.abspath("downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# =========================
# ניקוי שם קובץ
# =========================

def clean_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip()
    return name[:180] or "song"


# =========================
# תרגום שגיאות
# =========================

def translate_error(error):
    text = str(error)

    if "429" in text or "Too Many Requests" in text:
        return "YouTube חסם זמנית את השרת בגלל יותר מדי בקשות."

    if "Sign in to confirm" in text:
        return "YouTube דורש אימות עבור השרת."

    if "Video unavailable" in text:
        return "הסרטון אינו זמין."

    if "Private video" in text:
        return "הסרטון פרטי."

    if "not found" in text.lower():
        return "הסרטון לא נמצא."

    return "אירעה שגיאה בהורדת הקובץ."


# =========================
# חיפוש YouTube
# =========================

def search_youtube(query):

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            f"ytsearch8:{query}",
            download=False
        )

    results = []

    for entry in info.get("entries", []):

        if not entry:
            continue

        video_id = entry.get("id")

        if not video_id:
            continue

        results.append({
            "id": video_id,
            "title": entry.get(
                "title",
                "ללא כותרת"
            ),
            "url": f"https://www.youtube.com/watch?v={video_id}"
        })

    return results


# =========================
# אתר ראשי
# =========================

@app.route("/")
def home():

    query = request.args.get("q", "").strip()

    results = []
    error = ""

    if query:

        try:
            results = search_youtube(query)

        except Exception as e:

            error = translate_error(e)

    html = """
    <!DOCTYPE html>

    <html lang="he" dir="rtl">

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Music Downloader</title>

        <style>

            body {
                margin: 0;
                background: #111;
                color: white;
                font-family: Arial, sans-serif;
            }

            .container {
                max-width: 900px;
                margin: 50px auto;
                padding: 20px;
            }

            h1 {
                text-align: center;
            }

            form {
                display: flex;
                gap: 10px;
                margin-bottom: 30px;
            }

            input {
                flex: 1;
                padding: 15px;
                border: none;
                border-radius: 10px;
                font-size: 18px;
            }

            button {
                padding: 15px 25px;
                border: none;
                border-radius: 10px;
                background: #22c55e;
                color: white;
                font-size: 17px;
                cursor: pointer;
            }

            .result {
                background: #222;
                padding: 18px;
                margin-bottom: 15px;
                border-radius: 12px;
            }

            .title {
                font-size: 18px;
                margin-bottom: 12px;
            }

            .download {
                display: inline-block;
                padding: 10px 18px;
                background: #ef4444;
                color: white;
                text-decoration: none;
                border-radius: 8px;
            }

            .error {
                background: #441111;
                padding: 15px;
                border-radius: 10px;
            }

        </style>

    </head>

    <body>

        <div class="container">

            <h1>🎵 הורדת שירים</h1>

            <form method="GET">

                <input
                    type="text"
                    name="q"
                    placeholder="חפש שיר..."
                    value="{{ query }}"
                >

                <button type="submit">
                    חיפוש
                </button>

            </form>

            {% if error %}

                <div class="error">
                    {{ error }}
                </div>

            {% endif %}

            {% for song in results %}

                <div class="result">

                    <div class="title">
                        {{ song.title }}
                    </div>

                    <a
                        class="download"
                        href="/download?id={{ song.id }}&title={{ song.title|urlencode }}"
                    >
                        ⬇️ הורד MP3
                    </a>

                </div>

            {% endfor %}

        </div>

    </body>

    </html>
    """

    return render_template_string(
        html,
        query=query,
        results=results,
        error=error
    )


# =========================
# API חיפוש עבור PHP
# =========================

@app.route("/search")
def api_search():

    query = request.args.get("q", "").strip()

    if not query:

        return {
            "success": False,
            "error": "חסר שם שיר"
        }, 400

    try:

        results = search_youtube(query)

        return {
            "success": True,
            "query": query,
            "results": results
        }

    except Exception as e:

        return {
            "success": False,
            "error": translate_error(e),
            "raw_error": str(e)
        }, 500


# =========================
# הורדת MP3
# =========================

@app.route("/download")
def download():

    video_id = request.args.get("id", "").strip()
    title = request.args.get("title", "song").strip()

    if not video_id:

        return {
            "error": "חסר מזהה סרטון"
        }, 400

    title = clean_filename(title)

    output_template = os.path.join(
        DOWNLOAD_FOLDER,
        f"{title}.%(ext)s"
    )

    try:

        ydl_opts = {
            "format": "bestaudio/best",

            "outtmpl": output_template,

            "noplaylist": True,

            "quiet": False,

            "no_warnings": False,

            "retries": 1,

            "fragment_retries": 1,

            "socket_timeout": 30,

            "continuedl": True,

            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        url = f"https://www.youtube.com/watch?v={video_id}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            ydl.download([url])

        mp3_file = os.path.join(
            DOWNLOAD_FOLDER,
            f"{title}.mp3"
        )

        if not os.path.exists(mp3_file):

            files = glob.glob(
                os.path.join(
                    DOWNLOAD_FOLDER,
                    f"{title}.*"
                )
            )

            if not files:

                return {
                    "error": "הקובץ לא נמצא לאחר ההורדה."
                }, 500

            mp3_file = files[0]

        return send_file(
            mp3_file,
            as_attachment=True,
            download_name=f"{title}.mp3"
        )

    except Exception as e:

        traceback.print_exc()

        # ניקוי קבצים חלקיים
        for file in glob.glob(
            os.path.join(
                DOWNLOAD_FOLDER,
                f"{title}.*"
            )
        ):

            try:
                os.remove(file)
            except:
                pass

        return {
            "error": translate_error(e),
            "raw_error": str(e)
        }, 500


# =========================
# בדיקת שרת
# =========================

@app.route("/health")
def health():

    return {
        "status": "ok"
    }


# =========================
# הפעלה
# =========================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
