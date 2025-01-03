import cv2
import numpy as np
from ultralytics import YOLO
import smtplib
from email.mime.text import MIMEText
import time
import threading
import os
import sys
from datetime import datetime
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import RPi.GPIO as GPIO

# ANSI escape codes for colors
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

# GPIO setup
LED_PIN = 18  # GPIO18 (pin 12)
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

def find_available_camera():
    """Try to find an available camera, prioritizing CSI camera if available."""
    # First try CSI camera (Raspberry Pi camera module)
    try:
        # Try gstreamer pipeline for CSI camera
        gstreamer_pipeline = (
            "nvarguscamerasrc ! "
            "video/x-raw(memory:NVMM), "
            "width=1280, height=720, "
            "format=(string)NV12, "
            "framerate=30/1 ! "
            "nvvidconv ! "
            "video/x-raw, format=(string)BGRx ! "
            "videoconvert ! "
            "video/x-raw, format=(string)BGR ! "
            "appsink"
        )
        cap = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                logging.info("Using CSI camera")
                return cap
            cap.release()
    except Exception as e:
        logging.warning(f"CSI camera not available: {e}")
    
    # If CSI camera fails, try legacy CSI camera method
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            # Try to set typical CSI camera properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)
            ret, _ = cap.read()
            if ret:
                logging.info("Using legacy CSI camera")
                return cap
            cap.release()
    except Exception as e:
        logging.warning(f"Legacy CSI camera not available: {e}")

    # Finally, try USB cameras
    for i in range(10):  # Test first 10 camera indices
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    logging.info(f"Using USB camera at index {i}")
                    return cap
                cap.release()
        except Exception as e:
            logging.warning(f"Failed to open camera at index {i}: {e}")
    
    logging.error("No cameras found")
    return None

