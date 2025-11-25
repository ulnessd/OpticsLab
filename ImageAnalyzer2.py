import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv

class ImageAnalysisApp(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack(fill=tk.BOTH, expand=True)
        
        # Variables to store state
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.image = None
        self.image_id = None
        self.plot_figure = None
        self.current_data = None # Stores data for CSV export
        self.current_headers = []

        self.create_widgets()

    def create_widgets(self):
        # --- Control Panel (Top) ---
        control_frame = tk.Frame(self, bg="#f0f0f0", bd=1, relief=tk.RAISED)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # Open Button
        self.open_button = tk.Button(control_frame, text="Open Image", command=self.open_image)
        self.open_button.pack(side=tk.LEFT, padx=10, pady=10)

        # Direction Toggles
        tk.Label(control_frame, text="|  Profile Direction:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.dir_var = tk.StringVar(value="Horizontal")
        tk.Radiobutton(control_frame, text="Horizontal (X)", variable=self.dir_var, value="Horizontal", bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Radiobutton(control_frame, text="Vertical (Y)", variable=self.dir_var, value="Vertical", bg="#f0f0f0").pack(side=tk.LEFT)

        # Color Mode Toggles
        tk.Label(control_frame, text="|  Color Mode:", bg="#f0f0f0").pack(side=tk.LEFT, padx=10)
        self.mode_var = tk.StringVar(value="Grayscale")
        tk.Radiobutton(control_frame, text="Grayscale (Intensity)", variable=self.mode_var, value="Grayscale", bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Radiobutton(control_frame, text="RGB Channels", variable=self.mode_var, value="RGB", bg="#f0f0f0").pack(side=tk.LEFT)

        # Save Button
        self.save_button = tk.Button(control_frame, text="Save Plot Data (.csv)", command=self.save_csv, state=tk.DISABLED)
        self.save_button.pack(side=tk.RIGHT, padx=10)

        # --- Main Layout (Split Pane) ---
        paned_window = tk.PanedWindow(self, orient=tk.VERTICAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # Image Area (Top/Left)
        self.canvas_frame = tk.Frame(paned_window)
        self.canvas = tk.Canvas(self.canvas_frame, bg="#555", width=800, height=400)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        paned_window.add(self.canvas_frame)

        # Plot Area (Bottom)
        self.plot_frame = tk.Frame(paned_window, bg="white", height=300)
        self.plot_frame.pack(fill=tk.BOTH, expand=True)
        paned_window.add(self.plot_frame)

        # Event bindings
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def open_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png *.jpeg *.bmp *.tif")])
        if file_path:
            self.image = Image.open(file_path)
            self.tk_image = ImageTk.PhotoImage(self.image)
            
            # Reset canvas
            self.canvas.delete("all")
            self.canvas.config(scrollregion=(0, 0, self.image.width, self.image.height))
            self.image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
            self.rect = None

    def on_button_press(self, event):
        if self.image_id is not None:
            self.start_x = self.canvas.canvasx(event.x)
            self.start_y = self.canvas.canvasy(event.y)

            if self.rect:
                self.canvas.delete(self.rect)
            self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def on_move_press(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        if self.rect and self.image:
            # Get coordinates
            coords = self.canvas.coords(self.rect)
            # Handle dragging in any direction (ensure x1<x2, y1<y2)
            x1, y1, x2, y2 = coords
            bbox = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
            
            # Clamp to image boundaries
            bbox[0] = max(0, min(self.image.width, bbox[0]))
            bbox[1] = max(0, min(self.image.height, bbox[1]))
            bbox[2] = max(0, min(self.image.width, bbox[2]))
            bbox[3] = max(0, min(self.image.height, bbox[3]))

            # Avoid zero-size crashes
            if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                self.analyze_image(bbox)

    def analyze_image(self, bbox):
        # 1. Crop Image
        cropped = self.image.crop(bbox)
        mode = self.mode_var.get()
        direction = self.dir_var.get()

        # 2. Prepare Data
        plot_dict = {} # Key: Label, Value: Data Array
        
        if mode == "Grayscale":
            # Convert to Grayscale (L)
            gray_img = cropped.convert("L")
            img_array = np.array(gray_img)
            
            if direction == "Horizontal":
                # Average columns (axis 0) -> 1D array along X
                data = np.mean(img_array, axis=0)
            else:
                # Average rows (axis 1) -> 1D array along Y
                data = np.mean(img_array, axis=1)
            
            plot_dict["Intensity"] = data
            
        else: # RGB Mode
            # Ensure RGB
            rgb_img = cropped.convert("RGB")
            img_array = np.array(rgb_img)
            
            if direction == "Horizontal":
                # Average down rows (axis 0), keeping 3 channels
                # Result shape: (Width, 3)
                means = np.mean(img_array, axis=0)
            else:
                # Average across columns (axis 1)
                # Result shape: (Height, 3)
                means = np.mean(img_array, axis=1)

            plot_dict["Red"] = means[:, 0]
            plot_dict["Green"] = means[:, 1]
            plot_dict["Blue"] = means[:, 2]

        # 3. Update Plot
        self.update_plot(plot_dict, direction)

    def update_plot(self, data_dict, direction):
        # Clear previous plot
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        # Create new Figure
        self.plot_figure = plt.figure(figsize=(6, 3), dpi=100)
        ax = self.plot_figure.add_subplot(111)

        # Setup CSV Data Structure
        # Get length from first dataset
        first_key = next(iter(data_dict))
        length = len(data_dict[first_key])
        indices = np.arange(length)
        
        # Initialize rows for CSV: [ [0], [1], [2]... ]
        csv_rows = [[i] for i in indices]
        self.current_headers = ["Index"]

        # Plot each line (Gray or R/G/B)
        for label, values in data_dict.items():
            # Assign standard colors
            color = 'black'
            if label == "Red": color = 'red'
            elif label == "Green": color = 'green'
            elif label == "Blue": color = 'blue'
            
            ax.plot(indices, values, label=label, color=color, linewidth=1)
            
            # Add to CSV structure
            self.current_headers.append(label)
            for i, val in enumerate(values):
                csv_rows[i].append(val)

        self.current_data = csv_rows

        # Formatting
        ax.set_title(f"Average Intensity ({direction} Profile)")
        ax.set_xlabel("Pixel Position")
        ax.set_ylabel("Avg Intensity (0-255)")
        ax.grid(True, linestyle='--', alpha=0.6)
        if len(data_dict) > 1:
            ax.legend()

        # Render to Tkinter
        canvas = FigureCanvasTkAgg(self.plot_figure, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Enable Save Button
        self.save_button.config(state=tk.NORMAL)

    def save_csv(self):
        if not self.current_data:
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        
        if file_path:
            try:
                with open(file_path, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(self.current_headers)
                    writer.writerows(self.current_data)
                print(f"Saved data to {file_path}")
            except Exception as e:
                print(f"Error saving CSV: {e}")

def main():
    root = tk.Tk()
    root.title("Optic Lab Image Analyzer")
    root.geometry("1000x900")
    app = ImageAnalysisApp(master=root)
    root.mainloop()

if __name__ == "__main__":
    main()
