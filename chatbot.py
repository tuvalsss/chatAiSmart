import subprocess
import pyautogui
import time
import os
import threading
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import pytesseract
from PIL import ImageGrab
import openai
import pyperclip  # מודול להדבקה מהלוח
import keyboard   # מודול לדימוי לחיצות בצורה "אגרסיבית"

# טעינת משתני סביבה
load_dotenv()

# הגדרת API Keys
NGROK_URL = os.getenv("NGROK_URL")
OPENAI_API_KEY = os.getenv("API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL")

# הגדרת הנתיב של Tesseract-OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# משתנים גלובליים לניהול מצבים
cursor_mode = False
tool_call_count = 0
latest_chat_text = "הצ'אט עוד לא נטען."
autonomous_mode = False
last_processed_chat = ""
bot_enabled = True  # מצב הבוט – מופעל כברירת מחדל

# הגדרת האזור של הצ'אט למסגרת OCR (עדכון בהתאם למיקום האמיתי)
CHAT_REGION = (1600, 1600, 2500, 2000)

# ---------------------------
# פונקציה חדשה: go_chat_region
# ---------------------------
def go_chat_region():
    """
    מנסה לאתר את תמונת האזור המלא של הצ'אט (chat_area.png) על המסך,
    לעדכן את CHAT_REGION בהתאם, לקרוא OCR מהאזור ולעדכן את latest_chat_text.
    """
    global CHAT_REGION, latest_chat_text
    try:
        region = pyautogui.locateOnScreen("chat_area.png", confidence=0.9)
        if region is not None:
            left, top, width, height = region
            CHAT_REGION = (left, top, left + width, top + height)
            print(f"[go_chat_region] Updated CHAT_REGION to: {CHAT_REGION}")
            screenshot = ImageGrab.grab(bbox=CHAT_REGION)
            ocr_text = pytesseract.image_to_string(screenshot)
            latest_chat_text = ocr_text.strip() if ocr_text.strip() else "No text detected in chat."
            return f"[go_chat_region] אזור הצ'אט עודכן: {CHAT_REGION}\nתוכן OCR:\n{latest_chat_text}"
        else:
            return "❌ לא נמצאה תמונת chat_area.png על המסך. ודא שהתמונה קיימת ושהחלון גלוי."
    except Exception as e:
        return f"❌ שגיאה ב-go_chat_region: {str(e)}"

# ---------------------------
# פונקציה לעדכון תוכן הצ'אט ברקע באמצעות OCR
# ---------------------------
def update_chat_text():
    global latest_chat_text
    while True:
        try:
            screenshot = ImageGrab.grab(bbox=CHAT_REGION)
            ocr_text = pytesseract.image_to_string(screenshot)
            latest_chat_text = ocr_text.strip() if ocr_text.strip() else "No text detected in chat."
        except Exception as e:
            latest_chat_text = f"❌ OCR error in chat: {str(e)}"
        time.sleep(5)  # עדכון כל 5 שניות

# הפעלת תהליך רקע לעדכון תוכן הצ'אט
chat_thread = threading.Thread(target=update_chat_text, daemon=True)
chat_thread.start()

# ---------------------------
# פונקציה להפעלת מצב שיחה אוטונומית – מאזינה לצ'אט ומגיבה אליו
# ---------------------------
def autonomous_conversation_loop():
    global autonomous_mode, last_processed_chat
    while autonomous_mode:
        if latest_chat_text != last_processed_chat and latest_chat_text != "No text detected in chat.":
            prompt = f"Based on the following chat content, generate a command to interact with the cursor: {latest_chat_text}"
            command_response = ask_gpt_api(prompt)
            print(f"[Autonomous] Generated command: {command_response}")
            send_command_to_cursor(command_response)
            last_processed_chat = latest_chat_text
        time.sleep(10)  # בדיקה כל 10 שניות

# יצירת אפליקציית Flask
app = Flask(__name__)
CORS(app)

