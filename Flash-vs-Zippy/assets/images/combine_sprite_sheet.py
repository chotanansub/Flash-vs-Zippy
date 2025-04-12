from PIL import Image
import os

# Base path (directory where this script is located)
base_path = os.path.dirname(os.path.abspath(__file__))

# Base animation folder
animation_base_folder = os.path.join(base_path, "flash")
output_path = os.path.join(base_path, "flash.png")

# Define the desired animation folder stacking order
animation_order = ["idle", "run", "jump",'attack1','attack2','take_hit','dead']  # Change as needed

# Load all animations
animation_images = []
max_frame_count = 0

for anim in animation_order:
    folder_path = os.path.join(animation_base_folder, anim)
    image_files = sorted([f for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg'))])
    images = [Image.open(os.path.join(folder_path, f)) for f in image_files]
    animation_images.append(images)
    max_frame_count = max(max_frame_count, len(images))

# Assume all frames are same size
frame_width, frame_height = animation_images[0][0].size

# Determine sprite sheet size
sheet_width = max(len(anim) for anim in animation_images) * frame_width
sheet_height = len(animation_images) * frame_height

# Create the sprite sheet
sprite_sheet = Image.new("RGBA", (sheet_width, sheet_height))

# Paste each animation row by row
for row, anim_frames in enumerate(animation_images):
    for col, img in enumerate(anim_frames):
        x = col * frame_width
        y = row * frame_height
        sprite_sheet.paste(img, (x, y))

# Save the result
sprite_sheet.save(output_path)
print(f"Saved sprite sheet as {output_path}")
