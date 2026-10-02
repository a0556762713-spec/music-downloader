import os
import re
import glob
import traceback

from flask import Flask, request, send_file, jsonify
import yt_dlp

# static-ffmpeg מספק ffmpeg בתוך סביבת Python
import static_ffmpeg

static_ffmpeg.add_paths()

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.abspath("downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def clean_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip()

    if not name:
        name = "song"

    return name[:150]


def translate_error(error):
    text = str(error)

    if "Sign in to confirm" in text or "not a bot" in text:
        return "YouTube לא מאפשר כרגע לשרת לבצע את ההורדה."

    if "429" in text or "Too Many Requests" in text:
        return "YouTube חסם זמנית את השרת בגלל יותר מדי בקשות."

    if "Video unavailable" in text:
        return "הסרטון אינו זמין."

    if "Private video" in text:
        return "הסרטון פרטי."

    return "אירעה שגיאה בהורדה."


@app.route("/")
def home():
    return {
        "status": "ok",
        "service": "music-downloader-worker"
    }


@app.route("/health")
def health():
    return {
        "status": "ok"
    }


@app.route("/download")
def download():

    video_id = request.args.get("id", "").strip()
    title = request.args.get("title", "song").strip()

    if not video_id:
        return jsonify({
            "success": False,
            "error": "חסר מזהה סרטון"
        }), 400

    title = clean_filename(title)

    output_template = os.path.join(
        DOWNLOAD_FOLDER,
        f"{title}.%(ext)s"
    )

    try:

        url = f"https://www.youtube.com/watch?v={video_id}"

        ydl_opts = {
            "format": "bestaudio/best",

            "outtmpl": output_template,

            "noplaylist": True,

            "quiet": False,

            "no_warnings": False,

            "retries": 2,

            "fragment_retries": 2,

            "socket_timeout": 60,

            "continuedl": True,

            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

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
                return jsonify({
                    "success": False,
                    "error": "הקובץ לא נמצא לאחר ההורדה."
                }), 500

            mp3_file = files[0]

        return send_file(
            mp3_file,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name=f"{title}.mp3"
        )

    except Exception as e:

        traceback.print_exc()

        error_text = str(e)

        return jsonify({
            "success": False,
            "error": translate_error(e),
            "raw_error": error_text
        }), 500


if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", "8000")
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
