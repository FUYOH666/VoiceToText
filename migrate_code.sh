#!/bin/bash
# Скрипт для автоматической миграции кода из старых репозиториев VoiceToText

set -e

echo "🚀 VoiceToText Code Migration Script"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the VoiceToText directory
if [ ! -f "README.md" ] || [ ! -d "platforms" ]; then
    echo "❌ Error: Please run this script from the VoiceToText repository root"
    exit 1
fi

TEMP_DIR="/tmp/voicetotext-migration-$$"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo "📥 Cloning old repositories..."
git clone https://github.com/FUYOH666/VoiceToText-MACos.git 2>/dev/null || echo "⚠️  VoiceToText-MACos already cloned or error"
git clone https://github.com/FUYOH666/VoiceToText-Linux.git 2>/dev/null || echo "⚠️  VoiceToText-Linux already cloned or error"
git clone https://github.com/FUYOH666/VoiceToText-MLX-M1-8Gb.git 2>/dev/null || echo "⚠️  VoiceToText-MLX-M1-8Gb already cloned or error"

echo ""
echo "📦 Migrating code..."

# Get VoiceToText repo path (assume it's parent of script location)
VTT_REPO=$(dirname "$(readlink -f "$0")" 2>/dev/null || pwd)
if [ ! -f "$VTT_REPO/README.md" ]; then
    echo "❌ Error: Cannot find VoiceToText repository"
    echo "   Please run: cd /path/to/VoiceToText && ./migrate_code.sh"
    exit 1
fi

cd "$VTT_REPO"

# macOS migration
if [ -d "$TEMP_DIR/VoiceToText-MACos" ]; then
    echo -e "${GREEN}🍎 Migrating macOS platform...${NC}"
    mkdir -p platforms/macos
    
    [ -d "$TEMP_DIR/VoiceToText-MACos/src" ] && cp -r "$TEMP_DIR/VoiceToText-MACos/src" platforms/macos/ && echo "   ✅ Copied src/"
    [ -d "$TEMP_DIR/VoiceToText-MACos/models" ] && cp -r "$TEMP_DIR/VoiceToText-MACos/models" platforms/macos/ && echo "   ✅ Copied models/"
    [ -f "$TEMP_DIR/VoiceToText-MACos/config.yaml" ] && cp "$TEMP_DIR/VoiceToText-MACos/config.yaml" platforms/macos/ && echo "   ✅ Copied config.yaml"
    [ -f "$TEMP_DIR/VoiceToText-MACos/requirements.txt" ] && cp "$TEMP_DIR/VoiceToText-MACos/requirements.txt" platforms/macos/ && echo "   ✅ Copied requirements.txt"
    [ -f "$TEMP_DIR/VoiceToText-MACos/QUICKSTART.md" ] && cp "$TEMP_DIR/VoiceToText-MACos/QUICKSTART.md" platforms/macos/ && echo "   ✅ Copied QUICKSTART.md"
    [ -d "$TEMP_DIR/VoiceToText-MACos/.github" ] && cp -r "$TEMP_DIR/VoiceToText-MACos/.github" platforms/macos/ 2>/dev/null || true
fi

# Linux migration
if [ -d "$TEMP_DIR/VoiceToText-Linux" ]; then
    echo -e "${GREEN}🐧 Migrating Linux platform...${NC}"
    mkdir -p platforms/linux
    
    [ -d "$TEMP_DIR/VoiceToText-Linux/src" ] && cp -r "$TEMP_DIR/VoiceToText-Linux/src" platforms/linux/ && echo "   ✅ Copied src/"
    [ -d "$TEMP_DIR/VoiceToText-Linux/scripts" ] && cp -r "$TEMP_DIR/VoiceToText-Linux/scripts" platforms/linux/ && echo "   ✅ Copied scripts/"
    [ -d "$TEMP_DIR/VoiceToText-Linux/docs" ] && cp -r "$TEMP_DIR/VoiceToText-Linux/docs" platforms/linux/ && echo "   ✅ Copied docs/"
    [ -f "$TEMP_DIR/VoiceToText-Linux/config.yaml" ] && cp "$TEMP_DIR/VoiceToText-Linux/config.yaml" platforms/linux/ && echo "   ✅ Copied config.yaml"
    [ -f "$TEMP_DIR/VoiceToText-Linux/install.sh" ] && cp "$TEMP_DIR/VoiceToText-Linux/install.sh" platforms/linux/ && echo "   ✅ Copied install.sh"
    [ -d "$TEMP_DIR/VoiceToText-Linux/.github" ] && cp -r "$TEMP_DIR/VoiceToText-Linux/.github" platforms/linux/ 2>/dev/null || true
fi

# MLX migration
if [ -d "$TEMP_DIR/VoiceToText-MLX-M1-8Gb" ]; then
    echo -e "${GREEN}⚡ Migrating MLX platform...${NC}"
    mkdir -p platforms/mlx
    
    [ -d "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/src" ] && cp -r "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/src" platforms/mlx/ && echo "   ✅ Copied src/"
    [ -d "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/models" ] && cp -r "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/models" platforms/mlx/ && echo "   ✅ Copied models/"
    [ -d "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/tests" ] && cp -r "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/tests" platforms/mlx/ && echo "   ✅ Copied tests/"
    [ -f "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/config.yaml" ] && cp "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/config.yaml" platforms/mlx/ && echo "   ✅ Copied config.yaml"
    [ -f "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/config.m1-8gb.yaml.example" ] && cp "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/config.m1-8gb.yaml.example" platforms/mlx/ && echo "   ✅ Copied config.m1-8gb.yaml.example"
    [ -f "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/config.m4-128gb.yaml.example" ] && cp "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/config.m4-128gb.yaml.example" platforms/mlx/ && echo "   ✅ Copied config.m4-128gb.yaml.example"
    [ -f "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/requirements.txt" ] && cp "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/requirements.txt" platforms/mlx/ && echo "   ✅ Copied requirements.txt"
    [ -f "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/QUICKSTART.md" ] && cp "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/QUICKSTART.md" platforms/mlx/ && echo "   ✅ Copied QUICKSTART.md"
    [ -d "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/.github" ] && cp -r "$TEMP_DIR/VoiceToText-MLX-M1-8Gb/.github" platforms/mlx/ 2>/dev/null || true
fi

# Cleanup
echo ""
echo "🧹 Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo ""
echo -e "${GREEN}✅ Migration completed!${NC}"
echo ""
echo "📋 Next steps:"
echo "1. Review the migrated code in platforms/"
echo "2. Test each platform:"
echo "   cd platforms/macos && python src/main.py --help"
echo "   cd platforms/linux && ./install.sh --help"
echo "   cd platforms/mlx && python src/main.py --help"
echo "3. Update import paths if needed"
echo "4. Commit and push:"
echo "   git add ."
echo "   git commit -m 'Migrate code from separate repositories'"
echo "   git push origin main"

