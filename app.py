
import streamlit as st
import requests
from PIL import Image, ImageOps, ImageDraw
import io
import zipfile
import math
import json
import hashlib
from datetime import datetime

# =====================================================
# GRIDLY PRO - INSTAGRAM PUZZLE GRID STUDIO
# =====================================================

st.set_page_config(
    page_title="Gridly Pro | Instagram Grid Studio",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# PREMIUM CSS
# =====================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(135deg,#0b1020,#15152c,#101827);
    color: #ffffff;
}

header[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    padding-top: 2rem;
    max-width: 1450px;
}

.hero {
    padding: 35px;
    border-radius: 22px;
    background: linear-gradient(120deg,#6546e8,#9b55d7,#3479e9);
    margin-bottom: 25px;
    box-shadow: 0 15px 45px #00000040;
}

.hero h1 {
    font-size: 38px;
    font-weight: 800;
    color: white;
    margin-bottom: 8px;
}

.hero p {
    color: #eeeaff;
    font-size: 15px;
}

.section {
    background: #191f33;
    border: 1px solid #303954;
    padding: 22px;
    border-radius: 18px;
    margin-bottom: 20px;
}

.metric {
    background: #202942;
    border: 1px solid #36415e;
    padding: 20px;
    border-radius: 15px;
    text-align: center;
}

.metric h2 {
    color: #a78bfa;
    font-size: 27px;
}

.metric p {
    color: #cbd5e1;
}

.stButton > button {
    background: linear-gradient(90deg,#7654ef,#a34ee8);
    color: white;
    border: none;
    border-radius: 12px;
    min-height: 45px;
    font-weight: 700;
    width: 100%;
}

.stButton > button:hover {
    border: 1px solid #c4b5fd;
    color: white;
    transform: translateY(-2px);
}

.stDownloadButton > button {
    background: linear-gradient(90deg,#059669,#10b981);
    color: white;
    border: none;
    border-radius: 12px;
    min-height: 45px;
    width: 100%;
    font-weight: 700;
}

h1, h2, h3 {
    color: white !important;
}

label, .stMarkdown p {
    color: #e2e8f0;
}

div[data-testid="stFileUploader"] {
    background: #202942;
    padding: 15px;
    border-radius: 15px;
    border: 1px dashed #8b75ef;
}

.small-note {
    color: #9ca3af;
    font-size: 12px;
}

</style>
""", unsafe_allow_html=True)
# =====================================================
# GUMROAD LICENSE KEY VERIFICATION
# =====================================================

GUMROAD_PRODUCT_ID = "oojYjXG1nY6lS2uGBj8KJg==" 

def verify_gumroad_license(license_key):
    clean_key = license_key.strip()
    
    # Personal testing ke liye Master Key
    if clean_key == "ADMIN-GRIDLY-2026":
        return True, "Admin Access Granted!"

    api_endpoint = "https://" + "://gumroad.com"

    try:
        response = requests.post(
            api_endpoint,
            headers={
                "User-Agent": "GridlyProApp/1.0",
                "Accept": "application/json"
            },
            data={
                "product_id": GUMROAD_PRODUCT_ID,
                "license_key": clean_key,
                "increment_uses_count": "false"
            },
            timeout=15
        )
        data = response.json()
        if data.get("success") and not data.get("purchase", {}).get("refunded") and not data.get("purchase", {}).get("chargebacked"):
            return True, "License Verified!"
        return False, f"Invalid key: {data.get('message', 'Please check your Gumroad license key.')}"
    except Exception as e:
        return False, f"Connection error: {e}"

if "unlocked" not in st.session_state:
    st.session_state.unlocked = False

if not st.session_state.unlocked:
    st.markdown("""
    <div class="hero" style="text-align:center;">
        <h1>📸 GRIDLY PRO</h1>
        <p>Creator Studio Activation</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔒 Enter Your Gumroad License Key")
        st.info("Paste the unique License Key from your Gumroad receipt or library to unlock Gridly Pro.")
        user_key = st.text_input("License Key:", placeholder="XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX")
        
        if st.button("Activate & Unlock Studio 🚀"):
            if not user_key.strip():
                st.warning("Please enter your license key.")
            else:
                with st.spinner("Verifying your Gumroad license..."):
                    is_valid, msg = verify_gumroad_license(user_key)
                    if is_valid:
                        st.session_state.unlocked = True
                        st.rerun()
                    else:
                        st.error(msg)
    st.stop()

# =====================================================
# SESSION STATE
# =====================================================

if "tiles" not in st.session_state:
    st.session_state.tiles = []

if "preview" not in st.session_state:
    st.session_state.preview = None

if "generated" not in st.session_state:
    st.session_state.generated = False


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def image_to_bytes(image, fmt="JPEG", quality=95):
    """Encode a tile with predictable color mode and export quality."""
    buffer = io.BytesIO()

    if fmt.upper() == "JPEG":
        if image.mode != "RGB":
            image = image.convert("RGB")

        image.save(
            buffer,
            format="JPEG",
            quality=max(85, min(100, int(quality))),
            optimize=True,
            progressive=True,
        )
    else:
        # PNG supports RGB and RGBA; normalize palette/other modes.
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")
        image.save(buffer, format="PNG", optimize=True)

    return buffer.getvalue()


# Instagram's portrait profile-grid tile target.
# Each exported post is prepared at 1080 x 1440 (3:4).
INSTAGRAM_TILE_WIDTH = 1080
INSTAGRAM_TILE_HEIGHT = 1440


def prepare_instagram_canvas(image, cols, rows, fit_mode="Crop to Fill",
                             crop_x=0.5, crop_y=0.5,
                             background_color="#111111"):
    """
    Prepare one continuous puzzle canvas whose individual tiles are 3:4.
    The canvas ratio is (cols * 3) : (rows * 4), not automatically 1:1.
    Crop-to-fill never stretches the source image.
    Fit-without-cropping preserves the complete source and adds background
    bands where required.
    """
    target_size = (
        cols * INSTAGRAM_TILE_WIDTH,
        rows * INSTAGRAM_TILE_HEIGHT,
    )

    if fit_mode == "Crop to Fill":
        return ImageOps.fit(
            image.convert("RGB"),
            target_size,
            method=Image.Resampling.LANCZOS,
            centering=(crop_x, crop_y),
        )

    contained = ImageOps.contain(
        image.convert("RGB"),
        target_size,
        method=Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGB", target_size, background_color)
    x_offset = (target_size[0] - contained.width) // 2
    y_offset = (target_size[1] - contained.height) // 2
    canvas.paste(contained, (x_offset, y_offset))
    return canvas


def split_image(image, cols, rows):
    width, height = image.size

    if cols < 1 or rows < 1:
        raise ValueError("Grid rows and columns must be at least 1.")

    if width % cols != 0 or height % rows != 0:
        raise ValueError(
            "Prepared canvas dimensions must divide evenly into the selected grid."
        )

    x_points = [i * (width // cols) for i in range(cols + 1)]
    y_points = [i * (height // rows) for i in range(rows + 1)]

    tiles = []

    for row in range(rows):
        for col in range(cols):

            tile = image.crop((
                x_points[col],
                y_points[row],
                x_points[col + 1],
                y_points[row + 1]
            ))

            tiles.append({
                "image": tile,
                "row": row,
                "col": col,
                "number": row * cols + col + 1
            })

    return tiles


def add_outer_border(tile, row, col, rows, cols,
                     border_size, border_color):

    if border_size <= 0:
        return tile.copy()

    width, height = tile.size

    canvas = Image.new(
        "RGB",
        (width, height),
        "#000000"
    )

    tile = tile.convert("RGB")
    canvas.paste(tile, (0, 0))

    draw = ImageDraw.Draw(canvas)

    # Only outer edges receive border.
    if row == 0:
        draw.rectangle(
            (0, 0, width - 1, min(border_size - 1, height - 1)),
            fill=border_color
        )

    if row == rows - 1:
        draw.rectangle(
            (0, max(0, height - border_size), width - 1, height - 1),
            fill=border_color
        )

    if col == 0:
        draw.rectangle(
            (0, 0, min(border_size - 1, width - 1), height - 1),
            fill=border_color
        )

    if col == cols - 1:
        draw.rectangle(
            (max(0, width - border_size), 0, width - 1, height - 1),
            fill=border_color
        )

    return canvas


def create_grid_preview(tiles, cols, rows, border_size, color):

    if not tiles:
        return None

    tile_w, tile_h = tiles[0]["image"].size

    preview = Image.new(
        "RGB",
        (tile_w * cols, tile_h * rows),
        color
    )

    for item in tiles:

        tile = add_outer_border(
            item["image"],
            item["row"],
            item["col"],
            rows,
            cols,
            border_size,
            color
        )

        preview.paste(
            tile,
            (
                item["col"] * tile_w,
                item["row"] * tile_h
            )
        )

    return preview


def create_zip(tiles, cols, rows, border_size, color, fmt, quality=95):

    zip_buffer = io.BytesIO()

    extension = fmt.lower()

    with zipfile.ZipFile(
        zip_buffer,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zip_file:

        for item in tiles:

            final_tile = add_outer_border(
                item["image"],
                item["row"],
                item["col"],
                rows,
                cols,
                border_size,
                color
            )

            data = image_to_bytes(final_tile, fmt, quality)

            zip_file.writestr(
                f"Gridly_Post_{item['number']:02d}.{extension}",
                data
            )

        # Instagram posting sequence.
        sequence = []

        for row in reversed(range(rows)):
            for col in reversed(range(cols)):
                number = row * cols + col + 1

                sequence.append({
                    "upload_order": len(sequence) + 1,
                    "tile_number": number,
                    "filename": f"Gridly_Post_{number:02d}.{extension}"
                })

        instructions = {
            "product": "Gridly Pro",
            "created": datetime.now().isoformat(),
            "grid": f"{cols}x{rows}",
            "tile_aspect_ratio": "3:4",
            "tile_dimensions_px": f"{INSTAGRAM_TILE_WIDTH}x{INSTAGRAM_TILE_HEIGHT}",
            "posting_sequence": sequence,
            "instructions": [
                "Upload tiles in the listed order, starting bottom-right.",
                "Do not crop, zoom, or change the aspect ratio after export.",
                "Keep all posts in the same 3:4 portrait format.",
                "If Instagram offers Adjust Preview, do not change the crop.",
                "The newest post should appear at the top-left of the profile grid."
            ]
        }

        zip_file.writestr(
            "INSTAGRAM_POSTING_GUIDE.json",
            json.dumps(instructions, indent=4)
        )

        zip_file.writestr(
            "README.txt",
            """GRIDLY PRO - INSTAGRAM GRID MAKER

Thank you for using Gridly Pro!

HOW TO USE:
1. Extract all images.
2. Open INSTAGRAM_POSTING_GUIDE.json.
3. Upload images in the specified order.
4. Avoid cropping images while uploading.

For the best result, use the original exported images.
"""
        )

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


# =====================================================
# HEADER
# =====================================================

st.markdown("""
<div class="hero">
    <h1>📸 GRIDLY PRO</h1>
    <p>Instagram Puzzle Grid Studio</p>
    <p>Design. Split. Preview. Publish.</p>
</div>
""", unsafe_allow_html=True)


# =====================================================
# SIDEBAR SETTINGS
# =====================================================

with st.sidebar:

    st.markdown("## ⚙️ Studio Settings")

    st.markdown("### Grid Layout")

    layout = st.selectbox(
        "Choose Layout",
        [
            "3 × 3",
            "3 × 2",
            "3 × 1",
            "2 × 2",
            "2 × 3",
            "Custom"
        ]
    )

    if layout == "Custom":

        cols = st.slider("Columns", 1, 6, 3)
        rows = st.slider("Rows", 1, 6, 3)

    else:

        cols, rows = map(
            int,
            layout.replace(" ", "").split("×")
        )

    st.markdown("---")
    st.markdown("### 🖼️ Instagram Image Framing")

    fit_mode = st.radio(
        "Image fitting mode",
        ["Crop to Fill", "Fit Without Cropping"],
        help=(
            "Crop to Fill fills the complete puzzle canvas without stretching. "
            "Fit Without Cropping keeps the whole source image and may add "
            "background bands."
        )
    )

    crop_x = 0.5
    crop_y = 0.5

    if fit_mode == "Crop to Fill":
        crop_x = st.slider(
            "Horizontal crop position",
            0.0, 1.0, 0.5, 0.01,
            help="Move the crop focus left or right."
        )
        crop_y = st.slider(
            "Vertical crop position",
            0.0, 1.0, 0.5, 0.01,
            help="Move the crop focus up or down."
        )

    fit_background = st.color_picker(
        "Background for Fit Without Cropping",
        "#111111"
    )

    st.caption(
        "Each exported post is prepared at 1080 × 1440 pixels (3:4)."
    )

    st.markdown("---")
    st.markdown("### 🎨 Border Settings")

    border_style = st.selectbox(
        "Border Preset",
        [
            "Luxury White",
            "Minimal Black",
            "Cream",
            "Custom",
            "No Border"
        ]
    )

    color_options = {
        "Luxury White": "#FFFFFF",
        "Minimal Black": "#111111",
        "Cream": "#F3E8D0",
        "Custom": "#FFFFFF",
        "No Border": "#000000"
    }

    border_color = color_options[border_style]

    if border_style == "Custom":

        border_color = st.color_picker(
            "Choose Border Color",
            "#FFFFFF"
        )

    border_size = st.slider(
        "Outer Border Width (px)",
        0,
        100,
        20
    )

    if border_style == "No Border":
        border_size = 0

    st.markdown("---")
    st.markdown("### 📥 Export Settings")

    export_format = st.selectbox(
        "Image Format",
        ["JPEG", "PNG"]
    )

    jpeg_quality = 95
    if export_format == "JPEG":
        jpeg_quality = st.slider(
            "JPEG Quality",
            min_value=85,
            max_value=100,
            value=95,
            help="Higher quality preserves more detail but creates larger files."
        )

    st.caption("Gridly Pro | Instagram 3:4 Creator Edition")


# =====================================================
# MAIN CONTENT
# =====================================================

left, right = st.columns([1.05, 1])

with left:

    st.markdown("## 📤 Upload Your Image")

    uploaded_file = st.file_uploader(
        "Drag & Drop Your Image Here",
        type=["jpg", "jpeg", "png", "webp"]
    )

    # Initialize these on every Streamlit rerun.
    image = None
    uploaded_hash = None

    if uploaded_file:

        try:

            uploaded_bytes = uploaded_file.getvalue()
            uploaded_hash = hashlib.sha256(uploaded_bytes).hexdigest()

            uploaded_file.seek(0)
            with Image.open(uploaded_file) as source_image:
                source_image.verify()

            uploaded_file.seek(0)
            with Image.open(uploaded_file) as source_image:
                image = ImageOps.exif_transpose(source_image).convert("RGB")

            st.image(
                image,
                caption="Original Image",
                width="stretch"
            )

            st.markdown(
                f"""
                <div class="section">
                    <b>Image Information</b><br>
                    Width: {image.width}px<br>
                    Height: {image.height}px<br>
                    Resolution: {image.width} × {image.height}<br>
                    Original Aspect Ratio: {image.width / image.height:.3f}:1
                </div>
                """,
                unsafe_allow_html=True
            )

        except Exception as error:
            st.error(f"Unable to open image: {error}")
            image = None

    else:
        image = None
        uploaded_hash = None
        st.info("Upload an image to start creating your Instagram grid.")


with right:

    st.markdown("## ✨ Grid Studio")

    st.markdown(
        f"""
        <div class="section">
            <h3>Selected Configuration</h3>
            <p>Grid Layout: <b>{cols} × {rows}</b></p>
            <p>Each Instagram Tile: <b>{INSTAGRAM_TILE_WIDTH} × {INSTAGRAM_TILE_HEIGHT}px (3:4)</b></p>
            <p>Full Puzzle Canvas: <b>{cols * INSTAGRAM_TILE_WIDTH} × {rows * INSTAGRAM_TILE_HEIGHT}px</b></p>
            <p>Image Fit: <b>{fit_mode}</b></p>
            <p>Border Style: <b>{border_style}</b></p>
            <p>Border Width: <b>{border_size}px</b></p>
            <p>Export Format: <b>{export_format}</b></p>
        </div>
        """,
        unsafe_allow_html=True
    )

    generate = st.button(
        "🚀 Generate Premium Grid",
        disabled=image is None
    )

    if generate:

        with st.spinner("Creating your premium grid..."):

            prepared_canvas = prepare_instagram_canvas(
                image=image,
                cols=cols,
                rows=rows,
                fit_mode=fit_mode,
                crop_x=crop_x,
                crop_y=crop_y,
                background_color=fit_background,
            )

            st.session_state.master_canvas = prepared_canvas
            st.session_state.tiles = split_image(
                prepared_canvas,
                cols,
                rows
            )

            st.session_state.preview = create_grid_preview(
                st.session_state.tiles,
                cols,
                rows,
                border_size,
                border_color
            )

            st.session_state.generated = True

            # Store export configuration.
            st.session_state.config = {
                "cols": cols,
                "rows": rows,
                "border_size": border_size,
                "border_color": border_color,
                "format": export_format,
                "quality": jpeg_quality,
                "fit_mode": fit_mode,
                "crop_x": crop_x,
                "crop_y": crop_y,
                "fit_background": fit_background,
                "source_hash": uploaded_hash,
            }

        st.success("Your premium grid is ready! 🎉")


# =====================================================
# RESULTS
# =====================================================

if st.session_state.generated:

    tiles = st.session_state.tiles
    preview = st.session_state.preview
    config = st.session_state.config

    current_signature = {
        "cols": cols,
        "rows": rows,
        "border_size": border_size,
        "border_color": border_color,
        "format": export_format,
        "quality": jpeg_quality,
        "fit_mode": fit_mode,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "fit_background": fit_background,
        "source_hash": uploaded_hash,
    }

    saved_signature = {
        "cols": config["cols"],
        "rows": config["rows"],
        "border_size": config["border_size"],
        "border_color": config["border_color"],
        "format": config["format"],
        "quality": config.get("quality", 95),
        "fit_mode": config.get("fit_mode", "Crop to Fill"),
        "crop_x": config.get("crop_x", 0.5),
        "crop_y": config.get("crop_y", 0.5),
        "fit_background": config.get("fit_background", "#111111"),
        "source_hash": config.get("source_hash"),
    }

    if current_signature != saved_signature:
        st.warning(
            "Settings or source image changed after the last generation. "
            "Click Generate Premium Grid again to refresh the preview and downloads."
        )

    cols = config["cols"]
    rows = config["rows"]
    border_size = config["border_size"]
    border_color = config["border_color"]
    export_format = config["format"]
    jpeg_quality = config.get("quality", 95)

    st.markdown("---")
    st.markdown("## 🎨 Your Grid Preview")

    original_col, preview_col = st.columns(2)

    with original_col:
        st.markdown("### Original Image")

        if image is not None:
            st.image(image, width="stretch")
        else:
            st.info("Original preview is available after uploading again.")

    with preview_col:
        st.markdown("### Final Puzzle Canvas")

        st.image(
            st.session_state.master_canvas,
            width="stretch"
        )

    st.caption(
        "The complete image is prepared for the selected grid first. "
        "Every tile is then split at exactly 1080 × 1440 pixels, without stretching."
    )

    # =================================================
    # INSTAGRAM PROFILE PREVIEW
    # =================================================

    st.markdown("---")
    st.markdown("## 📱 Instagram Profile Preview")

    # Use 3:4 portrait thumbnails instead of forcing every tile into a square.
    # The thumbnail dimensions mirror the exported 1080 x 1440 tile ratio.
    profile_tile_w = 180
    profile_tile_h = 240
    profile_width = profile_tile_w * cols
    profile_height = profile_tile_h * rows

    profile = Image.new(
        "RGB",
        (profile_width, profile_height),
        "#111111"
    )

    for item in tiles:

        tile = item["image"].resize(
            (profile_tile_w, profile_tile_h),
            Image.Resampling.LANCZOS
        )

        preview_border_size = round(
            border_size * profile_tile_w / INSTAGRAM_TILE_WIDTH
        )

        tile = add_outer_border(
            tile,
            item["row"],
            item["col"],
            rows,
            cols,
            preview_border_size,
            border_color
        )

        profile.paste(
            tile,
            (
                item["col"] * profile_tile_w,
                item["row"] * profile_tile_h
            )
        )

    st.image(
        profile,
        caption="Instagram Grid Appearance",
        width="stretch"
    )

    # =================================================
    # POSTING SEQUENCE
    # =================================================

    st.markdown("---")
    st.markdown("## 🔢 Instagram Posting Guide")

    st.info(
        "Upload tiles from bottom-right to top-left. "
        "The following list shows the recommended sequence."
    )

    posting_sequence = []

    for row in reversed(range(rows)):
        for col in reversed(range(cols)):

            number = row * cols + col + 1
            posting_sequence.append(number)

    sequence_cols = st.columns(min(3, len(posting_sequence)))

    for index, number in enumerate(posting_sequence):

        with sequence_cols[index % len(sequence_cols)]:

            st.markdown(
                f"""
                <div class="metric">
                    <h2>{index + 1}</h2>
                    <p>Upload Tile #{number}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    # =================================================
    # INDIVIDUAL DOWNLOADS
    # =================================================

    st.markdown("---")
    st.markdown("## 🖼️ Download Individual Tiles")

    for start in range(0, len(tiles), 3):

        tile_columns = st.columns(3)

        for index, item in enumerate(tiles[start:start + 3]):

            with tile_columns[index]:

                final_tile = add_outer_border(
                    item["image"],
                    item["row"],
                    item["col"],
                    rows,
                    cols,
                    border_size,
                    border_color
                )

                st.image(
                    final_tile,
                    caption=f"Tile #{item['number']}",
                    width="stretch"
                )

                st.download_button(
                    label=f"⬇️ Download Tile {item['number']}",
                    data=image_to_bytes(
                        final_tile,
                        export_format,
                        jpeg_quality
                    ),
                    file_name=(
                        f"Gridly_Post_{item['number']:02d}."
                        f"{export_format.lower()}"
                    ),
                    mime=(
                        "image/jpeg"
                        if export_format == "JPEG"
                        else "image/png"
                    ),
                    key=f"download_{item['number']}"
                )

    # =================================================
    # COMPLETE ZIP EXPORT
    # =================================================

    st.markdown("---")
    st.markdown("## 📦 Complete Creator Package")

    zip_data = create_zip(
        tiles,
        cols,
        rows,
        border_size,
        border_color,
        export_format,
        jpeg_quality
    )

    st.download_button(
        label="📦 Download Complete Gridly Pro Package",
        data=zip_data,
        file_name="Gridly_Pro_Instagram_Grid.zip",
        mime="application/zip",
        width="stretch"
    )

    st.success(
        "Your ZIP includes all tiles, posting sequence guide and README."
    )

    if st.button("🔄 Reset Studio"):

        st.session_state.tiles = []
        st.session_state.preview = None
        st.session_state.master_canvas = None
        st.session_state.generated = False
        st.session_state.config = {}

        st.rerun()


# =====================================================
# FOOTER
# =====================================================

st.markdown("---")

st.markdown("""
<div style="text-align:center;padding:20px;color:#9ca3af;">
    <h3 style="color:#a78bfa;">GRIDLY PRO</h3>
    <p>Designed for Creators. Built for Aesthetics.</p>
    <p>© 2026 Gridly Pro | Creator Edition</p>
</div>
""", unsafe_allow_html=True)
