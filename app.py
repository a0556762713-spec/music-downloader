import os
import re
from flask import Flask, request, render_template_string, send_file
import yt_dlp

# התקנת והפעלת FFmpeg להמרה ל-MP3
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# תבנית האתר עם השם "דביר מיוזיק" והעיצוב המבוקש
HTML_PAGE = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>דביר מיוזיק - הורדת שירים מיוטיוב</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f4f9; padding: 20px; direction: rtl; }
        .container { max-width: 800px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); text-align: center; }
        input[type="text"] { width: 60%; padding: 12px; border: 1px solid #ccc; border-radius: 20px; font-size: 16px; outline: none; }
        button { padding: 12px 25px; background: #ffcc00; border: none; border-radius: 20px; font-weight: bold; cursor: pointer; font-size: 16px; }
        button:hover { background: #e6b800; }
        .results { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; margin-top: 30px; }
        .card { border: 1px solid #eee; padding: 15px; border-radius: 10px; background: #fafafa; text-align: center; }
        .card img { width: 100%; height: 140px; object-fit: cover; border-radius: 8px; }
        .card h4 { margin: 10px 0 5px 0; font-size: 15px; height: 38px; overflow: hidden; }
        .card p { margin: 0 0 10px 0; color: #666; font-size: 13px; }
        .download-btn { display: block; background: #28a745; color: white; text-decoration: none; padding: 10px; margin-top: 10px; border-radius: 5px; font-weight: bold; }
        .download-btn:hover { background: #218838; }
        .info-text { font-size: 14px; color: #666; margin-top: 15px; }
    </style>
</head>
<body>

<div class="container">
    <h1>🎵 דביר מיוזיק - הורדת שירים מיוטיוב</h1>

    <form method="GET" action="/">
        <input type="text" name="q" placeholder="הקלד שם שיר או הדבק קישור מיוטיוב..." value="{{ search_query }}" required>
        <button type="submit">חפש</button>
    </form>

    {% if search_query %}
        <p class="info-text">תוצאות חיפוש עבור: <strong>{{ search_query }}</strong></p>
    {% endif %}

    <div class="results">
        {% for song in results %}
            <div class="card">
                <img src="{{ song.thumbnail }}" alt="תמונה">
                <h4>{{ song.title }}</h4>
                <p>{{ song.artist }}</p>
                <a href="/download?id={{ song.id }}&title={{ song.url_title }}" class="download-btn">
                    ⬇ הורד MP3 למחשב
                </a>
            </div>
        {% endfor %}
    </div>
</div>

</body>
</html>
"""

def search_youtube(query):
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
    }
    results = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            target = query.strip()
            if not ("youtube.com" in target or "youtu.be" in target):
                target = f"ytsearch8:{target}"
            info = ydl.extract_info(target, download=False)
            entries = info.get('entries', [info]) if 'entries' in info else [info]
            for entry in entries:
                if not entry:
                    continue
                v_id = entry.get('id')
                title = entry.get('title', 'שיר')
                clean_title = re.sub(r'[^\w\s\d\-_~.-]', '', title) or 'song'
                results.append({
                    'id': v_id,
                    'title': title,
                    'artist': entry.get('uploader') or entry.get('channel') or 'יוטיוב',
                    'thumbnail': f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg",
                    'url_title': clean_title
                })
        except Exception as e:
            print(f"Search error: {e}")
    return results

@app.route('/')
def home():
    query = request.args.get('q', '').strip()
    results = []
    if query:
        results = search_youtube(query)
    return render_template_string(HTML_PAGE, search_query=query, results=results)

@app.route('/download')
def download():
    video_id = request.args.get('id')
    title = request.args.get('title', 'song')
    if not video_id:
        return "חסר מזהה סרטון", 400

    out_file = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp3")
    
    if not os.path.exists(out_file):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, f"{video_id}.%(ext)s"),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

    if os.path.exists(out_file):
        return send_file(
            out_file,
            as_attachment=True,
            download_name=f"{title}.mp3",
            mimetype="audio/mpeg"
        )
    return "שגיאה בהורדת הקובץ", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)
