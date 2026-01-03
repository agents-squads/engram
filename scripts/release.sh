#!/bin/bash
# Release script for Engram
# Usage: ./scripts/release.sh [patch|minor|major]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION_FILE="$ROOT_DIR/VERSION"

# Get current version
CURRENT_VERSION=$(cat "$VERSION_FILE" | tr -d '\n')
echo "Current version: $CURRENT_VERSION"

# Parse version components
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Determine bump type
BUMP_TYPE="${1:-patch}"

case "$BUMP_TYPE" in
  major)
    MAJOR=$((MAJOR + 1))
    MINOR=0
    PATCH=0
    ;;
  minor)
    MINOR=$((MINOR + 1))
    PATCH=0
    ;;
  patch)
    PATCH=$((PATCH + 1))
    ;;
  *)
    echo "Usage: $0 [patch|minor|major]"
    exit 1
    ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo "New version: $NEW_VERSION"

# Confirm
read -p "Create release v$NEW_VERSION? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 1
fi

# Update VERSION file
echo "$NEW_VERSION" > "$VERSION_FILE"
echo "Updated VERSION file"

# Check if CHANGELOG has entry for new version
if ! grep -q "\[$NEW_VERSION\]" "$ROOT_DIR/CHANGELOG.md"; then
  echo ""
  echo "WARNING: No CHANGELOG entry for v$NEW_VERSION"
  echo "Please update CHANGELOG.md before releasing."
  echo ""
  read -p "Open CHANGELOG.md now? [Y/n] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    ${EDITOR:-vim} "$ROOT_DIR/CHANGELOG.md"
  fi
fi

# Commit version bump
git add "$VERSION_FILE" "$ROOT_DIR/CHANGELOG.md"
git commit -m "chore: Release v$NEW_VERSION

🤖 Generated with [Agents Squads](https://agents-squads.com)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Create and push tag
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
echo "Created tag v$NEW_VERSION"

echo ""
echo "Release prepared. To publish:"
echo "  git push origin main"
echo "  git push origin v$NEW_VERSION"
echo ""
echo "GitHub Actions will automatically:"
echo "  - Build and push Docker images to GHCR"
echo "  - Create GitHub Release with changelog"
