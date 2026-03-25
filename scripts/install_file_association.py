#!/usr/bin/env python3
"""
install_file_association.py
===========================
Register .gfp files with your OS so that double-clicking them opens
GraffitiPlot with an interactive terminal.

Usage:
    python scripts/install_file_association.py          # install
    python scripts/install_file_association.py --remove # uninstall

Requirements: ``graffiti-plot`` must already be installed (``pip install graffiti-plot``).
The ``gfp-open`` command must be on PATH (it is when installed via pip).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gfp_open_path() -> str | None:
    """Return the full path to the gfp-open executable, or None."""
    return shutil.which("gfp-open")


def _python_exe() -> str:
    return sys.executable


# ---------------------------------------------------------------------------
# Linux (XDG / freedesktop)
# ---------------------------------------------------------------------------

_MIME_TYPE = "application/x-graffiti-plot"
_MIME_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-graffiti-plot">
    <comment>GraffitiPlot Figure</comment>
    <glob pattern="*.gfp"/>
  </mime-type>
</mime-info>
"""

_DESKTOP_TEMPLATE = """\
[Desktop Entry]
Version=1.0
Type=Application
Name=GraffitiPlot Viewer
Comment=Open GraffitiPlot .gfp figures interactively
Exec={exec_cmd} %f
Icon=python3
Terminal=true
MimeType=application/x-graffiti-plot;
Categories=Science;Education;
"""


def install_linux():
    home = Path.home()

    # ── 1. Register MIME type ──────────────────────────────────────────────
    mime_dir = home / ".local" / "share" / "mime" / "packages"
    mime_dir.mkdir(parents=True, exist_ok=True)
    mime_file = mime_dir / "graffiti-plot.xml"
    mime_file.write_text(_MIME_XML)
    print(f"  Wrote MIME type: {mime_file}")

    ok = subprocess.run(
        ["update-mime-database", str(home / ".local" / "share" / "mime")],
        capture_output=True,
    ).returncode == 0
    if ok:
        print("  Updated MIME database.")
    else:
        print("  Warning: update-mime-database failed (may not be installed).")

    # ── 2. Create .desktop entry ───────────────────────────────────────────
    exec_cmd = _gfp_open_path() or f"{_python_exe()} -m graffiti_plot.viewer"
    desktop_dir = home / ".local" / "share" / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = desktop_dir / "graffiti-plot.desktop"
    desktop_file.write_text(_DESKTOP_TEMPLATE.format(exec_cmd=exec_cmd))
    print(f"  Wrote .desktop entry: {desktop_file}")

    ok = subprocess.run(
        ["update-desktop-database", str(desktop_dir)],
        capture_output=True,
    ).returncode == 0
    if ok:
        print("  Updated desktop database.")
    else:
        print("  Warning: update-desktop-database failed (may not be installed).")

    # ── 3. Associate MIME type with the .desktop entry ────────────────────
    ok = subprocess.run(
        [
            "xdg-mime", "default",
            "graffiti-plot.desktop",
            _MIME_TYPE,
        ],
        capture_output=True,
    ).returncode == 0
    if ok:
        print(f"  Associated {_MIME_TYPE} → graffiti-plot.desktop")
    else:
        print("  Warning: xdg-mime failed.  Try running manually:")
        print(f"    xdg-mime default graffiti-plot.desktop {_MIME_TYPE}")

    print()
    print("Done.  You may need to log out and back in for changes to take effect.")
    print("Test with:  xdg-open my_plot.gfp")


def uninstall_linux():
    home = Path.home()
    removed = []

    for p in [
        home / ".local" / "share" / "mime" / "packages" / "graffiti-plot.xml",
        home / ".local" / "share" / "applications" / "graffiti-plot.desktop",
    ]:
        if p.exists():
            p.unlink()
            removed.append(str(p))

    for cmd, arg in [
        (["update-mime-database", str(home / ".local/share/mime")], None),
        (["update-desktop-database", str(home / ".local/share/applications")], None),
    ]:
        subprocess.run(cmd, capture_output=True)

    if removed:
        print("Removed:", "\n  ".join(removed))
    else:
        print("Nothing to remove.")


# ---------------------------------------------------------------------------
# macOS
# ---------------------------------------------------------------------------

_MACOS_APP_TEMPLATE = """\
#!/bin/bash
# GraffitiPlot file opener
GFP_FILE="$1"
{python} -c "
import graffiti_plot, sys
sys.argv = ['gfp-open', '$GFP_FILE']
import graffiti_plot.viewer as v
v.main()
"
"""


