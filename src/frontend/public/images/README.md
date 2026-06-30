# Images for NutriGain

Add your images to this folder.

## Folder Structure

- `plate.svg` - Currently a placeholder SVG (generated dynamically)
- `plate.png` or `plate.jpg` - Add your custom image here (optional replacement)

## Required Images

### plate.svg / plate.png / plate.jpg
- **Purpose**: Visual for login page right side
- **Recommended size**: 520px x 520px or higher
- **Format**: SVG, PNG, or JPG
- **Description**: The yellow circular plate graphic with nutrition indicators
- **Used in**: LoginView.jsx
- **Current**: SVG placeholder is active

### (Optional) salad.jpg
- **Purpose**: Hero image for nutrition section
- **File**: Not currently used, but can be added
- **Note**: Reserved for future use in DashboardView

## How to Replace with Your Images

### Option 1: Replace the SVG (Recommended for quality)
1. Save your plate image as `plate.png` or `plate.jpg` in this folder
2. Update `LoginView.jsx` line 11 to:
   ```jsx
   src="/images/plate.png"  // or plate.jpg
   ```
3. Rebuild: `docker compose up -d --build frontend`

### Option 2: Edit the SVG directly
- Edit `plate.svg` with your design tool
- Save and it will automatically update on refresh

## Image Format Tips

- **SVG**: Vector graphic (current format) - scales perfectly, smaller file
- **PNG**: Raster with transparency - good for graphics with transparency
- **JPG**: Raster compressed - best for photos

## Testing

After updating images:
1. Clear browser cache (Ctrl+Shift+Delete)
2. Rebuild frontend: `docker compose up -d --build frontend`
3. Visit http://localhost:5173 to see changes

## Current Status

✓ Placeholder SVG created and working
✓ Image folder structure ready
- Ready to accept your custom images

Next step: Add your images to this folder and update file references!

