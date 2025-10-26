#!/bin/bash
# Version bump script for semantic versioning
# Usage: ./bump-version.sh <current_version> <bump_type>
# Example: ./bump-version.sh v1.0.0 patch -> v1.0.1

set -e

CURRENT_VERSION=$1
BUMP_TYPE=$2

# Validate inputs
if [ -z "$CURRENT_VERSION" ]; then
    echo "Error: Current version required" >&2
    exit 1
fi

if [ -z "$BUMP_TYPE" ]; then
    echo "Error: Bump type required (patch, minor, major)" >&2
    exit 1
fi

# Remove 'v' prefix if present
VERSION="${CURRENT_VERSION#v}"

# Parse version components
if [[ "$VERSION" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="${BASH_REMATCH[2]}"
    PATCH="${BASH_REMATCH[3]}"
else
    echo "Error: Invalid version format: $CURRENT_VERSION" >&2
    echo "Expected format: vX.Y.Z or X.Y.Z" >&2
    exit 1
fi

# Bump version based on type
case "$BUMP_TYPE" in
    patch)
        NEW_PATCH=$((PATCH + 1))
        NEW_VERSION="v${MAJOR}.${MINOR}.${NEW_PATCH}"
        ;;
    minor)
        NEW_MINOR=$((MINOR + 1))
        NEW_VERSION="v${MAJOR}.${NEW_MINOR}.0"
        ;;
    major)
        NEW_MAJOR=$((MAJOR + 1))
        NEW_VERSION="v${NEW_MAJOR}.0.0"
        ;;
    *)
        echo "Error: Invalid bump type: $BUMP_TYPE" >&2
        echo "Valid types: patch, minor, major" >&2
        exit 1
        ;;
esac

# Output new version
echo "$NEW_VERSION"
