import pyautogui
import time

print("תמקם את העכבר על הכפתור בעוד 5 שניות...")
time.sleep(5)  # המתן 5 שניות כדי שתספיק להעביר את העכבר לכפתור
x, y = pyautogui.position()
print(f"נמצאו קואורדינטות: x={x}, y={y}")
