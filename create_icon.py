from PIL import Image
import os

def create_icon():
    # Create a new image with a red square
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    
    # Draw a red square with black border
    for x in range(size):
        for y in range(size):
            # Calculate distance from center
            center_x, center_y = size/2, size/2
            dx = (x - center_x) / (size/2)
            dy = (y - center_y) / (size/2)
            distance = (dx*dx + dy*dy) ** 0.5
            
            # Draw circle
            if distance < 0.8:
                img.putpixel((x, y), (255, 0, 0, 255))  # Red fill
            elif distance < 0.85:
                img.putpixel((x, y), (0, 0, 0, 255))    # Black border

    # Save as ICO
    icon_path = os.path.join('resources', 'icon.ico')
    img.save(icon_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
    print(f"Icon created at {icon_path}")

if __name__ == '__main__':
    create_icon()