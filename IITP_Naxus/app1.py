# app.py – backend with STT + TTS using SQLite DB (no API)

import os, uuid, subprocess, shlex, smtplib, requests, sqlite3
from flask import Flask, request, jsonify, render_template, url_for
from dotenv import load_dotenv
from email.mime.text import MIMEText
from googletrans import Translator
import whisper
from gtts import gTTS
import sqlite3  


# ────────── config ──────────
load_dotenv()
EMAIL_SENDER   = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL= "rupali_24a12res562@iitp.ac.in"

os.makedirs("static/tts", exist_ok=True)
os.makedirs("temp",       exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")

# ────────── load models ──────────
whisper_model = whisper.load_model("base")
translator = Translator()

# ────────── helper: fetch answer from database ──────────
def kb_answer(q):
    conn = sqlite3.connect("data/data.db")
    cursor = conn.cursor()
    q = q.lower()

    # fetch all questions & answers and match
    cursor.execute("SELECT question, answer FROM knowledge")
    for row in cursor.fetchall():
        if row[0].lower() in q:
            conn.close()
            return row[1]
    conn.close()
    return None

# ────────── speech + TTS ──────────
def text2speech(text):
    fname = f"{uuid.uuid4().hex}.mp3"
    fpath = os.path.join("static", "tts", fname)
    gTTS(text, lang="en").save(fpath)
    return url_for("static", filename=f"tts/{fname}")

def speech2text(blob):
    try:
        return whisper_model.transcribe(blob)["text"].strip()
    except:
        pass
    wav = blob + ".wav"
    cmd = f'ffmpeg -y -i {shlex.quote(blob)} -ar 16000 -ac 1 {shlex.quote(wav)}'
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    txt = whisper_model.transcribe(wav)["text"].strip()
    os.remove(wav)
    return txt or "(no speech recognised)"

# ────────── routes ──────────
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    j = request.json or {}
    msg = j.get("message", "").strip()
    lang = j.get("language", "English")

    if not msg:
        return jsonify({"response": "Please ask something."}), 400

    if lang != "English":
        msg = translator.translate(msg, src=lang, dest="en").text

    ans = get_db_answer(msg)
    if not ans:
        ans = "Sorry, I don’t have information about that yet."

    if lang != "English":
        ans = translator.translate(ans, src="en", dest=lang).text

    return jsonify({"response": ans})

    # translate to English if needed
    if lang != "English":
        msg = translator.translate(msg, src=lang, dest="en").text

    # find answer from database
    ans = kb_answer(msg)

    if not ans:
        ans = "⚠️ Sorry, I couldn't find the answer in my database."

    # translate back to original language if needed
    if lang != "English":
        ans = translator.translate(ans, src="en", dest=lang).text

    return jsonify({"response": ans})

@app.route("/stt", methods=["POST"])
def stt():
    if "audio" not in request.files:
        return jsonify({"error": "no audio"}), 400
    f = request.files["audio"]
    ext = os.path.splitext(f.filename)[1] or ".webm"
    path = os.path.join("temp", uuid.uuid4().hex + ext)
    f.save(path)
    try:
        txt = speech2text(path)
    finally:
        os.remove(path)
    return jsonify({"text": txt})

@app.route("/tts", methods=["POST"])
def tts():
    txt = (request.json or {}).get("text", "").strip()
    if not txt:
        return jsonify({"error": "no text"}), 400
    return jsonify({"audio_url": text2speech(txt)})

@app.route("/complaint", methods=["POST"])
def complaint():
    t = (request.json or {}).get("complaint", "").strip()
    if not t:
        return jsonify({"message": "No complaint"}), 400
    msg = MIMEText(t)
    msg["Subject"] = "New Complaint"
    msg["From"] = EMAIL_SENDER
    msg["To"] = RECIPIENT_EMAIL
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_SENDER, EMAIL_PASSWORD)
        s.send_message(msg)
    return jsonify({"message": "Complaint submitted"})

# ────────── run ──────────
if __name__ == "__main__":
    app.run(debug=True, port=5050)