class PeopleMonitor:
    def __init__(self, 
                 slack_token='your_slack_token',
                 slack_channel='#team-alerts',
                 email_sender='your_email@example.com', 
                 email_password='your_app_password', 
                 email_recipient='team_lead@example.com', 
                 min_people=2, 
                 check_interval=300,
                 log_dir='./monitoring_logs'):
        # Setup logging
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, 'people_monitoring.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # People detection setup
        self.model = YOLO('yolov8n.pt')
        
        # Notification channels
        self.slack_token = slack_token
        self.slack_channel = slack_channel
        self.slack_client = WebClient(token=self.slack_token)
        
        # Email setup
        self.email_sender = email_sender
        self.email_password = email_password
        self.email_recipient = email_recipient
        
        # Monitoring parameters
        self.min_people = min_people
        self.check_interval = check_interval
        self.monitoring = False
        self.log_dir = log_dir
        
        # Video recording setup
        self.video_writer = None
        self.current_video_path = None

    def send_slack_alert(self, message):
        try:
            response = self.slack_client.chat_postMessage(
                channel=self.slack_channel,
                text=message
            )
            self.logger.info(f"Slack alert sent: {message}")
        except SlackApiError as e:
            self.logger.error(f"Failed to send Slack alert: {e}")

    def send_email_alert(self, current_count):
        try:
            msg = MIMEText(f'ALERT: Only {current_count} person(s) detected in sensitive project area!')
            msg['Subject'] = 'People Monitoring Alert'
            msg['From'] = self.email_sender
            msg['To'] = self.email_recipient

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
                smtp_server.login(self.email_sender, self.email_password)
                smtp_server.sendmail(self.email_sender, self.email_recipient, msg.as_string())
            
            self.logger.info(f"Email alert sent for {current_count} people detected")
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")

    def start_video_recording(self):
        try:
            # Stop any existing recording
            self.stop_video_recording()
            
            # Create a new video file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_video_path = os.path.join(
                self.log_dir, 
                f'security_recording_{timestamp}.avi'
            )
            
            # Get camera properties from the main capture
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Initialize video writer with XVID codec (more compatible with Linux)
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.video_writer = cv2.VideoWriter(
                self.current_video_path, 
                fourcc, 
                10.0,  # Lower framerate for better performance
                (width, height)
            )
            
            self.logger.info(f"Started video recording: {self.current_video_path}")
        except Exception as e:
            self.logger.error(f"Error starting video recording: {e}")
            self.video_writer = None

    def stop_video_recording(self):
        try:
            if self.video_writer is not None:
                self.video_writer.release()
                self.logger.info(f"Stopped video recording: {self.current_video_path}")
                self.video_writer = None
                self.current_video_path = None
        except Exception as e:
            self.logger.error(f"Error stopping video recording: {e}")
            self.video_writer = None
            self.current_video_path = None

    def display_frame(self, frame, people_count):
        try:
            # Clear the previous line in terminal
            sys.stdout.write('\033[F\033[K')
            
            # Print colored status in terminal
            if people_count >= self.min_people:
                status = f"{GREEN}✓ {people_count} people detected (Meeting minimum requirement of {self.min_people}){RESET}"
            else:
                status = f"{RED}⚠ Only {people_count} person(s) detected (Below minimum requirement of {self.min_people}){RESET}"
            
            print(status)
            sys.stdout.flush()
            return True
                
        except Exception as e:
            self.logger.error(f"Display error: {e}")
            print(f"People detected: {people_count}")
            sys.stdout.flush()
            return True

    def update_led(self, people_count):
        """Update the LED based on the number of people detected."""
        try:
            if people_count < self.min_people:
                if people_count == 1:
                    # LED OFF for exactly one person
                    GPIO.output(LED_PIN, GPIO.LOW)
                else:
                    # LED ON (white) for zero people
                    GPIO.output(LED_PIN, GPIO.HIGH)
            else:
                # LED ON (green) for two or more people
                GPIO.output(LED_PIN, GPIO.HIGH)
        except Exception as e:
            self.logger.error(f"Failed to update LED: {e}")

    def detect_and_display_people(self):
        try:
            self.cap = find_available_camera()
            if self.cap is None:
                self.logger.error("Error: Could not find any available cameras")
                return
            
            recording_started = False
            print("\n")  # Add initial newline for status updates
            last_alert_time = 0
            alert_interval = 5  # Minimum seconds between alerts
            
            while self.monitoring:
                ret, frame = self.cap.read()
                if not ret:
                    self.logger.error("Failed to grab frame")
                    break
                
                # Detect people using YOLO
                results = self.model(frame, verbose=False)
                
                # Filter only person class (class 0 is person)
                people = [box for box in results[0].boxes if int(box.cls) == 0]
                people_count = len(people)
                
                # Update LED based on people count
                self.update_led(people_count)
                
                # Draw bounding boxes
                frame_with_boxes = frame.copy()
                for box in people:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    color = (0, 0, 255) if people_count < self.min_people else (0, 255, 0)
                    cv2.rectangle(frame_with_boxes, (x1, y1), (x2, y2), color, 2)
                
                # Add text overlay
                text_color = (0, 0, 255) if people_count < self.min_people else (0, 255, 0)
                cv2.putText(frame_with_boxes, f'People: {people_count}', (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)
                
                # Display the frame and status
                self.display_frame(frame_with_boxes, people_count)
                
                current_time = time.time()
                
                # Handle recording if fewer than minimum people
                if people_count < self.min_people:
                    if not recording_started:
                        self.start_video_recording()
                        recording_started = True
                    
                    if self.video_writer is not None:
                        try:
                            self.video_writer.write(frame_with_boxes)  # Save frame with boxes
                        except Exception as e:
                            self.logger.error(f"Error writing video frame: {e}")
                    
                    # Only log alerts at the specified interval
                    if current_time - last_alert_time >= alert_interval:
                        alert_message = f"SECURITY ALERT: Only {people_count} person(s) detected in sensitive project area!"
                        self.logger.warning(alert_message)
                        last_alert_time = current_time
                else:
                    if recording_started:
                        self.stop_video_recording()
                        recording_started = False
                
                time.sleep(0.05)  # Reduced sleep time for smoother operation
            
            # Cleanup
            self.stop_video_recording()
            if self.cap is not None:
                self.cap.release()
        
        except Exception as e:
            self.logger.error(f"Unexpected error in detection: {e}")
            self.monitoring = False
        finally:
            # Ensure cleanup happens
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()
            self.stop_video_recording()

    def start_monitoring(self):
        self.monitoring = True
        monitor_thread = threading.Thread(target=self.detect_and_display_people)
        monitor_thread.start()

    def stop_monitoring(self):
        self.monitoring = False
        time.sleep(0.1)  # Reduced cleanup time
        # Ensure cleanup happens
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
        self.stop_video_recording()
        # Turn off LED before closing
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.cleanup()

if __name__ == "__main__":
    try:
        monitor = PeopleMonitor(
            slack_token='xoxb-your-slack-token',
            slack_channel='#team-alerts',
            email_sender='wyantethan@gmail.com',
            email_password='your_app_password',
            email_recipient='wyantethan@gmail.com',
            min_people=2
        )
        
        monitor.start_monitoring()
        print("Press Ctrl+C to quit")
        while monitor.monitoring:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        monitor.stop_monitoring()
    finally:
        # Ensure GPIO is cleaned up
        GPIO.cleanup()
