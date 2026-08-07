# Ollama

This service uses the official `ollama/ollama` image and exposes the API on the
LAN address `192.168.50.136:11434`.

The model directory is mounted from the host and passed to Ollama with
the official image's default storage path:

```sh
/mnt/models/ollama:/root/.ollama
```

This keeps the existing host model store while matching the official
`ollama/ollama` Docker examples.

The official image normally runs as root, so make sure the host directory is
readable and writable by the container:

```sh
sudo chown -R root:root /mnt/models/ollama
```

If you later choose to run the container as a non-root uid/gid, change the
directory ownership to match that uid/gid and add a `user:` entry to the compose
service.

The default context length remains configurable with `OLLAMA_CONTEXT_LENGTH` in
`.env`.

Run with:

```sh
docker compose up -d ollama
```

Pull or inspect models through the container:

```sh
docker exec -it ollama-c ollama list
docker exec -it ollama-c ollama pull llama3.2
```
