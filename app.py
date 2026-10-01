import os
import re
import glob
from flask import Flask, request, render_template_string, send_file
import yt_dlp
import static_ffmpeg

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.abspath("downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# טוען FFmpeg
static_ffmpeg.add_paths()


def clean_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180] or "song"


def translate_error(error):
    text = str(error)

    if "Sign in to confirm" in text or "not a bot" in text:
        return "YouTube חסם את הבקשה מהשרת. נסה שוב מאוחר יותר."

    if "429" in text or "Too Many Requests" in text:
        return "YouTube הגביל זמנית את הבקשות מהשרת."

    if "Video unavailable" in text:
        return "הסרטון אינו זמין."

    if "Private video" in text:
        return "זהו סרטון פרטי."

    return "אירעה שגיאה בהורדה."


def search_youtube(query):
    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        result = ydl.extract_info(
            f"ytsearch8:{query}",
            download=False
        )

    videos = []

    for item in result.get("entries", []):
        if not item:
            continue

        video_id = item.get("id")
        title = item.get("title", "ללא שם")

        if video_id:
            videos.append({
                "id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            })

    return videos


HTML = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>הורדת שירים מיוטיוב</title>

<style>
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #111;
    color: white;
}

.container {
    max-width: 850px;
    margin: 60px auto;
    padding: 20px;
}

h1 {
    text-align: center;
}

.search {
    display: flex;
    gap: 10px;
    margin: 30px 0;
}

input {
    flex: 1;
    padding: 15px;
    border-radius: 10px;
    border: none;
    font-size: 17px;
}

button {
    padding: 15px 25px;
    border: none;
    border-radius: 10px;
    background: #e00;
    color: white;
    cursor: pointer;
    font-size: 16px;
}

.result {
    background: #222;
    padding: 18px;
    border-radius: 12px;
    margin-bottom: 12px;
}

.title {
    font-size: 18px;
    margin-bottom: 12px;
}

.download {
    display: inline-block;
    background: #168a3a;
    color: white;
    padding: 10px 18px;
    border-radius: 8px;
    text-decoration: none;
}

.youtube {
    display: inline-block;
    margin-right: 8px;
    background: #333;
    color: white;
    padding: 10px 18px;
    border-radius: 8px;
    text-decoration: none;
}
</style>
</head>

<body>

<div class="container">

<h1>🎵 הורדת שירים מיוטיוב</h1>

<form class="search" method="GET">
    <input
        type="text"
        name="q"
        placeholder="חפש שיר או אמן..."
        value="{{ query }}"
        required
    >
    <button type="submit">חיפוש</button>
</form>

{% if error %}
<div class="result">
    ❌ {{ error }}
</div>
{% endif %}

{% for video in videos %}

<div class="result">

    <div class="title">
        {{ video.title }}
    </div>

    <a
        class="download"
        href="/download?id={{ video.id }}&title={{ video.title|urlencode }}"
    >
        ⬇️ הורד MP3
    </a>

    <a
        class="youtube"
        href="{{ video.url }}"
        target="_blank"
    >
        ▶️ YouTube
    </a>

</div>

{% endfor %}

</div>

</body>
</html>
"""


@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    videos = []
    error = None

    if query:
        try:
            videos = search_youtube(query)
        except Exception as e:
            error = translate_error(e)

    return render_template_string(
        HTML,
        query=query,
        videos=videos,
        error=error
    )


@app.route("/download")
def download():
    video_id = request.args.get("id", "").strip()
    title = request.args.get("title", "song").strip()

    if not video_id:
        return "חסר מזהה סרטון", 400

    filename = clean_filename(title)

    output_template = os.path.join(
        DOWNLOAD_FOLDER,
        filename + ".%(ext)s"
    )

    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "retries": 1,
        "fragment_retries": 1,
        "socket_timeout": 30,

        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        url = f"https://www.youtube.com/watch?v={video_id}"

        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

        files = glob.glob(
            os.path.join(DOWNLOAD_FOLDER, filename + ".*")
        )

        mp3_files = [
            f for f in files
            if f.lower().endswith(".mp3")
        ]

        if mp3_files:
            return send_file(
                mp3_files[0],
                as_attachment=True,
                download_name=filename + ".mp3"
            )

        if files:
            return send_file(
                files[0],
                as_attachment=True,
                download_name=os.path.basename(files[0])
            )

        return "הקובץ לא נוצר", 500

    except Exception as e:
        return f"""
        <html lang="he" dir="rtl">
        <body style="font-family:Arial;padding:40px">
            <h2>❌ ההורדה נכשלה</h2>
            <p>{translate_error(e)}</p>
            <hr>
            <small>{str(e)}</small>
        </body>
        </html>
        """, 500


@app.route("/health")
def health():
    return {
        "status": "ok"
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port
    )
