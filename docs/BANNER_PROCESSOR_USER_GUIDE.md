# Banner Processor - User Guide

> **For technical details**, see [Banner Processor Technical Documentation](BANNER_PROCESSOR_TECHNICAL.md)

## Quick Start

The Banner Processor features intelligent person detection and an interactive crop preview system. You have two ways to use it:

### Method 1: Quick Auto-Process (No Preview)

Perfect when you trust the automatic detection:

1. Navigate to the **Banner Processor** page
2. Upload your images (drag & drop or click to select)
3. Adjust settings if needed:
   - Width/Height (default: 600×340 for email)
   - Crop Padding (default: 15%)
   - JPEG Quality (default: 82)
4. Click **"🚀 Process All Images"**
5. Download your ZIP file

### Method 2: Preview & Adjust (Recommended)

Perfect for important images where you want control:

1. Navigate to the **Banner Processor** page
2. Upload your images
3. Adjust settings (especially **Crop Padding** slider)
4. Click **"👁️ Preview & Adjust Crops"**
5. For each image:
   - Review the automatic crop suggestion
   - See how many people/faces were detected
   - Drag the crop box to adjust position
   - Resize the crop box if needed (maintains aspect ratio)
   - Click **"Accept Crop →"** to move to next image
   - Or click **"Skip"** to use automatic detection
6. After reviewing all images, processing starts automatically
7. Download your ZIP file

## How Detection Works

The system uses a three-tier fallback approach:

### 1. MediaPipe Person Detection (Best)
- Detects full bodies using 33 landmark points per person
- Identifies outstretched arms, legs, and body positions
- Works with up to 5 people per image
- **Best for**: Group photos, action shots, full-body images

### 2. Face Detection (Fallback)
- Uses OpenCV to detect faces
- Adds padding above heads
- **Best for**: Close-up portraits, headshots

### 3. Center Crop (Last Resort)
- Centers the crop region
- **Used when**: No people or faces detected

## Settings Explained

### Width & Height
- **Default**: 600×340 pixels (standard email banner)
- **Range**: 100-2000px width, 100-1000px height
- **Common sizes**:
  - Email headers: 600×340
  - Wide banners: 800×400
  - Square: 600×600

### Crop Padding
- **What it does**: Adds space around detected people
- **Default**: 15%
- **Range**: 0-30%
- **Use cases**:
  - **0-10%**: Tight crop, minimal background
  - **15-20%**: Balanced (recommended)
  - **25-30%**: Generous space, include more context

### JPEG Quality
- **Default**: 82
- **Range**: 1-100
- **Guidelines**:
  - **60-70**: Smaller files, slight quality loss
  - **80-85**: Good balance (recommended for email)
  - **90-100**: Maximum quality, larger files

### Include Retina
- **Default**: Enabled
- **What it does**: Creates 2× resolution version for high-DPI displays
- **Files generated**: 
  - Standard: 600×340
  - Retina: 1200×680

### Filename Prefix
- **Optional**: Add identifier to output filenames
- **Example**: "DFMC_2024" → `DFMC_2024_email_banner_600.jpg`

## Tips & Best Practices

### For Best Results

1. **Image Quality**
   - Use high-resolution source images (1920×1080 or better)
   - Avoid heavily compressed JPEGs
   - Well-lit photos work best

2. **Composition**
   - Center important subjects
   - Leave space above heads
   - Avoid cutting people at joints (knees, elbows)

3. **Settings**
   - Preview your first image to dial in padding
   - Use same settings for batch of similar photos
   - Increase padding for action shots (gestures, movement)

### Interactive Cropping Tips

1. **Drag to Move**: Click inside crop box to reposition
2. **Resize Handles**: Drag corners/edges to resize (maintains aspect ratio)
3. **Zoom**: Mouse wheel to zoom in/out for precision
4. **Compare**: Toggle detection info to see what was found

### Common Scenarios

#### Group Photos
- Use 20-30% padding to include everyone
- Preview to ensure no one gets cut off
- MediaPipe will detect all people

#### Action Shots (High-fives, Dancing)
- Increase padding to 25-30%
- MediaPipe detects extended limbs
- Preview to verify gesture is fully captured

#### Close-up Portraits
- 10-15% padding is sufficient
- Face detection handles these well
- Quick auto-process works great

#### Landscape/No People
- System will center crop automatically
- Preview to manually adjust composition
- Consider custom aspect ratio for scenery

## Output Files

### ZIP Contents

For a single image with retina enabled:
```
email_banner_600.jpg    (600×340)
email_banner_1200.jpg   (1200×680)
```

For multiple images with prefix "EVENT":
```
EVENT_email_banner1_600.jpg
EVENT_email_banner1_1200.jpg
EVENT_email_banner2_600.jpg
EVENT_email_banner2_1200.jpg
```

### File Sizes

Typical sizes at quality 82:
- **600×340**: 40-60 KB
- **1200×680**: 120-180 KB

Perfect for email - images load quickly without quality issues.

## Troubleshooting

### "No people detected" but there are people in the image
- Try increasing crop padding
- Manually adjust in preview mode
- System will fall back to center crop

### Faces are cut off
- Increase crop padding slider
- Use preview mode to manually adjust
- Face detection adds automatic head padding

### Crop is too tight/loose
- Adjust crop padding slider before preview
- Or manually adjust in preview mode
- Save settings for similar images

### Browser Performance
- Processing large batches may take time
- One preview at a time for responsiveness
- Consider processing in smaller batches

## Keyboard Shortcuts (Future)

Coming soon:
- `Enter`: Accept current crop
- `Space`: Skip to next
- `←/→`: Navigate between images
- `+/-`: Adjust padding

## Examples

### Example 1: Golf Course Photo
**Scenario**: Two people shaking hands over golf cart

**Settings**:
- Width: 600, Height: 340
- Padding: 20%
- Auto-detection finds both people
- Result: Both people fully visible with golf cart context

### Example 2: Event Headshot
**Scenario**: Single person, professional photo

**Settings**:
- Width: 600, Height: 340
- Padding: 15%
- Face detection finds person
- Result: Centered headshot with appropriate space

### Example 3: Team Photo
**Scenario**: 5 people in a row

**Settings**:
- Width: 800, Height: 400 (wider for group)
- Padding: 25%
- MediaPipe detects all 5 people
- Result: Everyone visible with breathing room

## Support

For issues or questions:
1. Check detection info in preview mode
2. Try adjusting crop padding
3. Use manual adjustment in preview
4. Review this guide for tips

The Banner Processor is designed to handle 95% of use cases automatically, with manual controls available when you need them.
