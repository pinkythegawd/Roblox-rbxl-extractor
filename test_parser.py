"""
Test harness for binary RBXL parser.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from rbxl_extractor.rbx_binary_parser import parse
from rbxl_extractor.binary_extractor import extract_from_bytes

def test_parse_rbxl(file_path: str) -> None:
    """Test parsing a binary RBXL file."""
    print(f"\nTesting binary RBXL parser with: {file_path}")
    print("-" * 80)
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return
        
    try:
        # Read binary data
        with open(file_path, 'rb') as f:
            data = f.read()
            
        print(f"File size: {len(data):,} bytes")
        print(f"First 32 bytes: {data[:32]!r}")
        
        # Try full binary parser
        print("\nAttempting full binary parse...")
        result = parse(data)
        
        # Print summary of what was found
        print("\nParse results:")
        print(f"- Type: {result['type']}")
        print(f"- Version: {result['version']}")
        print(f"- Compressed: {result['compressed']}")
        print(f"- Number of instances: {len(result['instances'])}")
        
        # Print first few instances
        print("\nFirst 5 instances:")
        for i, (ref, inst) in enumerate(result['instances'].items()):
            if i >= 5:
                break
            print(f"\n[Instance {i+1}]")
            print(f"Class: {inst.class_name}")
            print(f"Referent: {inst.referent}")
            print(f"Properties: {len(inst.properties)} properties")
            print(f"Children: {len(inst.children)} children")
            if inst.properties:
                print("Sample properties:")
                for name, value in list(inst.properties.items())[:3]:
                    print(f"  {name}: {value[:100] if isinstance(value, str) else value}")
                    
    except Exception as e:
        print(f"\nFull parser error: {e}")
        print("\nTrying heuristic extractor as fallback...")
        
        # Create a temp output dir
        out_dir = os.path.join(os.path.dirname(file_path), "test_output")
        os.makedirs(out_dir, exist_ok=True)
        
        try:
            options = {
                'scripts': True,
                'models': True,
                'sounds': True,
                'images': True
            }
            results = extract_from_bytes(data, out_dir, options)
            
            print("\nHeuristic extraction results:")
            for k, v in results.items():
                if v:
                    print(f"\n{k.title()}:")
                    for path in v[:5]:  # Show first 5 of each type
                        print(f"- {os.path.basename(path)}")
                    if len(v) > 5:
                        print(f"  ... and {len(v)-5} more")
                        
        except Exception as e2:
            print(f"\nHeuristic extractor error: {e2}")
            
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python test_parser.py <rbxl_file>")
        sys.exit(1)
        
    test_parse_rbxl(sys.argv[1])