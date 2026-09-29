# Samba

Containerized SMB sharing for the host `/mnt` tree.

The container generates `/etc/samba/smb.conf` at startup and creates the Samba
password database inside the container from runtime environment variables. Do
not commit real passwords; put them in the local `.env`, which is ignored by
git, or use `SMB_PASSWORD_FILE`.

Required runtime value:

```bash
SMB_PASSWORD=...
```

Useful optional values:

```bash
SMB_USERNAME=nas
SMB_VERSION=3
SMB_SHARE_NAME=mounts
SMB_NETBIOS_NAME=nas-mini
```

The NetBIOS name should match the hostname clients use to reach the server.

`SMB_VERSION` defaults to `3`. It accepts `1`, `2`, `3`, `NT1`, `SMB2`,
`SMB3`, `SMB3_02`, and `SMB3_11`. Major versions select a compatible range: `3` allows `SMB3_00` through
`SMB3_11`, `2` allows `SMB2_02` through `SMB2_10`, and `1` pins `NT1`.
Specific dialects such as `SMB3_02` are pinned exactly. Set
`SMB_MIN_PROTOCOL` and `SMB_MAX_PROTOCOL` directly if a custom range is needed.

Because the host currently owns TCP ports 139/445 and UDP ports 137/138 while
the native Samba service is running, start this service only after stopping the
host service or changing the published ports.

## Client mount

On another Linux machine on the LAN, install the CIFS mount helper:

```bash
sudo apt install cifs-utils
```

Then create a root-owned credentials file for the Samba user. Keep this file
outside the repository.

```bash
sudo mkdir -p /etc/samba/credentials
sudo nano /etc/samba/credentials/nas-mini
sudo chmod 600 /etc/samba/credentials/nas-mini
```

Example contents:

```ini
username=nas
password=your_smb_password
domain=NAS-MINI
```

Create the local mount point and mount the share as a kernel CIFS filesystem:

```bash
sudo mkdir -p /mnt/nas
sudo mount -t cifs //nas-mini.local/mounts /mnt/nas \
  -o credentials=/etc/samba/credentials/nas-mini,uid=1000,gid=1000,vers=3.0,nodfs,sec=ntlmssp,nosharesock
```

Equivalent `/etc/fstab` entry:

```fstab
//nas-mini.local/mounts /mnt/nas cifs credentials=/etc/samba/credentials/nas-mini,uid=1000,gid=1000,vers=3.0,nodfs,sec=ntlmssp,nosharesock,_netdev,nofail,x-systemd.automount 0 0
```

The `domain` value should match `SMB_NETBIOS_NAME`; with the default configuration that is `NAS-MINI`. If local DNS does not resolve `nas-mini.local`, use the server LAN IP address instead.

