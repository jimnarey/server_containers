#!/bin/bash
set -euo pipefail

USERID=${USERID:-1000}
GROUPID=${GROUPID:-1000}
SMB_USERNAME=${SMB_USERNAME:-nas}
SMB_PASSWORD=${SMB_PASSWORD:-}
SMB_PASSWORD_FILE=${SMB_PASSWORD_FILE:-}
SMB_WORKGROUP=${SMB_WORKGROUP:-WORKGROUP}
SMB_NETBIOS_NAME=${SMB_NETBIOS_NAME:-}
SMB_SERVER_STRING=${SMB_SERVER_STRING:-%h server (Samba, Docker)}
SMB_SHARE_NAME=${SMB_SHARE_NAME:-mounts}
SMB_SHARE_COMMENT=${SMB_SHARE_COMMENT:-NAS Mounts}
SMB_SHARE_PATH=${SMB_SHARE_PATH:-/mnt}
SMB_VERSION=${SMB_VERSION:-3}
SMB_BROWSEABLE=${SMB_BROWSEABLE:-yes}
SMB_WIDE_LINKS=${SMB_WIDE_LINKS:-yes}

normalize_protocol_range() {
    case "${1^^}" in
        1|SMB1|NT1) echo "NT1 NT1" ;;
        2|SMB2) echo "SMB2_02 SMB2_10" ;;
        2_02|SMB2_02) echo "SMB2_02 SMB2_02" ;;
        2_10|SMB2_10) echo "SMB2_10 SMB2_10" ;;
        3|SMB3) echo "SMB3_00 SMB3_11" ;;
        3_00|SMB3_00) echo "SMB3_00 SMB3_00" ;;
        3_02|SMB3_02) echo "SMB3_02 SMB3_02" ;;
        3_11|SMB3_11) echo "SMB3_11 SMB3_11" ;;
        *)
            echo "Unsupported SMB_VERSION '${1}'. Use 1, 2, 3, NT1, SMB2, SMB3, SMB3_02, or SMB3_11." >&2
            exit 1
            ;;
    esac
}

read -r DEFAULT_MIN_PROTOCOL DEFAULT_MAX_PROTOCOL < <(normalize_protocol_range "$SMB_VERSION")
SMB_MIN_PROTOCOL=${SMB_MIN_PROTOCOL:-$DEFAULT_MIN_PROTOCOL}
SMB_MAX_PROTOCOL=${SMB_MAX_PROTOCOL:-$DEFAULT_MAX_PROTOCOL}

if [[ -n "$SMB_PASSWORD_FILE" ]]; then
    if [[ ! -r "$SMB_PASSWORD_FILE" ]]; then
        echo "SMB_PASSWORD_FILE is set but is not readable: $SMB_PASSWORD_FILE" >&2
        exit 1
    fi
    SMB_PASSWORD=$(<"$SMB_PASSWORD_FILE")
fi

if [[ -z "$SMB_PASSWORD" ]]; then
    echo "SMB_PASSWORD or SMB_PASSWORD_FILE must be set before starting the Samba container." >&2
    exit 1
fi

if [[ "$SMB_USERNAME" == "root" ]]; then
    echo "SMB_USERNAME must not be root." >&2
    exit 1
fi

if [[ -z "$SMB_NETBIOS_NAME" ]]; then
    SMB_NETBIOS_NAME=${HOSTNAME%%.*}
fi

groupmod -o -g "$GROUPID" runuser
usermod -o -u "$USERID" -g "$GROUPID" -c "$SMB_USERNAME" runuser

if [[ "$SMB_USERNAME" != "runuser" ]]; then
    if getent passwd "$SMB_USERNAME" >/dev/null; then
        echo "SMB_USERNAME already exists in the image: $SMB_USERNAME" >&2
        exit 1
    fi
    if getent group "$SMB_USERNAME" >/dev/null; then
        echo "A group already exists in the image with SMB_USERNAME: $SMB_USERNAME" >&2
        exit 1
    fi
    groupmod -n "$SMB_USERNAME" runuser
    usermod -l "$SMB_USERNAME" -d "/home/$SMB_USERNAME" -m runuser
fi

mkdir -p /run/samba /var/log/samba
chown -R "$SMB_USERNAME:$SMB_USERNAME" "/home/$SMB_USERNAME"

cat > /etc/samba/smb.conf <<EOF
[global]
   workgroup = $SMB_WORKGROUP
   netbios name = $SMB_NETBIOS_NAME
   server string = $SMB_SERVER_STRING
   server role = standalone server
   map to guest = Bad User
   log file = /var/log/samba/log.%m
   logging = file
   max log size = 1000
   load printers = no
   printing = bsd
   printcap name = /dev/null
   disable spoolss = yes
   host msdfs = no
   unix extensions = no
   allow insecure wide links = yes
   server min protocol = $SMB_MIN_PROTOCOL
   server max protocol = $SMB_MAX_PROTOCOL

[$SMB_SHARE_NAME]
   comment = $SMB_SHARE_COMMENT
   path = $SMB_SHARE_PATH
   read only = no
   browseable = $SMB_BROWSEABLE
   guest ok = no
   msdfs root = no
   valid users = $SMB_USERNAME
   force user = $SMB_USERNAME
   force group = $SMB_USERNAME
   follow symlinks = yes
   wide links = $SMB_WIDE_LINKS
EOF

pdbedit -x "$SMB_USERNAME" >/dev/null 2>&1 || true
printf '%s\n%s\n' "$SMB_PASSWORD" "$SMB_PASSWORD" | smbpasswd -s -a "$SMB_USERNAME" >/dev/null
smbpasswd -e "$SMB_USERNAME" >/dev/null

echo "Starting Samba share //$HOSTNAME/$SMB_SHARE_NAME for user $SMB_USERNAME using protocol range $SMB_MIN_PROTOCOL-$SMB_MAX_PROTOCOL"
exec supervisord -c /etc/supervisord.conf
