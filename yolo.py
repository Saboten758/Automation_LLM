
import cv2
from ultralytics import YOLO

# Load the YOLOv8n model
model = YOLO('yolov8n.pt')

# Initialize the video capture object
cap = cv2.VideoCapture(0)  # 0 is the default camera; use the appropriate camera index if needed

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Perform object detection on the frame
    results = model(frame)
    
    # Draw bounding boxes on the frame
    for result in results:
        boxes = result.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame, 'Person', (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    # Display the frame
    cv2.imshow('Frame', frame)
    
    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the video capture object and close all windows
cap.release()
cv2.destroyAllWindows()