# ---------------------------
# פונקציה לשיחה עם GPT API
# ---------------------------
def ask_gpt_api(user_input):
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # ניתן לעדכן ל-gpt-4 אם נדרש
        messages=[{"role": "user", "content": user_input}]
    )
    return response.choices[0].message.content

# ---------------------------
# פונקציה לעדכון README – בעברית (סיכום) ובאנגלית (פרוט מלא)
# ---------------------------
def update_readme():
    try:
        hebrew_summary = ask_gpt_api("בבקשה כתוב סיכום קצר בעברית לפרויקט זה, רק נקודות עיקריות.")
        english_detail = ask_gpt_api("Please provide a detailed README for this project in English.")
        content = f"## Hebrew Summary\n{hebrew_summary}\n\n## Detailed README (English)\n{english_detail}"
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(content)
        print("[Update README] Updated successfully.")
        return "README updated successfully."
    except Exception as e:
        print(f"[Update README] Failed: {str(e)}")
        return f"Failed to update README: {str(e)}"

# ---------------------------
# פונקציה לשליחת הודעות אינטראקטיביות (Interactive Buttons) בוואטסאפ
# ---------------------------
def send_interactive_commands(to_phone):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        interactive_message = {
            "type": "button",
            "body": { "text": "בחר פקודה:" },
            "action": {
                "buttons": [
                    { "type": "reply", "reply": {"id": "accept_all", "title": "Accept All"} },
                    { "type": "reply", "reply": {"id": "toggle_cursor", "title": "Toggle Cursor"} },
                    { "type": "reply", "reply": {"id": "toggle_autonomous", "title": "Toggle Autonomous"} },
                    { "type": "reply", "reply": {"id": "bot_off", "title": "Bot Off"} },
                    { "type": "reply", "reply": {"id": "bot_on", "title": "Bot On"} }
                ]
            }
        }
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_phone,
            interactive=interactive_message
        )
        return message.sid
    except Exception as e:
        print(f"[Interactive Commands] Error: {str(e)}")
        return None

# ---------------------------
# פונקציה לביצוע סגירת השרת – כיבוי הבוט לגמרי
# ---------------------------
def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    print("[Shutdown] Server is shutting down.")
    func()

# ---------------------------
# פונקציה שמבצעת את פעולת "resume conversation"
# ---------------------------
def resume_conversation():
    global tool_call_count
    time.sleep(3)  # השהייה של 3 שניות לפני לחיצה
    x, y = 2224, 1268  # מיקום "resume the conversation"
    pyautogui.moveTo(x, y, duration=0.5)
    pyautogui.click()
    tool_call_count = 0
    print("[Resume] Conversation resumed after 25 tool calls.")
    return "Resumed conversation after 25 tool calls."

# ---------------------------
# פונקציה המדמה לחיצות במקלדת בצורה "אגרסיבית" – CTRL+V ואחריו Enter
# ---------------------------
def simulate_ctrl_v_and_enter():
    keyboard.press_and_release('ctrl+v')
    time.sleep(0.2)
    keyboard.press_and_release('enter')
    time.sleep(0.2)

# ---------------------------
# פונקציה משופרת לשליחת הודעות לצ'אט באמצעות הדבקה מהלוח
# ---------------------------
def send_message_to_chat(message):
    """
    פונקציה שמנסה לאתר את תיבת הקלט באמצעות תמונת תבנית.
    אם לא נמצאה, משתמשת בקואורדינטות ברירת מחדל (1847, 1693).
    לאחר מכן, לוחצת על תיבת הקלט, מוודאת שהחלון קיבל מיקוד, ומדביקה את ההודעה מהלוח.
    """
    try:
        chat_input = pyautogui.locateCenterOnScreen('chat_input.png', confidence=0.9)
        if chat_input is not None:
            input_x, input_y = chat_input
            print(f"[send_message_to_chat] Found chat input at: {input_x}, {input_y}")
        else:
            raise Exception("Chat input image not found")
    except Exception as e:
        print(f"[send_message_to_chat] Using default coordinates due to: {e}")
        input_x, input_y = 1847, 1693

    pyautogui.click(input_x, input_y)
    time.sleep(1)  # השהייה לוודא שהחלון מקבל מיקוד
    pyperclip.copy(message)
    time.sleep(0.1)
    simulate_ctrl_v_and_enter()

