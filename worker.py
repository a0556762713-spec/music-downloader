import os
import re
import glob
import traceback

from flask import Flask, request, jsonify, send_file
import yt_dlp


# ============================================================
# APP
# ============================================================

app = Flask(__name__)

PORT = int(
    os.environ.get(
        "PORT",
        "10000"
    )
)


# ============================================================
# FFMPEG
# ============================================================

try:

    import static_ffmpeg

    static_ffmpeg.add_paths()

    print("FFmpeg loaded successfully")

except Exception as e:

    print(
        "Warning: FFmpeg not loaded:",
        e
    )


# ============================================================
# DOWNLOAD FOLDER
# ============================================================

DOWNLOAD_FOLDER = os.path.abspath(
    "downloads"
)

os.makedirs(
    DOWNLOAD_FOLDER,
    exist_ok=True
)


# ============================================================
# HELPERS
# ============================================================

def clean_filename(name):

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


def translate_error(error):

    text = str(error)

    lower = text.lower()

    if (
        "429" in lower
        or "too many requests" in lower
    ):
        return (
            "מקור המדיה הגביל את הבקשה "
            "והחזיר HTTP 429."
        )

    if (
        "sign in to confirm" in lower
        or "you're not a bot" in lower
        or "you’re not a bot" in lower
        or "captcha" in lower
    ):
        return (
            "מקור המדיה דורש אימות נוסף "
            "עבור בקשת ההורדה."
        )

    if "private video" in lower:
        return (
            "הסרטון פרטי ולכן אינו זמין."
        )

    if (
        "video unavailable" in lower
        or "video removed" in lower
    ):
        return (
            "הסרטון אינו זמין כרגע."
        )

    if "403" in lower:
        return (
            "השרת קיבל HTTP 403 "
            "ממקור המדיה."
        )

    if "404" in lower:
        return (
            "הסרטון לא נמצא."
        )

    if "ffmpeg" in lower:
        return (
            "אירעה בעיה בעיבוד המדיה "
            "באמצעות FFmpeg."
        )

    if (
        "timeout" in lower
        or "timed out" in lower
        or "connection reset" in lower
    ):
        return (
            "אירעה בעיית תקשורת "
            "עם מקור המדיה."
        )

    return (
        "אירעה שגיאה בזמן הורדת המדיה."
    )


# ============================================================
# SEARCH
# ============================================================

@app.route("/search")
def search():

    query = request.args.get(
        "q",
        ""
    ).strip()

    if not query:

        return jsonify({
            "results": []
        })


    try:

        search_query = (
            "ytsearch8:"
            + query
        )

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "noplaylist": True
        }

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            info = ydl.extract_info(
                search_query,
                download=False
            )

        results = []

        if not info:

            return jsonify({
                "results": []
            })

        for entry in info.get(
            "entries",
            []
        ):

            if not entry:
                continue

            video_id = entry.get("id")

            if not video_id:
                continue

            title = (
                entry.get("title")
                or "ללא כותרת"
            )

            artist = (
                entry.get("channel")
                or entry.get("uploader")
                or ""
            )

            thumbnail = (
                entry.get("thumbnail")
                or
                f"https://i.ytimg.com/vi/"
                f"{video_id}/hqdefault.jpg"
            )

            results.append({
                "id": video_id,
                "title": title,
                "artist": artist,
                "thumbnail": thumbnail,
                "url":
                    "https://www.youtube.com/watch?v="
                    + video_id
            })

        return jsonify({
            "results": results
        })

    except Exception as e:

        print("=" * 60)
        print("SEARCH ERROR")
        print("=" * 60)

        traceback.print_exc()

        return jsonify({
            "error": translate_error(e),
            "code": "SEARCH-ERROR",
            "results": []
        }), 500


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

        return jsonify({
            "error":
                "לא סופק מזהה של הסרטון.",
            "code":
                "MISSING-ID"
        }), 400


    youtube_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )


    print("=" * 60)
    print("DOWNLOAD START")
    print("=" * 60)

    print("VIDEO:", video_id)
    print("TITLE:", title)


    # ========================================================
    # EXISTING FILE
    # ========================================================

    existing_files = glob.glob(
        os.path.join(
            DOWNLOAD_FOLDER,
            video_id + ".*"
        )
    )


    if existing_files:

        file_path = existing_files[0]

        return send_file(
            file_path,
            as_attachment=True,
            download_name=(
                clean_filename(title)
                + os.path.splitext(file_path)[1]
            )
        )


    # ========================================================
    # OUTPUT
    # ========================================================

    output_template = os.path.join(
        DOWNLOAD_FOLDER,
        video_id + ".%(ext)s"
    )


    # ========================================================
    # YT-DLP
    # ========================================================

    ydl_opts = {

        "format":
            "bestaudio/best",

        "outtmpl":
            output_template,

        "noplaylist":
            True,

        "quiet":
            False,

        "no_warnings":
            False,

        "retries":
            1,

        "fragment_retries":
            1,

        "socket_timeout":
            30,

        "continuedl":
            True,

        "postprocessors": [

            {
                "key":
                    "FFmpegExtractAudio",

                "preferredcodec":
                    "mp3",

                "preferredquality":
                    "192"
            }

        ]
    }


    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.download([
                youtube_url
            ])


        # ====================================================
        # FIND FILE
        # ====================================================

        files = glob.glob(
            os.path.join(
                DOWNLOAD_FOLDER,
                video_id + ".*"
            )
        )


        if not files:

            raise RuntimeError(
                "ההורדה הסתיימה "
                "אך לא נוצר קובץ."
            )


        mp3_files = [
            f for f in files
            if f.lower().endswith(".mp3")
        ]


        if mp3_files:

            file_path = mp3_files[0]

        else:

            file_path = files[0]


        filename = (
            clean_filename(title)
            + os.path.splitext(file_path)[1]
        )


        print(
            "DOWNLOAD SUCCESS:",
            file_path
        )


        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )


    except Exception as e:

        print("=" * 60)
        print("DOWNLOAD ERROR")
        print("=" * 60)

        traceback.print_exc()


        # מחיקת קבצים חלקיים

        for file_path in glob.glob(
            os.path.join(
                DOWNLOAD_FOLDER,
                video_id + ".*"
            )
        ):

            try:
                os.remove(file_path)
            except Exception:
                pass


        return jsonify({

            "error":
                translate_error(e),

            "raw_error":
                str(e),

            "code":
                "DOWNLOAD-ERROR"

        }), 500


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "service": "download-worker"
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
