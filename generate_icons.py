"""
Generate all PWA icons for Patcus Ventures
Run: python generate_icons.py
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Create static folder if it doesn't exist
os.makedirs('static', exist_ok=True)

# Icon sizes needed
sizes = [72, 96, 128, 144, 152, 192, 384, 512]

def create_icon(size):
    # Create image with dark green background
    img = Image.new('RGB', (size, size), color='#0f2b22')
    draw = ImageDraw.Draw(img)
    
    # Draw gold border
    border_width = max(2, size // 50)
    for i in range(border_width):
        draw.rectangle([i, i, size-1-i, size-1-i], outline='#f9b81b')
    
    # Draw "P" in center
    try:
        font_size = size // 2
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Calculate text position to center it
    draw.text((size//2 - size//6, size//2 - size//6), "P", fill='#f9b81b', font=font)
    
    # Save icon
    img.save(f'static/icon-{size}.png')
    print(f"✅ Created static/icon-{size}.png")

# Generate all icons
print("🎨 Generating PWA icons...")
for size in sizes:
    create_icon(size)

print("\n✅ All icons created successfully in 'static' folder!")
print("\n📱 You can now run: python app.py")