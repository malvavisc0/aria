#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build-appimage.sh — Build the Aria GUI AppImage (Linux x86_64)
#
# Prerequisites:
#   - uv (https://docs.astral.sh/uv/)
#   - appimagetool (downloaded automatically if not found)
#
# Usage (from project root):
#   ./packaging/build-appimage.sh
#
# Output:
#   dist/Aria-x86_64.AppImage
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
APPDIR="${DIST_DIR}/Aria.AppDir"
APPIMAGE_OUT="${DIST_DIR}/Aria-x86_64.AppImage"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── 1. Ensure we are on Linux ─────────────────────────────────────────────────
[[ "$(uname -s)" == "Linux" ]] || error "AppImage builds are Linux-only."

# ── 2. Ensure uv is available ─────────────────────────────────────────────────
command -v uv &>/dev/null || error "uv not found. Install from https://docs.astral.sh/uv/"

# ── 3. Install/sync dependencies (including GUI extra and dev group) ──────────
info "Syncing dependencies (gui + dev)..."
cd "${ROOT_DIR}"
uv sync --extra gui --group dev
success "Dependencies ready."

# ── 4. Run PyInstaller ────────────────────────────────────────────────────────
info "Running PyInstaller..."
uv run pyinstaller packaging/aria-gui.spec --noconfirm
success "PyInstaller build complete: ${DIST_DIR}/aria-gui/"

# ── 5. Build the AppDir structure ─────────────────────────────────────────────
info "Building AppDir structure..."
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"

# Copy the PyInstaller one-folder bundle into AppDir
cp -r "${DIST_DIR}/aria-gui/." "${APPDIR}/usr/bin/"

# ── 6. AppRun entry point ─────────────────────────────────────────────────────
cat > "${APPDIR}/AppRun" << 'EOF'
#!/usr/bin/env bash
# AppRun — entry point for the Aria AppImage
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/bin:${LD_LIBRARY_PATH:-}"
# Qt platform plugin path
export QT_PLUGIN_PATH="${HERE}/usr/bin/PySide6/Qt/plugins"
export QML2_IMPORT_PATH="${HERE}/usr/bin/PySide6/Qt/qml"
exec "${HERE}/usr/bin/aria-gui" "$@"
EOF
chmod +x "${APPDIR}/AppRun"

# ── 7. Desktop entry ──────────────────────────────────────────────────────────
cat > "${APPDIR}/aria-gui.desktop" << 'EOF'
[Desktop Entry]
Name=Aria
Comment=AI Assistant with web UI and local LLM support
Exec=aria-gui
Icon=aria-gui
Type=Application
Categories=Utility;Science;
Terminal=false
EOF

# Also place the desktop file in the standard location
cp "${APPDIR}/aria-gui.desktop" "${APPDIR}/usr/share/applications/aria-gui.desktop"

# ── 8. Icon ───────────────────────────────────────────────────────────────────
# Convert favicon.png to the AppImage icon (must be named after the Exec= value)
if command -v convert &>/dev/null; then
    convert "${ROOT_DIR}/public/favicon.png" -resize 256x256 \
        "${APPDIR}/usr/share/icons/hicolor/256x256/apps/aria-gui.png"
    cp "${APPDIR}/usr/share/icons/hicolor/256x256/apps/aria-gui.png" \
        "${APPDIR}/aria-gui.png"
else
    warn "ImageMagick 'convert' not found — copying favicon.png as icon directly."
    cp "${ROOT_DIR}/public/favicon.png" "${APPDIR}/aria-gui.png"
    cp "${ROOT_DIR}/public/favicon.png" \
        "${APPDIR}/usr/share/icons/hicolor/256x256/apps/aria-gui.png"
fi

# ── 9. Download appimagetool if not present ───────────────────────────────────
APPIMAGETOOL="${DIST_DIR}/appimagetool-x86_64.AppImage"
if [[ ! -x "${APPIMAGETOOL}" ]]; then
    info "Downloading appimagetool..."
    curl -fsSL -o "${APPIMAGETOOL}" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "${APPIMAGETOOL}"
    success "appimagetool downloaded."
fi

# ── 10. Build the AppImage ────────────────────────────────────────────────────
info "Building AppImage..."
ARCH=x86_64 "${APPIMAGETOOL}" "${APPDIR}" "${APPIMAGE_OUT}"

success "AppImage built: ${APPIMAGE_OUT}"
echo ""
echo "  Run with:  ${APPIMAGE_OUT}"
echo "  Or:        chmod +x ${APPIMAGE_OUT} && ${APPIMAGE_OUT}"
