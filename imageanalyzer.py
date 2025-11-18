import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv

class ImageAnalysisApp(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
        self.create_widgets()

    def create_widgets(self):
        self.open_button = tk.Button(self, text="Open Image", command=self.open_image)
        self.open_button.pack()

        self.canvas = tk.Canvas(self, bg="white", width=1024, height=768)
        self.canvas.pack()

        self.save_button = tk.Button(self, text="Save as CSV", command=self.save_csv, state=tk.DISABLED)
        self.save_button.pack()

        # Event bindings
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        self.start_x = None
        self.start_y = None
        self.rect = None
        self.image = None
        self.image_id = None
        self.plot_figure = None

    def open_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png *.jpeg")])
        if file_path:
            self.image = Image.open(file_path)
            self.tk_image = ImageTk.PhotoImage(self.image)
            self.canvas.config(scrollregion=(0, 0, self.image.width, self.image.height))
            self.image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

    def on_button_press(self, event):
        if self.image_id is not None:  # Only start drawing the rectangle if an image is loaded
            # save mouse drag start position
            self.start_x = self.canvas.canvasx(event.x)
            self.start_y = self.canvas.canvasy(event.y)

            # create rectangle if not yet exist
            if not self.rect:
                self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red')

    def on_move_press(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)

        # expand rectangle as you drag the mouse
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        if self.rect and self.image:
            # Transform canvas coordinates to image coordinates
            bbox = self.canvas.coords(self.rect)
            bbox[0] = max(0, min(self.image.width - 1, bbox[0]))
            bbox[1] = max(0, min(self.image.height - 1, bbox[1]))
            bbox[2] = max(0, min(self.image.width - 1, bbox[2]))
            bbox[3] = max(0, min(self.image.height - 1, bbox[3]))

            # Perform the analysis
            self.analyze_image(bbox)

    def analyze_image(self, bbox):
        # Crop the image to the selected region and convert to grayscale
        cropped_img = self.image.crop(bbox).convert("L")
        img_array = np.array(cropped_img)

        # Calculate the average for each column
        averages = np.mean(img_array, axis=0)

        # Plotting the average
        self.plot_figure = plt.figure()
        plt.plot(averages)

        # Embedding the plot in the Tkinter window
        self.chart = FigureCanvasTkAgg(self.plot_figure, self.master)
        self.chart.get_tk_widget().pack()
        self.save_button.config(state=tk.NORMAL)

    def save_csv(self):
        if self.plot_figure:
            file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                     filetypes=[("CSV files", "*.csv")])
            if file_path:
                # Extract data from the plot and save to CSV
                plot_data = self.plot_figure.axes[0].lines[0].get_xydata()
                with open(file_path, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['x', 'Average Intensity'])
                    writer.writerows(plot_data)

def main():
    root = tk.Tk()
    root.title("Image Analysis App")
    app = ImageAnalysisApp(master=root)
    app.mainloop()

if __name__ == "__main__":
    main()

