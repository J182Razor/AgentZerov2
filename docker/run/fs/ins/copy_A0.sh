#!/bin/bash
set -e

# Paths
SOURCE_DIR="/git/agent-zero"
TARGET_DIR="/a0"

# Always sync code from the image into /a0 so container upgrades
# pick up fixes.  User data lives in named volumes (knowledge, usr/*)
# and won't be touched — only code files are overwritten.
echo "Copying files from $SOURCE_DIR to $TARGET_DIR..."
cp -r --no-preserve=ownership,mode "$SOURCE_DIR/." "$TARGET_DIR"