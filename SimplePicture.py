import tkinter as tk
from PIL import Image, ImageTk
from picamera import PiCamera
from picamera.array import PiRGBArray
import threading
import time

class SimpleCameraApp(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
        self.create_widgets()
        self.live_view_running = False

    def create_widgets(self):
        self.file_name_var = tk.StringVar(value='image.jpg')  # default filename
        tk.Label(self, text="File Name").pack(padx=10, pady=5)
        tk.Entry(self, textvariable=self.file_name_var).pack(fill="x", padx=10, pady=5)

        self.capture_button = tk.Button(self, text="Capture Image", command=self.capture_image)
        self.capture_button.pack(pady=5)

        self.live_view_button = tk.Button(self, text="Live View", command=self.toggle_live_view)
        self.live_view_button.pack(pady=5)

        self.quit_button = tk.Button(self, text="QUIT", command=self.master.destroy)
        self.quit_button.pack(pady=5)

        self.image_label = tk.Label(self)  # This label will hold the image display
        self.image_label.pack(side="bottom", fill="both", expand="yes")

    def capture_image(self):
        file_name = self.file_name_var.get() or 'image.jpg'  # Preventing an empty file name
        with PiCamera() as camera:
            camera.resolution = (1024, 768)
            camera.exposure_mode = 'off'
            camera.shutter_speed = 500
            camera.capture(file_name)
            self.display_image(file_name)

    def display_image(self, image_path):
        image = Image.open(image_path)
        photo = ImageTk.PhotoImage(image)

        self.image_label.config(image=photo)
        self.image_label.image = photo

    def toggle_live_view(self):
        self.live_view_running = not self.live_view_running
        if self.live_view_running:
            self.live_view_button.config(text="Stop Live View")
            threading.Thread(target=self.live_camera_view).start()
        else:
            self.live_view_button.config(text="Live View")

    def live_camera_view(self):
        try:
            # Initialize the camera

            with PiCamera() as camera:
                camera.resolution = (320, 320)
                camera.framerate = 24  # You can adjust the framerate
                raw_capture = PiRGBArray(camera, size=(320, 320))
                camera.exposure_mode = 'off'
                camera.shutter_speed = 500

                # Allow the camera to warm up
                time.sleep(2)

                # Capture continuously, and display the frames in the Tkinter label
                for frame in camera.capture_continuous(raw_capture, format="bgr", use_video_port=True):
                    if not self.live_view_running:
                        break  # If the 'Stop Live View' button is clicked, close the camera view

                    # Clear the stream for the next frame
                    raw_capture.truncate(0)

                    # Convert the image to PIL format
                    image = Image.fromarray(frame.array)

                    # Convert the image from PIL format to ImageTk format
                    imgtk = ImageTk.PhotoImage(image=image)

                    # Update the label with the current frame
                    # This operation should be thread-safe, as we're not directly interacting with Tkinter's main loop
                    self.image_label.config(image=imgtk)
                    self.image_label.image = imgtk

        except Exception as e:
            print(f"An error occurred: {e}")

def main():
    root = tk.Tk()
    root.geometry('800x800')  # Set the size of the window
    root.title("Simple Camera App")  # Set the title of the window
    app = SimpleCameraApp(master=root)
    app.mainloop()

if __name__ == "__main__":
    main()
