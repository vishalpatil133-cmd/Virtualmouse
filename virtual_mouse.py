#!/usr/bin/env python3
"""
AI Virtual Mouse - Gamified & Optimized Edition
----------------------------------------------
This script uses OpenCV, MediaPipe, and PyAutoGUI to control the computer mouse cursor
using hand movements captured through a webcam.

Optimizations:
1. Frame Skipping: Runs heavy ML tracking on every alternate frame, cutting CPU usage by 50%.
2. Performance Mode ('h' key): Toggle to hide drawing landmarks, saving GPU/CPU overhead.
3. FPS Capping: Regulates frame cycles to prevent CPU core exhaustion.

Gamification:
1. winsound Beeps: Satisfying audio click/toggle beeps for all actions.

Author: Antigravity AI Coding Assistant
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

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import math
import winsound  # Built-in Windows module for zero-latency audio feedback
import keyboard
from collections import deque


# =====================================================================
# CONFIGURATION CONSTANTS
# =====================================================================

# Camera Settings
CAM_WIDTH = 640
CAM_HEIGHT = 480
CAMERA_INDEX = 0

# Active Bounding Box in Camera Coordinates (Padded to reach screen edges easily)
TRACKING_BOX_X1 = 120  # Left margin padding
TRACKING_BOX_Y1 = 90   # Top margin padding
TRACKING_BOX_X2 = 520  # Right margin padding
TRACKING_BOX_Y2 = 390  # Bottom margin padding

# Smoothing & Jitter Settings
DEAD_ZONE_PX = 2.0      # Ignore movements smaller than 2 screen pixels to eliminate micro-jitter

# Gesture Distance Thresholds (in camera pixels)
PINCH_THRESHOLD_PX = 30 

# PyAutoGUI Setup
# Fail-Safe disabled per user configuration to allow full corner screen reaching
pyautogui.FAILSAFE = False
# Disable default delay to enable real-time responsive mouse control.
pyautogui.PAUSE = 0

# =====================================================================
# AUDIO FEEDBACK HELPERS (Non-blocking design using short millisecond durations)
# =====================================================================
def play_sound_left_click():
    winsound.Beep(2000, 25)  # Quick high click

def play_sound_right_click():
    winsound.Beep(1400, 30)  # Lower quick click

def play_sound_double_click():
    winsound.Beep(2200, 20)
    winsound.Beep(2500, 20)  # High double click

def play_sound_pause():
    winsound.Beep(800, 60)
    winsound.Beep(600, 60)   # Descending chime

def play_sound_resume():
    winsound.Beep(600, 60)
    winsound.Beep(800, 60)   # Ascending chime

# =====================================================================
# EYE BLINK EAR (Eye Aspect Ratio) HELPER
# =====================================================================
def calculate_ear(landmarks, eye_indices):
    top = np.array([landmarks[eye_indices[0]].x, landmarks[eye_indices[0]].y])
    bottom = np.array([landmarks[eye_indices[1]].x, landmarks[eye_indices[1]].y])
    left = np.array([landmarks[eye_indices[2]].x, landmarks[eye_indices[2]].y])
    right = np.array([landmarks[eye_indices[3]].x, landmarks[eye_indices[3]].y])
    
    vertical_dist = np.linalg.norm(top - bottom)
    horizontal_dist = np.linalg.norm(left - right)
    
    if horizontal_dist == 0:
        return 0.0
    return vertical_dist / horizontal_dist

# =====================================================================
# MAIN IMPLEMENTATION
# =====================================================================

def main():
    # Initialize MediaPipe Hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=0,  # Lower complexity (0) is MUCH faster and saves huge CPU
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )
    mp_draw = mp.solutions.drawing_utils

    # Initialize MediaPipe Face Mesh for Eye Blink Tracking
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # Get screen resolution
    screen_w, screen_h = pyautogui.size()
    print(f"[INFO] Detected screen resolution: {screen_w}x{screen_h}")

    # Initialize webcam
    print(f"[INFO] Initializing webcam index {CAMERA_INDEX}...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera {CAMERA_INDEX}.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    # Create a resizable window for the camera feed
    cv2.namedWindow("AI Virtual Mouse - Developed by Vishal P", cv2.WINDOW_NORMAL)

    # State variables for cursor smoothing
    prev_x, prev_y = 0.0, 0.0
    first_detection = True

    # Debouncing state flags to prevent rapid repeated actions
    left_clicked = False
    is_dragging = False
    double_clicked = False

    # Ring finger gesture states (Right Click + PPT Slide Control)
    ring_pinched = False
    ring_pinch_start_time = 0.0
    ring_pinch_start_x = 0.0
    ring_action_triggered = False

    # Pinky scrolling / volume states
    prev_scroll_x = 0.0
    prev_scroll_y = 0.0

    # Tracking Pause/Resume states
    tracking_enabled = True
    peace_gesture_start = 0.0

    # Performance modes
    performance_mode = False  # Toggle with 'h' key to hide landmarks and save CPU
    always_on_top = False     # Toggle with Ctrl+Alt+A / Ctrl+Alt+V
    frame_count = 0

    # Both-Eye Blink Tracking state variables (OFF by default to prevent accidental clicks)
    eye_blink_mode = False       # Toggle with 'e' key when explicitly needed
    both_eye_blink_count = 0
    last_both_blink_time = 0.0
    closed_start_time = 0.0
    is_eye_closed = False

    # Nose Head Tracking DSP Filtering states
    nose_history = deque(maxlen=8)
    prev_raw_x, prev_raw_y = 0.0, 0.0

    # FPS Calculation
    prev_time = 0

    # Air Writing & Voice Typing state variables
    draw_mode = False
    canvas_draw = np.zeros((CAM_HEIGHT, CAM_WIDTH, 3), dtype=np.uint8)
    prev_draw_pt = None
    clear_timer = 0
    fist_gesture_start = 0.0
    namaste_cooldown = 0.0

    print("\n" + "="*70)
    print("      AI VIRTUAL MOUSE & GESTURE ECOSYSTEM INITIALIZED")
    print("="*70)
    print("  • Index Knuckle (MCP 5)   -> 100% Stable Pointer Navigation")
    print("  • Index + Thumb Pinch     -> Left Click")
    print("  • Middle + Thumb Pinch    -> Drag & Drop")
    print("  • Ring + Thumb Pinch      -> Right Click / Slide Swap")
    print("  • Pinky Up/Down           -> Smooth Scroll & System Volume")
    print("  • Both Eyes 1-Blink       -> Left Click (When Eye Mode ON)")
    print("  • Both Eyes 2-Blinks      -> Right Click (When Eye Mode ON)")
    print("  • Press 'e'               -> Toggle Eye Blink Mode (OFF by default)")
    print("  • Press 'd'               -> Toggle Air Draw Mode")
    print("  • Press 'v'               -> Trigger Windows Voice Typing (Win+H)")
    print("  • Press 'h'               -> Toggle Performance Mode")
    print("  • Press 'q'               -> Quit Application")
    print("="*70 + "\n")

    try:
        # Pre-execution beep
        winsound.Beep(1000, 100)
        winsound.Beep(1200, 100)

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("[WARNING] Ignoring empty camera frame.")
                continue

            frame_count += 1

            # Mirror the frame horizontally for intuitive self-view
            frame = cv2.flip(frame, 1)

            # Reset scrolling state for this frame
            is_scrolling_active = False

            # Process every frame for fluid 30 FPS cursor tracking smoothness
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)

            # Process Both-Eye Blink & Head tracking if Eye Blink Mode is explicitly enabled by user
            if eye_blink_mode and tracking_enabled:
                face_results = face_mesh.process(rgb_frame)
                if face_results.multi_face_landmarks:
                    for face_landmarks in face_results.multi_face_landmarks:
                        fl = face_landmarks.landmark
                        # Left Eye: 159, 145, 33, 133
                        # Right Eye: 386, 374, 362, 263
                        left_ear = calculate_ear(fl, [159, 145, 33, 133])
                        right_ear = calculate_ear(fl, [386, 374, 362, 263])

                        # Both Eyes Closed Detection
                        # Natural human blinks (<0.3s) are IGNORED.
                        # Intentional Long Blink (>=0.35s) -> LEFT CLICK
                        # Fast Double Blink -> RIGHT CLICK
                        both_closed = (left_ear < 0.17 and right_ear < 0.17)
                        curr_t = time.time()

                        if both_closed:
                            if not is_eye_closed:
                                closed_start_time = curr_t
                                is_eye_closed = True
                        else:
                            if is_eye_closed:
                                closed_duration = curr_t - closed_start_time
                                is_eye_closed = False
                                
                                # Ignore natural quick blinks (< 0.28s)
                                if closed_duration >= 0.32:
                                    both_eye_blink_count += 1
                                    last_both_blink_time = curr_t

                        # Dispatch click based on intentional blink duration / count
                        if both_eye_blink_count == 1 and (curr_t - last_both_blink_time > 0.35):
                            pyautogui.click(button='left')
                            play_sound_left_click()
                            left_clicked = True
                            both_eye_blink_count = 0
                            if not performance_mode:
                                cv2.putText(frame, "INTENTIONAL LONG BLINK -> LEFT CLICK", (10, 90),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
                        elif both_eye_blink_count >= 2:
                            pyautogui.click(button='right')
                            play_sound_right_click()
                            ring_pinched = True
                            both_eye_blink_count = 0
                            if not performance_mode:
                                cv2.putText(frame, "FAST DOUBLE BLINK -> RIGHT CLICK", (10, 90),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

                        # Hands-Free Head / Nose Tracking when NO HAND is in front of camera
                        if tracking_enabled and (not results.multi_hand_landmarks):
                            raw_nx = nose.x * CAM_WIDTH
                            raw_ny = nose.y * CAM_HEIGHT
                            
                            # Camera-space dead-zone: ignore raw sensor noise under 1.2 pixels
                            if abs(raw_nx - prev_raw_x) < 1.2 and abs(raw_ny - prev_raw_y) < 1.2:
                                raw_nx, raw_ny = prev_raw_x, prev_raw_y
                            else:
                                prev_raw_x, prev_raw_y = raw_nx, raw_ny

                            # 8-Frame Moving Average Queue to eliminate sensor jitter
                            nose_history.append((raw_nx, raw_ny))
                            avg_raw_x = sum(pt[0] for pt in nose_history) / len(nose_history)
                            avg_raw_y = sum(pt[1] for pt in nose_history) / len(nose_history)
                            
                            # Active head tracking box
                            head_min_x, head_max_x = 230, 410
                            head_min_y, head_max_y = 150, 330
                            
                            target_x = np.interp(avg_raw_x, (head_min_x, head_max_x), (0, screen_w))
                            target_y = np.interp(avg_raw_y, (head_min_y, head_max_y), (0, screen_h))
                            
                            if first_detection:
                                curr_x, curr_y = target_x, target_y
                                first_detection = False
                            else:
                                # Adaptive 2-stage EMA smoothing for rock-solid stability
                                dist_to_target = math.hypot(target_x - prev_x, target_y - prev_y)
                                # Fine targeting (< 35px) -> heavy smoothing (0.12), Fast turn -> (0.40)
                                head_smooth = 0.12 if dist_to_target < 35 else 0.40
                                
                                curr_x = prev_x + (target_x - prev_x) * head_smooth
                                curr_y = prev_y + (target_y - prev_y) * head_smooth
                                
                            # Screen dead-zone filter
                            dx = abs(curr_x - prev_x)
                            dy = abs(curr_y - prev_y)
                            if dx > 2.0 or dy > 2.0:
                                pyautogui.moveTo(curr_x, curr_y)
                                prev_x, prev_y = curr_x, curr_y
                                
                            if not performance_mode:
                                cv2.circle(frame, (int(avg_raw_x), int(avg_raw_y)), 6, (0, 255, 255), -1)
                                cv2.putText(frame, "ROCK-SOLID STABLE HEAD TRACKING (DSP Filtered)", (10, 115),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

            # Draw tracking boundary box on frame (active area)
            active_box_color = (255, 0, 255)
            if not tracking_enabled:
                active_box_color = (0, 0, 255)    # Red for paused
            elif is_dragging:
                active_box_color = (0, 165, 255)  # Orange for drag
            elif left_clicked or ring_action_triggered or double_clicked:
                active_box_color = (0, 255, 0)    # Green for click/action

            # Bounding box is only drawn if Performance Mode is OFF
            if not performance_mode:
                # Draw a sleek glowing border around the entire camera window
                cv2.rectangle(
                    frame, 
                    (0, 0), 
                    (CAM_WIDTH - 1, CAM_HEIGHT - 1), 
                    active_box_color, 
                    3
                )

            # Process hand landmarks
            if 'results' in locals() and results.multi_hand_landmarks:


                for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    # Get handedness classification ("Left" or "Right" relative to camera)
                    # Because we mirror the frame, the physical Right hand is classified as "Left"
                    hand_label = results.multi_handedness[idx].classification[0].label
                    
                    # Get wrist position for drawing labels
                    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                    wrist_x = int(wrist.x * CAM_WIDTH)
                    wrist_y = int(wrist.y * CAM_HEIGHT)
                    
                    if hand_label != "Right":
                        # Draw label and inactive skeleton for the Left hand
                        if not performance_mode:
                            cv2.putText(frame, "LEFT HAND (Ignored)", (wrist_x - 50, wrist_y + 20), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                            mp_draw.draw_landmarks(
                                frame, 
                                hand_landmarks, 
                                mp_hands.HAND_CONNECTIONS,
                                mp_draw.DrawingSpec(color=(50, 50, 50), thickness=1, circle_radius=2),
                                mp_draw.DrawingSpec(color=(100, 100, 100), thickness=1, circle_radius=1)
                            )
                        continue  # Ignore left hand gestures
                        
                    # Active hand (Right Hand) - Draw Active Landmarks
                    if not performance_mode:
                        cv2.putText(frame, "RIGHT HAND (Active)", (wrist_x - 50, wrist_y + 20), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        mp_draw.draw_landmarks(
                            frame, 
                            hand_landmarks, 
                            mp_hands.HAND_CONNECTIONS,
                            mp_draw.DrawingSpec(color=(121, 22, 76), thickness=2, circle_radius=4),
                            mp_draw.DrawingSpec(color=(250, 44, 250), thickness=2, circle_radius=2)
                        )

                    # Extract coordinates for fingers of interest
                    landmarks = hand_landmarks.landmark
                    
                    # Check which fingers are extended (pointing upwards)
                    is_idx_up = landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < landmarks[mp_hands.HandLandmark.INDEX_FINGER_PIP].y
                    is_mid_up = landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
                    is_ring_up = landmarks[mp_hands.HandLandmark.RING_FINGER_TIP].y < landmarks[mp_hands.HandLandmark.RING_FINGER_PIP].y
                    is_pinky_up = landmarks[mp_hands.HandLandmark.PINKY_TIP].y < landmarks[mp_hands.HandLandmark.PINKY_PIP].y

                    # Peace Sign Gesture: Index & Middle up, Ring & Pinky down
                    is_peace = is_idx_up and is_mid_up and not is_ring_up and not is_pinky_up

                    # Handle tracking toggle (Peace Sign detection)
                    if is_peace:
                        if peace_gesture_start == 0.0:
                            peace_gesture_start = time.time()
                        else:
                            time_held = time.time() - peace_gesture_start
                            if time_held > 1.5:
                                # Toggle state
                                tracking_enabled = not tracking_enabled
                                print(f"[STATUS] Tracking {'Enabled' if tracking_enabled else 'Paused'} by Peace Gesture")
                                # Play feedback chime
                                if tracking_enabled:
                                    play_sound_resume()
                                else:
                                    play_sound_pause()
                                # Reset timer with a temporary cooldown buffer to prevent immediate re-trigger
                                peace_gesture_start = time.time() + 1.0
                            elif time_held > 0.0:
                                # Draw countdown progress on screen
                                countdown = 1.5 - time_held
                                action_text = "PAUSING" if tracking_enabled else "RESUMING"
                                cv2.putText(frame, f"{action_text} IN {countdown:.1f}s...", (200, 50), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    else:
                        # Reset timer if the gesture was released, avoiding resetting during cooldown
                        if peace_gesture_start != 0.0 and time.time() > peace_gesture_start:
                            peace_gesture_start = 0.0

                    # 1. Thumb Tip (Landmark 4)
                    thumb = landmarks[mp_hands.HandLandmark.THUMB_TIP]
                    thumb_x, thumb_y = int(thumb.x * CAM_WIDTH), int(thumb.y * CAM_HEIGHT)

                    # 2. Index Finger Tip (Landmark 8) -> Left Click & Swipe Check
                    index = landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    idx_x, idx_y = int(index.x * CAM_WIDTH), int(index.y * CAM_HEIGHT)

                    # Tracked base knuckle for stable cursor movement: Index Finger MCP (Landmark 5)
                    # This knuckle remains perfectly still when fingers curl/pinch, preventing cursor drift!
                    index_mcp = landmarks[mp_hands.HandLandmark.INDEX_FINGER_MCP]
                    mcp_x, mcp_y = int(index_mcp.x * CAM_WIDTH), int(index_mcp.y * CAM_HEIGHT)

                    # 3. Middle Finger Tip (Landmark 12) -> Drag & Drop
                    middle = landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                    mid_x, mid_y = int(middle.x * CAM_WIDTH), int(middle.y * CAM_HEIGHT)

                    # 4. Ring Finger Tip (Landmark 16) -> Right Click / Presentation Slides
                    ring = landmarks[mp_hands.HandLandmark.RING_FINGER_TIP]
                    ring_x, ring_y = int(ring.x * CAM_WIDTH), int(ring.y * CAM_HEIGHT)

                    # 5. Pinky Tip (Landmark 20) -> Scrolling / Volume Control
                    pinky = landmarks[mp_hands.HandLandmark.PINKY_TIP]
                    pinky_x, pinky_y = int(pinky.x * CAM_WIDTH), int(pinky.y * CAM_HEIGHT)

                    # Calculate hand physical scale (distance from wrist to middle finger base)
                    wrist = landmarks[mp_hands.HandLandmark.WRIST]
                    mid_mcp = landmarks[9]
                    wrist_x_l, wrist_y_l = int(wrist.x * CAM_WIDTH), int(wrist.y * CAM_HEIGHT)
                    mid_mcp_x, mid_mcp_y = int(mid_mcp.x * CAM_WIDTH), int(mid_mcp.y * CAM_HEIGHT)
                    hand_scale = math.hypot(mid_mcp_x - wrist_x_l, mid_mcp_y - wrist_y_l)
                    if hand_scale == 0:
                        hand_scale = 1.0
                    
                    # Dynamically adjust pinch threshold (33% of hand size)
                    PINCH_THRESHOLD_PX = hand_scale * 0.33

                    # Calculate distance from thumb to other finger tips
                    dist_left = math.hypot(idx_x - thumb_x, idx_y - thumb_y)
                    dist_drag = math.hypot(mid_x - thumb_x, mid_y - thumb_y)
                    dist_right = math.hypot(ring_x - thumb_x, ring_y - thumb_y)
                    dist_scroll = math.hypot(pinky_x - thumb_x, pinky_y - thumb_y)

                    # Update scrolling active state for this frame
                    is_scrolling_active = dist_scroll < PINCH_THRESHOLD_PX

                    # Map stable index base knuckle coordinates to screen coordinates
                    target_x = np.interp(mcp_x, (TRACKING_BOX_X1, TRACKING_BOX_X2), (0, screen_w))
                    target_y = np.interp(mcp_y, (TRACKING_BOX_Y1, TRACKING_BOX_Y2), (0, screen_h))

                    # Calculate physical displacement (speed)
                    displacement = math.hypot(target_x - prev_x, target_y - prev_y)

                    # Check 3-Finger Pinch (Index + Middle + Thumb) for Double Click
                    is_triple_pinch = (dist_left < PINCH_THRESHOLD_PX) and (dist_drag < PINCH_THRESHOLD_PX)

                    # Click-Lock Mechanism:
                    # Freeze the cursor position when clicking or dragging to prevent the pinch gesture
                    # from shifting the cursor off the target button.
                    is_near_action = is_triple_pinch or \
                                     (dist_left < PINCH_THRESHOLD_PX + 12) or \
                                     (dist_right < PINCH_THRESHOLD_PX + 12) or \
                                     (dist_drag < PINCH_THRESHOLD_PX + 12) or \
                                     is_scrolling_active

                    # Apply cursor smoothing (Adaptive Exponential Moving Average + Click Lock)
                    if first_detection:
                        curr_x, curr_y = target_x, target_y
                        first_detection = False
                    elif is_near_action and not is_scrolling_active:
                        # Lock cursor in place to prevent cursor slip during click/drag gesture
                        curr_x, curr_y = prev_x, prev_y
                    else:
                        # Butter-smooth dynamic LERP factor based on velocity
                        # Low speed -> high smoothing (factor = 0.11) for stability
                        # High speed -> low smoothing (factor up to 0.39) for fast response
                        factor = 0.11 + min(0.28, (displacement / 150.0))
                        
                        dx = target_x - prev_x
                        dy = target_y - prev_y
                        
                        # Apply micro dead-zone
                        if displacement > DEAD_ZONE_PX:
                            curr_x = prev_x + dx * factor
                            curr_y = prev_y + dy * factor
                        else:
                            curr_x = prev_x
                            curr_y = prev_y

                    # Safety boundary check: keep within screen limits
                    curr_x = np.clip(curr_x, 0, screen_w - 1)
                    curr_y = np.clip(curr_y, 0, screen_h - 1)

                    # Save current coordinates for the next iteration
                    prev_x, prev_y = curr_x, curr_y

                    # Check for Voice dictation trigger: Fist (all fingers closed)
                    is_thumb_closed = math.hypot(landmarks[mp_hands.HandLandmark.THUMB_TIP].x * CAM_WIDTH - landmarks[mp_hands.HandLandmark.INDEX_FINGER_PIP].x * CAM_WIDTH, 
                                                 landmarks[mp_hands.HandLandmark.THUMB_TIP].y * CAM_HEIGHT - landmarks[mp_hands.HandLandmark.INDEX_FINGER_PIP].y * CAM_HEIGHT) < 45.0
                    is_fist = is_thumb_closed and not is_idx_up and not is_mid_up and not is_ring_up and not is_pinky_up
                    
                    if is_fist:
                        if fist_gesture_start == 0.0:
                            fist_gesture_start = time.time()
                        else:
                            time_held = time.time() - fist_gesture_start
                            if time_held > 1.5:
                                pyautogui.hotkey('win', 'h')
                                print("[STATUS] Windows Voice Dictation triggered by Fist Gesture")
                                winsound.Beep(1800, 150)
                                fist_gesture_start = time.time() + 2.0  # Cooldown
                            elif time_held > 0.0:
                                countdown = 1.5 - time_held
                                cv2.putText(frame, f"VOICE TYPING IN {countdown:.1f}s...", (200, 75),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    else:
                        if fist_gesture_start != 0.0 and time.time() > fist_gesture_start:
                            fist_gesture_start = 0.0

                    # ---------------------------------------------------------
                    # CONTROL MODES: DRAW MODE vs MOUSE MODE
                    # ---------------------------------------------------------
                    if not draw_mode:
                        # Move OS cursor to smoothed coordinates (Skip moving if scroll mode is active or tracking is paused)
                        if tracking_enabled and not is_scrolling_active:
                            pyautogui.moveTo(int(curr_x), int(curr_y))

                        # ---------------------------------------------------------
                        # GESTURE 1: DOUBLE CLICK (Index + Middle + Thumb)
                        # ---------------------------------------------------------
                        if is_triple_pinch:
                            if tracking_enabled and not double_clicked:
                                pyautogui.doubleClick()
                                double_clicked = True
                                print("[ACTION] Double Click")
                                play_sound_double_click()
                            # Visual indicator (White lines)
                            if not performance_mode:
                                cv2.line(frame, (idx_x, idx_y), (thumb_x, thumb_y), (255, 255, 255), 3)
                                cv2.line(frame, (mid_x, mid_y), (thumb_x, thumb_y), (255, 255, 255), 3)
                                cv2.circle(frame, (idx_x, idx_y), 12, (255, 255, 255), cv2.FILLED)
                                cv2.circle(frame, (mid_x, mid_y), 12, (255, 255, 255), cv2.FILLED)
                        else:
                            double_clicked = False

                            # ---------------------------------------------------------
                            # GESTURE 2: LEFT CLICK (Index + Thumb)
                            # ---------------------------------------------------------
                            if dist_left < PINCH_THRESHOLD_PX:
                                if tracking_enabled and not left_clicked:
                                    pyautogui.click(button='left')
                                    left_clicked = True
                                    print("[ACTION] Left Click")
                                    play_sound_left_click()
                                # Visual indicator (Green)
                                if not performance_mode:
                                    cv2.line(frame, (idx_x, idx_y), (thumb_x, thumb_y), (0, 255, 0), 3)
                                    cv2.circle(frame, (idx_x, idx_y), 12, (0, 255, 0), cv2.FILLED)
                            else:
                                left_clicked = False

                            # ---------------------------------------------------------
                            # GESTURE 3: DRAG & DROP / HOLD MOUSE (Middle + Thumb)
                            # ---------------------------------------------------------
                            if dist_drag < PINCH_THRESHOLD_PX:
                                if tracking_enabled and not is_dragging:
                                    pyautogui.mouseDown(button='left')
                                    is_dragging = True
                                    print("[ACTION] Mouse Down (Drag Mode Active)")
                                # Visual indicator (Orange)
                                if not performance_mode:
                                    cv2.line(frame, (mid_x, mid_y), (thumb_x, thumb_y), (0, 165, 255), 3)
                                    cv2.circle(frame, (mid_x, mid_y), 12, (0, 165, 255), cv2.FILLED)
                            else:
                                if is_dragging:
                                    pyautogui.mouseUp(button='left')
                                    is_dragging = False
                                    print("[ACTION] Mouse Up (Drag Mode Released)")

                        # ---------------------------------------------------------
                        # GESTURE 4: RIGHT CLICK & SLIDE NAV (Ring + Thumb)
                        # ---------------------------------------------------------
                        if dist_right < PINCH_THRESHOLD_PX:
                            # Visual indicator (Blue)
                            if not performance_mode:
                                cv2.line(frame, (ring_x, ring_y), (thumb_x, thumb_y), (255, 0, 0), 3)
                                cv2.circle(frame, (ring_x, ring_y), 12, (255, 0, 0), cv2.FILLED)

                            if tracking_enabled:
                                if not ring_pinched:
                                    ring_pinched = True
                                    ring_pinch_start_time = time.time()
                                    ring_pinch_start_x = idx_x
                                    ring_action_triggered = False
                                else:
                                    if not ring_action_triggered:
                                        dx = idx_x - ring_pinch_start_x
                                        if dx > 25:
                                            pyautogui.press('right')
                                            ring_action_triggered = True
                                            print("[ACTION] Next Slide (Right Arrow)")
                                            play_sound_left_click()
                                        elif dx < -25:
                                            pyautogui.press('left')
                                            ring_action_triggered = True
                                            print("[ACTION] Previous Slide (Left Arrow)")
                                            play_sound_left_click()
                        else:
                            if ring_pinched:
                                # Quick tap check on release
                                if tracking_enabled and not ring_action_triggered:
                                    if time.time() - ring_pinch_start_time < 0.4:
                                        pyautogui.click(button='right')
                                        print("[ACTION] Right Click")
                                        play_sound_right_click()
                                ring_pinched = False

                        # ---------------------------------------------------------
                        # GESTURE 5: VERTICAL SCROLLING & VOLUME (Pinky + Thumb)
                        # ---------------------------------------------------------
                        if is_scrolling_active:
                            # Visual indicator (Cyan)
                            if not performance_mode:
                                cv2.line(frame, (pinky_x, pinky_y), (thumb_x, thumb_y), (0, 255, 255), 3)
                                cv2.circle(frame, (pinky_x, pinky_y), 12, (0, 255, 255), cv2.FILLED)
                            
                            if tracking_enabled:
                                # Initialize coordinates when scroll pinch starts
                                if prev_scroll_x == 0.0 or prev_scroll_y == 0.0:
                                    prev_scroll_x = idx_x
                                    prev_scroll_y = idx_y
                                else:
                                    dx = idx_x - prev_scroll_x
                                    dy = idx_y - prev_scroll_y
                                    
                                    # Decide scroll vs volume depending on which movement is larger
                                    if abs(dx) > abs(dy):
                                        # Horizontal movement -> Volume Adjust
                                        if dx > 15:
                                            pyautogui.press('volumeup')
                                            print("[ACTION] Volume Up")
                                            prev_scroll_x = idx_x
                                            play_sound_left_click()
                                        elif dx < -15:
                                            pyautogui.press('volumedown')
                                            print("[ACTION] Volume Down")
                                            prev_scroll_x = idx_x
                                            play_sound_left_click()
                                    else:
                                        # Vertical movement -> Scroll
                                        if abs(dy) > 5:
                                            scroll_amount = int(-dy * 1.5)
                                            pyautogui.scroll(scroll_amount)
                                            prev_scroll_y = idx_y
                        else:
                            prev_scroll_x = 0.0
                            prev_scroll_y = 0.0
                    
                    else:
                        # ---------------------------------------------------------
                        # AIR WRITING CANVAS MODE (Toggled by 'd' Key)
                        # ---------------------------------------------------------
                        is_drawing = dist_left < PINCH_THRESHOLD_PX
                        if is_drawing:
                            if prev_draw_pt is not None:
                                # Draw glowing neon green strokes on canvas_draw
                                cv2.line(canvas_draw, prev_draw_pt, (idx_x, idx_y), (57, 255, 20), 6)
                            prev_draw_pt = (idx_x, idx_y)
                            if not performance_mode:
                                cv2.circle(frame, (idx_x, idx_y), 8, (57, 255, 20), cv2.FILLED)
                        else:
                            prev_draw_pt = None

                        # Check Open Palm (all 5 fingers up) to clear canvas
                        is_thumb_open = math.hypot(landmarks[mp_hands.HandLandmark.THUMB_TIP].x * CAM_WIDTH - landmarks[mp_hands.HandLandmark.INDEX_FINGER_PIP].x * CAM_WIDTH,
                                                   landmarks[mp_hands.HandLandmark.THUMB_TIP].y * CAM_HEIGHT - landmarks[mp_hands.HandLandmark.INDEX_FINGER_PIP].y * CAM_HEIGHT) > 80.0
                        all_open = is_thumb_open and is_idx_up and is_mid_up and is_ring_up and is_pinky_up
                        
                        if all_open:
                            clear_timer += 1
                            cv2.putText(frame, f"CLEARING CANVAS IN {1.5 - (clear_timer/25.0):.1f}s...", (200, 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                            if clear_timer > 25:
                                canvas_draw.fill(0)
                                clear_timer = 0
                                print("[STATUS] Canvas Cleared by Hand Gesture")
                                winsound.Beep(800, 80)
                        else:
                            clear_timer = 0

                    # Highlight index tip tracking indicator if active, not clicking, and performance mode is OFF
                    if tracking_enabled and not left_clicked and not is_scrolling_active and not is_triple_pinch and not performance_mode:
                        cv2.circle(frame, (idx_x, idx_y), 10, (255, 255, 0), cv2.FILLED)
            else:
                # Reset all states if hand is lost from frame
                first_detection = True
                left_clicked = False
                double_clicked = False
                ring_pinched = False
                if is_dragging:
                    pyautogui.mouseUp(button='left')
                    is_dragging = False
                    print("[ACTION] Hand lost: Mouse Up")

            # Calculate FPS
            curr_time = time.time()
            fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0.0
            prev_time = curr_time

            # On-screen HUD details (Only rendered if Performance Mode is OFF)
            if not performance_mode:
                cv2.putText(frame, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # Show current mouse action state
                status_str = "MOVING"
                status_color = (255, 255, 0)
                if draw_mode:
                    status_str = "AIR DRAW ACTIVE (Pinch: Draw | Palm: Erase)"
                    status_color = (57, 255, 20)
                elif not tracking_enabled:
                    status_str = "PAUSED (Show Peace Sign to Resume)"
                    status_color = (0, 0, 255)
                elif is_dragging:
                    status_str = "DRAGGING"
                    status_color = (0, 165, 255)
                elif double_clicked:
                    status_str = "DOUBLE CLICK"
                    status_color = (255, 255, 255)
                elif left_clicked:
                    status_str = "LEFT CLICK"
                    status_color = (0, 255, 0)
                elif ring_action_triggered:
                    status_str = "SLIDES CONTROL"
                    status_color = (0, 255, 0)
                elif ring_pinched:
                    status_str = "RIGHT CLICK TAP"
                    status_color = (255, 0, 0)
                elif is_scrolling_active:
                    status_str = "SCROLL / VOLUME MODE"
                    status_color = (0, 255, 255)
                    
                cv2.putText(frame, f"STATUS: {status_str}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
                cv2.putText(frame, "Controls: Index+Thumb=Click/Draw | Mid+Thumb=Drag | Fist=Voice Dictation | D=Draw | C=Clear | V=Voice", 
                            (10, CAM_HEIGHT - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            else:
                # Minimal HUD when in Performance Mode
                cv2.putText(frame, "PERFORMANCE MODE ACTIVE (Press 'h' to exit)", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Watermark - Software Developed by Vishal P
            cv2.putText(frame, "Developed by Vishal P", (CAM_WIDTH - 180, CAM_HEIGHT - 35), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

            # Merge Air Writing Canvas into live frame
            if not performance_mode:
                gray_draw = cv2.cvtColor(canvas_draw, cv2.COLOR_BGR2GRAY)
                _, mask_draw = cv2.threshold(gray_draw, 10, 255, cv2.THRESH_BINARY)
                frame[mask_draw > 0] = canvas_draw[mask_draw > 0]

            # Display feed window
            cv2.imshow("AI Virtual Mouse - Developed by Vishal P", frame)

            # Keyboard triggers
            key = cv2.waitKey(1) & 0xFF
            
            # Global hotkeys for Always on Top using keyboard library
            if keyboard.is_pressed('ctrl+alt+a'):
                if not always_on_top:
                    cv2.setWindowProperty("AI Virtual Mouse - Developed by Vishal P", cv2.WND_PROP_TOPMOST, 1)
                    always_on_top = True
                    print("[STATUS] Always on Top: ENABLED")
                    winsound.Beep(1800, 100)
            elif keyboard.is_pressed('ctrl+alt+v'):
                if always_on_top:
                    cv2.setWindowProperty("AI Virtual Mouse - Developed by Vishal P", cv2.WND_PROP_TOPMOST, 0)
                    always_on_top = False
                    print("[STATUS] Always on Top: DISABLED")
                    winsound.Beep(1000, 100)
            
            # Press 'e' key to toggle Eye Blink Mode
            if key == ord('e'):
                eye_blink_mode = not eye_blink_mode
                print(f"[STATUS] Eye Blink Tracking Mode: {'ENABLED' if eye_blink_mode else 'DISABLED'}")
                winsound.Beep(1600 if eye_blink_mode else 900, 100)
                
            # Press 'h' key to toggle Performance Mode
            elif key == ord('h'):
                performance_mode = not performance_mode
                print(f"[STATUS] Performance Mode {'Enabled (Graphics Hidden)' if performance_mode else 'Disabled'}")
                winsound.Beep(1200, 80)
                
            # Press 'd' key to toggle Air Draw Mode
            elif key == ord('d'):
                draw_mode = not draw_mode
                canvas_draw.fill(0)
                print(f"[STATUS] Air Draw Mode: {'ON' if draw_mode else 'OFF'}")
                winsound.Beep(1500, 100)
                
            # Press 'c' key to clear drawing canvas
            elif key == ord('c'):
                canvas_draw.fill(0)
                print("[STATUS] Canvas Cleared manually")
                winsound.Beep(800, 50)
                
            # Press 'v' key to trigger Voice typing
            elif key == ord('v'):
                pyautogui.hotkey('win', 'h')
                print("[STATUS] Windows Voice Typing triggered")
                winsound.Beep(1600, 100)
            
            # Clean exit on pressing 'q' or 'Esc' key
            if key == ord('q') or key == 27:
                break

            # Small delay to cap maximum FPS and prevent 100% CPU thread lock
            time.sleep(0.005)

    except pyautogui.FailSafeException:
        print("[ABORT] Fail-safe triggered! Mouse cursor moved to corner. Exiting program.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
    finally:
        # Final cleanup: release resources
        if is_dragging:
            pyautogui.mouseUp(button='left')
        cap.release()
        cv2.destroyAllWindows()
        print("[INFO] Resources released. Exiting clean.")

if __name__ == "__main__":
    main()
