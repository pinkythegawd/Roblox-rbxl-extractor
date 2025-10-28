import argparse
import os
from .binary_extractor import extract_from_binary

def main():
    parser = argparse.ArgumentParser(description='Extract assets from Roblox .rbxl files')
    parser.add_argument('input_file', help='Input .rbxl file path')
    parser.add_argument('--out-dir', help='Output directory (default: same as input file)', default=None)
    parser.add_argument('--scripts', help='Extract Lua scripts', action='store_true')
    parser.add_argument('--sounds', help='Extract sound files', action='store_true')
    parser.add_argument('--images', help='Extract image files', action='store_true')
    parser.add_argument('--all', help='Extract all assets', action='store_true')
    
    args = parser.parse_args()
    
    # If no specific assets are requested, extract all
    if not (args.scripts or args.sounds or args.images):
        args.all = True
    
    # Set up extraction options
    options = {
        'scripts': args.scripts or args.all,
        'sounds': args.sounds or args.all,
        'images': args.images or args.all,
    }
    
    # Use input file's directory as default output directory
    if args.out_dir is None:
        args.out_dir = os.path.dirname(os.path.abspath(args.input_file))
    
    # Perform extraction
    result = extract_from_binary(args.input_file, args.out_dir, options)
    
    # Print results
    print('\nExtraction complete:')
    if options['scripts']:
        print(f'- {len(result["scripts"])} Lua scripts extracted')
    if options['sounds']:
        print(f'- {len(result["sounds"])} sound files found')
        print(f'- {len(result["sound_refs"])} sound references extracted')
    if options['images']:
        print(f'- {len(result["images"])} images extracted')
        print(f'- {len(result["image_refs"])} image references extracted')

if __name__ == '__main__':
    main()