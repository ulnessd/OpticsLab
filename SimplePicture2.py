import tkinter as tk
from tkinter import Label, Button, filedialog
from PIL import Image, ImageTk
from picamera2 import Picamera2
import threading
import time
import sys
import queue

class CameraApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.window.geometry("900x800")

        # Thread communication
        self.frame_queue = queue.Queue(maxsize=1)
        self.is_running = False
        self.camera_thread = None
        self.current_raw_image = None # Holds the image for saving

        # 1. Setup UI first
        self.setup_ui()

        # 2. Initialize Camera (BLOCKING)
        # We reverted to the blocking method because it is more stable on the Pi 4.
        # The GUI will freeze for 20-40 seconds here. This is expected.
        self.status_update("Initializing Hardware (GUI may freeze for 30s)...", "orange")
        self.window.update() # Force the label to appear before we freeze

        try:
            self.picam2 = Picamera2()
            # RGB888 is easier for Tkinter/PIL to handle than YUV
            config = self.picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
            self.picam2.configure(config)
            self.picam2.start() # Warmup
            self.picam2.stop()
            
            self.camera_ready = True
            self.status_update("System Ready. Press Start.", "green")
            self.btn_start.config(state=tk.NORMAL)
            
        except Exception as e:
            self.camera_ready = False
            self.status_update(f"Camera Error: {e}", "red")
            print(f"Detailed Error: {e}")

    def setup_ui(self):
        # Header
        self.label_title = Label(self.window, text="Raspberry Pi Optic Lab", font=("Arial", 20, "bold"))
        self.label_title.pack(pady=10)

        # Video Area
        self.video_label = Label(self.window, text="[ Camera Standby ]", bg="#222", fg="#888", width=110, height=30)
        self.video_label.pack(pady=10, fill=tk.BOTH, expand=True)

        # Buttons
        self.btn_frame = tk.Frame(self.window)
        self.btn_frame.pack(pady=15)

        self.btn_start = Button(self.btn_frame, text="Start Camera", font=("Arial", 12), width=12, bg="#dddddd", command=self.start_camera, state=tk.DISABLED)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_stop = Button(self.btn_frame, text="Stop Camera", font=("Arial", 12), width=12, bg="#dddddd", command=self.stop_camera, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        # SAVE BUTTON: Green to make it obvious
        self.btn_save = Button(self.btn_frame, text="Save Image", font=("Arial", 12, "bold"), width=12, bg="#aaffaa", command=self.save_image, state=tk.DISABLED)
        self.btn_save.pack(side=tk.LEFT, padx=20)

        # Status Bar
        self.status_label = Label(self.window, text="Booting...", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def status_update(self, msg, color="black"):
        self.status_label.config(text=msg, fg=color)
        print(msg)

    def start_camera(self):
        if not self.camera_ready:
            return

        if not self.is_running:
            self.status_update("Starting Stream...", "blue")
            self.picam2.start()
            self.is_running = True
            
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.btn_save.config(state=tk.NORMAL)

            # Start the background capture thread
            self.camera_thread = threading.Thread(target=self.capture_loop, daemon=True)
            self.camera_thread.start()
            
            # Start the GUI update loop
            self.update_gui_loop()

    def stop_camera(self):
        if self.is_running:
            self.status_update("Stopping...", "orange")
            self.is_running = False
            
            # Allow thread to exit gracefully
            self.window.after(500, self._finalize_stop)

    def _finalize_stop(self):
        try:
            self.picam2.stop()
        except:
            pass
        
        self.video_label.config(image='', text="[ Camera Standby ]", bg="#222")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_save.config(state=tk.DISABLED)
        self.status_update("Camera Stopped.", "black")

    def save_image(self):
        """Saves the current frame using a file dialog"""
        if self.current_raw_image is None:
            self.status_update("No image data to save!", "red")
            return

        # Note: The preview will freeze while this dialog is open. 
        # This is normal behavior for a simple GUI. 
        # The camera hardware stays on, and it resumes immediately after saving.
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            title="Save Snapshot"
        )

        if filepath:
            try:
                # Save the raw PIL object
                self.current_raw_image.save(filepath)
                self.status_update(f"Saved: {filepath}", "green")
            except Exception as e:
                self.status_update(f"Save Failed: {e}", "red")

    def capture_loop(self):
        """Background Thread: Captures data from hardware"""
        while self.is_running:
            try:
                frame = self.picam2.capture_array()
                
                # Queue management: Drop old frames if GUI is lagging
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.frame_queue.put(frame)
                
            except Exception as e:
                print(f"Capture Error: {e}")
                self.is_running = False
                break

    def update_gui_loop(self):
        """Main Thread: Updates the screen"""
        if not self.is_running:
            return

        try:
            frame = self.frame_queue.get_nowait()
            
            # Create PIL Image (Raw 640x480)
            image = Image.fromarray(frame)
            
            # Store a COPY for the save button (so we save the raw resolution)
            self.current_raw_image = image.copy()

            # Resize for the Window (800x600)
            image_resized = image.resize((800, 600)) 
            photo = ImageTk.PhotoImage(image=image_resized)

            self.current_image = photo 
            self.video_label.config(image=photo, width=0, height=0)

        except queue.Empty:
            pass # GUI is faster than camera, just wait

        # Schedule next check
        self.window.after(20, self.update_gui_loop)

    def on_close(self):
        self.status_update("Shutting down...")
        self.is_running = False
        if hasattr(self, 'picam2'):
            try:
                self.picam2.stop()
                self.picam2.close()
            except:
                pass
        self.window.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root, "Pi Camera Controller")
    root.mainloop()
