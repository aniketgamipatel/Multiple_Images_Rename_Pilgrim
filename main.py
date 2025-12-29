import os
import re
import shutil
import pytesseract
from PIL import Image

# ---------------- CONFIG ----------------
INPUT_FOLDER = "C:/Users/vadia/OneDrive/Documents/Desktop/Images_rename/Before_Rename"
OUTPUT_FOLDER = "C:/Users/vadia/OneDrive/Documents/Desktop/Images_rename/After_Rename"
VALID_EXTENSIONS = (".png", ".jpg", ".jpeg")

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def clean_text(text):
    """Clean and sanitize text for use as filename."""
    text = text.strip().replace("\n", " ")
    # Replace invalid filename characters with underscore
    text = re.sub(r"[^a-zA-Z0-9_&-]", "_", text)
    # Remove multiple consecutive underscores
    text = re.sub(r"_+", "_", text)
    # Remove leading/trailing underscores
    text = text.strip("_")
    return text[:80]  # Limit length for filename compatibility


def extract_product_name(text):
    """
    Extract product name from OCR text.
    Uses multiple strategies to find the most likely product name.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Strategy 1: Look for lines with product keywords
    product_keywords = ['oil', 'serum', 'cream', 'foundation', 'lotion', 'gel', 
                       'moisturizer', 'cleanser', 'toner', 'essence', 'mask',
                       'balm', 'primer', 'powder', 'lipstick', 'mascara']
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        # Check if line contains product keywords
        if any(keyword in line_lower for keyword in product_keywords):
            # Exclude lines that are clearly descriptions
            exclude_phrases = ['was evaluated', 'tested', 'description', 'ingredients', 
                             'how to use', 'directions', 'warning', 'caution']
            if not any(phrase in line_lower for phrase in exclude_phrases):
                # Prefer lines that aren't too short or too long
                if 5 < len(line) < 100:
                    return line
    
    # Strategy 2: Look for line before "was evaluated" or "tested"
    trigger_phrases = ['was evaluated', 'tested for', 'test results']
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(phrase in line_lower for phrase in trigger_phrases) and i > 0:
            # Return previous line if it's substantial
            prev_line = lines[i-1]
            if len(prev_line) > 5:
                return prev_line
    
    # Strategy 3: Look for lines with brand names or specific patterns
    # This catches lines that might have "by [Brand]" or similar
    for line in lines:
        if re.search(r'\bby\b|\bfrom\b', line, re.IGNORECASE):
            if len(line) > 5 and len(line) < 100:
                return line
    
    # Strategy 4: Fallback - return first substantial line
    for line in lines:
        if len(line) > 10 and len(line) < 100:
            # Skip common headers
            if not any(header in line.lower() for header in ['report', 'test', 'analysis', 'certificate']):
                return line
    
    return None


def create_output_folder():
    """Create output folder if it doesn't exist."""
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"✓ Created output folder: {OUTPUT_FOLDER}")


def rename_images():
    """Process images from input folder and save renamed copies to output folder."""
    # Ensure output folder exists
    create_output_folder()
    
    # Get list of image files
    image_files = [f for f in os.listdir(INPUT_FOLDER) 
                   if f.lower().endswith(VALID_EXTENSIONS)]
    
    if not image_files:
        print(f"⚠ No image files found in {INPUT_FOLDER}")
        return
    
    print(f"Found {len(image_files)} image(s) to process\n")
    print("=" * 60)
    
    processed = 0
    skipped = 0
    
    for filename in image_files:
        input_path = os.path.join(INPUT_FOLDER, filename)
        
        print(f"\n📄 Processing: {filename}")
        
        try:
            # Extract text using OCR
            text = pytesseract.image_to_string(Image.open(input_path))
            print(f"   Extracted text preview: {text[:150].strip()}...")
            
            # Extract product name
            product_name = extract_product_name(text)
            
            if not product_name:
                print("   ⚠ No product name found, skipping")
                skipped += 1
                continue
            
            print(f"   🔍 Found product: {product_name}")
            
            # Clean the product name for filename
            clean_name = clean_text(product_name)
            
            if not clean_name:
                print("   ⚠ Product name cleaned to empty string, skipping")
                skipped += 1
                continue
            
            # Generate new filename
            file_extension = os.path.splitext(filename)[1]
            new_filename = clean_name + file_extension
            output_path = os.path.join(OUTPUT_FOLDER, new_filename)
            
            # Handle duplicate filenames
            counter = 1
            while os.path.exists(output_path):
                new_filename = f"{clean_name}_{counter}{file_extension}"
                output_path = os.path.join(OUTPUT_FOLDER, new_filename)
                counter += 1
            
            # Copy file to output folder with new name
            shutil.copy2(input_path, output_path)
            print(f"   ✅ Saved as: {new_filename}")
            processed += 1
            
        except Exception as e:
            print(f"   ❌ Error processing file: {str(e)}")
            skipped += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"\n📊 Summary:")
    print(f"   Successfully processed: {processed}")
    print(f"   Skipped: {skipped}")
    print(f"   Total: {len(image_files)}")
    print(f"\n✓ Output saved to: {OUTPUT_FOLDER}")


if __name__ == "__main__":
    print("🖼️  Image Renaming Tool")
    print("=" * 60)
    print(f"Input folder:  {INPUT_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print("=" * 60)
    
    rename_images()