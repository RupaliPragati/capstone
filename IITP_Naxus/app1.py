# app.py – backend with STT + working TTS URL for Codespaces
import os, json, uuid, subprocess, shlex, smtplib, requests
from flask import Flask, request, jsonify, render_template, url_for
from dotenv import load_dotenv
from email.mime.text import MIMEText
from googletrans import Translator
import whisper
from gtts import gTTS

# ────────── config ──────────
load_dotenv()
EMAIL_SENDER   = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
OPENROUTER_API = os.getenv("OPENROUTER_API_KEY")
RECIPIENT_EMAIL= "rupali_24a12res562@iitp.ac.in"

os.makedirs("static/tts", exist_ok=True)
os.makedirs("temp",       exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")

whisper_model = whisper.load_model("base")   # or "tiny"
with open("data/knowledge.json", encoding="utf‑8") as f:
    knowledge_base = json.load(f)

translator = Translator()

# ────────── helper functions ──────────
def kb_answer(q):
    for k,v in knowledge_base.items():
        if k.lower() in q.lower():
            return v

def llm_answer(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API}",
        "HTTP-Referer":  "http://localhost",
        "X-Title":       "IITP Nexus"
    }
    data = {
        "model":"google/gemini-pro",
        "messages":[
            {"role":"system","content":"You are IITP Nexus …"},
            {"role":"user",  "content":prompt}
        ]
    }
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers=headers, json=data, timeout=45)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("LLM error",e)
        return "⚠️ Sorry, I cannot answer now."

def text2speech(text):
    fname = f"{uuid.uuid4().hex}.mp3"
    fpath = os.path.join("static","tts",fname)
    gTTS(text, lang="en").save(fpath)
    # return **relative** URL so Codespaces proxy works
    return url_for("static", filename=f"tts/{fname}")

def speech2text(blob):
    try:
        return whisper_model.transcribe(blob)["text"].strip()
    except: pass
    wav = blob + ".wav"
    cmd = f'ffmpeg -y -i {shlex.quote(blob)} -ar 16000 -ac 1 {shlex.quote(wav)}'
    subprocess.run(cmd,shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    txt = whisper_model.transcribe(wav)["text"].strip()
    os.remove(wav)
    return txt or "(no speech recognised)"

# ────────── routes ──────────
@app.route("/")
def home(): return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    j = request.json or {}
    msg = j.get("message","").strip()
    lang= j.get("language","English")
    if not msg: return jsonify({"response":"Please ask something."}),400
    if lang!="English": msg = translator.translate(msg,src=lang,dest="en").text
    ans = kb_answer(msg) or llm_answer(msg)
    if lang!="English": ans = translator.translate(ans,src="en",dest=lang).text
    return jsonify({"response": ans})

@app.route("/stt", methods=["POST"])
def stt():
    if "audio" not in request.files: return jsonify({"error":"no audio"}),400
    f = request.files["audio"]
    ext = os.path.splitext(f.filename)[1] or ".webm"
    path= os.path.join("temp",uuid.uuid4().hex+ext); f.save(path)
    try:  txt = speech2text(path)
    finally: os.remove(path)
    return jsonify({"text":txt})

@app.route("/tts", methods=["POST"])
def tts():
    txt = (request.json or {}).get("text","").strip()
    if not txt: return jsonify({"error":"no text"}),400
    return jsonify({"audio_url": text2speech(txt)})

# email route unchanged …
@app.route("/complaint", methods=["POST"])
def complaint():
    t=(request.json or {}).get("complaint","").strip()
    if not t: return jsonify({"message":"No complaint"}),400
    msg=MIMEText(t); msg["Subject"]="New Complaint"; msg["From"]=EMAIL_SENDER; msg["To"]=RECIPIENT_EMAIL
    with smtplib.SMTP_SSL("smtp.gmail.com",465) as s:
        s.login(EMAIL_SENDER,EMAIL_PASSWORD); s.send_message(msg)
    return jsonify({"message":"Complaint submitted"})

if __name__=="__main__":
    app.run(debug=True,port=5050)
