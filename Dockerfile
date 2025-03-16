FROM python:3.9-slim

WORKDIR /app

# מעתיקים את קובץ הדרישות (אם יש) ומתקינים
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# מעתיקים את כל הקבצים
COPY . .

# מצהירים על הפורט שהאפליקציה מאזינה לו (למשל 5005)
EXPOSE 5005

# מריצים את האפליקציה
CMD ["python", "chatbot.py"]
