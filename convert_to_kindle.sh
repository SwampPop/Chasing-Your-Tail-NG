#!/bin/bash

# ============================================================
# CYT Documentation to Kindle Converter
# ============================================================
# Converts CYT markdown documentation to Kindle-optimized format
# using Pandoc and Calibre for Xcode-style technical reading
#
# Prerequisites:
#   - Pandoc: brew install pandoc
#   - Calibre: brew install --cask calibre
#   - Optional: Kindle Previewer 3 (for KFX format)
#
# Usage:
#   ./convert_to_kindle.sh
#
# Output:
#   - EPUB file (intermediate)
#   - Ready for Calibre conversion to KFX/AZW3
# ============================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/kindle_output"
CSS_FILE="$SCRIPT_DIR/kindle-style.css"

# Documentation files (in reading order)
DOCS=(
    "QUICK_REFERENCE.md"
    "DEVICE_IDENTIFICATION_GUIDE.md"
    "PROBE_REQUEST_ANALYSIS.md"
    "REALTIME_INVESTIGATION.md"
    "DEVICE_INVESTIGATION_QUERIES.md"
)

# Book metadata
BOOK_TITLE="Chasing Your Tail - Investigation Guide"
BOOK_AUTHOR="CYT Project"
BOOK_VERSION="1.0"

# ============================================================
# Helper Functions
# ============================================================

print_step() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

check_prerequisites() {
    print_step "Checking prerequisites..."

    if ! command -v pandoc &> /dev/null; then
        print_error "Pandoc not found. Install with: brew install pandoc"
        exit 1
    fi

    if ! command -v calibre &> /dev/null; then
        print_warning "Calibre not found. You'll need it for KFX conversion."
        print_warning "Install with: brew install --cask calibre"
    fi

    if [ ! -f "$CSS_FILE" ]; then
        print_error "CSS file not found: $CSS_FILE"
        exit 1
    fi

    print_step "Prerequisites OK"
}

create_output_dir() {
    print_step "Creating output directory..."
    mkdir -p "$OUTPUT_DIR"
}

create_metadata() {
    print_step "Creating metadata file..."

    cat > "$OUTPUT_DIR/metadata.yaml" << EOF
---
title: "$BOOK_TITLE"
author: "$BOOK_AUTHOR"
version: "$BOOK_VERSION"
date: "$(date +%Y-%m-%d)"
lang: en-US
toc-title: "Table of Contents"
---
EOF
}

create_title_page() {
    print_step "Creating title page..."

    cat > "$OUTPUT_DIR/title.md" << EOF
# $BOOK_TITLE

**Version:** $BOOK_VERSION
**Generated:** $(date +"%Y-%m-%d")
**Project:** Chasing Your Tail - Next Generation

---

## About This Guide

This comprehensive investigation guide covers:

- **Quick Reference** - Daily commands and workflows
- **Device Identification** - How to identify unknown devices
- **Probe Request Analysis** - Investigating WiFi probe requests
- **Real-Time Investigation** - Finding active devices near you
- **SQL Query Reference** - Ready-to-use database queries

---

## Usage

This guide is designed for offline reading on Kindle devices. Use the Table of Contents to navigate between sections.

All commands and queries are formatted for easy copy/paste when you return to your computer.

---

EOF
}

check_files_exist() {
    print_step "Checking documentation files..."

    local missing_files=0
    for doc in "${DOCS[@]}"; do
        if [ ! -f "$SCRIPT_DIR/$doc" ]; then
            print_warning "File not found: $doc"
            missing_files=$((missing_files + 1))
        fi
    done

    if [ $missing_files -gt 0 ]; then
        print_warning "$missing_files file(s) missing. Continuing with available files..."
    fi
}

convert_to_epub() {
    print_step "Converting to EPUB format..."

    # Build list of existing files
    local input_files=("$OUTPUT_DIR/title.md")
    for doc in "${DOCS[@]}"; do
        if [ -f "$SCRIPT_DIR/$doc" ]; then
            input_files+=("$SCRIPT_DIR/$doc")
        fi
    done

    # Convert to EPUB
    pandoc "${input_files[@]}" \
        -o "$OUTPUT_DIR/CYT-Investigation-Guide.epub" \
        --metadata-file="$OUTPUT_DIR/metadata.yaml" \
        --css="$CSS_FILE" \
        --toc \
        --toc-depth=3 \
        --highlight-style=pygments \
        --epub-embed-font="$(fc-match 'Courier New' --format='%{file}')" \
        --number-sections \
        --standalone

    print_step "EPUB created: $OUTPUT_DIR/CYT-Investigation-Guide.epub"
}

