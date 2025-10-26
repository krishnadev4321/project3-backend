from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time

app = Flask(__name__)
CORS(app)

USER_REQUEST_LIMIT = 20
user_request_counts = {}
blocked_ips = {}  # IPs blocked with unblock timestamp

GEMINI_API_KEY = "AIzaSyBHyiMX-EZwVo4G_NSOGGMu4itjKoguRmA"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

abusive_keywords = ['sex', 'xxx', 'gandi', 'gaali', 'badword1', 'badword2']  # ??? ?? ???? ????? ?? ?????? ??????

def contains_abuse(text):
    lower_text = text.lower()
    for word in abusive_keywords:
        if word in lower_text:
            return True
    return False

@app.route('/chat', methods=['POST'])
def chat():
    # Get real user IP behind proxy if present
    if "X-Forwarded-For" in request.headers:
        user_ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    else:
        user_ip = request.remote_addr
    print(f"User IP: {user_ip}")

    # Check if blocked
    if user_ip in blocked_ips:
        if time.time() < blocked_ips[user_ip]:
            return jsonify({"reply": "Aap block hain 24 ghante tak. Kripya baad mein fir koshish karein."}), 403
        else:
            del blocked_ips[user_ip]

    if contains_abuse(request.json.get("message", "")):
        blocked_ips[user_ip] = time.time() + 86400  # block for 24 hours
        return jsonify({"reply": "Aapka message inappropriate tha, aapko 24 ghante ke liye block kiya gaya hai."}), 403

    count = user_request_counts.get(user_ip, 0)
    if count >= USER_REQUEST_LIMIT:
        return jsonify({"reply": "Aapki daily request limit puri ho gayi hai, kal try karo."}), 429

    user_request_counts[user_ip] = count + 1

    message = request.json.get("message", "")
    if not message:
        return jsonify({"reply": "Message bhejna zaroori hai."}), 400

    prompt_text = f"""
    Tum ek helpful assistant ho jo BCA Guide website ke baare me baat karoge.
    Ye website notes, purane question papers (PYQs), syllabus, Assignment templates, aur bhi study materials provide karti hai.
    User ka question hai: "{message}"
    Kripya karke chhota aur seedha jawaab dein, jisme website ki materials aur download ke options ka zikr ho.
    Agar user kisi language me baat kare to use usi mein jawab do.
    Agar user pooche ki tum kon ho ya kisne banaya hai, to bolo ki Krishna Seth ne banaya hai main ek Smart AI hu.
    Agar user website ki link mange to ye dena: https://bca-guide-web.onrender.com/
    """

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt_text
            }]
        }]
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        return jsonify({"reply": "Gemini API se error aaya."}), response.status_code

    result = response.json()
    reply_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Maaf kijiye, jawab nahi mil paaya.")

    return jsonify({"reply": reply_text})

if __name__ == '__main__':
    app.run(debug=True)
