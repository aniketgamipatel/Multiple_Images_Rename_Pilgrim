import streamlit as st
import re
import io
import zipfile
from PIL import Image
import pytesseract
import os

st.set_page_config(page_title="Image Renaming Tool", page_icon="🖼️")

# Initialize session state
if 'processed_images' not in st.session_state:
    st.session_state.processed_images = []
if 'failed_count' not in st.session_state:
    st.session_state.failed_count = 0
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False

def clean_text(text):
    """Clean and sanitize text for use as filename."""
    text = text.strip().replace("\n", " ")
    text = re.sub(r"[^a-zA-Z0-9_&-]", "_", text)
    text = re.sub(r"_+", "_", text)
    text = text.strip("_")
    return text[:80]

def extract_product_name(text):
    """Extract product name from OCR text using multiple strategies."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    product_keywords = ['oil', 'serum', 'cream', 'foundation', 'lotion', 'gel', 
                       'moisturizer', 'cleanser', 'toner', 'essence', 'mask',
                       'balm', 'primer', 'powder', 'lipstick', 'mascara']
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in product_keywords):
            exclude_phrases = ['was evaluated', 'tested', 'description', 'ingredients', 
                             'how to use', 'directions', 'warning', 'caution']
            if not any(phrase in line_lower for phrase in exclude_phrases):
                if 5 < len(line) < 100:
                    return line
    
    trigger_phrases = ['was evaluated', 'tested for', 'test results']
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(phrase in line_lower for phrase in trigger_phrases) and i > 0:
            prev_line = lines[i-1]
            if len(prev_line) > 5:
                return prev_line
    
    for line in lines:
        if re.search(r'\bby\b|\bfrom\b', line, re.IGNORECASE):
            if len(line) > 5 and len(line) < 100:
                return line
    
    for line in lines:
        if len(line) > 10 and len(line) < 100:
            if not any(header in line.lower() for header in ['report', 'test', 'analysis', 'certificate']):
                return line
    
    return None

def process_image(image, original_filename):
    """Process a single image and return new filename and image bytes."""
    try:
        text = pytesseract.image_to_string(image)
        product_name = extract_product_name(text)
        
        if not product_name:
            return None, None
        
        clean_name = clean_text(product_name)
        
        if not clean_name:
            return None, None
        
        file_extension = original_filename.split('.')[-1]
        new_filename = f"{clean_name}.{file_extension}"
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=image.format or 'PNG')
        img_byte_arr.seek(0)
        
        return new_filename, img_byte_arr.getvalue()
    
    except Exception as e:
        return None, None

def reset_processing():
    """Reset processing state."""
    st.session_state.processed_images = []
    st.session_state.failed_count = 0
    st.session_state.processing_complete = False

# Sidebar for Tesseract configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    tesseract_path = st.text_input(
        "Tesseract Path (optional)",
        placeholder="C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
        help="Leave empty if Tesseract is in system PATH"
    )
    
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    st.divider()
    st.markdown("""
    ### 📁 Folder Upload
    
    **For Chrome/Edge:**
    1. Drag and drop a folder into the upload area
    2. Or select multiple files from a folder
    
    **Note:** Browser folder upload works best in Chrome and Edge browsers.
    """)

# Main app
st.title("🖼️ Image Renaming Tool")
st.markdown("Upload images to automatically rename them based on detected product names using OCR.")

# File uploader
uploaded_files = st.file_uploader(
    "📤 Upload Images (or drag & drop a folder)",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True,
    help="You can select multiple files or drag and drop an entire folder (Chrome/Edge)",
    on_change=reset_processing
)

if uploaded_files and not st.session_state.processing_complete:
    st.write(f"📊 Total Images: {len(uploaded_files)}")
    
    # Process button
    if st.button("🚀 Process Images", type="primary"):
        st.session_state.processed_images = []
        st.session_state.failed_count = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processing: {uploaded_file.name}")
            
            image = Image.open(uploaded_file)
            new_filename, img_bytes = process_image(image, uploaded_file.name)
            
            if new_filename and img_bytes:
                st.session_state.processed_images.append((new_filename, img_bytes))
            else:
                st.session_state.failed_count += 1
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
        
        progress_bar.empty()
        status_text.empty()
        st.session_state.processing_complete = True
        st.rerun()

# Display results and download buttons
if st.session_state.processing_complete:
    if st.session_state.processed_images:
        st.success("✅ Processing Complete!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("✅ Passed", len(st.session_state.processed_images))
        with col2:
            st.metric("❌ Failed", st.session_state.failed_count)
        
        st.divider()
        
        # Download section
        st.subheader("📥 Download Results")
        
        if len(st.session_state.processed_images) == 1:
            st.download_button(
                label="⬇️ Download Renamed Image",
                data=st.session_state.processed_images[0][1],
                file_name=st.session_state.processed_images[0][0],
                mime="image/png",
                use_container_width=True
            )
        else:
            # Create ZIP file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                used_names = {}
                for filename, img_bytes in st.session_state.processed_images:
                    if filename in used_names:
                        used_names[filename] += 1
                        name_parts = filename.rsplit('.', 1)
                        filename = f"{name_parts[0]}_{used_names[filename]}.{name_parts[1]}"
                    else:
                        used_names[filename] = 0
                    
                    zip_file.writestr(filename, img_bytes)
            
            zip_buffer.seek(0)
            
            st.download_button(
                label=f"⬇️ Download All as ZIP ({len(st.session_state.processed_images)} images)",
                data=zip_buffer.getvalue(),
                file_name="renamed_images.zip",
                mime="application/zip",
                use_container_width=True
            )
        
        # Show preview of renamed files
        with st.expander("👁️ Preview Renamed Files"):
            for idx, (filename, _) in enumerate(st.session_state.processed_images[:10], 1):
                st.text(f"{idx}. {filename}")
            if len(st.session_state.processed_images) > 10:
                st.text(f"... and {len(st.session_state.processed_images) - 10} more")
        
        # Process new images button
        if st.button("🔄 Process New Images", use_container_width=True):
            reset_processing()
            st.rerun()
    else:
        st.warning("⚠️ No images could be processed. Please check if Tesseract is installed correctly.")
        if st.button("🔄 Try Again", use_container_width=True):
            reset_processing()
            st.rerun()