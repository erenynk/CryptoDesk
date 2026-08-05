#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="Caspian"
APP_ID="io.github.erenynk.CryptoDesk"

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"
PROJECT_ROOT="$(
    cd -- "${SCRIPT_DIR}/../.."
    pwd
)"

INSTALL_ROOT="${CASPIAN_INSTALL_ROOT:-${HOME}/.local/opt/caspian}"
APP_DIR="${INSTALL_ROOT}/app"
VENV_DIR="${INSTALL_ROOT}/venv"

LOCAL_BIN_DIR="${HOME}/.local/bin"
LAUNCHER_PATH="${LOCAL_BIN_DIR}/caspian"

XDG_DATA_ROOT="${XDG_DATA_HOME:-${HOME}/.local/share}"
APPLICATIONS_DIR="${XDG_DATA_ROOT}/applications"
DESKTOP_PATH="${APPLICATIONS_DIR}/${APP_ID}.desktop"
ICON_ROOT="${XDG_DATA_ROOT}/icons/hicolor"

DESKTOP_TEMPLATE="${SCRIPT_DIR}/${APP_ID}.desktop.in"

STAGE_DIR=""
BACKUP_DIR=""

usage() {
    cat <<'EOF'
Kullanım:
  bash packaging/fedora/install.sh

Ortam değişkenleri:
  CASPIAN_INSTALL_ROOT
      Varsayılan: ~/.local/opt/caspian
EOF
}

cleanup() {
    if [[ -n "${STAGE_DIR}" && -d "${STAGE_DIR}" ]]; then
        rm -rf -- "${STAGE_DIR}"
    fi
}

fail() {
    printf 'Hata: %s\n' "$*" >&2
    exit 1
}

require_command() {
    local command_name="$1"

    if ! command -v "${command_name}" >/dev/null 2>&1; then
        fail "'${command_name}' komutu bulunamadı."
    fi
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

install_python_environment() {
    mkdir -p -- "${INSTALL_ROOT}"

    if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
        printf 'Python sanal ortamı oluşturuluyor...\n'
        python3 -m venv "${VENV_DIR}" || fail \
            "Sanal ortam oluşturulamadı. Fedora'da python3 paketini kontrol et."
    fi

    printf 'Python bağımlılıkları kuruluyor...\n'
    "${VENV_DIR}/bin/python" \
        -m pip \
        install \
        --disable-pip-version-check \
        --requirement "${PROJECT_ROOT}/requirements.txt"
}

stage_application_files() {
    STAGE_DIR="$(
        mktemp -d "${INSTALL_ROOT}/.app-stage.XXXXXX"
    )"

    tar \
        --exclude='./.git' \
        --exclude='./.github' \
        --exclude='./.venv' \
        --exclude='./.pytest_cache' \
        --exclude='./.coverage' \
        --exclude='./build' \
        --exclude='./dist' \
        --exclude='./tests' \
        --exclude='./packaging' \
        --exclude='*/__pycache__' \
        --exclude='*.pyc' \
        --exclude='*.pyo' \
        -C "${PROJECT_ROOT}" \
        -cf - . \
        | tar -C "${STAGE_DIR}" -xf -

    [[ -f "${STAGE_DIR}/app.py" ]] || fail \
        "Kurulum kopyasında app.py bulunamadı."
}

activate_staged_application() {
    if [[ -d "${APP_DIR}" ]]; then
        BACKUP_DIR="$(
            mktemp -d "${INSTALL_ROOT}/.app-backup.XXXXXX"
        )"
        rmdir -- "${BACKUP_DIR}"
        mv -- "${APP_DIR}" "${BACKUP_DIR}"
    fi

    if ! mv -- "${STAGE_DIR}" "${APP_DIR}"; then
        if [[ -n "${BACKUP_DIR}" && -d "${BACKUP_DIR}" ]]; then
            mv -- "${BACKUP_DIR}" "${APP_DIR}"
        fi
        fail "Yeni uygulama dosyaları etkinleştirilemedi."
    fi

    STAGE_DIR=""

    if [[ -n "${BACKUP_DIR}" && -d "${BACKUP_DIR}" ]]; then
        rm -rf -- "${BACKUP_DIR}"
    fi
    BACKUP_DIR=""
}

install_launcher() {
    mkdir -p -- "${LOCAL_BIN_DIR}"

    {
        printf '#!/usr/bin/env bash\n'
        printf 'set -Eeuo pipefail\n'
        printf 'exec %q %q "$@"\n' \
            "${VENV_DIR}/bin/python" \
            "${APP_DIR}/app.py"
    } > "${LAUNCHER_PATH}"

    chmod 0755 "${LAUNCHER_PATH}"
}

install_desktop_entry() {
    [[ -f "${DESKTOP_TEMPLATE}" ]] || fail \
        "Masaüstü şablonu bulunamadı: ${DESKTOP_TEMPLATE}"

    mkdir -p -- "${APPLICATIONS_DIR}"

    local desktop_content
    desktop_content="$(
        < "${DESKTOP_TEMPLATE}"
    )"
    desktop_content="${desktop_content//@EXEC@/${LAUNCHER_PATH}}"

    printf '%s\n' "${desktop_content}" > "${DESKTOP_PATH}"
    chmod 0644 "${DESKTOP_PATH}"
}

install_icons() {
    local icon_source
    local icon_size
    local installed_count=0

    shopt -s nullglob

    for icon_source in \
        "${APP_DIR}/assets/icons/hicolor/"*/apps/"${APP_ID}.png"
    do
        icon_size="$(
            basename -- "$(
                dirname -- "$(
                    dirname -- "${icon_source}"
                )"
            )"
        )"

        install \
            -D \
            -m 0644 \
            "${icon_source}" \
            "${ICON_ROOT}/${icon_size}/apps/${APP_ID}.png"

        installed_count=$((installed_count + 1))
    done

    shopt -u nullglob

    if (( installed_count == 0 )); then
        fail "Kurulabilecek hicolor uygulama simgesi bulunamadı."
    fi
}

main() {
    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        usage
        exit 0
    fi

    if (( $# != 0 )); then
        usage >&2
        exit 2
    fi

    require_command python3
    require_command tar
    require_command mktemp
    require_command install

    [[ -f "${PROJECT_ROOT}/app.py" ]] || fail \
        "Bu betik Caspian proje deposu içinden çalıştırılmalı."
    [[ -f "${PROJECT_ROOT}/requirements.txt" ]] || fail \
        "requirements.txt bulunamadı."

    trap cleanup EXIT

    install_python_environment
    stage_application_files
    activate_staged_application
    install_launcher
    install_desktop_entry
    install_icons
    refresh_desktop_caches

    trap - EXIT

    printf '\n%s kurulumu tamamlandı.\n' "${APP_NAME}"
    printf 'Menü adı : %s\n' "${APP_NAME}"
    printf 'Komut     : %s\n' "${LAUNCHER_PATH}"
    printf 'Uygulama  : %s\n' "${APP_DIR}"
    printf '\nBaşlatmak için: caspian\n'
}

main "$@"
