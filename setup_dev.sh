#!/bin/bash
# Exit on error
set -e

# Define paths
REPO_DIR="/Users/attilioturco/Documents/GitHub/anki-race"
ADDON_NAME="anki_race"
SRC_DIR="$REPO_DIR/$ADDON_NAME"
ANKI_ADDONS_ROOT="$HOME/Library/Application Support/Anki2/addons21"
DEST_LINK="$ANKI_ADDONS_ROOT/$ADDON_NAME"

echo "=== Anki Race Developer Setup ==="
echo "Local source: $SRC_DIR"
echo "Anki addons root: $ANKI_ADDONS_ROOT"

# 1. Check if Anki addons directory exists
if [ ! -d "$ANKI_ADDONS_ROOT" ]; then
    echo "Error: Anki addons directory does not exist at:"
    echo "  $ANKI_ADDONS_ROOT"
    echo ""
    echo "Please ensure that Anki is installed and has been opened at least once."
    exit 1
fi

# 2. Check if a link or directory already exists at destination
if [ -L "$DEST_LINK" ]; then
    echo "Removing existing symbolic link at: $DEST_LINK"
    rm "$DEST_LINK"
elif [ -d "$DEST_LINK" ]; then
    BACKUP_DIR="${DEST_LINK}_backup_$(date +%Y%m%d_%H%M%S)"
    echo "Warning: A directory already exists at: $DEST_LINK"
    echo "Moving it to: $BACKUP_DIR"
    mv "$DEST_LINK" "$BACKUP_DIR"
fi

# 3. Create the symlink
echo "Creating symlink..."
ln -s "$SRC_DIR" "$DEST_LINK"

echo "Success! Symlink created successfully at:"
echo "  $DEST_LINK -> $SRC_DIR"
echo ""
echo "Restart Anki to load the add-on."