# ---------------------------
# פונקציה חדשה: send_image_now
# ---------------------------
def send_image_now():
    """
    לוכדת את תמונת הצ'אט לפי CHAT_REGION, שומרת אותה כ-IMGNEW1.PNG בתוך תיקיית static (מחליפה קבצים ישנים),
    ומחזירה את הנתיב היחסי של הקובץ.
    """
    try:
        screenshot = ImageGrab.grab(bbox=CHAT_REGION)
        static_folder = os.path.join(os.getcwd(), "static")
        if not os.path.exists(static_folder):
            os.makedirs(static_folder)
        image_path = os.path.join(static_folder, "IMGNEW1.PNG")
        screenshot.save(image_path)
        print("[send_image_now] Image captured and saved as static/IMGNEW1.PNG")
        return "IMGNEW1.PNG"
    except Exception as e:
        print(f"[send_image_now] Error: {str(e)}")
        return None

# ---------------------------
# פונקציה מרכזית לעיבוד הודעות
# ---------------------------
def process_message(message):
    global cursor_mode, tool_call_count, latest_chat_text, autonomous_mode, bot_enabled
    if not message.strip():
        return "❌ ההודעה שלך ריקה, נסה לכתוב משהו."

    # אם ההודעה מתחילה באות "C" גדולה, היא תתפס כצ'אט חי – ההודעה תוקלד לתיבת הקלט
    if message.strip().startswith("C"):
        chat_message = message.strip()[1:].strip()
        print(f"[Direct Chat Input] {chat_message}")
        send_message_to_chat(chat_message)
        return f"Message '{chat_message}' sent to chat."

    lower_message = message.lower().strip()

    # בדיקת מצב הבוט – אם כבוי, רק פקודת 'bot on' תופעל
    if not bot_enabled and lower_message not in ["bot on", "off all now"]:
        return "Bot is disabled. Send 'bot on' to enable. (Red)"

    # פקודת כיבוי הבוט – "off all now" סוגרת את השרת
    if lower_message == "off all now":
        shutdown_server()
        return "Bot is shutting down..."

    # Toggle לבוט
    if lower_message == "bot off":
        bot_enabled = False
        print("[Bot] Bot disabled.")
        return "Bot disabled (Red)"
    if lower_message == "bot on":
        bot_enabled = True
        print("[Bot] Bot enabled.")
        return "Bot enabled (Green)"

    # Toggle למצב קורסור
    if lower_message == "toggle cursor":
        global cursor_mode
        cursor_mode = not cursor_mode
        if cursor_mode:
            print("[Cursor] Cursor mode activated.")
            return "Cursor mode activated (Green)"
        else:
            update_result = update_readme()
            print("[Cursor] Cursor mode deactivated.")
            return "Cursor mode deactivated (Red). " + update_result

    # Toggle למצב שיחה אוטונומית
    if lower_message == "toggle autonomous":
        global autonomous_mode
        if autonomous_mode:
            autonomous_mode = False
            print("[Autonomous] Autonomous conversation mode deactivated.")
            return "Autonomous conversation mode deactivated (Red)"
        else:
            autonomous_mode = True
            threading.Thread(target=autonomous_conversation_loop, daemon=True).start()
            print("[Autonomous] Autonomous conversation mode activated.")
            return "Autonomous conversation mode activated (Green)"

    # פקודות קיימות:
    if "show commands" in lower_message:
        return "interactive"  # סימן מיוחד לטיפול ב-/bot
    if "resume 25" in lower_message:
        return resume_conversation()
    if "enter cursor mode" in lower_message:
        cursor_mode = True
        print("[Cursor] Entering cursor mode.")
        return "Entering cursor mode. (Green)"
    if "exit cursor mode" in lower_message:
        cursor_mode = False
        update_result = update_readme()
        print("[Cursor] Exiting cursor mode.")
        return "Exiting cursor mode. (Red) " + update_result
    if "read chat" in lower_message or "get chat" in lower_message:
        return f"Chat Content:\n{latest_chat_text}"
    
    # טיפול בפקודת "TUT" – לשליחת מדריך המשתמש (מ- static)
    if message.strip() == "TUT":
        manual_url = NGROK_URL + "static/UserManual.txt"
        return f"Please download your user manual here: {manual_url}"

    # טיפול בפקודת "getimagesnow" – כאן הפקודה מתועדת בהמשך (נוספת לטיפול בפקודה בדאטה ב־/bot)
    if lower_message == "getimagesnow":
        return "getimagesnow"

    # במצב קורסור, כל הודעה היא פקודת קורסור
    if cursor_mode:
        result = send_command_to_cursor(message)
        return result

    # פקודות רגילות נוספות
    if "accept all" in lower_message:
        result = focus_cursor_and_accept_all()
        return result
    elif "cursor" in lower_message:
        result = send_command_to_cursor(message)
        return result
    elif "qa" in lower_message:
        result = subprocess.run(["python", "QA_Logger.py"], capture_output=True, text=True)
        return f"QA הושלם: {result.stdout}"
    elif "backup" in lower_message:
        result = subprocess.run(["python", "Github_Backup.py"], capture_output=True, text=True)
        return f"גיבוי הושלם: {result.stdout}"
    elif "index" in lower_message:
        result = subprocess.run(["python", "Project_Indexing.py"], capture_output=True, text=True)
        return f"אינדוקס הושלם: {result.stdout}"
    elif "read screen" in lower_message or "read text" in lower_message:
        try:
            screenshot = ImageGrab.grab()
            ocr_text = pytesseract.image_to_string(screenshot)
            return f"Screen Text:\n{ocr_text}"
        except Exception as e:
            return f"❌ OCR error: {str(e)}"
    else:
        return ask_gpt_api(message)

