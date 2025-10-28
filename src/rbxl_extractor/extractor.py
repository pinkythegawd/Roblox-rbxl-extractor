import os
import json
from typing import Dict, Any, List, Optional, Any, Union
import xml.etree.ElementTree as ET
import base64
import gzip
import io
import shutil
import zlib

class RobloxExtractor:
    def __init__(self, file_path: str, output_path: str, progress_var: Optional[Any] = None, status_var: Optional[Any] = None):
        """Initialize the RobloxExtractor.
        
        Args:
            file_path: Path to the .rbxl file to extract
            output_path: Directory where extracted assets will be saved
            progress_var: Optional variable for progress updates (0-100)
            status_var: Optional variable for status message updates
        """
        self.file_path = file_path
        self.output_path = output_path
        self.progress_var = progress_var
        self.status_var = status_var
        
    def update_progress(self, value: float, status: Optional[str] = None) -> None:
        """Update the progress bar and status message.
        
        Args:
            value: Progress value between 0 and 100
            status: Optional status message to display
        """
        if self.progress_var:
            self.progress_var.set(value)
        if status and self.status_var:
            self.status_var.set(status)
            print(status)  # Also print to console for debugging
            
    def extract_content(self, xml_root: ET.Element, content_type: str, output_dir: str) -> List[str]:
        """Extract specific content from XML elements.
        
        Args:
            xml_root: Root XML element
            content_type: Type of content to extract ("scripts", "models", "sounds", "images")
            output_dir: Directory where to save extracted content
            
        Returns:
            List of paths to extracted files
        """
        items = []
        
        # Define what to look for based on content type
        if content_type == "scripts":
            elements = xml_root.findall(".//Script") + xml_root.findall(".//LocalScript")
            ext = ".lua"
        elif content_type == "models":
            elements = xml_root.findall(".//Model") + xml_root.findall(".//Part")
            ext = ".model"
        elif content_type == "sounds":
            elements = xml_root.findall(".//Sound")
            ext = ".rbxm"
        elif content_type == "images":
            elements = xml_root.findall(".//Decal") + xml_root.findall(".//Texture")
            ext = ".png"
        else:
            elements = []
            
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Process each element
        for i, elem in enumerate(elements):
            try:
                name = elem.get("Name", "")
                if not name:
                    name = f"{elem.tag}_{i}"
                    
                if content_type == "scripts":
                    # Find the Source property
                    source = elem.find(".//ProtectedString[@name='Source']")
                    if source is not None and source.text:
                        content = source.text
                    else:
                        content = ""
                        
                elif content_type == "models":
                    # Save model element as XML
                    content = ET.tostring(elem, encoding="unicode", method="xml")
                    
                elif content_type == "sounds":
                    # Save sound reference
                    content = elem.get("SoundId", "")
                    
                elif content_type == "images":
                    # Save texture/decal reference
                    content = elem.get("TextureId", "") or elem.get("Texture", "")
                    
                else:
                    content = ""
                    
                # Save to file if we have content
                if content:
                    safe_name = "".join(c if c.isalnum() or c in ".-_ " else "_" for c in name)
                    file_path = os.path.join(output_dir, f"{safe_name}{ext}")
                    
                    # Handle duplicate names
                    base_path = file_path
                    counter = 1
                    while os.path.exists(file_path):
                        file_path = base_path[:-len(ext)] + f"_{counter}" + ext
                        counter += 1
                    
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    items.append(file_path)
                    print(f"Extracted: {os.path.basename(file_path)}")
                    
            except Exception as e:
                print(f"Error extracting {content_type} item {i}: {e}")
                
        if items:
            print(f"\nExtracted {len(items)} {content_type}")
        else:
            print(f"\nNo {content_type} found to extract")
            
        return items
            
    def extract(self, options: Dict[str, bool]) -> None:
        """Extract assets from the RBXL file.
        
        Args:
            options: Dictionary of what to extract (scripts, models, sounds, images)
        """
        try:
            self.update_progress(0, "Reading RBXL file...")
            
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"RBXL file not found: {self.file_path}")
                
            # Create base output directory
            os.makedirs(self.output_path, exist_ok=True)
            
            # Read raw bytes first and attempt multiple decode strategies
            with open(self.file_path, 'rb') as f:
                data = f.read()

            # Helpful debug header (first 12 bytes)
            header = data[:12]
            print(f"File header (first 12 bytes): {header!r}")

            xml_content = None

            # 1) If it's a gzip stream (standard gzip magic bytes), decompress
            try:
                if data.startswith(b"\x1f\x8b"):
                    self.update_progress(10, "Detected gzip-compressed RBXL, decompressing...")
                    xml_content = gzip.decompress(data).decode('utf-8')
                    print("Successfully decompressed gzip RBXL")
            except Exception as e:
                print(f"Gzip decompress attempt failed: {e}")

            # 2) If not gzip or that failed, try plain UTF-8 decode
            if xml_content is None:
                try:
                    self.update_progress(15, "Attempting to decode as UTF-8 XML...")
                    xml_content = data.decode('utf-8')
                    print("Successfully decoded as UTF-8 XML")
                except UnicodeDecodeError as e:
                    print(f"UTF-8 decode failed: {e}")

            # 3) Try zlib raw/deflate (some RBX variants use deflate without gzip wrapper)
            if xml_content is None:
                try:
                    self.update_progress(20, "Attempting raw zlib/deflate decompression...")
                    decompressed = zlib.decompress(data)
                    xml_content = decompressed.decode('utf-8')
                    print("Successfully decompressed raw deflate RBXL")
                except Exception as e:
                    print(f"Raw zlib decompress failed: {e}")

            # 4) If none of the above worked, try binary parsing
            if xml_content is None:
                try:
                    from . import rbx_binary_parser
                    self.update_progress(25, "Attempting binary RBXL parsing...")
                    
                    try:
                        # Try full binary parser first
                        result = rbx_binary_parser.parse(data)
                        self.update_progress(50, "Successfully parsed binary RBXL format")
                        
                        # Convert to XML-like structure
                        xml_content = self._binary_to_xml(result)
                        print("Converted binary structure to XML format")
                        
                    except Exception as e:
                        print(f"Full binary parser failed: {e}")
                        print("Falling back to heuristic extraction...")
                        
                        # Fall back to heuristic extraction
                        from . import binary_extractor
                        bin_result = binary_extractor.extract_from_bytes(data, self.output_path, options)
                        
                        # Report results
                        total_found = sum(len(v) for v in bin_result.values())
                        self.update_progress(100, f"Binary heuristic extraction finished — {total_found} items written")
                        print("\nBinary extraction results:")
                        for k, v in bin_result.items():
                            print(f"  {k}: {len(v)} files")
                        return
                        
                except ImportError as e:
                    # If imports fail (shouldn't happen), raise helpful error
                    msg = (
                        "The RBXL file appears to be in Roblox's binary format.\n"
                        "Binary parsing support is not available (import failed).\n"
                        f"Error: {e}"
                    )
                    raise ValueError(msg)
                    
    def _binary_to_xml(self, binary_result: Dict[str, Any]) -> str:
        """Convert binary parser result to XML format."""
        def instance_to_xml(inst, depth=0):
            indent = "  " * depth
            props = []
            for name, value in inst.properties.items():
                if isinstance(value, str):
                    if name == "Source":
                        props.append(f'{indent}  <ProtectedString name="{name}">{value}</ProtectedString>')
                    else:
                        props.append(f'{indent}  <string name="{name}">{value}</string>')
                # Add more property types as needed
            
            children = [instance_to_xml(child, depth + 1) for child in inst.children]
            
            return (
                f'{indent}<Item class="{inst.class_name}" referent="{inst.referent}">\n'
                f'{indent}  <Properties>\n' +
                "\n".join(props) + f'\n{indent}  </Properties>\n' +
                "\n".join(children) +
                f'{indent}</Item>'
            )
        
        # Start with root instance if available, otherwise all instances
        if binary_result["root"]:
            content = instance_to_xml(binary_result["root"])
        else:
            content = "\n".join(
                instance_to_xml(inst) 
                for inst in binary_result["instances"].values()
            )
            
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime">\n' +
            content +
            '\n</roblox>'
        )
                    
            # Parse the XML
            self.update_progress(30, "Parsing file structure...")
            try:
                root = ET.fromstring(xml_content)
                print("Successfully parsed XML structure")
            except ET.ParseError as e:
                raise ValueError(f"Failed to parse RBXL file: {e}")
                
            # Extract requested content types
            if options.get('scripts', False):
                self.update_progress(50, "Extracting scripts...")
                scripts_dir = os.path.join(self.output_path, "Scripts")
                self.extract_content(root, "scripts", scripts_dir)
                
            if options.get('models', False):
                self.update_progress(60, "Extracting models...")
                models_dir = os.path.join(self.output_path, "Models")
                self.extract_content(root, "models", models_dir)
                
            if options.get('sounds', False):
                self.update_progress(70, "Extracting sounds...")
                sounds_dir = os.path.join(self.output_path, "Sounds")
                self.extract_content(root, "sounds", sounds_dir)
                
            if options.get('images', False):
                self.update_progress(80, "Extracting images...")
                images_dir = os.path.join(self.output_path, "Images")
                self.extract_content(root, "images", images_dir)
                
            self.update_progress(100, "Extraction complete!")
            
        except Exception as e:
            self.update_progress(0, f"Error: {str(e)}")
            raise