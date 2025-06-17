from flask import Flask, request, jsonify, render_template
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from googletrans import Translator
import json
import requests

# Load .env variables
load_dotenv()
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
RECIPIENT_EMAIL = "rupali_24a12res562@iitp.ac.in"

# Init Flask
app = Flask(__name__)

# Load knowledge base
with open("data/knowledge.json") as f:
    knowledge_base = json.load(f)

# Translator
translator = Translator()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message")
    lang = data.get("language", "English")

    if not message:
        return jsonify({"response": "No message received."}), 400

    if lang != "English":
        try:
            message = translator.translate(message, src=lang, dest='en').text
        except:
            return jsonify({"response": "Translation error."})

    # Knowledge Base
    response = get_answer_from_kb(message)
    if not response:
        response = get_gemini_response_openrouter(message)

    if lang != "English":
        try:
            response = translator.translate(response, src='en', dest=lang).text
        except:
            return jsonify({"response": "Translation error."})

    return jsonify({"response": response})

@app.route("/complaint", methods=["POST"])
def complaint():
    data = request.json
    complaint_text = data.get("complaint")
    if not complaint_text:
        return jsonify({"message": "No complaint received."}), 400
    send_email(complaint_text)
    return jsonify({"message": " Complaint submitted successfully."})

def get_answer_from_kb(message):
    for question, answer in knowledge_base.items():
        if question.lower() in message.lower():
            return answer
    return None

def get_gemini_response_openrouter(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "http://localhost",
            "X-Title": "IITP Nexus"
        }

        data = {
            "model": "google/gemini-pro",
            "messages": [
                {"role": "system", "content": "You are IITP Nexus, the official AI assistant of IIT Patna. You answer queries only about IIT Patna, its departments, admissions, faculty, events, facilities, courses, placements, and student life. Be factual, concise, and formal. Do not talk like a general chatbot. If something is unknown or unrelated, respond clearly and briefly."},
                {"role": "user", "content": prompt}
            ]
        }

        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        return res.json()["choices"][0]["message"]["content"]

    except Exception as e:
        print(f"Gemini Error: {e}")
        try:
            data["model"] = "mistralai/mistral-7b-instruct"
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
            return res.json()["choices"][0]["message"]["content"]
        except Exception as fallback_e:
            print(f"Fallback Error: {fallback_e}")
            return "⚠️ All models are currently unreachable. Please try again later."



def send_email(complaint_text):
    try:
        msg = MIMEText(complaint_text)
        msg['Subject'] = 'New Complaint from IITP Nexus'
        msg['From'] = EMAIL_SENDER
        msg['To'] = RECIPIENT_EMAIL

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✅ Email sent.")
    except Exception as e:
        print(f"Email error: {e}")

if __name__ == "__main__":
    app.run(debug=True, port=5050)  # Change port to avoid conflict
