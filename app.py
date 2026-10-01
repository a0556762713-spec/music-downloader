import os
import re
import requests

from flask import (
    Flask,
    request,
    render_template_string,
    Response
)

app = Flask(__name__)

PORT = int(os.environ.get("PORT", "10000"))

# כתובת ה-Worker תוגדר ב-Render כ-Environment Variable
WORKER_URL = os.environ.get("WORKER_URL", "").rstrip("/")


# ============================================================
# HTML
# ============================================================

HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="he" dir="rtl">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>מוריד שירים</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #111827, #1f2937);
    color: white;
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
    margin: 0 0 10px;
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
    border: none;
    border-radius: 12px;
    font-size: 17px;
}

.search-box button {
    padding: 17px 30px;
    border: none;
    border-radius: 12px;
    background: #ef4444;
    color: white;
    font-size: 17px;
    font-weight: bold;
    cursor: pointer;
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

.error {
    background: #7f1d1d;
    border: 1px solid #ef4444;
    padding: 20px;
    border-radius: 12px;
    white-space: pre-line;
    line-height: 1.7;
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
        <h1>🎵 מוריד שירים</h1>
        <p>חפש שיר והורד אותו כקובץ שמע</p>
    </div>

    <form class="search-box" method="GET" action="/">
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

    {% if error_message %}
        <div class="error">
            {{ error_message }}
        </div>
        <br>
    {% endif %}

    {% if query and not results and not error_message %}
        <div class="empty">
            לא נמצאו תוצאות.
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

ERROR_PAGE = r"""
<!DOCTYPE html>
<html lang="he" dir="rtl">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>שגיאה</title>

<style>
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
    padding: 30px;
    border-radius: 18px;
}

.message {
    background: #111827;
    padding: 20px;
    border-radius: 12px;
    white-space: pre-line;
    line-height: 1.8;
}

.back {
    display: inline-block;
    margin-top: 25px;
    padding: 12px 20px;
    background: #3b82f6;
    color: white;
    text-decoration: none;
    border-radius: 10px;
}
</style>

</head>

<body>

<div class="box">

<h1>❌ הפעולה נכשלה</h1>

<div class="message">
{{ message }}
</div>

<a class="back" href="/">
← חזרה לחיפוש
</a>

</div>

</body>
</html>
"""


# ============================================================
# SEARCH
# ============================================================

def search_youtube(query):

    if not WORKER_URL:
        raise RuntimeError(
            "WORKER_URL לא הוגדר בשרת."
        )

    response = requests.get(
        f"{WORKER_URL}/search",
        params={"q": query},
        timeout=60
    )

    try:
        data = response.json()
    except Exception:
        raise RuntimeError(
            "שרת ההורדה החזיר תשובה לא תקינה."
        )

    if response.status_code != 200:
        raise RuntimeError(
            data.get(
                "error",
                "החיפוש נכשל."
            )
        )

    return data.get("results", [])


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
    error_message = ""

    if query:

        try:
            results = search_youtube(query)

        except Exception as e:
            error_message = str(e)

    return render_template_string(
        HTML_PAGE,
        query=query,
        results=results,
        error_message=error_message
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
            ERROR_PAGE,
            message="לא סופק מזהה של הסרטון."
        ), 400

    if not WORKER_URL:

        return render_template_string(
            ERROR_PAGE,
            message="WORKER_URL לא הוגדר בשרת."
        ), 500

    try:

        response = requests.get(
            f"{WORKER_URL}/download",
            params={
                "id": video_id,
                "title": title
            },
            timeout=600,
            stream=True
        )

        # Worker החזיר שגיאה
        if response.status_code != 200:

            try:
                data = response.json()

                message = data.get(
                    "error",
                    "ההורדה נכשלה."
                )

            except Exception:
                message = (
                    "שרת ההורדה החזיר שגיאה."
                )

            return render_template_string(
                ERROR_PAGE,
                message=message
            ), response.status_code

        # ----------------------------------------------------
        # החזרת הקובץ למשתמש
        # ----------------------------------------------------

        filename = re.sub(
            r'[<>:"/\\|?*\x00-\x1F]',
            '',
            title
        ).strip()

        if not filename:
            filename = "song"

        if not filename.lower().endswith(".mp3"):
            filename += ".mp3"

        def generate():

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:
                    yield chunk

        result = Response(
            generate(),
            content_type=response.headers.get(
                "Content-Type",
                "audio/mpeg"
            )
        )

        result.headers[
            "Content-Disposition"
        ] = (
            f'attachment; filename="{filename}"'
        )

        return result

    except requests.exceptions.Timeout:

        return render_template_string(
            ERROR_PAGE,
            message=(
                "שרת ההורדה לא סיים את הפעולה "
                "בזמן שהוקצב."
            )
        ), 504

    except Exception:

        return render_template_string(
            ERROR_PAGE,
            message=(
                "לא ניתן להתחבר כרגע "
                "לשרת ההורדה."
            )
        ), 500


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "service": "web"
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
