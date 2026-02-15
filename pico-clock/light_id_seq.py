#!/usr/bin/python3

import time
from time import sleep
import cv2
import numpy as np
import subprocess
from picamera2 import Picamera2, Preview
from math import pi, pow
import csv
import sys
import tempfile
import collections
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class LedInfo:
    led_id: int
    coords: list[int]
    size: int

def pico_exec(command: str):
    subprocess.run([
        "mpremote",
        "connect", "id:560ca184b37d9ae2",
        "mount", "./device-fs/",
        "exec", f"from led_identification_setup import ac ; {command}"])
    sleep(0.5)

pico_exec("ac.set_all(True)")

picam2 = Picamera2()
picam2.set_controls({
    "ExposureTime": 100000,
    "AeEnable": False,
    "AnalogueGain": 1.0}
)
max_size = picam2.sensor_modes[0]['size']  # Usually already sorted largest first
print(f'max_size={max_size}')
picam2.configure(picam2.create_still_configuration(
    main={"size": max_size}
))

# preview_config = picam2.create_preview_configuration(main={"size": (800, 600)})
# picam2.configure(preview_config)
picam2.start_preview(Preview.QTGL)

picam2.start()

t_end = time.time() + 5

while time.time() < t_end:
    # Capture frame-by-frame
    all_frame = picam2.capture_array()

    # Get the frame dimensions
    frame_height, frame_width, _ = all_frame.shape

    copy_for_decoration = all_frame.copy()

    # Draw a crosshair in the middle of the frame
    center_x, center_y = frame_width // 2, frame_height // 2
    color = (0, 255, 0)  # Green colour
    thickness = 2

    cv2.line(copy_for_decoration, (center_x - 20, center_y), (center_x + 20, center_y), color, thickness)
    cv2.line(copy_for_decoration, (center_x, center_y - 20), (center_x, center_y + 20), color, thickness)

    # Display the resulting frame
    cv2.imshow("Preview", copy_for_decoration)

cv2.destroyWindow("Preview")

height, width = all_frame.shape[:2]
print(width, height)

cv2.imwrite('all.png', copy_for_decoration)

smallest_res = min(height, width)
rough_dot_diameter = smallest_res / 95
rough_dot_area = int(round(pi * pow(rough_dot_diameter / 2, 2)))

print(f"rough_dot_area={rough_dot_area}")

# Setup SimpleBlobDetector parameters
params = cv2.SimpleBlobDetector_Params()
params.blobColor = 255
params.minThreshold = 100
params.maxThreshold = 250
params.filterByArea = True
params.minArea = rough_dot_area / 2
params.maxArea = rough_dot_area * 4
params.filterByCircularity = True
params.minCircularity = 0.6
params.filterByConvexity = True
params.minConvexity = 0.9
detector = cv2.SimpleBlobDetector_create(params)

def extract_blobs(frame, id: str, desc: str):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    keypoints = detector.detect(gray)
    output = cv2.drawKeypoints(frame, keypoints, None, (0, 0, 255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

    for kp in keypoints:
        x = int(kp.pt[0])
        y = int(kp.pt[1])
        radius = int((kp.size+2) / 2)
        cv2.circle(output, (x, y), radius, color=(0, 0, 255), thickness=3)

    cv2.imshow(f"Blobs: {desc}", output)
    print(f"Blobs found: {len(keypoints)}")
    cv2.imwrite(f'{id}.png', output)
    return keypoints

all_led_keypoints = extract_blobs(all_frame, "all", "All LEDs")
# for kp in sorted(all_led_keypoints, key=lambda kp: kp.size):
#     print(f'{kp.pt} : {round(kp.size)}')

led_ids = [0] * len(all_led_keypoints)

sleep(2)
for phase in range(10):
    pico_exec(f"ac.light_pixel_identification_step({phase})")
    phase_frame = picam2.capture_array()
    phase_kps = extract_blobs(phase_frame, f"phase-{phase}", f"Phase {phase}")
    phase_power = 1 << phase
    for index, led_kp in enumerate(all_led_keypoints):
        if any(cv2.KeyPoint.overlap(led_kp, phase_kp) > 0.6 for phase_kp in phase_kps):
            led_ids[index] += phase_power

    sleep(1)
picam2.close()

print(f"Duplicates: {[item for item, count in collections.Counter(led_ids).items() if count > 1]}")

big_dot_kp_index = max(range(len(all_led_keypoints)), key=lambda i: all_led_keypoints[i].size)
big_dot_kp = all_led_keypoints[big_dot_kp_index]

print(f'Big dot LED id: {led_ids[big_dot_kp_index]}')

led_infos = [LedInfo(led_ids[index], [round(c-big_dot_kp.pt[ci]) for ci, c in enumerate(led_kp.pt)] , round(led_kp.size)) for index, led_kp in enumerate(all_led_keypoints)]

led_infos.sort(key=lambda x: x.led_id)

# print(led_infos)

with tempfile.NamedTemporaryFile(
        mode="w",
        newline="",
        delete=False,   # Keep file after closing
        suffix=".csv"
) as tmp:
    writer = csv.DictWriter(tmp, fieldnames=asdict(led_infos[0]).keys())
    writer.writeheader()

    for led_info in led_infos:
        writer.writerow(asdict(led_info))

    print("CSV written to:", tmp.name)

# for index, led_kp in enumerate(all_led_keypoints):
#     print(f'{led_ids[index]}: {[int(c) for c in led_kp.pt]} : {round(kp.size)}')

