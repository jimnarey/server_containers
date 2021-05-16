#!/bin/bash

# Pass an image (not container) with caddy installed as the first argument
# and the password as the second argument

# docker run --rm -it $1 caddy hash-password -plaintext '$2' > ./hashes/$2

docker run --rm -it $1 caddy hash-password --algorithm bcrypt -plaintext '$2' > ./hashes/$2