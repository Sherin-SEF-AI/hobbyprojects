import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import serial
import serial.tools.list_ports
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from datetime import datetime
import csv

class MPU6050Dashboard:
    def __init__(self, root):
        # Initialize main window with a modern look
        self.root = root
        self.root.title("MPU6050 Sensor Dashboard")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # Create custom styles for widgets
        self.setup_styles()
        
        # Initialize data storage
        self.initialize_data_storage()
        
        # Create the main interface
        self.create_gui()
        
        # Initialize serial connection and start data collection
        if self.init_serial():
            self.start_data_collection()

    def setup_styles(self):
        """Configure custom styles for the application widgets"""
        self.style = ttk.Style()
        self.style.configure('Header.TLabel', 
                           font=('Arial', 14, 'bold'),
                           padding=5)
        self.style.configure('Value.TLabel', 
                           font=('Arial', 12),
                           padding=3)
        self.style.configure('Alert.TLabel',
                           font=('Arial', 12, 'bold'),
                           foreground='red')
        self.style.configure('Status.TLabel',
                           font=('Arial', 10),
                           padding=2)

    def initialize_data_storage(self):
        """Initialize data structures for storing sensor readings"""
        self.data_points = 100  # Number of points to display on graphs
        self.timestamps = []
        self.accel_data = {'x': [], 'y': [], 'z': []}
        self.gyro_data = {'x': [], 'y': [], 'z': []}
        self.orientation_data = {'roll': [], 'pitch': []}
        self.temp_data = []
        self.motion_data = []
        self.recording = False

    def create_gui(self):
        """Create the main GUI layout"""
        # Create main frames
        self.create_menu()
        self.create_control_panel()
        self.create_visualization_panel()
        
        # Configure grid weights
        self.root.grid_columnconfigure(1, weight=3)
        self.root.grid_rowconfigure(0, weight=1)

    def create_menu(self):
        """Create the application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Start Recording", command=self.start_recording)
        file_menu.add_command(label="Stop Recording", command=self.stop_recording)
        file_menu.add_command(label="Save Data", command=self.save_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.cleanup_and_exit)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Calibrate Sensor", command=self.calibrate_sensor)
        tools_menu.add_command(label="Reset Plots", command=self.reset_plots)
        tools_menu.add_command(label="Connection Settings", command=self.show_connection_settings)

    def create_control_panel(self):
        """Create the control panel with sensor readings"""
        self.control_frame = ttk.LabelFrame(self.root, text="Sensor Control Panel", padding=10)
        self.control_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Sensor readings section
        readings_frame = ttk.LabelFrame(self.control_frame, text="Real-time Readings", padding=5)
        readings_frame.pack(fill='x', padx=5, pady=5)
        
        self.reading_labels = {}
        self.create_sensor_section(readings_frame, "Accelerometer", ['X', 'Y', 'Z'], 'g')
        self.create_sensor_section(readings_frame, "Gyroscope", ['X', 'Y', 'Z'], '°/s')
        self.create_sensor_section(readings_frame, "Orientation", ['Roll', 'Pitch'], '°')
        self.create_sensor_section(readings_frame, "Temperature", [''], '°C')
        
        # Motion detection indicator
        self.motion_frame = ttk.LabelFrame(self.control_frame, text="Motion Detection", padding=5)
        self.motion_frame.pack(fill='x', padx=5, pady=5)
        self.motion_indicator = ttk.Label(self.motion_frame, 
                                        text="No Motion Detected",
                                        style='Value.TLabel')
        self.motion_indicator.pack(pady=5)
        
        # Status bar
        self.status_frame = ttk.Frame(self.control_frame)
        self.status_frame.pack(fill='x', side='bottom', pady=5)
        self.status_label = ttk.Label(self.status_frame, 
                                    text="Initializing...",
                                    style='Status.TLabel')
        self.status_label.pack(side='left')
        
        # Recording indicator
        self.recording_label = ttk.Label(self.status_frame,
                                       text="",
                                       style='Status.TLabel')
        self.recording_label.pack(side='right')

    def create_visualization_panel(self):
        """Create the visualization panel with plots"""
        self.plot_frame = ttk.LabelFrame(self.root, text="Sensor Data Visualization", padding=10)
        self.plot_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        # Create matplotlib figure
        self.fig, self.axes = plt.subplots(3, 1, figsize=(10, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configure plots
        self.setup_plots()

    def create_sensor_section(self, parent, title, axes, unit):
        """Create a section for displaying sensor readings"""
        frame = ttk.LabelFrame(parent, text=title, padding=5)
        frame.pack(fill='x', padx=5, pady=2)
        
        for axis in axes:
            row = ttk.Frame(frame)
            row.pack(fill='x')
            
            label_text = f"{axis}:" if axis else title
            ttk.Label(row, text=label_text, style='Value.TLabel').pack(side='left', padx=5)
            
            value_label = ttk.Label(row, text=f"0.00 {unit}", style='Value.TLabel')
            value_label.pack(side='right', padx=5)
            self.reading_labels[f"{title}{axis}"] = value_label

    def setup_plots(self):
        """Configure the matplotlib plots"""
        plot_configs = [
            ('Accelerometer', ['X', 'Y', 'Z'], 'g'),
            ('Gyroscope', ['X', 'Y', 'Z'], '°/s'),
            ('Orientation', ['Roll', 'Pitch'], 'degrees')
        ]
        
        self.plot_lines = []
        for i, (title, labels, ylabel) in enumerate(plot_configs):
            self.axes[i].set_title(title)
            self.axes[i].set_ylabel(ylabel)
            self.axes[i].grid(True)
            
            lines = [self.axes[i].plot([], [], label=label)[0] for label in labels]
            self.axes[i].legend()
            self.plot_lines.append(lines)

    # ... [Continue in next message due to length]


    def init_serial(self):
        """Initialize serial connection with error handling"""
        try:
            # First list available ports for debugging
            ports = serial.tools.list_ports.comports()
            print("Available serial ports:")
            for port in ports:
                print(f"{port.device}: {port.description}")

            # Close any existing connection
            if hasattr(self, 'serial_port'):
                self.serial_port.close()

            # Establish new connection
            self.serial_port = serial.Serial(
                port='COM6',
                baudrate=115200,
                timeout=1,
                write_timeout=1
            )
            
            # Wait for device initialization
            time.sleep(2)
            self.serial_port.flushInput()
            
            self.status_label.config(text="Connected to MPU6050", foreground="green")
            return True
            
        except serial.SerialException as e:
            messagebox.showerror(
                "Connection Error",
                f"Could not connect to MPU6050 on COM6.\n\n"
                f"Please check:\n"
                f"1. Arduino IDE Serial Monitor is closed\n"
                f"2. ESP32 is properly connected\n"
                f"3. Correct COM port is selected\n\n"
                f"Error: {str(e)}"
            )
            self.status_label.config(text="Connection Failed", foreground="red")
            return False

    def start_data_collection(self):
        """Initialize and start the data collection thread"""
        self.running = True
        self.data_thread = threading.Thread(target=self.collect_data)
        self.data_thread.daemon = True
        self.data_thread.start()

    def collect_data(self):
        """Main data collection loop with improved debugging"""
        while self.running:
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode().strip()
                    
                    # Print raw received data for debugging
                    print(f"Received: {line}")
                    
                    # Process only data lines
                    if line.startswith("DATA:"):
                        data_str = line[5:]  # Remove "DATA:" prefix
                        values = [float(x) for x in data_str.split(',')]
                        
                        # Print parsed values for debugging
                        print("Parsed values:")
                        print(f"Accel: X={values[0]:.2f}, Y={values[1]:.2f}, Z={values[2]:.2f}")
                        print(f"Gyro: X={values[3]:.2f}, Y={values[4]:.2f}, Z={values[5]:.2f}")
                        
                        # Update data storage with error checking
                        try:
                            # Update accelerometer data
                            for i, axis in enumerate(['x', 'y', 'z']):
                                self.accel_data[axis].append(values[i])
                                if len(self.accel_data[axis]) > self.data_points:
                                    self.accel_data[axis].pop(0)
                            
                            # Update gyroscope data
                            for i, axis in enumerate(['x', 'y', 'z']):
                                self.gyro_data[axis].append(values[i+3])
                                if len(self.gyro_data[axis]) > self.data_points:
                                    self.gyro_data[axis].pop(0)
                            
                            # Update GUI
                            self.root.after(0, self.update_display, values)
                            
                        except Exception as e:
                            print(f"Error updating data storage: {e}")
                            
            except Exception as e:
                print(f"Error in data collection: {e}")
                time.sleep(0.1)
            
            time.sleep(0.01)

    def update_data_storage(self, timestamp, values):
        """Update internal data storage with new sensor readings"""
        # Store timestamp
        self.timestamps.append(timestamp)
        if len(self.timestamps) > self.data_points:
            self.timestamps.pop(0)
        
        # Update accelerometer data
        for i, axis in enumerate(['x', 'y', 'z']):
            self.accel_data[axis].append(values[i])
            if len(self.accel_data[axis]) > self.data_points:
                self.accel_data[axis].pop(0)
        
        # Update gyroscope data
        for i, axis in enumerate(['x', 'y', 'z']):
            self.gyro_data[axis].append(values[i+3])
            if len(self.gyro_data[axis]) > self.data_points:
                self.gyro_data[axis].pop(0)
        
        # Update orientation data
        self.orientation_data['roll'].append(values[6])
        self.orientation_data['pitch'].append(values[7])
        if len(self.orientation_data['roll']) > self.data_points:
            self.orientation_data['roll'].pop(0)
            self.orientation_data['pitch'].pop(0)

    def update_display(self, values):
        """Update display with improved error checking"""
        try:
            # Print values being displayed for debugging
            print("Updating display with values:", values)
            
            # Update accelerometer readings
            for i, axis in enumerate(['X', 'Y', 'Z']):
                value = values[i]
                label = self.reading_labels[f'Accelerometer{axis}']
                new_text = f"{value:.2f} g"
                print(f"Setting Accel{axis} to {new_text}")
                label.config(text=new_text)
            
            # Update gyroscope readings
            for i, axis in enumerate(['X', 'Y', 'Z']):
                value = values[i+3]
                label = self.reading_labels[f'Gyroscope{axis}']
                new_text = f"{value:.2f} °/s"
                print(f"Setting Gyro{axis} to {new_text}")
                label.config(text=new_text)
            
            # Update plots with error checking
            try:
                self.update_plots()
            except Exception as e:
                print(f"Error updating plots: {e}")
                
        except Exception as e:
            print(f"Error updating display: {e}")
    def update_plots(self):
        """Update all real-time plots with new data"""
        try:
            # Update accelerometer plot
            for i, axis in enumerate(['x', 'y', 'z']):
                self.plot_lines[0][i].set_data(range(len(self.accel_data[axis])), 
                                             self.accel_data[axis])
            
            # Update gyroscope plot
            for i, axis in enumerate(['x', 'y', 'z']):
                self.plot_lines[1][i].set_data(range(len(self.gyro_data[axis])), 
                                             self.gyro_data[axis])
            
            # Update orientation plot
            self.plot_lines[2][0].set_data(range(len(self.orientation_data['roll'])), 
                                         self.orientation_data['roll'])
            self.plot_lines[2][1].set_data(range(len(self.orientation_data['pitch'])), 
                                         self.orientation_data['pitch'])
            
            # Adjust plot limits
            for ax in self.axes:
                ax.relim()
                ax.autoscale_view()
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating plots: {e}")


    def save_data(self):
        """Save current sensor data to a CSV file"""
        try:
            # Get filename from user
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = filedialog.asksaveasfilename(
                initialfile=f'mpu6050_data_{timestamp}.csv',
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if filename:  # If user didn't cancel
                with open(filename, 'w', newline='') as file:
                    writer = csv.writer(file)
                    
                    # Write header
                    writer.writerow([
                        'Timestamp',
                        'AccelX', 'AccelY', 'AccelZ',
                        'GyroX', 'GyroY', 'GyroZ',
                        'Roll', 'Pitch',
                        'Temperature', 'Motion'
                    ])
                    
                    # Write data points
                    for i in range(len(self.timestamps)):
                        writer.writerow([
                            datetime.fromtimestamp(self.timestamps[i]).strftime('%Y-%m-%d %H:%M:%S.%f'),
                            self.accel_data['x'][i],
                            self.accel_data['y'][i],
                            self.accel_data['z'][i],
                            self.gyro_data['x'][i],
                            self.gyro_data['y'][i],
                            self.gyro_data['z'][i],
                            self.orientation_data['roll'][i],
                            self.orientation_data['pitch'][i],
                            self.temp_data[i] if i < len(self.temp_data) else '',
                            self.motion_data[i] if i < len(self.motion_data) else ''
                        ])
                
                messagebox.showinfo("Success", "Data saved successfully!")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")

    def calibrate_sensor(self):
        """Triggers sensor calibration and provides visual feedback to the user"""
        try:
            # Create a calibration dialog window
            cal_window = tk.Toplevel(self.root)
            cal_window.title("Sensor Calibration")
            cal_window.geometry("400x300")
            cal_window.transient(self.root)  # Make window modal
            
            # Add instructions
            ttk.Label(cal_window, text="MPU6050 Calibration", style='Header.TLabel').pack(pady=10)
            ttk.Label(cal_window, text="Please ensure the sensor is:", style='Value.TLabel').pack(pady=5)
            instructions = [
                "1. Placed on a flat, stable surface",
                "2. Not moving or vibrating",
                "3. Oriented correctly (Z-axis vertical)"
            ]
            for instruction in instructions:
                ttk.Label(cal_window, text=instruction, style='Value.TLabel').pack(pady=2)
            
            # Progress indicator
            progress = ttk.Progressbar(cal_window, length=300, mode='indeterminate')
            progress.pack(pady=20)
            
            status_label = ttk.Label(cal_window, text="Ready to calibrate", style='Value.TLabel')
            status_label.pack(pady=10)
            
            def start_calibration():
                try:
                    # Disable the start button during calibration
                    start_button.config(state='disabled')
                    progress.start(10)
                    status_label.config(text="Calibrating... Keep sensor still")
                    
                    # Send calibration command to ESP32
                    self.serial_port.write(b'CALIBRATE\n')
                    
                    # Wait for calibration confirmation
                    def check_calibration():
                        try:
                            if self.serial_port.in_waiting:
                                response = self.serial_port.readline().decode().strip()
                                if "Calibration complete" in response:
                                    progress.stop()
                                    status_label.config(text="Calibration successful!", foreground="green")
                                    self.status_label.config(text="Sensor calibrated", foreground="green")
                                    start_button.config(text="Done", command=cal_window.destroy)
                                    return
                            
                            # Check again after 100ms
                            cal_window.after(100, check_calibration)
                            
                        except Exception as e:
                            progress.stop()
                            status_label.config(text=f"Calibration failed: {str(e)}", foreground="red")
                            start_button.config(state='normal')
                    
                    check_calibration()
                    
                except Exception as e:
                    progress.stop()
                    status_label.config(text=f"Calibration failed: {str(e)}", foreground="red")
                    start_button.config(state='normal')
            
            # Add control buttons
            button_frame = ttk.Frame(cal_window)
            button_frame.pack(pady=20)
            
            start_button = ttk.Button(button_frame, text="Start Calibration", command=start_calibration)
            start_button.pack(side='left', padx=5)
            
            ttk.Button(button_frame, text="Cancel", command=cal_window.destroy).pack(side='left', padx=5)
            
            # Center the window on screen
            cal_window.update_idletasks()
            width = cal_window.winfo_width()
            height = cal_window.winfo_height()
            x = (cal_window.winfo_screenwidth() // 2) - (width // 2)
            y = (cal_window.winfo_screenheight() // 2) - (height // 2)
            cal_window.geometry(f'{width}x{height}+{x}+{y}')
            
            # Make window modal
            cal_window.grab_set()
            
        except Exception as e:
            messagebox.showerror("Calibration Error", f"Failed to start calibration: {str(e)}")

    def reset_plots(self):
        """
        Resets all plots and data storage to their initial state.
        This is useful when the plots become too crowded or when starting a new measurement session.
        """
        try:
            # Clear all stored data
            self.timestamps = []
            self.accel_data = {'x': [], 'y': [], 'z': []}
            self.gyro_data = {'x': [], 'y': [], 'z': []}
            self.orientation_data = {'roll': [], 'pitch': []}
            self.temp_data = []
            self.motion_data = []

            # Reset all plot lines
            for plot_group in self.plot_lines:
                for line in plot_group:
                    line.set_data([], [])

            # Reset plot scales
            for ax in self.axes:
                ax.relim()
                ax.autoscale_view()

            # Redraw the canvas
            self.canvas.draw()

            # Update status to confirm reset
            self.status_label.config(text="Plots reset successfully", foreground="green")
            
            # Reset all reading labels to zero
            for label_key in self.reading_labels:
                unit = self.reading_labels[label_key].cget("text").split()[-1]
                self.reading_labels[label_key].config(text=f"0.00 {unit}")

            # Reset motion indicator
            self.motion_indicator.config(
                text="No Motion Detected",
                foreground='black',
                background='#f0f0f0'
            )

        except Exception as e:
            self.status_label.config(text=f"Error resetting plots: {str(e)}", foreground="red")
            messagebox.showerror("Reset Error", f"Failed to reset plots: {str(e)}")

    def show_connection_settings(self):
        """
        Creates a window for managing serial connection settings.
        Allows users to select COM ports and configure connection parameters.
        """
        # Create settings window
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Connection Settings")
        settings_window.geometry("500x400")
        settings_window.transient(self.root)
        
        # Configure styles for the settings window
        settings_frame = ttk.LabelFrame(settings_window, text="Serial Connection Settings", padding=15)
        settings_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Create variables to store settings
        port_var = tk.StringVar(value='COM6')
        baud_var = tk.StringVar(value='115200')
        
        # Get available ports
        available_ports = []
        try:
            ports = serial.tools.list_ports.comports()
            available_ports = [port.device for port in ports]
        except Exception as e:
            messagebox.showwarning("Port Detection", f"Error detecting ports: {str(e)}")
        
        # Port selection section
        ttk.Label(settings_frame, text="Select COM Port:", style='Value.TLabel').pack(anchor='w', pady=5)
        port_frame = ttk.Frame(settings_frame)
        port_frame.pack(fill='x', pady=5)
        
        port_combobox = ttk.Combobox(port_frame, textvariable=port_var, values=available_ports)
        port_combobox.pack(side='left', padx=5)
        
        def refresh_ports():
            """Updates the list of available COM ports"""
            try:
                ports = serial.tools.list_ports.comports()
                available_ports = [port.device for port in ports]
                port_combobox['values'] = available_ports
                status_label.config(text="Ports refreshed successfully", foreground="green")
            except Exception as e:
                status_label.config(text=f"Error refreshing ports: {str(e)}", foreground="red")

        ttk.Button(port_frame, text="Refresh Ports", command=refresh_ports).pack(side='left', padx=5)

        # Baud rate selection
        ttk.Label(settings_frame, text="Baud Rate:", style='Value.TLabel').pack(anchor='w', pady=5)
        baud_rates = ['9600', '19200', '38400', '57600', '115200']
        ttk.Combobox(settings_frame, textvariable=baud_var, values=baud_rates).pack(fill='x', pady=5)

        # Connection status display
        status_frame = ttk.LabelFrame(settings_frame, text="Current Connection Status", padding=10)
        status_frame.pack(fill='x', pady=10)
        
        if hasattr(self, 'serial_port') and self.serial_port.is_open:
            current_status = f"Connected to {self.serial_port.port} at {self.serial_port.baudrate} baud"
            status_color = "green"
        else:
            current_status = "Not connected"
            status_color = "red"
        
        status_label = ttk.Label(status_frame, text=current_status, foreground=status_color)
        status_label.pack()

        def apply_settings():
            """Applies the new connection settings"""
            try:
                # Close existing connection if open
                if hasattr(self, 'serial_port') and self.serial_port.is_open:
                    self.serial_port.close()
                
                # Open new connection with selected settings
                self.serial_port = serial.Serial(
                    port=port_var.get(),
                    baudrate=int(baud_var.get()),
                    timeout=1,
                    write_timeout=1
                )
                
                # Update status displays
                status_label.config(
                    text=f"Connected to {self.serial_port.port} at {self.serial_port.baudrate} baud",
                    foreground="green"
                )
                self.status_label.config(text="Connection settings updated", foreground="green")
                
                # Wait for device initialization
                time.sleep(2)
                self.serial_port.flushInput()
                
                settings_window.after(1000, settings_window.destroy)
                
            except Exception as e:
                error_msg = f"Failed to apply settings: {str(e)}"
                status_label.config(text=error_msg, foreground="red")
                self.status_label.config(text=error_msg, foreground="red")
                messagebox.showerror("Connection Error", error_msg)

        # Create buttons frame
        button_frame = ttk.Frame(settings_frame)
        button_frame.pack(fill='x', pady=20)
        
        ttk.Button(button_frame, text="Apply Settings", command=apply_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side='left', padx=5)

        # Add help text
        help_text = """
        Connection Tips:
        • Make sure no other program is using the selected port
        • The default baud rate for the ESP32 is 115200
        • If connection fails, try refreshing the ports
        • Close any open Serial Monitor windows in Arduino IDE
        """
        help_label = ttk.Label(settings_frame, text=help_text, wraplength=400, justify='left')
        help_label.pack(pady=20)

        # Center window on screen
        settings_window.update_idletasks()
        width = settings_window.winfo_width()
        height = settings_window.winfo_height()
        x = (settings_window.winfo_screenwidth() // 2) - (width // 2)
        y = (settings_window.winfo_screenheight() // 2) - (height // 2)
        settings_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Make window modal
        settings_window.grab_set()

    def start_recording(self):
        """Start recording sensor data to file"""
        if not self.recording:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.data_file = open(f'mpu6050_data_{timestamp}.csv', 'w', newline='')
                self.csv_writer = csv.writer(self.data_file)
                self.csv_writer.writerow([
                    'Timestamp', 
                    'AccelX', 'AccelY', 'AccelZ',
                    'GyroX', 'GyroY', 'GyroZ',
                    'Roll', 'Pitch',
                    'Temperature', 'Motion'
                ])
                self.recording = True
                self.recording_label.config(text="Recording...", foreground="red")
            except Exception as e:
                messagebox.showerror("Error", f"Could not start recording: {e}")

    def stop_recording(self):
        """Stop recording sensor data"""
        if self.recording:
            self.recording = False
            self.data_file.close()
            self.recording_label.config(text="")

    def save_data_point(self, values):
        """Save a single data point to the recording file"""
        if self.recording:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            self.csv_writer.writerow([timestamp] + values)

    def cleanup_and_exit(self):
        """Clean up resources and exit application"""
        if self.recording:
            self.stop_recording()
        self.running = False
        if hasattr(self, 'data_thread'):
            self.data_thread.join(timeout=1)
        if hasattr(self, 'serial_port'):
            self.serial_port.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MPU6050Dashboard(root)
    root.protocol("WM_DELETE_WINDOW", app.cleanup_and_exit)
    root.mainloop()