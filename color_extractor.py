from PIL import Image
import os
from collections import Counter

def get_dominant_color(image_path):
    try:
        img = Image.open(image_path)
        img = img.resize((100, 100))  # Resize to speed up processing
        pixels = list(img.getdata())
        # Filter out white/near-white pixels if desired, but for a banner we probably want the main brand color.
        # Let's just get the most common color.
        
        # Remove transparent pixels if any
        if img.mode == 'RGBA':
            pixels = [p[:3] for p in pixels if p[3] > 0]
            
        counts = Counter(pixels)
        most_common = counts.most_common(1)[0][0]
        return most_common
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    path = "static/img/banner.jpg"
    if os.path.exists(path):
        color = get_dominant_color(path)
        print(f"Dominant Color: {color}")
        # Convert to hex
        if color:
            hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
            print(f"Hex Color: {hex_color}")
    else:
        print(f"File not found: {path}")
