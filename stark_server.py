#!/usr/bin/env python3
"""
JARVIS Stark 3D Hologram Simulator - Server
-------------------------------------------
Tracks hand gestures in 3D using MediaPipe and streams coordinates via WebSockets
to the Stark HUD 3D Webpage (Three.js).

Branding: Software Developed by Vishal P
Date: July 2026
"""

# =====================================================================
# PROTOBUF MONKEY PATCH (For MediaPipe compatibility with newer Protobuf)
# =====================================================================
import google.protobuf.message_factory
from google.protobuf import message_factory
if not hasattr(message_factory.MessageFactory, "GetPrototype"):
    def GetPrototype(self, descriptor):
        return self.GetMessageClass(descriptor)
    message_factory.MessageFactory.GetPrototype = GetPrototype

import os
import sys
import socket
import json
import asyncio
import threading
import http.server
import socketserver
import cv2
import mediapipe as mp
import math
import winsound
import time

# Server Ports
HTTP_PORT = 8001
WS_PORT = 8766

# Gesture state variables
is_grabbing = False
prev_x, prev_y = 0.5, 0.5

# =====================================================================
# SYSTEM UTILITIES
# =====================================================================
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# =====================================================================
# HTTP SERVER (Serves the Three.js HUD)
# =====================================================================
class StarkHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Redirect default page to Templates/stark_hud.html
        if self.path == '/' or self.path == '/index.html' or self.path == '/stark_hud.html':
            self.path = '/templates/stark_hud.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, format, *args):
        pass

def run_http_server(ip, port):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    socketserver.TCPServer.allow_reuse_address = True
    handler = StarkHTTPRequestHandler
    try:
        with socketserver.TCPServer((ip, port), handler) as httpd:
            print(f"[HTTP] HUD Server running at: http://{ip}:{port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"[HTTP] Server error: {e}")

# =====================================================================
# WEBSOCKET SENSOR STREAM (Broadcasts hand coordinates to browser)
# =====================================================================
import websockets

# Keep track of active websocket clients (browser sessions)
connected_clients = set()

async def ws_handler(websocket):
    print(f"[WS] Stark HUD Client connected from {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        # Keep connection open, client only listens
        async for message in websocket:
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        print("[WS] Stark HUD Client disconnected.")

async def broadcast_gesture(data):
    """Sends gesture updates to all connected browser sessions."""
    if not connected_clients:
        return
    message = json.dumps(data)
    # Gather tasks to send asynchronously
    await asyncio.gather(*[client.send(message) for client in connected_clients], return_exceptions=True)

# =====================================================================
# WEBCAM HAND GESTURE TRACKER (Runs in background)
# =====================================================================
def start_gesture_tracking_thread(loop):
    global is_grabbing
    
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,  # Track up to 2 hands for Stark dual-gestures
        model_complexity=0,  # CPU optimized
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Webcam cannot be opened. Gesture tracking offline.")
        return
        
    print("[INFO] Webcam active. Starting dual hand tracker...")
    
    # Winsound startup notification
    winsound.Beep(1500, 100)
    winsound.Beep(2000, 100)
    
    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                continue
                
            # Mirror frame horizontally
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)
            
            gesture_data = {"detected": False, "hands": []}
            
            if results.multi_hand_landmarks:
                gesture_data["detected"] = True
                any_hand_pinched = False
                
                for hand_landmarks in results.multi_hand_landmarks:
                    landmarks = hand_landmarks.landmark
                    
                    # 1. Base positions
                    wrist = landmarks[mp_hands.HandLandmark.WRIST]
                    idx = landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    thumb = landmarks[mp_hands.HandLandmark.THUMB_TIP]
                    pinky_mcp = landmarks[mp_hands.HandLandmark.PINKY_MCP]
                    
                    # 2. Pinch detection
                    pinch_dist = math.hypot(idx.x - thumb.x, idx.y - thumb.y)
                    is_pinched = pinch_dist < 0.08
                    if is_pinched:
                        any_hand_pinched = True
                    
                    # 3. Z-Scale
                    hand_scale = math.hypot(wrist.x - pinky_mcp.x, wrist.y - pinky_mcp.y)
                    
                    # 4. Pack all 21 joint coordinates as a light list
                    pts = [[lm.x, lm.y] for lm in landmarks]
                    
                    gesture_data["hands"].append({
                        "x": wrist.x,
                        "y": wrist.y,
                        "scale": hand_scale,
                        "grab": is_pinched,
                        "landmarks": pts
                    })
                
                # Audio feedback on grab trigger
                if any_hand_pinched != is_grabbing:
                    is_grabbing = any_hand_pinched
                    if is_grabbing:
                        winsound.Beep(1800, 30)
                    else:
                        winsound.Beep(1200, 30)
            
            # Send data to main asyncio loop to broadcast over WebSocket
            asyncio.run_coroutine_threadsafe(broadcast_gesture(gesture_data), loop)
            
            # Show a minimal console monitor line
            num_detected = len(gesture_data.get("hands", []))
            if num_detected > 0:
                sys.stdout.write(f"\r[HUD TRACKER] Active Hands: {num_detected} | Grab: {is_grabbing}                               ")
            else:
                sys.stdout.write("\r[HUD TRACKER] No hands in frame...                                            ")
            sys.stdout.flush()
            
            # Sleep briefly to regulate rate
            time.sleep(0.02)
            
    except Exception as e:
        print(f"\n[ERROR] Hand tracker thread crashed: {e}")
    finally:
        cap.release()
        print("\n[INFO] Webcam closed.")

# =====================================================================
# MAIN INITIATOR
# =====================================================================
def main():
    local_ip = get_local_ip()
    hud_url = f"http://{local_ip}:{HTTP_PORT}"
    
    # 1. Start HTTP Server to host stark_hud.html (bound to 0.0.0.0 to accept localhost)
    http_thread = threading.Thread(target=run_http_server, args=("0.0.0.0", HTTP_PORT), daemon=True)
    http_thread.start()
    
    # 2. Start Webcam tracker thread
    loop = asyncio.new_event_loop()
    tracker_thread = threading.Thread(target=start_gesture_tracking_thread, args=(loop,), daemon=True)
    tracker_thread.start()
    
    # Give servers a moment to bind
    time.sleep(0.5)
    
    print("\n" + "="*75)
    print("JARVIS STARK 3D HOLOGRAPHIC HUD RUNNING")
    print("Software Developed by Vishal P")
    print("="*75)
    print(f"1. PC HUD View: Open this link in your browser: http://localhost:{HTTP_PORT}  (or {hud_url})")
    print(f"2. Mobile Projector Mode: Open this link on your phone: {hud_url}")
    print("   place the CD Hologram Pyramid upside-down on the screen,")
    print("   and control the floating hologram using webcam gestures!")
    print("Press Ctrl+C in this terminal window to stop.")
    print("="*75 + "\n")
    
    # 3. Start WebSocket Broadcast Server on main thread (bound to 0.0.0.0 to accept localhost)
    async def start_ws():
        async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
            await asyncio.Future()
            
    try:
        # Run the asyncio loop for websockets
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_ws())
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down stark server...")
    finally:
        print("[INFO] Server stopped clean.")

if __name__ == "__main__":
    main()
