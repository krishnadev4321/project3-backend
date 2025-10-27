from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
import math

app = Flask(__name__)
CORS(app)

USER_REQUEST_LIMIT = 50
user_request_counts = {}
blocked_ips = {}  # IPs blocked with unblock timestamp

GEMINI_API_KEY = "AIzaSyBHyiMX-EZwVo4G_NSOGGMu4itjKoguRmA"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

abusive_keywords = ['sex', 'xxx', 'mardarchod', 'betichod', 'bsdk', 'sexy']

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
        remaining = blocked_ips[user_ip] - time.time()
        if remaining > 0:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            seconds = int(remaining % 60)
            msg = (
                f"Aap block hain 6 ghante tak. "
                f"Bacha hua samay: {hours} hour {minutes} min {seconds} sec."
            )
            print(f"Blocked user {user_ip} tried to send message. Remaining: {msg}")
            return jsonify({"reply": msg}), 403
        else:
            del blocked_ips[user_ip]

    # Check abuse content
    message = request.json.get("message", "")
    print(f"User Question: {message}")

    if contains_abuse(message):
        blocked_ips[user_ip] = time.time() + 21600  # 6 hours block
        print(f"User {user_ip} blocked for abuse.")
        msg = "Aapka message inappropriate tha, aapko 6 ghante ke liye block kiya gaya hai. Remaining Time: 6 hour 0 min 0 sec."
        return jsonify({"reply": msg}), 403

    # Check request limits
    count = user_request_counts.get(user_ip, 0)
    if count >= USER_REQUEST_LIMIT:
        print(f"User {user_ip} exceeded daily limit.")
        return jsonify({"reply": "Aapki daily request limit puri ho gayi hai, kal fir try karen."}), 429

    user_request_counts[user_ip] = count + 1

    if not message:
        return jsonify({"reply": "Message bhejna zaroori hai."}), 400

    prompt_text = f"""
    1.Tum ek helpful assistant ho jo BCA Guide website ke baare me baat karoge.
    2.Ye website notes, purane question papers (PYQs), syllabus, Assignment templates, aur bhi study materials provide karti hai.
    3.User ka question hai: "{message}"
    c. koi bhi answer tum ek dum ekdum short me do .
    4.Kripya karke bahut chhota aur seedha jawaab doge, jisme website ki materials aur download ke options ka zikr ho.
    5.Agar user kisi language me baat kare to use usi mein jawab do.
    6.Agar user pooche ki tum kon ho ya kisne banaya hai, to bolo ki Krishna Seth ne banaya hai main ek Smart AI hu.
    7.Agar user website ki link mange to ye dena: https://bca-guide-web.onrender.com/
    8.agar tumse koi puche ki notes kaise download kare to tu bata ki aap notes section se kisi bhi semester ke notes download kar sakte hai .
    9.agar tumse koi puche ki PyQs kaise download kare to tu bata ki aap pyqs section se kisi bhi semester ke 2018-2025 tk pyqs download kar sakte hai download kar sakte hai .
    9.agar tumse koi puche ki Templates kaise download kare to tu bata ki home page par assignment templates button par click kariye uske baad waha template choose karko aayega and aap select karke lets cretae par click kariye phirr waha apna poora detail enter kariye 
    uske baad download par click kariye within a click designer realiable , without any struggle aapka title page ready ho jayega . bina kisi dikkat ke and ye bahut hi fast hai isis ko banake bol dena tum and showrt me 
    10.agar tumse koi kahe ki image generate karne ko tu seedha mana kar dena main nhi kar sakta huun .
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
        print(f"Gemini API error for user {user_ip}: {response.status_code}")
        return jsonify({"reply": "Gemini API se error aaya."}), response.status_code

    result = response.json()
    reply_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Maaf kijiye, jawab nahi mil paaya.")

    print(f"Bot Reply to {user_ip}: {reply_text}")

    return jsonify({"reply": reply_text})

if __name__ == '__main__':
    app.run(debug=True)
