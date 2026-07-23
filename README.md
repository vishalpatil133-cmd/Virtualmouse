```
 █████╗ ██╗    ██╗   ██╗██╗██████╗ ████████╗██╗   ██╗ █████╗ ██╗     ███╗   ███╗ ██████╗ ██╗   ██╗███████╗███████╗
██╔══██╗██║    ██║   ██║██║██╔══██╗╚══██╔══╝██║   ██║██╔══██╗██║     ████╗ ████║██╔═══██╗██║   ██║██╔════╝██╔════╝
███████║██║    ██║   ██║██║██████╔╝   ██║   ██║   ██║███████║██║     ██╔████╔██║██║   ██║██║   ██║███████╗█████╗  
██╔══██║██║    ╚██╗ ██╔╝██║██╔══██╗   ██║   ██║   ██║██╔══██║██║     ██║╚██╔╝██║██║   ██║██║   ██║╚════██║██╔══╝  
██║  ██║██║     ╚████╔╝ ██║██║  ██║   ██║   ╚██████╔╝██║  ██║███████╗██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████║███████╗
╚═╝  ╚═╝╚═╝      ╚═══╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚══════╝
```

# AI Virtual Mouse & Interactive Gesture Ecosystem 🚀

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

[![Reddit Views](https://img.shields.io/badge/Reddit-9.2K%2B%20Views%20%F0%9F%94%A5-FF4500?style=for-the-badge&logo=reddit&logoColor=white)](https://reddit.com)
[![GitHub Stars](https://img.shields.io/github/stars/vishalpatil133-cmd/Virtualmouse?style=for-the-badge&color=gold&logo=github)](https://github.com/vishalpatil133-cmd/Virtualmouse)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Performance](https://img.shields.io/badge/Performance-30%20FPS%20Zero--Drift-brightgreen?style=for-the-badge)](https://github.com/vishalpatil133-cmd/Virtualmouse)

An advanced, multi-modal human-computer interaction (HCI) suite that translates **Computer Vision hand tracking**, **smartphone motion sensors**, and **voice commands** into real-time operating system control, interactive 3D simulations, and gamified browser servers.

Developed by **[Vishal P](https://github.com/vishalpatil133-cmd)** *(11th Grade Student Developer & ECE Enthusiast)*.

---

## 📽️ Project Overview
This project is a compilation of 4 futuristic utilities that bridge the gap between humans and machines without requiring expensive hardware:

1. **AI Webcam Virtual Mouse** (`virtual_mouse.py`): Control your cursor, click, scroll, draw in mid-air, and dictate voice text using a standard webcam.
2. **Smartphone Wi-Fi Air Mouse** (`wifi_mouse.py`): Turn your mobile phone's gyroscope/accelerometer into an air mouse and multi-touch trackpad over local Wi-Fi.
3. **Cyberpunk Neon Racer** (`car_server.py`): Control a browser-based 3D car simulation using two-hand virtual steering wheel gestures.
4. **Stark 3D Holographic HUD** (`stark_server.py`): Manipulate a 3D wireframe Arc Reactor using zoom/pan gestures, including 4-way projection mirroring for holographic plastic pyramids.

---

## 🌟 Key Features & Engineering Highlights

### ⚡ 1. Knuckle-Mapped Stable Click Tracking
Most hand-tracking systems map the cursor to the **index finger tip** (`Landmark 8`). However, when you curl your index finger to click/pinch, the tip slides downward, causing the cursor to drift away from the target button.
* **Our Solution**: We mapped cursor tracking to the **Index Finger MCP (Base Knuckle)** (`Landmark 5`). Because the base knuckle remains completely still during finger curls, clicks are **100% stable** and have zero cursor drift!

### 🏎️ 2. Butter-Smooth 30 FPS Performance
* Optimized the MediaPipe Hand pipeline to run at a solid 30 FPS.
* Lowered `model_complexity` to `0` and restricted tracking to `max_num_hands=1` in mouse mode. This completely eliminated CPU thermal throttling on consumer laptops.
* Integrated dynamic LERP (Linear Interpolation) smoothing to make cursor movement feel soft and fluid.

### 📌 3. Global Window Hotkeys
Need your webcam preview window to stay visible while playing games or working in Photoshop?
* **`Ctrl + Alt + A`**: Sets the Camera Feed window to **Always on Top** (Topmost). Includes a high-pitched audio beep.
* **`Ctrl + Alt + V`**: Reverts the window to normal. Includes a low-pitched audio beep.

---

## 🖐️ Gesture Command Reference

| Gesture | Action | Description |
| :--- | :--- | :--- |
| **Move Pointer (Hands-Free)** | Head Motion / Nose Tip (No Hands visible) | Ultra-Smooth & Sensitive Hands-Free Cursor Tracking |
| **Move Pointer (Hand)** | Index Knuckle Base (`Landmark 5`) | 100% Zero-Drift Smooth Pointer Motion |
| **Left Click** | Index + Thumb Pinch OR Both Eyes 1-Blink | Immediate Left Click Trigger & Audio Chime |
| **Right Click** | Ring + Thumb Pinch OR Both Eyes 2-Blinks | Right Click Context Menu Trigger & Audio Chime |
| **Drag & Drop** | Middle + Thumb Pinch | Hold Left Click & Move to Drag |
| **Double Click** | Index + Middle + Thumb Pinch | Quick double-beep confirmation. Opens folders instantly. |
| **Vertical Scroll & Volume** | Pinky + Thumb Pinch | Move hand up/down to scroll. Move hand left/right to adjust system volume. |
| **Closed Fist** (Hold 1.5s) | **Voice Dictation** | Opens Windows Speech-to-Text (`Win + H`) so you can type using your voice. |
| **Both Wrists Joined** | **Namaste (Show Desktop)** | Minimizes all active windows (`Win + D`). Perform again to restore. |
| **Keyboard 'D' Key** | **Toggle Paint Mode** | Draw in neon green mid-air. Open palm for 1.5s to clear the canvas. |

---

## ⚙️ Installation & Setup

### 1. Pre-requisites
Ensure you have **Python 3.8+** installed. Install all dependencies:
```bash
pip install opencv-python mediapipe pyautogui numpy websockets keyboard
```
*(Note: Run your terminal as Administrator on Windows to enable the `keyboard` library global hotkeys).*

### 2. Running the Utilities

#### 🖱️ Module A: Webcam Virtual Mouse
```bash
python virtual_mouse.py
```
* **Performance Mode**: Press `H` to hide landmarks and overlay graphics, saving CPU rendering overhead.
* **Always-on-Top hotkey**: Press `Ctrl+Alt+A` to keep the feed visible over other apps.

#### 📱 Module B: Smartphone Wi-Fi Controller
```bash
python wifi_mouse.py
```
* Note the IP address printed in the console (e.g., `http://192.168.1.5:8000`).
* Open this URL in your phone's browser (Safari/Chrome) while connected to the same Wi-Fi. Turn on your mobile rotation lock to use the air gyroscope!

#### 🏎️ Module C: Virtual Steering Racer
```bash
python car_server.py
```
* Open `http://localhost:8002` in your PC browser.
* Hold a virtual steering wheel in front of your camera. Tilt to steer! Pinch right hand to accelerate, left hand to brake.

#### ⚛️ Module D: Stark Hologram HUD
```bash
python stark_server.py
```
* Open `http://localhost:8001` in your PC browser.
* Pan with one hand, zoom with two hands, and double pinch to overcharge the arc reactor. Press `H` in the browser to toggle the 4-way holographic projector mode.

---

## 🛠️ Technology Stack
* **Languages**: Python 3, JavaScript (ES6+), HTML5, CSS3.
* **Libraries**: OpenCV (Image Processing), MediaPipe (Hand Landmark Inference), PyAutoGUI (OS Inputs), WebSockets (Real-time socket streams), Three.js (3D WebGL rendering).

---

## 🤝 Socials & Showcases
We are actively showcasing this project on developer platforms!
* **Twitter (X)**: [Watch the demo video](https://x.com) 🐦
* **Reddit**: [Read the discussion on r/programming](https://reddit.com) 💬
* **GitHub Stars**: If you like this project, please consider leaving a ⭐ star to show your support!

---
*Created with ❤️ by Vishal P. Aspiring Electronics & Communication Engineer.*
