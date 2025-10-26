from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

USER_REQUEST_LIMIT = 20
user_request_counts = {}

GEMINI_API_KEY = "AIzaSyBHyiMX-EZwVo4G_NSOGGMu4itjKoguRmA"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

@app.route('/chat', methods=['POST'])
def chat():
    user_ip = request.remote_addr
    print(f"User IP: {user_ip}")

    count = user_request_counts.get(user_ip, 0)
    if count >= USER_REQUEST_LIMIT:
        return jsonify({"reply": "Aapki daily request limit poori ho chuki hai. Kal phir try karein."}), 429

    user_request_counts[user_ip] = count + 1

    data = request.json
    message = data.get("message", "")
    if not message:
        return jsonify({"reply": "Message bhejna zaroori hai."}), 400

    prompt_text = f"""
    Tum ek helpful assistant ho jo BCA Guide website ke baare me baat karoge.
    Ye website notes, purane question papers (PYQs), syllabus, Assignment templates, aur bhi study materials provide karti hai.
    User ka question hai: "{message}"
    Kripya karke chhota aur seedha jawaab dein, jisme website ki materials aur download ke options ka zikr ho.
    Aur agar user ne koi specific language code maanga to woh bhi do.
    Aur agar user pooche tum kon ho ya kisne banaya hai, to bolo ki Krishna Seth ne banaya hai main ek Smart AI hu.
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
