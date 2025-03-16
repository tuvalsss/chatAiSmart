from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import openai
import os
from dotenv import load_dotenv

# טעינת משתני סביבה
load_dotenv()

# הגדרת API Keys
API_KEY = os.getenv("API_KEY")

app = Flask(__name__)

def chat_with_gpt(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

@app.route("/bot", methods=["POST"])
def whatsapp():
    user_msg = request.form.get("Body")
    gpt_response = chat_with_gpt(user_msg)
    response = MessagingResponse()
    response.message(gpt_response)
    return str(response)

if __name__ == "__main__":
    app.run(port=5001, debug=True)
