"""
Quick script to convert an image to base64 for testing
Usage: python test_image_encode.py path/to/image.jpg
"""
import base64
import sys

if len(sys.argv) < 2:
    print("Usage: python test_image_encode.py path/to/image.jpg")
    sys.exit(1)

image_path = sys.argv[1]

with open(image_path, "rb") as img_file:
    b64_string = base64.b64encode(img_file.read()).decode()
    
# Save to file
with open("valid_base64.txt", "w") as f:
    f.write(b64_string)

print(f"✓ Encoded {image_path}")
print(f"✓ Saved to valid_base64.txt")
print(f"✓ Length: {len(b64_string)} characters")
print(f"✓ First 50 chars: {b64_string[:50]}")
