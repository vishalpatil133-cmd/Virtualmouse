#!/usr/bin/env python3
"""
JARVIS Stark Virtual Steering Car Game - Server
----------------------------------------------
Tracks two hands representing a virtual steering wheel and streams steering angle
and pinch (Gas/Brake) coordinates to the Web Car Game (HTML5 Canvas).

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
import time
import winsound

# Server Ports
HTTP_PORT = 8002
WS_PORT = 8767

# Gesture state variables
is_grabbing = False

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
# HTTP SERVER (Serves the Web Car Game)
# =====================================================================
class StarkCarHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Redirect default page to templates/car_game.html
        if self.path == '/' or self.path == '/index.html' or self.path == '/car_game.html':
            self.path = '/templates/car_game.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, format, *args):
        pass

def run_http_server(ip, port):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    socketserver.TCPServer.allow_reuse_address = True
    handler = StarkCarHTTPRequestHandler
    try:
        with socketserver.TCPServer((ip, port), handler) as httpd:
            print(f"[HTTP] Car Game running at: http://localhost:{port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"[HTTP] Server error: {e}")

# =====================================================================
# WEBSOCKET STREAM (Broadcasts steering data to browser)
# =====================================================================
import websockets

connected_clients = set()

async def ws_handler(websocket):
    print(f"[WS] Car Game HUD connected from {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        print("[WS] Car Game HUD disconnected.")

async def broadcast_steering(data):
    if not connected_clients:
        return
    message = json.dumps(data)
    await asyncio.gather(*[client.send(message) for client in connected_clients], return_exceptions=True)

# =====================================================================
# WEBCAM HAND GESTURE STEERING TRACKER (Runs in background)
# =====================================================================
def start_steering_tracking_thread(loop):
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=0,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Webcam cannot be opened. Steering tracking offline.")
        return
        
    print("[INFO] Webcam active. Starting steering tracker...")
    
    # Winsound startup notification
    winsound.Beep(1200, 100)
    winsound.Beep(1600, 100)
    
    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                continue
                
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)
            
            # Default control states
            game_data = {
                "detected": False,
                "steering": 0.0,      # Steering angle in degrees (-45 to 45)
                "accelerate": False,  # Gas flag
                "brake": False,       # Brake flag
                "hands": []           # joint positions for skeleton lines
            }
            
            if results.multi_hand_landmarks:
                game_data["detected"] = True
                
                # Extract coordinates
                detected_hands = []
                for hand_landmarks in results.multi_hand_landmarks:
                    landmarks = hand_landmarks.landmark
                    wrist = landmarks[0]
                    idx = landmarks[8]
                    thumb = landmarks[4]
                    
                    # Pinch check
                    pinch_dist = math.hypot(idx.x - thumb.x, idx.y - thumb.y)
                    is_pinched = pinch_dist < 0.08
                    
                    # Extract 21 points for visual skeleton overlay
                    pts = [[lm.x, lm.y] for lm in landmarks]
                    
                    detected_hands.append({
                        "x": wrist.x,
                        "y": wrist.y,
                        "grab": is_pinched,
                        "landmarks": pts
                    })
                
                # Classify hands or calculate steering angle
                if len(detected_hands) == 1:
                    # 1 Hand Steering Mode: Horizontal displacement from screen center controls steer
                    hand = detected_hands[0]
                    # Map wrist X (0.1 to 0.9) to steering angle (-45 to 45)
                    steer_val = (hand["x"] - 0.5) * 90.0
                    steer_val = max(-45.0, min(45.0, steer_val))
                    
                    game_data["steering"] = steer_val
                    game_data["accelerate"] = hand["grab"]
                    game_data["brake"] = False
                    game_data["hands"] = [hand]
                    
                elif len(detected_hands) >= 2:
                    # 2 Hand Virtual Steering Mode
                    # Sort left-to-right based on X coordinate
                    detected_hands.sort(key=lambda h: h["x"])
                    left_hand = detected_hands[0]
                    right_hand = detected_hands[1]
                    
                    # Calculate angle of line connecting the two wrists
                    dx = right_hand["x"] - left_hand["x"]
                    dy = right_hand["y"] - left_hand["y"]
                    
                    # Compute angle in degrees. Level hands = 0 deg
                    steer_angle = math.degrees(math.atan2(dy, dx))
                    
                    # Clamp steering angle for gameplay limits
                    steer_angle = max(-50.0, min(50.0, steer_angle))
                    
                    # Right hand pinch = Gas, Left hand pinch = Brake
                    game_data["steering"] = steer_angle
                    game_data["accelerate"] = right_hand["grab"]
                    game_data["brake"] = left_hand["grab"]
                    game_data["hands"] = [left_hand, right_hand]
            
            # Send steering packet to the game
            asyncio.run_coroutine_threadsafe(broadcast_steering(game_data), loop)
            
            # Print console output line
            if game_data["detected"]:
                status = f"STEER: {game_data['steering']:+5.1f}° | GAS: {game_data['accelerate']} | BRAKE: {game_data['brake']}"
                sys.stdout.write(f"\r[STEERING HUD] {status}                                                   ")
            else:
                sys.stdout.write("\r[STEERING HUD] Bring hands up to hold virtual steering wheel...              ")
            sys.stdout.flush()
            
            time.sleep(0.02)
            
    except Exception as e:
        print(f"\n[ERROR] Steering thread crashed: {e}")
    finally:
        cap.release()
        print("\n[INFO] Webcam closed.")

# =====================================================================
# MAIN RUNNER
# =====================================================================
def main():
    local_ip = get_local_ip()
    game_url = f"http://{local_ip}:{HTTP_PORT}"
    
    # 1. Start HTTP Server
    http_thread = threading.Thread(target=run_http_server, args=("0.0.0.0", HTTP_PORT), daemon=True)
    http_thread.start()
    
    # 2. Start gesture loop
    loop = asyncio.new_event_loop()
    tracker_thread = threading.Thread(target=start_steering_tracking_thread, args=(loop,), daemon=True)
    tracker_thread.start()
    
    time.sleep(0.5)
    
    print("\n" + "="*75)
    print("JARVIS STARK VIRTUAL STEERING CAR GAME ONLINE")
    print("Software Developed by Vishal P")
    print("="*75)
    print(f"1. PC Game Link: Open in your browser: http://localhost:{HTTP_PORT}  (or {game_url})")
    print("2. How to Drive:")
    print("   - Hold hands up as if grasping a physical steering wheel.")
    print("   - Tilt hands Left/Right to steer.")
    print("   - Pinch Right Hand to Accelerate (Gas).")
    print("   - Pinch Left Hand to Brake.")
    print("Press Ctrl+C in this terminal window to exit.")
    print("="*75 + "\n")
    
    async def start_ws():
        async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
            await asyncio.Future()
            
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_ws())
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down car game server...")
    finally:
        print("[INFO] Clean exit.")

if __name__ == "__main__":
    main()
