# Kindle Setup Guide for CYT Documentation

**Convert CYT documentation to Kindle format for on-the-go reading**

This guide walks you through converting your CYT investigation guides into a professional Kindle ebook with Xcode-style formatting optimized for technical documentation.

---

## Quick Start

### Prerequisites

Install the required tools:

```bash
# Install Pandoc (Markdown to EPUB converter)
brew install pandoc

# Install Calibre (EPUB to Kindle converter)
brew install --cask calibre

# Optional: Install Kindle Previewer 3 (for best quality KFX format)
# Download from: https://www.amazon.com/gp/feature.html?docId=1000765261
```

### One-Command Conversion

```bash
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG
./convert_to_kindle.sh
```

This creates:
- `kindle_output/CYT-Investigation-Guide.epub` - Ready for Calibre
- `kindle_output/CALIBRE_INSTRUCTIONS.txt` - Step-by-step Calibre guide

---

## Step-by-Step Workflow

### Step 1: Convert Documentation to EPUB

The script combines all CYT guides into a single ebook:

**Included documents:**
1. Quick Reference
2. Device Identification Guide
3. Probe Request Analysis
4. Real-Time Investigation Guide
5. SQL Query Reference

**Features:**
- ✅ Xcode-style code formatting with line wrapping
- ✅ Syntax highlighting (optimized for E-ink grayscale)
- ✅ Clickable Table of Contents
- ✅ Monospace fonts for code blocks
- ✅ Section navigation with headers

```bash
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG
./convert_to_kindle.sh
```

**Output:**
```
kindle_output/
├── CYT-Investigation-Guide.epub
├── CALIBRE_INSTRUCTIONS.txt
├── metadata.yaml
└── title.md
```

### Step 2: Import to Calibre

1. **Open Calibre application**
2. **Add books:**
   - Click "Add books" button (or Cmd+A)
   - Navigate to `kindle_output/`
   - Select `CYT-Investigation-Guide.epub`
3. **Book appears in library**

### Step 3: Convert to Kindle Format

You have two options:

#### Option A: KFX Format (Recommended - Best Quality)

**Enhanced Typesetting format with superior code block rendering**

**Setup (one-time):**

1. **Install KFX Output plugin:**
   ```
   Calibre > Preferences > Plugins > Get new plugins
   Search: "KFX Output"
   Install > Restart Calibre
   ```

2. **Install Kindle Previewer 3:**
   - Download: https://www.amazon.com/gp/feature.html?docId=1000765261
   - Install on macOS
   - Calibre will auto-detect it

**Convert to KFX:**
```
Right-click book > Convert books
Output format: KFX
Click OK
```

**Benefits:**
- Superior code block wrapping
- Better monospace font rendering
- Enhanced navigation
- Hyphenation control

#### Option B: AZW3 Format (Standard - No Setup)

**Standard Kindle format, works on all devices**

```
Right-click book > Convert books
Output format: AZW3
Click OK
```

**Use this if:**
- You don't want to install plugins
- You have an older Kindle
- KFX conversion fails

### Step 4: Transfer to Kindle

**CRITICAL:** For technical documentation, **always use USB transfer**. Amazon's "Send to Kindle" cloud service strips code formatting!

#### USB Transfer (Recommended)

1. **Connect Kindle to Mac via USB cable**
2. **In Calibre:**
   - Select the converted book (KFX or AZW3 format)
   - Click "Send to device" button
   - Wait for "Jobs: 0" (bottom right corner)
3. **Eject Kindle:**
   - Click eject icon in Calibre
   - OR: Right-click Kindle in Finder > Eject
4. **Disconnect USB cable**
5. **Book appears on Kindle home screen**

#### Send to Kindle Email (NOT Recommended for Code)

**⚠️ WARNING:** Amazon converts EPUB in the cloud, which may destroy code formatting!

Only use this for simple text documents without code blocks.

```
1. Find Kindle email: Settings > Your Account > Send-to-Kindle Email
2. In Calibre: Right-click book > Connect/share > Email to...
3. Enter Kindle email address
4. Click OK
```

---

## Reading on Kindle

### Optimal Settings for Technical Docs

**Open the book, then:**

```
Tap top of screen > Aa (font settings)
```

**Recommended settings:**
- **Font:** Bookerly or Amazon Ember
- **Font Size:** 3-4 (smaller sizes better for code blocks)
- **Line Spacing:** Default
- **Margins:** Narrow (more code visible)
- **Orientation:** Portrait (unless wide tables)

### Navigation Tips

**Table of Contents:**
```
Tap top > Menu > Table of Contents
```

**Jump to specific section:**
- Use TOC to jump directly to guides
- Long-press to open in new location bar

**Search for commands:**
```
Tap top > Menu > Search
Type: "sqlite3" (finds all SQL references)
```

**Bookmarks:**
- Long-press a line > Add bookmark
- Great for marking favorite queries

### Reading Code Blocks

**How syntax highlighting appears on E-ink:**
- **Keywords:** Bold text (SELECT, FROM, WHERE)
- **Functions:** Italic text
- **Strings:** Underlined text
- **Comments:** Italic, lighter weight

**If code runs off screen:**
- Decrease font size (Aa > smaller)
- Rotate to landscape (wide code blocks)
- CSS ensures wrapping, but narrower fonts help

---

## Customization

### Adding More Documents

Edit `convert_to_kindle.sh` and add to the `DOCS` array:

