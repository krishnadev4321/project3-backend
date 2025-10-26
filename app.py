from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # CORS enable ???? ???? frontend ?? ??? ?? ???

# ???? Gemini API key ???? ?????
GEMINI_API_KEY = "AIzaSyBHyiMX-EZwVo4G_NSOGGMu4itjKoguRmA"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get("message", "")
    if not message:
        return jsonify({"reply": "Please send a message."}), 400

    # Gemini API ?? ??? JSON payload ????? ????
    payload = {
        "contents": [{
            "parts": [{
                "text": message
            }]
        }]
    }
    headers = {"Content-Type": "application/json"}

    # Gemini API ?? ??? ????
    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        return jsonify({"reply": "Error from Gemini API"}), response.status_code

    # API response ?? reply ??????? ?????
    result = response.json()
    reply_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Sorry, I didn't get that.")

    return jsonify({"reply": reply_text})

if __name__ == '__main__':
    app.run(debug=True)