create_calibre_instructions() {
    print_step "Creating Calibre conversion instructions..."

    cat > "$OUTPUT_DIR/CALIBRE_INSTRUCTIONS.txt" << EOF
============================================================
CALIBRE CONVERSION INSTRUCTIONS
============================================================

You now have an EPUB file ready for Calibre conversion.

STEP 1: Import to Calibre
--------------------------
1. Open Calibre
2. Click "Add books" button
3. Select: CYT-Investigation-Guide.epub
4. The book will appear in your library

STEP 2: Convert to KFX (Recommended) or AZW3
---------------------------------------------

METHOD A: KFX Format (Best Quality - Requires Setup)
1. Install KFX Output plugin:
   - Preferences > Plugins > Get new plugins
   - Search for "KFX Output"
   - Install and restart Calibre

2. Install Kindle Previewer 3:
   - Download from: https://www.amazon.com/gp/feature.html?docId=1000765261
   - Install on your Mac

3. Convert to KFX:
   - Right-click the book > Convert books
   - Output format: KFX
   - Click OK

METHOD B: AZW3 Format (Standard - No Setup Required)
1. Right-click the book > Convert books
2. Output format: AZW3
3. Click OK

STEP 3: Transfer to Kindle
---------------------------

METHOD A: USB Transfer (Preserves Formatting)
1. Connect Kindle to Mac via USB
2. In Calibre, click "Send to device" button
3. Wait for transfer to complete
4. Eject Kindle safely

METHOD B: Send to Kindle (Wireless)
1. Get your Kindle email: Settings > Your Account > Send-to-Kindle Email
2. In Calibre, right-click book > Connect/share > Email to...
3. Enter your Kindle email address
4. Click OK

**IMPORTANT:** For technical docs with code blocks, use USB transfer!
Amazon's cloud converter may strip code formatting if you email it.

STEP 4: Reading on Kindle
--------------------------
1. Open the book on your Kindle
2. Tap the top of the screen > Aa (font settings)
3. Recommended settings:
   - Font: Bookerly or Amazon Ember
   - Font size: 3-4 (smaller for code blocks)
   - Line spacing: Default
   - Margins: Default
4. Use Table of Contents to navigate (tap top > Table of Contents)

============================================================
TROUBLESHOOTING
============================================================

Issue: Code blocks run off screen
Solution: Use font size 3 or 4, ensure CSS file was included

Issue: Syntax highlighting missing
Solution: Normal - Kindle E-ink only shows grayscale. Keywords
         are bold, comments italic, strings underlined.

Issue: Images/emojis don't show
Solution: Expected - Kindle converts emojis to text descriptions

============================================================
EOF

    print_step "Instructions saved: $OUTPUT_DIR/CALIBRE_INSTRUCTIONS.txt"
}

show_summary() {
    echo ""
    echo "============================================================"
    echo -e "${GREEN}CONVERSION COMPLETE!${NC}"
    echo "============================================================"
    echo ""
    echo "Output directory: $OUTPUT_DIR"
    echo ""
    echo "Generated files:"
    echo "  📘 CYT-Investigation-Guide.epub"
    echo "  📄 CALIBRE_INSTRUCTIONS.txt"
    echo ""
    echo "Next steps:"
    echo "  1. Open Calibre"
    echo "  2. Import the EPUB file"
    echo "  3. Convert to KFX (best) or AZW3"
    echo "  4. Transfer to Kindle via USB"
    echo ""
    echo "See CALIBRE_INSTRUCTIONS.txt for detailed steps."
    echo ""
}

# ============================================================
# Main Execution
# ============================================================

main() {
    echo "============================================================"
    echo "CYT Documentation to Kindle Converter"
    echo "============================================================"
    echo ""

    check_prerequisites
    create_output_dir
    check_files_exist
    create_metadata
    create_title_page
    convert_to_epub
    create_calibre_instructions
    show_summary
}

# Run main function
main
