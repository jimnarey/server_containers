# VS Code in the Browser

This service runs [code-server](https://coder.com/docs/code-server) directly in
the browser. It does not run the VS Code Electron desktop, X11, VNC, or noVNC.

Authentication is provided by the Caddy reverse proxy inherited from
`base-ubuntu-caddy-24`. It uses the repository-wide `CADDY_USER` and
`CADDY_HASH` settings.

## Start the service

```sh
docker compose build vscode
docker compose up -d vscode
```

Open `http://<docker-host>:9033` and sign in with the Caddy credentials.

The host directory configured by `VSCODE_WORKSPACE` is mounted at `/workspace`.
The default is `/mnt/data/projects`; override it in `.env` as required:

```dotenv
VSCODE_WORKSPACE=/mnt/work/projects
```

Settings, credentials, sessions, and installed extensions persist in the
`vscode-home` volume mounted at `/home/runuser`.

## Extensions

Install extensions from the Extensions view in the browser, or through Compose:

```sh
docker compose exec --user runuser vscode \
  code-server --install-extension ms-python.python
```

Install a downloaded VSIX file with:

```sh
docker compose exec --user runuser vscode \
  code-server --install-extension /workspace/path/to/extension.vsix
```

code-server uses Open VSX rather than Microsoft's extension marketplace.
Extensions unavailable there can often be installed from a publisher-provided
VSIX file.

## Terminal and sudo

The integrated terminal runs inside the container as `runuser`. Passwordless
`sudo` is enabled for installing project dependencies:

```sh
sudo apt-get update
sudo apt-get install <package>
```

The same shell is available from the host with:

```sh
docker compose exec --user runuser --workdir /workspace vscode bash
```
