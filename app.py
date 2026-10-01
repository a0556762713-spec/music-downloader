==> Detected service running on port 10000
==> Docs on specifying a port: https://render.com/docs/web-services#port-binding
==> Deploying...
==> Setting WEB_CONCURRENCY=1 by default, based on available CPUs in the instance
Extracting /opt/render/project/src/.venv/lib/python3.14/site-packages/static_ffmpeg/bin/linux.zip -> /opt/render/project/src/.venv/lib/python3.14/site-packages/static_ffmpeg/bin
FFmpeg loaded successfully
========================================
SERVER STARTING
========================================
PORT: 10000
ERROR SERVER: https://merkazia-plus.wuaze.com/wer.php
DOWNLOAD FOLDER: /opt/render/project/src/downloads
========================================
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:10000
 * Running on http://10.27.232.1:10000
Press CTRL+C to quit
127.0.0.1 - - [01/Oct/2026 12:42:40] "HEAD / HTTP/1.1" 200 -
127.0.0.1 - - [01/Oct/2026 12:42:44] "GET / HTTP/1.1" 200 -
==> Your service is live 🎉
==> 
==> ///////////////////////////////////////////////////////////
==> 
==> Available at your primary URL https://music-downloader-laf6.onrender.com
==> 
==> ///////////////////////////////////////////////////////////
127.0.0.1 - - [01/Oct/2026 12:45:02] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [01/Oct/2026 12:45:13] "GET /?q=עומר+אדם HTTP/1.1" 200 -
ERROR: [youtube] fVMihvd4Xzs: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies
/opt/render/project/src/app.py:93: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  "time": datetime.utcnow().isoformat(),
127.0.0.1 - - [01/Oct/2026 12:45:24] "GET /download?id=fVMihvd4Xzs&title=עומר%20אדם%20-%20מלכת%20הדור%20%20Prod.By-%20Gal%20Adam%20%20Ilay%20Sidi HTTP/1.1" 500 -