# ---------------------------
# פונקציות לשליטה בקורסור
# ---------------------------
def focus_cursor_and_accept_all():
    global tool_call_count
    time.sleep(3)  # השהייה של 3 שניות
    x, y = 2462, 1493
    pyautogui.moveTo(x, y, duration=0.5)
    pyautogui.click()
    tool_call_count += 1
    result = "✅ ACCEPT ALL נלחץ!"
    if tool_call_count >= 25:
        resume_msg = resume_conversation()
        result += " " + resume_msg
    return result

def send_command_to_cursor(command):
    global tool_call_count
    command_lower = command.lower()
    result = ""
    
    # אם הפקודה היא "go chat region" – עדכון אזור הצ'אט על בסיס תמונת chat_area.png
    if "go chat region" in command_lower:
        result = go_chat_region()
        return result

    if "accept-all" in command_lower or "accept all" in command_lower:
        result = focus_cursor_and_accept_all()
        return result

    if "go chat" in command_lower:
        # עדכון הקואורדינטות לפי מה שסיפקת: x=1847, y=1693
        x, y = 1847, 1693
        pyautogui.moveTo(x, y, duration=0.5)
        pyautogui.click()
        result = "Focusing on the chat window."
    elif "add file" in command_lower:
        x, y = 1522, 1663
        pyautogui.moveTo(x, y, duration=0.5)
        pyautogui.click()
        result = "Pressed the 'Add File' button in the cursor chat window."
    elif "send button" in command_lower:
        x, y = 2498, 1740
        pyautogui.moveTo(x, y, duration=0.5)
        pyautogui.click()
        result = "Pressed the SEND button in the cursor chat."
    elif "new chat" in command_lower:
        x, y = 2410, 77
        pyautogui.moveTo(x, y, duration=0.5)
        pyautogui.click()
        result = "Opened a new chat in the cursor."
    else:
        move_match = re.search(r"move to (\d+)\s*,\s*(\d+)", command_lower)
        if move_match:
            x = int(move_match.group(1))
            y = int(move_match.group(2))
            pyautogui.moveTo(x, y, duration=0.5)
            result = f"Moving the cursor to: {x}, {y}"
        elif "click" in command_lower:
            pyautogui.click()
            result = "Performing a click."
        else:
            result = f"Command not recognized: {command}"
            
    tool_call_count += 1
    if tool_call_count >= 25:
        resume_msg = resume_conversation()
        result += " " + resume_msg
    return result