```bash
DOCS=(
    "QUICK_REFERENCE.md"
    "DEVICE_IDENTIFICATION_GUIDE.md"
    "PROBE_REQUEST_ANALYSIS.md"
    "REALTIME_INVESTIGATION.md"
    "DEVICE_INVESTIGATION_QUERIES.md"
    "YOUR_NEW_GUIDE.md"  # Add here
)
```

### Changing Book Metadata

Edit these variables in `convert_to_kindle.sh`:

```bash
BOOK_TITLE="Your Custom Title"
BOOK_AUTHOR="Your Name"
BOOK_VERSION="2.0"
```

### Customizing Styles

Edit `kindle-style.css` to change:
- Code block background color
- Font sizes
- Header styling
- Table formatting

**Example: Darker code blocks**
```css
pre {
    background-color: #e8e8e8;  /* Darker grey */
}
```

Re-run conversion script after changes.

---

## Troubleshooting

### Issue: Pandoc not found

```bash
# Install Pandoc
brew install pandoc

# Verify installation
pandoc --version
```

### Issue: Calibre not in PATH

```bash
# Add Calibre CLI tools to PATH (add to ~/.zshrc)
export PATH="/Applications/Calibre.app/Contents/MacOS:$PATH"

# Reload shell
source ~/.zshrc
```

### Issue: Code blocks run off screen

**Cause:** Font size too large for code content

**Solution:**
1. On Kindle: Aa > Font size 3 or smaller
2. Rotate to landscape for wide tables
3. Edit `kindle-style.css` > reduce `pre { font-size: 0.75em; }`

### Issue: No syntax highlighting

**This is normal!** Kindle E-ink is grayscale, so:
- Colors become shades of grey/bold/italic
- Keywords are **bold**
- Comments are *italic*
- Strings are underlined

This is intentional for readability.

### Issue: Conversion fails

**Check that all markdown files exist:**
```bash
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG
ls -la *.md
```

**Run conversion with verbose output:**
```bash
./convert_to_kindle.sh 2>&1 | tee conversion.log
cat conversion.log  # Review errors
```

### Issue: Book doesn't appear on Kindle

**After USB transfer:**
1. Ensure Kindle was ejected properly
2. Try disconnecting/reconnecting USB
3. Restart Kindle: Settings > Device Options > Restart

**Check Calibre transfer log:**
```
Calibre > View > Show: Device errors
```

---

## Advanced: Updating the Book

When you update CYT documentation:

```bash
# 1. Regenerate EPUB
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG
./convert_to_kindle.sh

# 2. In Calibre, delete old version:
Right-click old book > Remove books

# 3. Import new EPUB:
Add books > select new CYT-Investigation-Guide.epub

# 4. Convert to KFX/AZW3 again

# 5. Transfer to Kindle (overwrites old version)
```

**Note:** Your bookmarks and highlights are preserved if you keep the same book title!

---

## File Reference

**Generated by conversion script:**
```
kindle_output/
├── CYT-Investigation-Guide.epub    # Main output
├── CALIBRE_INSTRUCTIONS.txt        # Calibre guide
├── metadata.yaml                   # Book metadata
└── title.md                        # Generated title page
```

**Source files:**
```
Chasing-Your-Tail-NG/
├── convert_to_kindle.sh            # Conversion script
├── kindle-style.css                # Xcode-style CSS
├── QUICK_REFERENCE.md              # Chapter 1
├── DEVICE_IDENTIFICATION_GUIDE.md  # Chapter 2
├── PROBE_REQUEST_ANALYSIS.md       # Chapter 3
├── REALTIME_INVESTIGATION.md       # Chapter 4
└── DEVICE_INVESTIGATION_QUERIES.md # Chapter 5
```

---

## Why This Workflow?

### Why Pandoc + Calibre (instead of direct Calibre)?

**Calibre's markdown converter has limitations:**
- ❌ No syntax highlighting
- ❌ Poor code block wrapping
- ❌ Can't merge multiple files with TOC
- ❌ Limited CSS control

**Pandoc pre-processing:**
- ✅ True syntax highlighting (pygments)
- ✅ Smart code wrapping (`white-space: pre-wrap`)
- ✅ Multi-file merging with single TOC
- ✅ Full CSS customization

### Why KFX over AZW3?

**KFX (Kindle Format 10):**
- Enhanced Typesetting engine
- Better monospace font rendering
- Superior code block layout
- Hyphenation control
- Published in 2015+, all modern Kindles support it

**AZW3 (Kindle Format 8):**
- Older format (2011)
- Works on ALL Kindles
- Good fallback if KFX fails
- Slightly worse code rendering

### Why USB over Send-to-Kindle?

**USB Transfer:**
- ✅ Preserves CSS exactly as designed
- ✅ No cloud conversion = no formatting loss
- ✅ Offline, instant

**Send-to-Kindle:**
- ❌ Amazon re-converts the file in cloud
- ❌ May strip custom CSS
- ❌ Code blocks can become unreadable
- ✅ Syncs reading position across devices (only benefit)

**For technical docs with code: ALWAYS use USB!**

---

## Resources

**Official Documentation:**
- Pandoc User Guide: https://pandoc.org/MANUAL.html
- Calibre Manual: https://manual.calibre-ebook.com/
- KFX Output Plugin: https://www.mobileread.com/forums/showthread.php?t=272407

**Communities:**
- r/Calibre - Calibre tips and troubleshooting
- r/kindle - Kindle device optimization
- MobileRead Forums - Ebook conversion expertise

**YouTube Tutorials:**
- Search: "Pandoc technical documentation Kindle"
- Search: "Calibre KFX plugin setup"

---

**Version:** 1.0
**Last Updated:** 2025-12-21
**Project:** Chasing Your Tail - Next Generation
