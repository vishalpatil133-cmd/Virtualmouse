#!/usr/bin/env python3
"""
AI Wi-Fi Sensor Mouse - Server
-----------------------------
This script starts:
1. An HTTP Web Server (Port 8000) to serve the mobile controller web page.
2. A WebSocket Server (Port 8765) to receive real-time gyroscope data and taps.

Branding: Software Developed by Vishal P
Date: July 2026
"""

import os
import sys
import socket
import json
import asyncio
import threading
import http.server
import socketserver
import qrcode
import pyautogui
import winsound

# =====================================================================
# CONFIGURATION CONSTANTS
# =====================================================================
HTTP_PORT = 8000
WS_PORT = 8765

# Motion Mapping Constants
ROLL_DEAD_ZONE = 3.0    # Degrees of left/right tilt to ignore (neutral zone)
PITCH_DEAD_ZONE = 3.0   # Degrees of forward/backward tilt to ignore
SPEED_FACTOR = 0.9      # Sensitivity multiplier for cursor movement
VELOCITY_SMOOTH = 3.5   # LERP smoothing factor (higher = smoother, lower = faster)

# PyAutoGUI Setup
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

# Track smoothed velocity states across frames
prev_vx = 0.0
prev_vy = 0.0

# Active drag hold state tracker
is_drag_active = False

# =====================================================================
# AUDIO FEEDBACK HELPERS
# =====================================================================
def play_sound_left_click():
    winsound.Beep(2000, 25)

def play_sound_right_click():
    winsound.Beep(1400, 30)

def play_sound_double_click():
    winsound.Beep(2200, 20)
    winsound.Beep(2500, 20)

def play_sound_drag_on():
    winsound.Beep(1800, 40)
    winsound.Beep(1900, 40)

def play_sound_drag_off():
    winsound.Beep(1900, 40)
    winsound.Beep(1700, 40)

