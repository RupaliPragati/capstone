# iitp_nexus_app.py – Final Version with:
# - Local DB Q&A only (no GPT fallback)
# - PDF Q&A loader
# - Complaint fix
# - CSV Q&A loader
# - Basic auto-learning (stores unanswered questions for admin review)

import os, uuid, subprocess, shlex, smtplib, sqlite3
from flask import Flask, request, jsonify, render_template, url_for
from dotenv import load_dotenv
from email.mime.text import MIMEText
from deep_translator import GoogleTranslator
import whisper
from gtts import gTTS
import difflib
import fitz  
import pandas as pd
from sentence_transformers import SentenceTransformer, util
import torch
from flask import Flask, request, jsonify
from fuzzywuzzy import process
import sqlite3

# ───── Config ─────
load_dotenv()
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "rupali_24a12res562@iitp.ac.in")

os.makedirs("static/tts", exist_ok=True)
os.makedirs("temp", exist_ok=True)
os.makedirs("data", exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
whisper_model = whisper.load_model("base")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ───── Translation ─────
def translate_text(text, source, target):
    try:
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception as e:
        print("[Translation error]", e)
        return text

# ───── DB Init ─────
def init_db():
    with sqlite3.connect("data/data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT UNIQUE,
            answer TEXT
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT UNIQUE
        )""")

# ───── Knowledge Base Answer ─────
def kb_answer(user_input):
    conn = sqlite3.connect("data/data.db")
    cursor = conn.cursor()
    user_input = user_input.lower().strip()

    try:
        cursor.execute("SELECT question, answer FROM knowledge")
        data = cursor.fetchall()
        if not data:
            return "Sorry, no knowledge base is available yet."

        questions = [q.lower().strip() for q, _ in data]
        answers = [a for _, a in data]

        # Embed questions and user query
        query_embedding = embedder.encode(user_input, convert_to_tensor=True)
        corpus_embeddings = embedder.encode(questions, convert_to_tensor=True)

        # Compute cosine similarity
        cos_scores = util.pytorch_cos_sim(query_embedding, corpus_embeddings)[0]
        best_score_idx = torch.argmax(cos_scores).item()
        best_score_val = cos_scores[best_score_idx].item()

        if best_score_val >= 0.5:  # Lowered threshold
            return answers[best_score_idx]
        else:
            # Fuzzy fallback
            best_match, score = process.extractOne(user_input, questions)
            if score > 70:
                idx = questions.index(best_match)
                return answers[idx]
    finally:
        conn.close()

    return "I'm not sure about that yet. Please rephrase or check the Moodle site for more info."

# ───── TTS ─────
def text2speech(text):
    fname = f"{uuid.uuid4().hex}.mp3"
    fpath = os.path.join("static", "tts", fname)
    gTTS(text, lang="en").save(fpath)
    return url_for("static", filename=f"tts/{fname}")

# ───── STT ─────
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

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    j = request.json or {}
    msg = j.get("message", "").strip()
    lang = j.get("language", "English")
    voice_mode = j.get("voice_mode", False)
    if not msg:
        return jsonify({"response": "Please ask something."}), 400
    if lang != "English":
        msg = translate_text(msg, lang, "en")
    ans = kb_answer(msg)
    if lang != "English":
        ans = translate_text(ans, "en", lang)
    out = {"response": ans}
    if voice_mode:
        out["voice"] = text2speech(ans)
    return jsonify(out)

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
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_SENDER, EMAIL_PASSWORD)
            s.send_message(msg)
        return jsonify({"message": "Complaint submitted"})
    except:
        return jsonify({"message": "Email sending failed."})

@app.route("/load_pdf", methods=["POST"])
def load_pdf():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No PDF uploaded."}), 400
    pdf_path = os.path.join("temp", file.filename)
    file.save(pdf_path)
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()
    doc.close()
    os.remove(pdf_path)
    qas = [(line.strip(), "(Answer not available yet)") for line in text.split("\n") if "?" in line]
    conn = sqlite3.connect("data/data.db")
    cursor = conn.cursor()
    for q, a in qas:
        try:
            cursor.execute("INSERT INTO knowledge (question, answer) VALUES (?, ?)", (q, a))
        except:
            continue
    conn.commit()
    conn.close()
    return jsonify({"message": f"Loaded {len(qas)} entries from PDF."})

@app.route("/load_csv", methods=["POST"])
def load_csv():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No CSV uploaded."}), 400
    df = pd.read_csv(file)
    df["question"] = df["question"].str.strip()
    df["answer"] = df["answer"].str.strip()
    conn = sqlite3.connect("data/data.db")
    cursor = conn.cursor()
    for _, row in df.iterrows():
        try:
            cursor.execute("INSERT INTO knowledge (question, answer) VALUES (?, ?)", (row["question"], row["answer"]))
        except:
            continue
    conn.commit()
    conn.close()
    return jsonify({"message": f"Loaded {len(df)} entries from CSV."})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5050)
