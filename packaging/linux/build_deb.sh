#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="0.2.0"
PKG_DIR="${REPO_ROOT}/packaging/linux"
STAGE_DIR="${PKG_DIR}/build/typist_${VERSION}_all"
DIST_DIR="${REPO_ROOT}/dist"

echo "==> Preparing Debian build tree..."
rm -rf "${PKG_DIR}/build"
mkdir -p "${STAGE_DIR}/DEBIAN"
mkdir -p "${STAGE_DIR}/usr/bin"
mkdir -p "${STAGE_DIR}/usr/lib/typist"
mkdir -p "${STAGE_DIR}/lib/udev/rules.d"
mkdir -p "${STAGE_DIR}/usr/lib/systemd/user"
mkdir -p "${DIST_DIR}"

# Copy DEBIAN control files
cp "${PKG_DIR}/DEBIAN/control" "${STAGE_DIR}/DEBIAN/"
cp "${PKG_DIR}/DEBIAN/postinst" "${STAGE_DIR}/DEBIAN/"
cp "${PKG_DIR}/DEBIAN/prerm" "${STAGE_DIR}/DEBIAN/"
chmod 755 "${STAGE_DIR}/DEBIAN/postinst" "${STAGE_DIR}/DEBIAN/prerm"

# Copy python source
cp -r "${REPO_ROOT}/src/typist" "${STAGE_DIR}/usr/lib/typist/"

# Create /usr/bin/typist launcher
cat <<'EOF' > "${STAGE_DIR}/usr/bin/typist"
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/lib/typist")
from typist.main import main
if __name__ == "__main__":
    main()
EOF
chmod 755 "${STAGE_DIR}/usr/bin/typist"

# Copy udev rules and systemd service
cp "${REPO_ROOT}/udev/99-ulanzi-au05.rules" "${STAGE_DIR}/lib/udev/rules.d/"
cp "${REPO_ROOT}/udev/99-uinput.rules" "${STAGE_DIR}/lib/udev/rules.d/"
cp "${REPO_ROOT}/systemd/typist.service" "${STAGE_DIR}/usr/lib/systemd/user/"

# Build package
echo "==> Building .deb package..."
dpkg-deb --build --root-owner-group "${STAGE_DIR}" "${DIST_DIR}/typist_${VERSION}_all.deb"

echo "==> Successfully created: ${DIST_DIR}/typist_${VERSION}_all.deb"
