import tkinter as tk
from tkinter import ttk, scrolledtext
from scapy.all import sniff, IP, TCP, UDP, conf
from scapy.arch import get_windows_if_list
import anthropic
import json
from datetime import datetime
import logging
import threading
import os
from typing import Optional, Dict, Any
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import collections

class PacketAnalyzer:
    def __init__(self):
        # Initialize data structures for both packet storage and visualization
        self.packets = []  # Store all captured packets
        self.packet_times = collections.deque(maxlen=100)  # Rolling window of packet timestamps
        self.packet_sizes = collections.deque(maxlen=100)  # Rolling window of packet sizes
        self.protocol_counts = {'TCP': 0, 'UDP': 0, 'Other': 0}  # Track protocol distribution
        self.capturing = False  # Flag to control packet capture state
        
        # Configure logging for debugging and error tracking
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize connection to Claude's AI analysis capabilities
        api_key = os.getenv('ANTHROPIC_API_KEY', 'your-api-key-here')
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Set up the graphical interface
        self.setup_gui()

    def setup_gui(self):
        # Create and configure main window
        self.root = tk.Tk()
        self.root.title("Network Packet Analyzer")
        self.root.geometry("1400x900")

        # Create main layout frames
        left_pane = ttk.Frame(self.root)
        left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_pane = ttk.Frame(self.root)
        right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Build left pane components
        self.create_options_frame(left_pane)
        self.create_packet_list_frame(left_pane)
        self.create_control_buttons(left_pane)
        self.create_analysis_frame(left_pane)
        
        # Build right pane components
        self.setup_visualization(right_pane)

    def create_options_frame(self, parent):
        # Create capture options panel
        options_frame = ttk.LabelFrame(parent, text="Capture Options")
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        # Network interface selection
        ttk.Label(options_frame, text="Network Interface:").pack(side=tk.LEFT, padx=5)
        self.iface_var = tk.StringVar()
        iface_combo = ttk.Combobox(options_frame, textvariable=self.iface_var, width=30)
        iface_combo['values'] = self.get_interfaces()
        iface_combo.pack(side=tk.LEFT, padx=5)
        iface_combo.set("Default")

        # Packet filter input
        ttk.Label(options_frame, text="Capture Filter:").pack(side=tk.LEFT, padx=5)
        self.filter_var = tk.StringVar(value="ip")
        filter_entry = ttk.Entry(options_frame, textvariable=self.filter_var, width=30)
        filter_entry.pack(side=tk.LEFT, padx=5)

    def create_packet_list_frame(self, parent):
        # Create packet display area
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure packet list columns
        columns = ("Time", "Source", "Destination", "Protocol", "Length", "Info")
        self.packet_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # Set up column headings
        for col in columns:
            self.packet_tree.heading(col, text=col)
            self.packet_tree.column(col, width=100)

        # Add scrollbar
        y_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, 
                                  command=self.packet_tree.yview)
        self.packet_tree.configure(yscrollcommand=y_scrollbar.set)
        
        # Position components
        self.packet_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_control_buttons(self, parent):
        # Create control button panel
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        # Configure button styles
        style = ttk.Style()
        style.configure("Start.TButton", foreground="green")
        style.configure("Stop.TButton", foreground="red")
        
        # Create control buttons
        ttk.Button(btn_frame, text="Start Capture", style="Start.TButton",
                  command=self.start_capture).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Stop Capture", style="Stop.TButton",
                  command=self.stop_capture).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Analyze Selected",
                  command=self.analyze_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear",
                  command=self.clear_display).pack(side=tk.LEFT, padx=5)

    def create_analysis_frame(self, parent):
        # Create analysis results display area
        analysis_frame = ttk.LabelFrame(parent, text="Analysis Results")
        analysis_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.analysis_text = scrolledtext.ScrolledText(analysis_frame, height=10)
        self.analysis_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_visualization(self, parent):
        # Create visualization panel
        viz_frame = ttk.LabelFrame(parent, text="Traffic Visualization")
        viz_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create matplotlib figure and subplots
        self.figure = Figure(figsize=(6, 8))
        self.ax1 = self.figure.add_subplot(211)  # Packet volume plot
        self.ax2 = self.figure.add_subplot(212)  # Protocol distribution plot
        
        # Configure initial plot settings
        self.ax1.set_title('Packet Volume Over Time')
        self.ax1.set_xlabel('Packets')
        self.ax1.set_ylabel('Size (bytes)')
        self.ax2.set_title('Protocol Distribution')
        
        # Create canvas and embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.figure, viz_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Start visualization updates
        self.update_visualization()

    def get_interfaces(self) -> list:
        # Get list of available network interfaces
        try:
            interfaces = get_windows_if_list()
            return ["Default"] + [iface['name'] for iface in interfaces]
        except Exception as e:
            self.logger.error(f"Failed to get interfaces: {e}")
            return ["Default"]

    def packet_callback(self, packet):
        # Process each captured packet
        if IP in packet:
            # Extract packet information
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            src = packet[IP].src
            dst = packet[IP].dst
            proto = "TCP" if TCP in packet else "UDP" if UDP in packet else "Other"
            length = len(packet)
            info = self.get_packet_info(packet)

            # Update data structures
            packet_info = (timestamp, src, dst, proto, length, info)
            self.packets.append(packet)
            self.packet_sizes.append(length)
            self.protocol_counts[proto] += 1
            
            # Update GUI safely from capture thread
            self.root.after(0, lambda: self.packet_tree.insert("", "end", 
                                                             values=packet_info))

    def get_packet_info(self, packet) -> str:
        # Extract detailed packet information
        info = []
        if TCP in packet:
            info.extend([
                f"Port: {packet[TCP].sport} → {packet[TCP].dport}",
                f"Flags: {packet[TCP].flags}"
            ])
        elif UDP in packet:
            info.extend([
                f"Port: {packet[UDP].sport} → {packet[UDP].dport}"
            ])
        return " | ".join(info)

    def start_capture(self):
        # Begin packet capture in separate thread
        if not self.capturing:
            self.capturing = True
            self.capture_thread = threading.Thread(target=self.capture_packets)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            self.analysis_text.insert(tk.END, "Packet capture started...\n")

    def capture_packets(self):
        # Perform packet capture with error handling
        try:
            interface = self.iface_var.get()
            filter_str = self.filter_var.get()
            
            capture_kwargs = {
                'prn': self.packet_callback,
                'store': False,
                'filter': filter_str
            }
            
            if interface != "Default":
                capture_kwargs['iface'] = interface

            sniff(**capture_kwargs)
        except Exception as e:
            self.logger.error(f"Capture error: {e}")
            self.root.after(0, lambda: self.show_error(str(e)))
            self.capturing = False

    def stop_capture(self):
        # Stop packet capture
        self.capturing = False
        self.analysis_text.insert(tk.END, "Packet capture stopped.\n")

    def clear_display(self):
        # Clear all displayed data
        self.packet_tree.delete(*self.packet_tree.get_children())
        self.analysis_text.delete(1.0, tk.END)
        self.packets = []
        self.packet_sizes.clear()
        self.protocol_counts = {'TCP': 0, 'UDP': 0, 'Other': 0}

    def update_visualization(self):
        # Update visualization graphs
        try:
            # Update packet volume graph
            self.ax1.clear()
            if len(self.packet_sizes) > 0:
                self.ax1.plot(range(len(self.packet_sizes)), 
                            list(self.packet_sizes), 'b-')
                self.ax1.set_title('Packet Volume Over Time')
                self.ax1.set_xlabel('Packets')
                self.ax1.set_ylabel('Size (bytes)')
            
            # Update protocol distribution
            self.ax2.clear()
            if sum(self.protocol_counts.values()) > 0:
                labels = self.protocol_counts.keys()
                sizes = self.protocol_counts.values()
                self.ax2.pie(sizes, labels=labels, autopct='%1.1f%%')
                self.ax2.set_title('Protocol Distribution')
            
            # Adjust layout and redraw
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            self.logger.error(f"Visualization update error: {e}")
        
        # Schedule next update if capturing
        if self.capturing:
            self.root.after(1000, self.update_visualization)

    def analyze_selected(self):
        # Analyze selected packet using Claude AI
        selected_item = self.packet_tree.selection()
        if not selected_item:
            self.show_error("Please select a packet to analyze")
            return

        index = self.packet_tree.index(selected_item)
        packet = self.packets[index]

        # Convert packet to analyzable format
        packet_dict = self.packet_to_dict(packet)
        
        # Create analysis prompt
        prompt = f"""Analyze this network packet for potential security concerns:
{json.dumps(packet_dict, indent=2)}

Please provide:
1. A security assessment
2. Any suspicious patterns or anomalies
3. Recommended actions if concerns are found"""

        # Get analysis from Claude
        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            analysis = message.content[0].text
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(tk.END, analysis)
            
        except Exception as e:
            self.show_error(f"Analysis error: {str(e)}")

    def packet_to_dict(self, packet) -> Dict[str, Any]:
        # Convert packet to dictionary format
        packet_dict = {
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "source_ip": packet[IP].src if IP in packet else None,
            "dest_ip": packet[IP].dst if IP in packet else None,
            "protocol": "TCP" if TCP in packet else "UDP" if UDP in packet else "Other",
            "length": len(packet),
        }

        if TCP in packet:
            packet_dict.update({
                "source_port": packet[TCP].sport,
                "dest_port": packet[TCP].dport,
                "tcp_flags": {
                    "SYN": packet[TCP].flags.S,
                    "ACK": packet[TCP].flags.A,
                    "FIN": packet[TCP].flags.F,
                    "RST": packet[TCP].flags.R,
                }
            })
        elif UDP in packet:
            packet_dict.update({
                "source_port": packet[UDP].sport,
                "dest_port": packet[UDP].dport,
            })

        return packet_dict

    def show_error(self, message: str):
        # Display error messages to user
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, f"Error: {message}\n")

    def run(self):
        # Start the application
        self.root.mainloop()

if __name__ == "__main__":
    analyzer = PacketAnalyzer()
    analyzer.run()