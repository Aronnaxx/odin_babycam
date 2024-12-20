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
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

# ANSI escape codes for colors
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

class VideoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Live Video Feed")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.label = QLabel()
        self.layout.addWidget(self.label)
        self.resize(800, 600)
        
    def update_frame(self, frame):
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.label.size(), Qt.KeepAspectRatio)
        self.label.setPixmap(scaled_pixmap)

class PeopleMonitor:
    def __init__(self, 
                 slack_token='your_slack_token',
                 slack_channel='#team-alerts',
                 email_sender='your_email@example.com', 
                 email_password='your_app_password', 
                 email_recipient='team_lead@example.com', 
                 min_people=2, 
                 check_interval=300,
                 log_dir='./monitoring_logs',
                 display_method='qt'):
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
        self.display_method = display_method
        
        # Video recording setup
        self.incident_video_writer = None
        self.continuous_video_writer = None
        self.current_incident_video_path = None
        self.current_continuous_video_path = None
        
        # Qt window setup
        if self.display_method == 'qt':
            self.app = QApplication.instance() or QApplication(sys.argv)
            self.window = VideoWindow()
            self.window.show()

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

    def start_continuous_recording(self):
        try:
            # Stop any existing continuous recording
            self.stop_continuous_recording()
            
            # Create a new video file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_continuous_video_path = os.path.join(
                self.log_dir, 
                f'continuous_recording_{timestamp}.mp4'
            )
            
            # Get camera properties from the main capture
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Initialize video writer with H264 codec
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.continuous_video_writer = cv2.VideoWriter(
                self.current_continuous_video_path, 
                fourcc, 
                10.0,
                (width, height)
            )
            
            self.logger.info(f"Started continuous recording: {self.current_continuous_video_path}")
        except Exception as e:
            self.logger.error(f"Error starting continuous recording: {e}")
            self.continuous_video_writer = None

    def stop_continuous_recording(self):
        try:
            if self.continuous_video_writer is not None:
                self.continuous_video_writer.release()
                self.logger.info(f"Stopped continuous recording: {self.current_continuous_video_path}")
                self.continuous_video_writer = None
                self.current_continuous_video_path = None
        except Exception as e:
            self.logger.error(f"Error stopping continuous recording: {e}")
            self.continuous_video_writer = None
            self.current_continuous_video_path = None

    def start_incident_recording(self):
        try:
            # Stop any existing incident recording
            self.stop_incident_recording()
            
            # Create a new video file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_incident_video_path = os.path.join(
                self.log_dir, 
                f'incident_recording_{timestamp}.mp4'
            )
            
            # Get camera properties from the main capture
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Initialize video writer with H264 codec
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.incident_video_writer = cv2.VideoWriter(
                self.current_incident_video_path, 
                fourcc, 
                10.0,
                (width, height)
            )
            
            self.logger.info(f"Started incident recording: {self.current_incident_video_path}")
        except Exception as e:
            self.logger.error(f"Error starting incident recording: {e}")
            self.incident_video_writer = None

    def stop_incident_recording(self):
        try:
            if self.incident_video_writer is not None:
                self.incident_video_writer.release()
                self.logger.info(f"Stopped incident recording: {self.current_incident_video_path}")
                self.incident_video_writer = None
                self.current_incident_video_path = None
        except Exception as e:
            self.logger.error(f"Error stopping incident recording: {e}")
            self.incident_video_writer = None
            self.current_incident_video_path = None

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
            
            # Update Qt window if using qt display method
            if self.display_method == 'qt':
                # Convert BGR to RGB for Qt
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.window.update_frame(rgb_frame)
                self.app.processEvents()  # Process Qt events
                
            return True
                
        except Exception as e:
            self.logger.error(f"Display error: {e}")
            print(f"People detected: {people_count}")
            sys.stdout.flush()
            return True

    def detect_and_display_people(self):
        try:
            self.cap = cv2.VideoCapture(0)
            
            if not self.cap.isOpened():
                self.logger.error("Error: Could not open camera.")
                return

            incident_recording_started = False
            print("\n")  # Add initial newline for status updates
            last_alert_time = 0
            alert_interval = 5  # Minimum seconds between alerts
            
            # Start continuous recording immediately
            self.start_continuous_recording()
            
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
                
                # Always write to continuous recording
                if self.continuous_video_writer is not None:
                    try:
                        self.continuous_video_writer.write(frame_with_boxes)
                    except Exception as e:
                        self.logger.error(f"Error writing continuous video frame: {e}")
                
                current_time = time.time()
                
                # Handle incident recording if fewer than minimum people
                if people_count < self.min_people:
                    if not incident_recording_started:
                        self.start_incident_recording()
                        incident_recording_started = True
                    
                    if self.incident_video_writer is not None:
                        try:
                            self.incident_video_writer.write(frame_with_boxes)
                        except Exception as e:
                            self.logger.error(f"Error writing incident video frame: {e}")
                    
                    # Only log alerts at the specified interval
                    if current_time - last_alert_time >= alert_interval:
                        alert_message = f"SECURITY ALERT: Only {people_count} person(s) detected in sensitive project area!"
                        self.logger.warning(alert_message)
                        last_alert_time = current_time
                else:
                    if incident_recording_started:
                        self.stop_incident_recording()
                        incident_recording_started = False
                
                time.sleep(0.05)  # Reduced sleep time for smoother operation
            
            # Cleanup
            self.stop_incident_recording()
            self.stop_continuous_recording()
            if self.cap is not None:
                self.cap.release()
        
        except Exception as e:
            self.logger.error(f"Unexpected error in detection: {e}")
            self.monitoring = False
        finally:
            # Ensure cleanup happens
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()
            self.stop_incident_recording()
            self.stop_continuous_recording()

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
        self.stop_incident_recording()
        self.stop_continuous_recording()
        # Close Qt window if it exists
        if hasattr(self, 'window'):
            self.window.close()

if __name__ == "__main__":
    monitor = PeopleMonitor(
        slack_token='xoxb-your-slack-token',
        slack_channel='#team-alerts',
        email_sender='wyantethan@gmail.com',
        email_password='your_app_password',
        email_recipient='wyantethan@gmail.com',
        min_people=2,
        display_method='qt'
    )
    
    try:
        monitor.start_monitoring()
        print("Press Ctrl+C to quit")
        while monitor.monitoring:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        monitor.stop_monitoring()