# ---------------------------
# נתיבים לצ'אט
# ---------------------------
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data:
            return jsonify({"response": "❌ The message was not received properly. Try again."})
        user_input = data["message"]
        response_text = process_message(user_input)
        if response_text == "interactive":
            return jsonify({"response": "Interactive commands sent."})
        return jsonify({"response": response_text})
    except Exception as e:
        return jsonify({"response": f'❌ Internal error: {str(e)}'})

@app.route("/run_qa", methods=["POST"])
def run_qa():
    response_text = process_message("qa")
    return jsonify({"status": "QA", "output": response_text})

@app.route("/backup_github", methods=["POST"])
def backup_github():
    response_text = process_message("backup")
    return jsonify({"status": "Backup", "output": response_text})

@app.route("/index_project", methods=["POST"])
def index_project():
    response_text = process_message("index")
    return jsonify({"status": "Index", "output": response_text})

# ---------------------------
# נתיב לשליחת הודעות WhatsApp – כולל טיפול בפקודות "TUT", "getimagesnow" ו-"show commands"
# ---------------------------
@app.route("/bot", methods=["GET", "POST"])
def bot():
    print("Received WhatsApp message:", request.form)
    user_msg = request.form.get("Body")
    from_phone = request.form.get("From")
    response = MessagingResponse()
    
    # טיפול בפקודת TUT – שליחת מדריך המשתמש מהתיקייה static
    if user_msg and user_msg.strip() == "TUT":
        manual_url = NGROK_URL + "static/UserManual.txt"
        response.message("Please download your user manual here: " + manual_url)
        return str(response)
    
    # טיפול בפקודת getimagesnow – שליחת תמונת מדיה באמצעות Twilio
    if user_msg and user_msg.lower().strip() == "getimagesnow":
        filename = send_image_now()  # תופסת ושומרת את התמונה כ-IMGNEW1.PNG בתוך static
        if filename:
            image_url = NGROK_URL + "static/" + filename
            msg = response.message("Here is the current chat image:")
            msg.media(image_url)
        else:
            response.message("❌ Failed to capture image.")
        return str(response)
    
    # טיפול בפקודת "show commands"
    if user_msg and "show commands" in user_msg.lower():
        sid = send_interactive_commands(from_phone)
        if sid:
            response.message("Interactive commands sent.")
        else:
            response.message("Available commands: Accept All, Toggle Cursor, Toggle Autonomous, Bot Off, Bot On")
        return str(response)
    
    # טיפול בכל הודעה אחרת
    response_text = process_message(user_msg)
    response.message(response_text)
    return str(response)

# ---------------------------
# נתיב לקבלת תוכן הצ'אט (OCR)
# ---------------------------
@app.route("/get_chat", methods=["GET"])
def get_chat():
    return jsonify({"chat_content": latest_chat_text})

# ---------------------------
# נתיב שמגיש קבצים – כולל IMGNEW1.PNG and UserManual.txt
# ---------------------------
@app.route("/")
def index():
    return send_from_directory(os.getcwd(), "ChatbotUi.html")

@app.route("/IMGNEW1.PNG")
def serve_imgnew():
    return send_from_directory(os.path.join(os.getcwd(), "static"), "IMGNEW1.PNG")

@app.route("/UserManual.txt")
def serve_manual():
    return send_from_directory(os.path.join(os.getcwd(), "static"), "UserManual.txt")

@app.route("/read_readme", methods=["GET"])
def read_readme():
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"readme": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5005, debug=True)
