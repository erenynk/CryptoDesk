#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="Caspian"
APP_ID="io.github.erenynk.CryptoDesk"

INSTALL_ROOT="${CASPIAN_INSTALL_ROOT:-${HOME}/.local/opt/caspian}"

LOCAL_BIN_DIR="${HOME}/.local/bin"
LAUNCHER_PATH="${LOCAL_BIN_DIR}/caspian"

XDG_DATA_ROOT="${XDG_DATA_HOME:-${HOME}/.local/share}"
APPLICATIONS_DIR="${XDG_DATA_ROOT}/applications"
DESKTOP_PATH="${APPLICATIONS_DIR}/${APP_ID}.desktop"
ICON_ROOT="${XDG_DATA_ROOT}/icons/hicolor"
USER_DATA_DIR="${XDG_DATA_ROOT}/CryptoDesk"

XDG_CONFIG_ROOT="${XDG_CONFIG_HOME:-${HOME}/.config}"
AUTOSTART_PATH="${XDG_CONFIG_ROOT}/autostart/cryptodesk.desktop"

PURGE_DATA=false

usage() {
    cat <<'EOF'
Kullanım:
  bash packaging/fedora/uninstall.sh
  bash packaging/fedora/uninstall.sh --purge-data

Seçenekler:
  --purge-data
      Ayarlar, veritabanı ve şifrelenmiş uygulama verileri dahil
      ~/.local/share/CryptoDesk dizinini de siler.

Varsayılan kaldırma kullanıcı verilerini korur.
EOF
}

refresh_desktop_caches() {
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "${APPLICATIONS_DIR}" \
            >/dev/null 2>&1 || true
    fi

    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache \
            --force \
            --ignore-theme-index \
            "${ICON_ROOT}" \
            >/dev/null 2>&1 || true
    fi

    if command -v kbuildsycoca6 >/dev/null 2>&1; then
        kbuildsycoca6 --noincremental \
            >/dev/null 2>&1 || true
    elif command -v kbuildsycoca5 >/dev/null 2>&1; then
        kbuildsycoca5 --noincremental \
            >/dev/null 2>&1 || true
    fi
}

remove_icons() {
    local icon_path

    shopt -s nullglob

    for icon_path in \
        "${ICON_ROOT}/"*/apps/"${APP_ID}.png"
    do
        rm -f -- "${icon_path}"
    done

    shopt -u nullglob
}

parse_arguments() {
    while (( $# > 0 )); do
        case "$1" in
            --purge-data)
                PURGE_DATA=true
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                printf 'Bilinmeyen seçenek: %s\n\n' "$1" >&2
                usage >&2
                exit 2
                ;;
        esac
        shift
    done
}

main() {
    parse_arguments "$@"

    rm -rf -- "${INSTALL_ROOT}"
    rm -f -- "${LAUNCHER_PATH}"
    rm -f -- "${DESKTOP_PATH}"
    rm -f -- "${AUTOSTART_PATH}"
    remove_icons

    if [[ "${PURGE_DATA}" == true ]]; then
        rm -rf -- "${USER_DATA_DIR}"
        printf '%s kullanıcı verileri silindi: %s\n' \
            "${APP_NAME}" \
            "${USER_DATA_DIR}"
    else
        printf '%s kullanıcı verileri korundu: %s\n' \
            "${APP_NAME}" \
            "${USER_DATA_DIR}"
    fi

    refresh_desktop_caches

    printf '%s kaldırıldı.\n' "${APP_NAME}"
}

main "$@"
