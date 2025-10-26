from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # CORS enable kar rahe hain taki frontend se request aaye toh block na ho

# Gemini API ki key yahan dalein
GEMINI_API_KEY = "AIzaSyBHyiMX-EZwVo4G_NSOGGMu4itjKoguRmA"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get("message", "")
    if not message:
        return jsonify({"reply": "Please message bhejein."}), 400

    # Customized prompt jisme website ke baare me mention hai
    prompt_text = f"""
    Tum ek helpful assistant ho jo BCA Guide website ke baare me baat karoge.
    Ye website notes, purane question papers (PYQs), syllabus, Assignment templates , aur bhi study materials provide karti hai.
    User ka question hai: "{message}"
    Kripya karke chhota aur seedha jawaab dein, jisme website ki materials aur download ke options ka zikr ho.
    aur agar User jis bhi language me baat karega to tum bhi ussi language me baat karoge .
    aur agar user kisi language ka code manga hai to tume usse code bhi doge and 
    message bahut hi chota and relevant dena
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
