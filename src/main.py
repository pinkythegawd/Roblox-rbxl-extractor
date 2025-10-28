import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os

# Add the src directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from rbxl_extractor.extractor import RobloxExtractor
except ImportError as e:
    print(f"Error importing RobloxExtractor: {e}")
    sys.exit(1)

class RobloxExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox RBXL Asset Extractor")
        self.root.geometry("600x400")
        
        # Input file selection
        self.input_frame = ttk.LabelFrame(root, text="Input", padding="5")
        self.input_frame.pack(fill="x", padx=5, pady=5)
        
        self.file_path = tk.StringVar()
        self.file_entry = ttk.Entry(self.input_frame, textvariable=self.file_path, width=50)
        self.file_entry.pack(side="left", padx=5)
        
        self.browse_button = ttk.Button(self.input_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side="left", padx=5)
        
        # Asset selection
        self.assets_frame = ttk.LabelFrame(root, text="Assets to Extract", padding="5")
        self.assets_frame.pack(fill="x", padx=5, pady=5)
        
        self.model_var = tk.BooleanVar(value=True)
        self.script_var = tk.BooleanVar(value=True)
        self.sound_var = tk.BooleanVar(value=True)
        self.image_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(self.assets_frame, text="Models", variable=self.model_var).pack(anchor="w")
        ttk.Checkbutton(self.assets_frame, text="Scripts", variable=self.script_var).pack(anchor="w")
        ttk.Checkbutton(self.assets_frame, text="Sounds", variable=self.sound_var).pack(anchor="w")
        ttk.Checkbutton(self.assets_frame, text="Images", variable=self.image_var).pack(anchor="w")
        
        # Output directory selection
        self.output_frame = ttk.LabelFrame(root, text="Output", padding="5")
        self.output_frame.pack(fill="x", padx=5, pady=5)
        
        self.output_path = tk.StringVar()
        self.output_entry = ttk.Entry(self.output_frame, textvariable=self.output_path, width=50)
        self.output_entry.pack(side="left", padx=5)
        
        self.output_button = ttk.Button(self.output_frame, text="Browse", command=self.browse_output)
        self.output_button.pack(side="left", padx=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(root, variable=self.progress_var, maximum=100)
        self.progress.pack(fill="x", padx=5, pady=5)
        
        # Extract button
        self.extract_button = ttk.Button(root, text="Extract Assets", command=self.extract_assets)
        self.extract_button.pack(pady=10)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(root, textvariable=self.status_var)
        self.status_label.pack(pady=5)
        
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Roblox Place File",
            filetypes=[("Roblox Place File", "*.rbxl")]
        )
        if filename:
            self.file_path.set(filename)
            
    def browse_output(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_path.set(directory)
            
    def extract_assets(self):
        if not self.file_path.get():
            messagebox.showerror("Error", "Please select a .rbxl file")
            return
            
        if not self.output_path.get():
            messagebox.showerror("Error", "Please select an output directory")
            return
            
        try:
            extractor = RobloxExtractor(
                self.file_path.get(),
                self.output_path.get(),
                self.progress_var,
                self.status_var
            )
            
            options = {
                "models": self.model_var.get(),
                "scripts": self.script_var.get(),
                "sounds": self.sound_var.get(),
                "images": self.image_var.get()
            }
            
            extractor.extract(options)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))

def main():
    try:
        print("Starting application...")
        root = tk.Tk()
        print("Created Tk root window")
        app = RobloxExtractorGUI(root)
        print("Created GUI application")
        root.mainloop()
    except Exception as e:
        print(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main()