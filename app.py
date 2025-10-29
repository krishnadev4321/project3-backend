from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
import psycopg2
from datetime import datetime, date

app = Flask(__name__)
CORS(app)

# Per device per day request limit
USER_REQUEST_LIMIT = 20
blocked_ips = {}
user_first_interaction = {}  # Track pehle interaction ke liye

# PostgreSQL config (update with your Render details!)
DB_CONFIG = {
    "host": "dpg-d405lu3uibrs73b307t0-a.oregon-postgres.render.com",
    "dbname": "backend_web_oosd",
    "user": "backend_web_oosd_user",
    "password": "uVvVzGx6Llv9ThZVLZJ43zqwW2O4z1uf",
    "port": 5432,
}

# Gemini API config
GEMINI_API_KEY = "AIzaSyBHyiMX-EZwVo4G_NSOGGMu4itjKoguRmA"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

abusive_keywords = ["sex", "xxx", "mardarchod", "betichod", "bsdk", "sexy"]


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def contains_abuse(text):
    lower_text = text.lower()
    for word in abusive_keywords:
        if word in lower_text:
            return True
    return False


def log_chat(device_id, ip_address, question, reply):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_logs (device_id, ip_address, request_timestamp, user_question, bot_reply) VALUES (%s, %s, %s, %s, %s)",
        (device_id, ip_address, datetime.now(), question, reply),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_request_count(device_id):
    conn = get_db_connection()
    cur = conn.cursor()
    today = date.today()
    cur.execute(
        "SELECT COUNT(*) FROM chat_logs WHERE device_id=%s AND request_timestamp::date=%s",
        (device_id, today),
    )
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


@app.route("/chat", methods=["POST"])
def chat():
    device_id = request.json.get("device_id")
    message = request.json.get("message", "")
    if "X-Forwarded-For" in request.headers:
        user_ip = request.headers.getlist("X-Forwarded-For")[0].split(",")[0]
    else:
        user_ip = request.remote_addr

    print(f"User IP: {user_ip}, Device ID: {device_id}")

    # Blocked IP logic
    if user_ip in blocked_ips:
        remaining = blocked_ips[user_ip] - time.time()
        if remaining > 0:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            seconds = int(remaining % 60)
            msg = (
                f"Aap block hain 6 ghante tak. "
                f"Bacha hua samay: {hours} hour {minutes} min {seconds} sec."
            )
            print(f"Blocked user {user_ip} tried. Remaining: {msg}")
            return jsonify({"reply": msg}), 403
        else:
            del blocked_ips[user_ip]

    if contains_abuse(message):
        blocked_ips[user_ip] = time.time() + 21600
        print(f"User {user_ip} blocked for abuse.")
        msg = "Aapka message inappropriate tha, aapko 6 ghante ke liye block kiya gaya hai. Remaining Time: 6 hour 0 min 0 sec."
        return jsonify({"reply": msg}), 403

    if not message or not device_id:
        print(f"User IP: {user_ip}, Device ID: {device_id}, Empty message or missing device_id.")
        return jsonify({"reply": "Message aur device_id bhejna zaroori hai."}), 400

    count = get_request_count(device_id)
    if count >= USER_REQUEST_LIMIT:
        print(f"Device {device_id} exceeded daily limit.")
        return jsonify({"reply": "Daily request limit 20 exceeded for your device"}), 429

    # First time user welcome logic
    is_first = device_id not in user_first_interaction
    if is_first:
        user_first_interaction[device_id] = True
        welcome_text = "BCA Guide me aapka swagat hai!"
        print(f"User IP: {user_ip}, Device ID: {device_id}, First interaction welcome message sent.")
    else:
        welcome_text = ""

    prompt_text = f"""
1. The user's question is: "{message}". Provide a very short and direct answer.
2. If this is the user's first time, first give this information: '{welcome_text}', otherwise give a direct answer.
3. If the user asks about how to download, explain the steps very briefly.
4. Answer in the same language the user uses.
5. If the user asks who you are, say Krishna Seth made me, I am a Smart AI.
6. If the user asks to generate an image, politely decline: "I cannot generate images."
7. Do not repeatedly mention BCA Guide unless the user asks or it is necessary.
8. If you need to share the website link, give this: [https://bca-guide-web.onrender.com/](https://bca-guide-web.onrender.com/)
9. If a user asks "Where can I get templates?", you can respond with these steps in user language:
"Go to the website. On the home page, click on the 'Assignment Templates' button. Then select the template you want, fill in the required details, and click on 'Download'. Within seconds, your template will be ready."
"""

    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    headers = {"Content-Type": "application/json"}

    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Gemini API error: {response.status_code}")
        return jsonify({"reply": "Servers have heavy load ! TRY AGAIN ."}), response.status_code

    result = response.json()
    reply_text = (
        result.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "Maaf kijiye, jawab nahi mil paaya.")
    )

    print(f"User question: {message}, Bot reply: {reply_text}")

    log_chat(device_id, user_ip, message, reply_text)

    return jsonify({"reply": reply_text})

if __name__ == "__main__":
    app.run(debug=True)
