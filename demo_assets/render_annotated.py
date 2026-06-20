"""
Pre-render the annotated CCTV video with bounding boxes and HUD overlay.
Uses imageio-ffmpeg for browser-compatible H.264 output.
"""
import cv2
import numpy as np
import imageio.v3 as iio
import os

BASE = os.path.dirname(__file__)
INPUT  = os.path.join(BASE, "traffic_cam.mp4")
OUTPUT = os.path.join(BASE, "traffic_cam_annotated.mp4")

cap = cv2.VideoCapture(INPUT)
fps = int(cap.get(cv2.CAP_PROP_FPS)) or 20
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

frames_out = []
frame_count = 0
trigger_frame = -1

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_count += 1

    # Brightness thresholding
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 90, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    vehicle_count = 0
    display = frame.copy()

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 300 < area < 12000:
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / max(bh, 1)
            if 0.2 < aspect < 5.0:
                cv2.rectangle(display, (x, y), (x+bw, y+bh), (0, 255, 0), 2)
                cv2.putText(display, "VEH", (x, y-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
                vehicle_count += 1

    density = min(vehicle_count / 40.0, 1.0)

    if density >= 0.85 and trigger_frame < 0:
        trigger_frame = frame_count

    # HUD overlay
    cv2.putText(display, f"Vehicles: {vehicle_count}", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    color = (0, 255, 0) if density < 0.6 else ((0, 180, 255) if density < 0.85 else (0, 0, 255))
    cv2.putText(display, f"Density: {density*100:.0f}%", (10, 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    if density >= 0.85:
        cv2.putText(display, "GRIDLOCK DETECTED", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Convert BGR to RGB for imageio
    frames_out.append(cv2.cvtColor(display, cv2.COLOR_BGR2RGB))

    if frame_count % 100 == 0:
        print(f"  Frame {frame_count}/{total}  vehicles={vehicle_count}  density={density:.0%}")

cap.release()

print(f"\nTrigger fired at frame {trigger_frame} ({trigger_frame/fps:.1f}s)")
print(f"Writing H.264 MP4 with {len(frames_out)} frames...")

# Write H.264 using imageio-ffmpeg
iio.imwrite(OUTPUT, np.stack(frames_out), fps=fps, codec="libx264", plugin="pyav", out_pixel_format="yuv420p")

print(f"Browser-compatible video saved: {OUTPUT}")
print(f"File size: {os.path.getsize(OUTPUT) / 1024 / 1024:.1f} MB")
