import tkinter as tk
from tkinter import ttk
import serial
import math
import time
from serial.tools import list_ports
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

class EnhancedSensorGUI:
    def __init__(self):
        # Initialize the main window
        self.root = tk.Tk()
        self.root.title("Advanced Sensor Visualization System")
        self.root.geometry("1200x800")
        
        # Initialize sensor data and parameters
        self.MAX_DISTANCE = 400
        self.sensor_readings = [0, 0, 0, 0]
        self.history_length = 100
        self.sensor_histories = [deque(maxlen=self.history_length) for _ in range(4)]
        self.sensor_labels = ["Front", "Right", "Left", "Back"]
        
        # Set up the serial connection
        self.setup_serial()
        
        # Create the main interface
        self.create_gui()
        
        # Start the update loop
        self.update_gui()

    def setup_serial(self):
        """Initialize serial connection with error handling"""
        try:
            ports = list(list_ports.comports())
            if not ports:
                raise Exception("No serial ports found!")
            
            # Use first available port
            port = ports[0].device
            self.serial = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)
            
        except Exception as e:
            self.show_error(f"Serial Connection Error: {str(e)}")

    def create_gui(self):
        """Create the main GUI layout"""
        # Create main container frames
        self.create_frames()
        
        # Create visualization elements
        self.create_radar_display()
        self.create_history_graph()
        self.create_readings_display()
        self.create_controls()

    def create_frames(self):
        """Set up the main layout frames"""
        # Left panel for radar display
        self.radar_frame = ttk.LabelFrame(self.root, text="Radar View")
        self.radar_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        
        # Right panel for controls and readings
        self.right_frame = ttk.Frame(self.root)
        self.right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        
        # Bottom panel for history graph
        self.graph_frame = ttk.LabelFrame(self.root, text="Sensor History")
        self.graph_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        
        # Configure grid weights
        self.root.grid_columnconfigure(0, weight=2)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=2)
        self.root.grid_rowconfigure(1, weight=1)

    def create_radar_display(self):
        """Create the radar visualization canvas"""
        self.radar_canvas = tk.Canvas(self.radar_frame, width=500, height=500, bg='white')
        self.radar_canvas.pack(expand=True, fill='both', padx=5, pady=5)

    def create_history_graph(self):
        """Create the matplotlib graph for sensor history"""
        self.fig, self.ax = plt.subplots(figsize=(12, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(expand=True, fill='both', padx=5, pady=5)
        
        # Configure the plot
        self.ax.set_title("Sensor Reading History")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Distance (cm)")
        self.ax.grid(True)

    def create_readings_display(self):
        """Create the digital readings display"""
        readings_frame = ttk.LabelFrame(self.right_frame, text="Sensor Readings")
        readings_frame.pack(fill='x', padx=5, pady=5)
        
        self.reading_labels = []
        for i, label in enumerate(self.sensor_labels):
            frame = ttk.Frame(readings_frame)
            frame.pack(fill='x', padx=5, pady=2)
            
            ttk.Label(frame, text=f"{label}:").pack(side='left')
            value_label = ttk.Label(frame, text="0 cm")
            value_label.pack(side='right')
            self.reading_labels.append(value_label)

    def create_controls(self):
        """Create control buttons and options"""
        controls_frame = ttk.LabelFrame(self.right_frame, text="Controls")
        controls_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Reset History", 
                  command=self.reset_history).pack(fill='x', padx=5, pady=2)
        
        ttk.Button(controls_frame, text="Save Data", 
                  command=self.save_data).pack(fill='x', padx=5, pady=2)

    def update_gui(self):
        """Main update loop for the GUI"""
        try:
            # Read sensor data
            if self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8').strip()
                if line.startswith("DATA:"):
                    data_parts = line[5:].split(',')
                    if len(data_parts) == 4:
                        self.sensor_readings = [int(x) for x in data_parts]
                        
                        # Update histories
                        for i, reading in enumerate(self.sensor_readings):
                            self.sensor_histories[i].append(reading)
            
            # Update visualization elements
            self.update_radar()
            self.update_readings()
            self.update_history_graph()
            
        except Exception as e:
            self.show_error(f"Update Error: {str(e)}")
        
        # Schedule next update
        self.root.after(50, self.update_gui)

    def update_radar(self):
        """Update the radar display"""
        self.radar_canvas.delete("all")
        
        # Calculate center point
        center_x = self.radar_canvas.winfo_width() // 2
        center_y = self.radar_canvas.winfo_height() // 2
        
        # Draw reference circles
        for radius in range(100, 401, 100):
            scaled_radius = radius * 0.5
            self.radar_canvas.create_oval(
                center_x - scaled_radius, center_y - scaled_radius,
                center_x + scaled_radius, center_y + scaled_radius,
                outline='gray'
            )
        
        # Draw sensor lines
        angles = [0, 90, 270, 180]
        colors = ['red', 'green', 'blue', 'purple']
        
        for reading, angle, color in zip(self.sensor_readings, angles, colors):
            rad_angle = math.radians(angle)
            scaled_reading = min(reading, self.MAX_DISTANCE) * 0.5
            
            end_x = center_x + scaled_reading * math.cos(rad_angle)
            end_y = center_y + scaled_reading * math.sin(rad_angle)
            
            self.radar_canvas.create_line(
                center_x, center_y, end_x, end_y,
                fill=color, width=2
            )
            
            if reading < self.MAX_DISTANCE:
                self.radar_canvas.create_oval(
                    end_x - 5, end_y - 5,
                    end_x + 5, end_y + 5,
                    fill=color
                )

    def update_readings(self):
        """Update the digital readings display"""
        for label, reading in zip(self.reading_labels, self.sensor_readings):
            label.configure(text=f"{reading} cm")

    def update_history_graph(self):
        """Update the history graph"""
        self.ax.clear()
        self.ax.set_title("Sensor Reading History")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Distance (cm)")
        self.ax.grid(True)
        
        colors = ['red', 'green', 'blue', 'purple']
        for history, label, color in zip(self.sensor_histories, self.sensor_labels, colors):
            if len(history) > 0:
                self.ax.plot(list(history), label=label, color=color)
        
        self.ax.legend()
        self.ax.set_ylim(0, self.MAX_DISTANCE)
        self.canvas.draw()

    def reset_history(self):
        """Reset the sensor history data"""
        for history in self.sensor_histories:
            history.clear()

    def save_data(self):
        """Save the current sensor data to a file"""
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"sensor_data_{timestamp}.csv"
            
            with open(filename, 'w') as f:
                f.write("Timestamp,Front,Right,Left,Back\n")
                f.write(f"{timestamp},{','.join(map(str, self.sensor_readings))}\n")
                
        except Exception as e:
            self.show_error(f"Save Error: {str(e)}")

    def show_error(self, message):
        """Display error messages"""
        print(f"Error: {message}")

    def run(self):
        """Start the main application loop"""
        self.root.mainloop()

if __name__ == "__main__":
    app = EnhancedSensorGUI()
    app.run()