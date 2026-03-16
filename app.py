from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import psycopg2
from datetime import datetime, date

app = Flask(__name__)
CORS(app)

# Per device per day request limit
USER_REQUEST_LIMIT = 20
blocked_ips = {}
user_first_interaction = {}

# PostgreSQL config (Neon)
DB_CONFIG = {
    "conn_str": "postgresql://neondb_owner:npg_WU7Lgklf1EiP@ep-autumn-tree-ahcwcxfv-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"
}

# abusive words
abusive_keywords = ["sex", "xxx", "mardarchod", "betichod", "bsdk", "sexy"]


def get_db_connection():
    return psycopg2.connect(DB_CONFIG["conn_str"])


def contains_abuse(text):
    lower_text = text.lower()
    for word in abusive_keywords:
        if word in lower_text:
            return True
    return False


def log_chat(device_id, ip_address, question, reply):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO chat_logs (device_id, ip_address, request_timestamp, user_question, bot_reply) VALUES (%s,%s,%s,%s,%s)",
            (device_id, ip_address, datetime.now(), question, reply)
        )

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print("Database log error:", e)


def get_request_count(device_id):
    conn = get_db_connection()
    cur = conn.cursor()

    today = date.today()

    cur.execute(
        "SELECT COUNT(*) FROM chat_logs WHERE device_id=%s AND request_timestamp::date=%s",
        (device_id, today)
    )

    count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return count


# PREDEFINED RESPONSES
def get_predefined_reply(message):

    replies = {

        "1": "Aap Home Page par Notes section me jaakar BCA ke sabhi notes download kar sakte hain:\nhttps://bca-guide-web.onrender.com",

        "2": "Aap Home Page par Syllabus section me jaakar BCA ka latest syllabus dekh sakte hain:\nhttps://bca-guide-web.onrender.com",

        "3": "Aap Home Page par Previous year question papers yaha se download karein:\nhttps://bca-guide-web.onrender.com",

        "4": "Assignment Templates ke liye website ke Home page par 'Assignment Templates' button par click karein.",

        "5": "Aap Home Page par About Us section me website aur creator ke baare me details mil jayengi:\nhttps://bca-guide-web.onrender.com",

        "6": "Aap Home Page par Useful Links section me BCA se related and MGKVP ke important links diye gaye hain."

    }

    return replies.get(message.strip(), "Please select Valid Option From 1 to 6.")


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

            msg = f"Aap block hain 6 ghante tak. Remaining time: {hours}h {minutes}m {seconds}s"

            return jsonify({"reply": msg}), 403

        else:
            del blocked_ips[user_ip]

    # Abuse check
    if contains_abuse(message):

        blocked_ips[user_ip] = time.time() + 21600

        return jsonify({
            "reply": "Aapka message inappropriate tha. Aapko 6 ghante ke liye block kiya gaya hai."
        }), 403

    if not message or not device_id:

        return jsonify({
            "reply": "Message aur device_id bhejna zaroori hai."
        }), 400

    # Request limit check
    count = get_request_count(device_id)

    if count >= USER_REQUEST_LIMIT:

        return jsonify({
            "reply": "Daily request limit 20 exceeded for your device"
        }), 429

    # First time welcome
    if device_id not in user_first_interaction:

        user_first_interaction[device_id] = True

        welcome = "BCA Guide me aapka swagat hai!\n\n"

    else:

        welcome = ""

    # Predefined reply
    reply_text = welcome + get_predefined_reply(message)

    # Log chat
    log_chat(device_id, user_ip, message, reply_text)

    print(f"User question: {message}, Bot reply: {reply_text}")

    return jsonify({"reply": reply_text})


if __name__ == "__main__":
    app.run(debug=True)