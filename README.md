# Hover 📌

> A lightweight, standalone desktop screenshot utility inspired by Grant Thornton's **"Picture This"** tool.

**Hover** lets you snip any region of your screen and immediately displays that snip as an undecorated, borderless, floating window pinned permanently on top of all other applications.

---

## ✨ Features

- **Permanent Foreground Priority (`Always on Top`)**: Pinned snips never lose hierarchy, even when clicking into complex workflows like Microsoft Excel, PowerPoint, IDEs, or web apps.
- **Undecorated & Borderless**: No OS title bars, menus, or window chrome. Features a crisp 1-pixel boundary so pure white documents stand out.
- **Draggable Anywhere**: Click and drag from any point on the image to position it effortlessly on your desktop.
- **Frictionless Dismissal**: Simply **Right-Click** or press **`Escape`** while focusing the window to instantly dismiss it.
- **Multiple Simultaneous Pins**: Keep multiple references open side-by-side (e.g., comparing figures from two different spreadsheets or slides).
- **Smooth Mouse Wheel Zoom**: Scroll your mouse wheel over any pinned snip to zoom in or out for reading fine print, small numbers, or diagrams.
- **Direct Clipboard Integration**: Press **`Ctrl+C`** on any pinned window to copy the image back to your clipboard.
- **Global Hotkey & System Tray**: Trigger new snips anytime with **`Ctrl + Shift + S`** or by clicking the Hover tray icon.
- **Multi-Monitor & Mixed-DPI Support**: Automatically captures across all connected displays without coordinate clipping.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
- **Python 3.10+**
- If Python is not yet installed on your system, you can install it using `winget` in PowerShell or from [python.org](https://www.python.org/downloads/):
  ```powershell
  winget install -e --id Python.Python.3.12
  ```

### 2. Install Dependencies
In your terminal, navigate to the `Try` directory and install requirements:
```powershell
pip install -r requirements.txt
```

*(Or inside a virtual environment)*:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🚀 Running Hover

Start the application:
```powershell
python main.py
```

Hover runs quietly in your **Windows System Tray** with a custom icon.

---

## ⌨️ Controls & Shortcuts

| Action | Shortcut / Trigger |
| :--- | :--- |
| **New Snip** | `Ctrl + Alt + S` / `F8` / `Ctrl + Shift + S` or Quick Bar |
| **Cancel Snip Overlay** | `Escape` or Right-Click |
| **Move Pinned Snip** | Left-Click & Drag anywhere on the snip |
| **Open Tools Menu** | **Right-Click** anywhere on the snip |
| **Diff Slider (Before / After)** | Press **`D`** or Right-Click → *Diff with Screen Underneath* |
| **Drag Comparison Divider** | Left-Click & Drag the central slider handle (`◀ ▶`) |
| **Swap Before / After** | Right-Click → *Swap* |
| **Adjust Opacity (5% steps)** | **`Ctrl + Shift + Mouse Wheel Up / Down`** |
| **Set Opacity Preset** | Right-Click → *Opacity (100%, 85%, 70%, 50%, 30%)* |
| **Toggle Ghost (Click-Through)** | **`Ctrl + G`** or Right-Click → *Ghost Mode* |
| **Un-Ghost All Pins** | **`Ctrl + Alt + G`** or Quick Bar `[👻 Un-Ghost]` |
| **Toggle Highlighter Pen** | Press **`H`** or Right-Click → *Highlight Mode* |
| **Cycle Highlight Color** | Right-Click → *Highlight Color* (🟡, 🟢, 🌸, 🔵) |
| **Undo Last Highlight** | **`Ctrl + Z`** or Right-Click → *Undo* |
| **Copy Image (+ Highlights)** | **`Ctrl + C`** or Right-Click → *Copy* |
| **Save Image to Disk** | **`Ctrl + S`** or Right-Click → *Save Image As...* |
| **Dismiss / Close Snip** | Press **`Escape`** or Right-Click → *Close* |
| **Zoom In / Out** | **Mouse Wheel Up / Down** (or `Ctrl + +/-`) |
| **Reset Zoom (100%)** | **Double-Click** or `Ctrl + 0` |
| **Close All Pinned Snips** | Quick Bar / Tray Menu → *Close All Pinned Snips* |
| **Exit Application** | Quick Bar `✕` or System Tray Menu → *Exit* |

---

## 📂 Project Architecture

```
Try/
├── assets/
│   ├── icon.ico         # Multi-size Windows application icon (16x16 -> 256x256)
│   └── icon.png         # High-resolution PNG logo
├── app/
│   ├── __init__.py      # Package metadata
│   ├── canvas.py        # PinnedCanvas floating window class
│   ├── hotkey.py        # Native Win32 global hotkey filter (ctypes)
│   ├── overlay.py       # SnippingOverlay screen capture & rubberband selector
│   ├── tray.py          # System tray icon and context menu
│   └── utils.py         # Icon loader/generator, DPI & clipboard utilities
├── run.bat              # Quick double-click launcher
├── main.py              # Application controller & entry point
├── requirements.txt     # Minimal dependencies (PyQt6, Pillow)
└── README.md            # Documentation
```
