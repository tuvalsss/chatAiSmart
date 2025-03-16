FROM python:3.9-slim

# עדכון מערכת והתקנת Xvfb
RUN apt-get update && apt-get install -y xvfb

WORKDIR /app

# העתקת קובץ הדרישות והתקנת התלויות
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתקת כל הקבצים
COPY . .

# חשיפת הפורט שהאפליקציה מאזינה לו (לדוגמה, 5005)
EXPOSE 5005

# הגדרת משתנה סביבה DISPLAY
ENV DISPLAY=:99

# הרצת האפליקציה באמצעות xvfb-run עם אפשרות auto-servernum
CMD ["xvfb-run", "--auto-servernum", "python", "chatbot.py"]