def install_macos():
    """Create an Automator-style shell app and register it with Launch Services."""
    app_dir = Path.home() / "Applications" / "GraffitiPlot.app"
    contents = app_dir / "Contents" / "MacOS"
    contents.mkdir(parents=True, exist_ok=True)

    # Info.plist
    plist = app_dir / "Contents" / "Info.plist"
    plist.write_text(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key><string>org.graffitiplot.viewer</string>
    <key>CFBundleName</key><string>GraffitiPlot</string>
    <key>CFBundleExecutable</key><string>gfp-open-wrapper</string>
    <key>CFBundleDocumentTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeExtensions</key><array><string>gfp</string></array>
            <key>CFBundleTypeName</key><string>GraffitiPlot Figure</string>
            <key>CFBundleTypeRole</key><string>Editor</string>
        </dict>
    </array>
</dict>
</plist>
""")

    # Executable shell wrapper
    wrapper = contents / "gfp-open-wrapper"
    wrapper.write_text(_MACOS_APP_TEMPLATE.format(python=_python_exe()))
    wrapper.chmod(0o755)

    print(f"  Created app bundle: {app_dir}")

    # Register with Launch Services
    ok = subprocess.run(
        ["/System/Library/Frameworks/CoreServices.framework/Versions/A"
         "/Frameworks/LaunchServices.framework/Versions/A"
         "/Support/lsregister", "-f", str(app_dir)],
        capture_output=True,
    ).returncode == 0
    if ok:
        print("  Registered with Launch Services.")
    else:
        print("  Note: run this to finish registration:")
        print(f"    /System/Library/…/lsregister -f {app_dir}")

    # Set as default via duti (if installed)
    if shutil.which("duti"):
        subprocess.run(
            ["duti", "-s", "org.graffitiplot.viewer", ".gfp", "all"],
            capture_output=True,
        )
        print("  Set default app via duti.")
    else:
        print("  Tip: install 'duti' (brew install duti) for automatic default-app setting.")
        print("  Alternatively: right-click a .gfp file → 'Open With' → 'Other…' → select GraffitiPlot.app")


def uninstall_macos():
    app_dir = Path.home() / "Applications" / "GraffitiPlot.app"
    if app_dir.exists():
        import shutil as _sh
        _sh.rmtree(app_dir)
        print(f"Removed {app_dir}")
    else:
        print("Nothing to remove.")


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

def install_windows():
    """Register .gfp → gfp-open via the Windows registry."""
    try:
        import winreg
    except ImportError:
        print("Error: winreg not available (not running on Windows).")
        return

    gfp_exe = _gfp_open_path()
    if gfp_exe is None:
        gfp_exe = f'"{_python_exe()}" -m graffiti_plot.viewer'
    else:
        gfp_exe = f'"{gfp_exe}"'

    cmd = f'{gfp_exe} "%1"'

    keys = {
        r"Software\Classes\.gfp": ("", "GraffitiPlotFile"),
        r"Software\Classes\GraffitiPlotFile": ("", "GraffitiPlot Figure"),
        r"Software\Classes\GraffitiPlotFile\DefaultIcon": ("", f"{_python_exe()},0"),
        r"Software\Classes\GraffitiPlotFile\shell\open\command": ("", cmd),
    }

    for key_path, (value_name, value_data) in keys.items():
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, value_data)
        winreg.CloseKey(key)
        print(f"  Set: HKCU\\{key_path} = {value_data!r}")

    # Notify Explorer
    subprocess.run(["ie4uinit.exe", "-show"], capture_output=True)
    print()
    print("Done.  Double-clicking .gfp files will now open GraffitiPlot.")


def uninstall_windows():
    try:
        import winreg
    except ImportError:
        return

    for key_path in [
        r"Software\Classes\GraffitiPlotFile\shell\open\command",
        r"Software\Classes\GraffitiPlotFile\shell\open",
        r"Software\Classes\GraffitiPlotFile\shell",
        r"Software\Classes\GraffitiPlotFile\DefaultIcon",
        r"Software\Classes\GraffitiPlotFile",
        r"Software\Classes\.gfp",
    ]:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            print(f"  Removed: HKCU\\{key_path}")
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Install or remove the .gfp file association for GraffitiPlot."
    )
    parser.add_argument("--remove", action="store_true", help="Uninstall the file association.")
    args = parser.parse_args()

    gfp_open = _gfp_open_path()
    if gfp_open:
        print(f"Found gfp-open: {gfp_open}")
    else:
        print("Warning: 'gfp-open' not found on PATH.")
        print("  Make sure graffiti-plot is installed: pip install graffiti-plot")
        print("  Then re-run this script.")
        print()

    if sys.platform.startswith("linux"):
        if args.remove:
            print("Uninstalling Linux file association …")
            uninstall_linux()
        else:
            print("Installing Linux file association (XDG) …")
            install_linux()

    elif sys.platform == "darwin":
        if args.remove:
            print("Uninstalling macOS file association …")
            uninstall_macos()
        else:
            print("Installing macOS file association …")
            install_macos()

    elif sys.platform == "win32":
        if args.remove:
            print("Uninstalling Windows file association …")
            uninstall_windows()
        else:
            print("Installing Windows file association …")
            install_windows()

    else:
        print(f"Unsupported platform: {sys.platform}")
        sys.exit(1)


if __name__ == "__main__":
    main()
