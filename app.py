import os
import re
import traceback
import requests

from flask import Flask, request, render_template_string


# ============================================================
# APP
# ============================================================

app = Flask(__name__)

PORT = int(os.environ.get("PORT", 10000))

# כתובת פנימית של שירות ההורדה.
# ב-Render נגדיר אותה כמשתנה סביבה.
WORKER_URL = os.environ.get(
    "WORKER_URL",
    "http://localhost:10001"
).rstrip("/")


# ============================================================
# STARTUP
# ============================================================

print("=" * 60)
print("MUSIC DOWNLOADER - WEB SERVER")
print("=" * 60)
print("PORT:", PORT)
print("WORKER URL:", WORKER_URL)
print("=" * 60)


# ============================================================
# SEARCH
# ============================================================

def search_youtube(query):

    try:
        response = requests.get(
            f"{WORKER_URL}/search",
            params={"q": query},
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        return data.get("results", [])

    except Exception as e:

        print("=" * 60)
        print("SEARCH ERROR")
        print("=" * 60)

        traceback.print_exc()

        return []


# ============================================================
# HTML
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


    {% if error_message %}

        <div class="error">
            {{ error_message }}
        </div>

        <br>

    {% endif %}


    {% if query and not results and not error_message %}

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

    error_message = ""

    if query:

        try:

            results = search_youtube(query)

            if not results:
                error_message = (
                    "לא נמצאו תוצאות או שהחיפוש "
                    "לא הצליח כרגע."
                )

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
            ERROR_TEMPLATE,

            error_message=(
                "לא סופק מזהה של הסרטון."
            ),

            error_code="MISSING-ID"

        ), 400


    try:

        print("=" * 60)
        print("REQUESTING DOWNLOAD FROM WORKER")
        print("=" * 60)

        print("VIDEO ID:", video_id)
        print("TITLE:", title)


        response = requests.get(

            f"{WORKER_URL}/download",

            params={
                "id": video_id,
                "title": title
            },

            timeout=600,

            stream=True
        )


        content_type = (
            response.headers.get(
                "Content-Type",
                ""
            )
        )


        # ----------------------------------------------------
        # אם ה-Worker החזיר שגיאה
        # ----------------------------------------------------

        if response.status_code != 200:

            try:

                data = response.json()

                error_message = data.get(
                    "error",
                    "ההורדה נכשלה."
                )

                error_code = data.get(
                    "code",
                    "WORKER-ERROR"
                )

            except Exception:

                error_message = (
                    "שרת ההורדה לא הצליח "
                    "להשלים את הפעולה."
                )

                error_code = (
                    f"WORKER-HTTP-{response.status_code}"
                )


            return render_template_string(

                ERROR_TEMPLATE,

                error_message=error_message,

                error_code=error_code

            ), 500


        # ----------------------------------------------------
        # קובץ
        # ----------------------------------------------------

        from flask import Response

        def generate():

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:

                    yield chunk


        filename = (
            title
            if title
            else "song"
        )

        filename = re.sub(
            r'[<>:"/\\|?*\x00-\x1F]',
            '',
            filename
        ).strip()

        if not filename:

            filename = "song"


        if not filename.lower().endswith(".mp3"):

            filename += ".mp3"


        flask_response = Response(
            generate(),
            content_type=(
                content_type
                or "audio/mpeg"
            )
        )


        flask_response.headers[
            "Content-Disposition"
        ] = (
            f'attachment; filename="{filename}"'
        )


        if response.headers.get(
            "Content-Length"
        ):

            flask_response.headers[
                "Content-Length"
            ] = response.headers[
                "Content-Length"
            ]


        return flask_response


    except requests.exceptions.Timeout:

        return render_template_string(

            ERROR_TEMPLATE,

            error_message=(
                "שרת ההורדה לא סיים את "
                "הפעולה בזמן שהוקצב."
            ),

            error_code="WORKER-TIMEOUT"

        ), 504


    except Exception as e:

        print("=" * 60)
        print("WEB DOWNLOAD ERROR")
        print("=" * 60)

        traceback.print_exc()


        return render_template_string(

            ERROR_TEMPLATE,

            error_message=(
                "אירעה שגיאה בתקשורת "
                "עם שרת ההורדה."
            ),

            error_code="WORKER-CONNECTION"

        ), 500


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "service": "music-downloader-web"
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
