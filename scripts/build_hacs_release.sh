#!/bin/bash
set -e

SOURCE_DIR="../sharp-iot-source"
RELEASE_DIR="../sharp-iot-release"
SOURCE_BRANCH="master"
RELEASE_BRANCH="hacs"

echo "Building HACS release..."

# Setup source worktree (always fresh)
if [ -d "$SOURCE_DIR" ]; then
  echo "Removing existing source worktree at $SOURCE_DIR"
  rm -rf "$SOURCE_DIR"
  git worktree prune
fi
echo "Creating fresh source worktree at $SOURCE_DIR"
# Use --detach to avoid "branch already checked out" error
git worktree add --detach "$SOURCE_DIR" $SOURCE_BRANCH

# Setup release worktree
if [ -d "$RELEASE_DIR" ]; then
  echo "Using existing release worktree at $RELEASE_DIR"
  cd "$RELEASE_DIR"
  git checkout $RELEASE_BRANCH
  if git ls-remote --exit-code origin $RELEASE_BRANCH >/dev/null 2>&1; then
    git pull origin $RELEASE_BRANCH
  fi
  cd -
else
  echo "Creating release worktree at $RELEASE_DIR"
  # Create release branch if doesn't exist
  if ! git show-ref --verify --quiet refs/heads/$RELEASE_BRANCH; then
    git branch $RELEASE_BRANCH
  fi
  git worktree add "$RELEASE_DIR" $RELEASE_BRANCH
fi

# Clean release directory (remove everything except .git)
echo "Cleaning release directory..."
cd "$RELEASE_DIR"
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
cd -

# Create target structure
echo "Copying files..."
mkdir -p "$RELEASE_DIR/custom_components/sharp_iot/lib"

# Copy vendored dependencies from source worktree
cp -r "$SOURCE_DIR/packages/sharp-core/src/sharp_core" "$RELEASE_DIR/custom_components/sharp_iot/lib/"
cp -r "$SOURCE_DIR/packages/sharp-devices/src/sharp_devices" "$RELEASE_DIR/custom_components/sharp_iot/lib/"

# Find and copy HA integration files (flexible to directory structure changes)
HA_SOURCE=$(find "$SOURCE_DIR/packages/sharp-homeassistant" -type d -name "sharp_iot" | head -1)
if [ -z "$HA_SOURCE" ]; then
  echo "Error: Could not find sharp_iot directory in sharp-homeassistant package"
  exit 1
fi

# Copy all files from HA integration
cp -r "$HA_SOURCE"/* "$RELEASE_DIR/custom_components/sharp_iot/"

# Rewrite imports in HA integration files only (not in lib/)
echo "Rewriting imports in HA integration files..."
find "$RELEASE_DIR/custom_components/sharp_iot" -maxdepth 1 -name "*.py" -type f -exec perl -i -pe \
  's/^from sharp_(core|devices)/from .lib.sharp_$1/g; s/(\s+)from sharp_(core|devices)/$1from .lib.sharp_$2/g' {} \;

# Rewrite imports in lib/sharp_devices to use relative imports to lib/sharp_core
echo "Rewriting imports in vendored packages..."
find "$RELEASE_DIR/custom_components/sharp_iot/lib/sharp_devices" -name "*.py" -type f -exec perl -i -pe \
  's/^from sharp_core/from ..sharp_core/g; s/(\s+)from sharp_core/$1from ..sharp_core/g' {} \;

# Update README
echo "Updating README..."
cat > "$RELEASE_DIR/README.md" << 'EOF'
# Sharp IoT - Home Assistant Integration

> **⚠️ Release Branch Notice**
>
> This is the `hacs` branch, automatically generated for HACS compatibility.
>
> **For development**, please use the `master` branch which uses UV workspaces.
>
> This branch contains vendored dependencies from `sharp-core` and `sharp-devices` packages.

---

EOF

# Append original README content
cat "$SOURCE_DIR/README.md" >> "$RELEASE_DIR/README.md"

# Copy hacs.json
echo "Copying hacs.json..."
cp "$SOURCE_DIR/hacs.json" "$RELEASE_DIR/hacs.json"

# Cleanup Python cache
echo "Cleaning Python cache..."
find "$RELEASE_DIR" -type d -name __pycache__ -exec rm -rf {} +
find "$RELEASE_DIR" -type f -name "*.pyc" -delete

# Git commit in worktree
echo "Committing changes..."
cd "$RELEASE_DIR"

SOURCE_COMMIT=$(git -C "$SOURCE_DIR" rev-parse --short HEAD)

git add -A
if git diff --cached --quiet; then
  echo "No changes to commit"
else
  git commit -m "Automated HACS release build

Generated from dev branch commit: $SOURCE_COMMIT"
  echo "Changes committed successfully"
fi

cd -

echo ""
echo "✓ Release branch built in $RELEASE_DIR"
echo ""
echo "To push:"
echo "  cd $RELEASE_DIR"
echo "  git push origin $RELEASE_BRANCH"
