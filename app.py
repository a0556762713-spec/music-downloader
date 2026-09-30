import gradio as gr
import subprocess
import sys
import os

try:
    import yt_dlp
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp

def download_song(query):
    if not query or not query.strip():
        return None, "נא להקליד שם שיר או להדביק קישור"
    
    os.makedirs("downloads", exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            target = query.strip()
            if not ("youtube.com" in target or "youtu.be" in target):
                target = f"ytsearch1:{target}"
                
            info = ydl.extract_info(target, download=True)
            if 'entries' in info and info['entries']:
                entry = info['entries'][0]
            else:
                entry = info
                
            title = entry.get('title', 'song')
            filename = ydl.prepare_filename(entry)
            
            if os.path.exists(filename):
                return filename, f"✔ השיר '{title}' מוכן להורדה ולהאזנה!"
            else:
                return None, "שגיאה: הקובץ לא נוצר."
    except Exception as e:
        return None, f"שגיאה בהורדה: {str(e)}"

with gr.Blocks(title="קופיקו - הורדת שירים מיוטיוב") as demo:
    gr.Markdown("""
    # 🐒 קופיקו Music - הורדת שירים מלאים
    כתבו את שם השיר או הדביקו קישור מיוטיוב, לחצו על **הורד שיר** והקובץ יירד ישירות למכשיר שלכם.
    """)
    
    with gr.Row():
        query_input = gr.Textbox(
            label="שם השיר או קישור מיוטיוב",
            placeholder="למשל: אושר כהן, חנן בן ארי, או הדבק קישור מיוטיוב...",
            scale=4
        )
        submit_btn = gr.Button("⬇ הורד שיר", variant="primary", scale=1)
        
    status_output = gr.Textbox(label="סטטוס", interactive=False)
    audio_output = gr.Audio(label="נגן השיר וכפתור הורדה למחשב", type="filepath")
    
    submit_btn.click(
        fn=download_song,
        inputs=query_input,
        outputs=[audio_output, status_output]
    )

# הגדרת הפורט עבור Render
port = int(os.environ.get("PORT", 7860))
demo.launch(server_name="0.0.0.0", server_port=port)