# =====================================================================
# SYSTEM UTILITIES
# =====================================================================
def get_local_ip():
    """Gets the active local LAN/Wi-Fi IP address of the PC."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a dummy address to resolve active network interface
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# =====================================================================
# HTTP WEB SERVER (Runs in background thread)
# =====================================================================
class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Default route to serve templates/index.html
        if self.path == '/' or self.path == '/index.html':
            self.path = '/templates/index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, format, *args):
        # Suppress verbose HTTP GET logs in the console to keep QR code clear
        pass

def run_http_server(ip, port):
    # Set server working directory to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Allow socket address reuse on restart
    socketserver.TCPServer.allow_reuse_address = True
    handler = CustomHTTPRequestHandler
    
    try:
        with socketserver.TCPServer((ip, port), handler) as httpd:
            print(f"[HTTP] Web Client Server hosted at: http://{ip}:{port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"[HTTP] Server error: {e}")

# =====================================================================
# WEBSOCKET CONTROLLER (Receives real-time phone sensor events)
# =====================================================================
import websockets

async def handle_websocket_message(websocket):
    global prev_vx, prev_vy, is_drag_active
    print(f"[WS] Phone connected from {websocket.remote_address}")
    
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get('type')
            
            # 1. Motion Event (Gyroscope Pitch/Roll coordinates)
            if msg_type == 'motion':
                roll = data.get('roll', 0.0)
                pitch = data.get('pitch', 0.0)
                
                # Apply joystick mapping logic with dead zones
                target_vx = 0.0
                target_vy = 0.0
                
                # Roll (left/right tilt) controls X velocity
                if abs(roll) > ROLL_DEAD_ZONE:
                    sign = 1.0 if roll > 0 else -1.0
                    excess = abs(roll) - ROLL_DEAD_ZONE
                    # Exponential mapping: subtle tilts are precise, large tilts are fast
                    target_vx = sign * (excess ** 1.35) * SPEED_FACTOR
                
                # Pitch (forward/backward tilt) controls Y velocity
                # Tilting forward (pointing down) decreases pitch, pointing up increases it.
                if abs(pitch) > PITCH_DEAD_ZONE:
                    sign = 1.0 if pitch > 0 else -1.0
                    excess = abs(pitch) - PITCH_DEAD_ZONE
                    target_vy = sign * (excess ** 1.35) * SPEED_FACTOR
                
                # LERP Smoothing: prevent cursor jumping/hand tremors
                prev_vx = prev_vx + (target_vx - prev_vx) / VELOCITY_SMOOTH
                prev_vy = prev_vy + (target_vy - prev_vy) / VELOCITY_SMOOTH
                
                # Execute cursor motion
                if abs(prev_vx) > 0.1 or abs(prev_vy) > 0.1:
                    pyautogui.moveRel(int(prev_vx), int(prev_vy))
            
            # 2. Trackpad Touch Movement
            elif msg_type == 'trackpad_motion':
                dx = data.get('dx', 0.0)
                dy = data.get('dy', 0.0)
                # Move cursor relatively based on finger swipe displacement
                pyautogui.moveRel(int(dx * 1.5), int(dy * 1.5))
            
            # 3. Button/Tap Actions
            elif msg_type == 'action':
                action = data.get('action')
                print(f"[ACTION] Phone trigger: {action}")
                
                if action == 'left_click':
                    pyautogui.click(button='left')
                    play_sound_left_click()
                    
                elif action == 'right_click':
                    pyautogui.click(button='right')
                    play_sound_right_click()
                    
                elif action == 'double_click':
                    pyautogui.doubleClick()
                    play_sound_double_click()
                    
                elif action == 'drag_down':
                    pyautogui.mouseDown(button='left')
                    is_drag_active = True
                    play_sound_drag_on()
                    
                elif action == 'drag_up':
                    pyautogui.mouseUp(button='left')
                    is_drag_active = False
                    play_sound_drag_off()
                    
                elif action == 'scroll_up':
                    pyautogui.scroll(120)  # Standard scroll step
                    
                elif action == 'scroll_down':
                    pyautogui.scroll(-120)

            # 3. Keyboard Input Events
            elif msg_type == 'keyboard':
                action = data.get('action')
                if action == 'write':
                    text = data.get('text', '')
                    pyautogui.write(text)
                    print(f"[KEYBOARD] Typed text: {text}")
                elif action == 'backspace':
                    count = data.get('count', 1)
                    for _ in range(count):
                        pyautogui.press('backspace')
                    print(f"[KEYBOARD] Backspaced {count} times")
                elif action == 'enter':
                    pyautogui.press('enter')
                    print("[KEYBOARD] Pressed Enter")

    except websockets.exceptions.ConnectionClosedOK:
        print("[WS] Phone disconnected cleanly.")
    except websockets.exceptions.ConnectionClosedError:
        print("[WS] Phone connection lost abruptly.")
    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        # Safe cleanup if phone disconnects while dragging
        if is_drag_active:
            pyautogui.mouseUp(button='left')
            is_drag_active = False
            print("[ACTION] Auto-released drag on connection loss.")

# =====================================================================
# MAIN RUNNER
# =====================================================================
def main():
    print("\n" + "="*70)
    print("AI WI-FI SENSOR MOUSE - SERVER ACTIVE")
    print("Software Developed by Vishal P")
    print("="*70)

    local_ip = get_local_ip()
    client_url = f"http://{local_ip}:{HTTP_PORT}"

    # 1. Start HTTP Server in a daemon background thread
    http_thread = threading.Thread(target=run_http_server, args=(local_ip, HTTP_PORT), daemon=True)
    http_thread.start()

    # Give HTTP server a brief moment to bind port
    time.sleep(0.5)

    # 2. Print Connection Details and Terminal QR Code
    print("\n" + "-"*70)
    print("CONNECT YOUR SMARTPHONE TO CONTROL THE MOUSE:")
    print(f"1. Make sure your phone is on the SAME Wi-Fi network: {local_ip}")
    print(f"2. Open this link on your phone: {client_url}")
    print("3. OR scan this QR Code using your phone camera:")
    print("-"*70 + "\n")

    # Generate and print console-ASCII QR Code
    try:
        qr = qrcode.QRCode(version=1, box_size=1, border=1)
        qr.add_data(client_url)
        qr.make(fit=True)
        # print_ascii with invert=True is optimal for typical dark developer terminals
        qr.print_ascii(invert=True)
    except Exception as e:
        print(f"[WARNING] Could not print QR code in terminal: {e}")
        print("Please manually type the URL in your phone browser.")

    print("\n" + "="*70)
    print("SERVER LISTENING FOR INCOMING PHONE MOTION SENSORS...")
    print("Move cursor off screen corners to abort script (Fail-safe).")
    print("Press Ctrl+C in this window to stop server.")
    print("="*70 + "\n")

    # 3. Start asyncio WebSocket server on the main thread
    async def start_ws():
        async with websockets.serve(handle_websocket_message, local_ip, WS_PORT):
            await asyncio.Future()  # run forever

    try:
        asyncio.run(start_ws())
    except KeyboardInterrupt:
        print("\n[INFO] Stopping server by KeyboardInterrupt...")
    except Exception as e:
        print(f"\n[ERROR] Server crash: {e}")
    finally:
        print("[INFO] Servers closed. Exiting clean.")

if __name__ == "__main__":
    import time
    main()
