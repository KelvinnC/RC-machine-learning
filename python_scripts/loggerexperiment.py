#!/usr/bin/env python3
import cv2
import csv
import os
import time

class DataLogger:
    def __init__(self,
                 csv_file: str = "driving_log.csv",
                 img_dir:  str = "images"):
        self.csv_file = csv_file
        self.img_dir  = img_dir
        os.makedirs(self.img_dir, exist_ok=True)
        # write header if new
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp",
                    "image_path",
                    "steering_pulse",
                    "throttle_pulse"
                ])

    def capture_frame(self, frame, steer: int, throttle: int):
        """Save a passed-in frame and append CSV row."""
        ts = time.time()
        img_name = f"{ts:.3f}.jpg"
        img_path = os.path.join(self.img_dir, img_name)

        cv2.imwrite(img_path, frame)

        with open(self.csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([ts, img_path, steer, throttle])
