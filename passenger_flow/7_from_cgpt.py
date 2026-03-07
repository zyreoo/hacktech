import cv2
cap = cv2.VideoCapture("airport_video.mp4")
while True:
    ret, frame = cap.read()
    if not ret:
        break
    # frame processing
cap.release()