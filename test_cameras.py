import cv2

def test_cameras():
    print("="*50)
    print("SCANNING CAMERA INDICES (0 to 5)...")
    print("="*50)
    found_any = False
    
    for index in range(6):
        # cv2.CAP_DSHOW is recommended for Windows to speed up initialization
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"[SUCCESS] Camera index {index} is available and sending frames!")
                found_any = True
            else:
                print(f"[SUCCESS] Camera index {index} is opened, but failed to read frames.")
            cap.release()
        else:
            # Try without CAP_DSHOW
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                print(f"[SUCCESS] Camera index {index} is available!")
                found_any = True
                cap.release()
            else:
                print(f"[FAILED] Camera index {index} is not available.")
                
    print("="*50)
    if not found_any:
        print("[WARNING] No cameras could be opened.")
        print("Please check if:")
        print("1. Your webcam is physically connected/enabled.")
        print("2. Another application (Zoom, Teams, Chrome, OBS) is currently using the camera.")
        print("3. Windows Settings -> Privacy -> Camera allows desktop apps to access the camera.")
    print("="*50)

if __name__ == "__main__":
    test_cameras()
