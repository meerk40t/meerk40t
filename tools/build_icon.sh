#!/bin/bash
# This script builds the Meerk40t icon in various sizes.
if [ ! -d images ]; then
    echo "Please run this script from the root of the sefrocut repository."
    exit 1
fi
if [ ! -x "$(command -v convert)" ]; then
    echo "This script requires ImageMagick to be installed."
    echo "Please install ImageMagick and try again."
    exit 1
fi
if [ $# -eq 0 ]
  then
    echo Usage: build_icon.sh version
    echo Example: build_icon.sh 0.9.75
    exit 1
fi

VER=$1
if [ -z "$VER" ]; then
    echo "Version number is required."
    exit 1
fi
echo Converting master image to a couple of smaller images
echo This requires imagemagick \(https://imagemagick.org\)
echo Superimposing Version information: "$VER"
convert images/sefrocut.png -fuzz 10% -transparent green1 mk_big.png
convert images/sefrocut_simple.png -fuzz 10% -transparent green1 mk_small.png

convert mk_big.png \
\( mk_small.png -resize 16x16 -extent 16x16 -background transparent \) \
\( mk_small.png -resize 32x32 -extent 32x32 -background transparent \) \
\( -clone 0 -resize 48x48 -extent 48x48 -background transparent \) \
\( -clone 0 -resize 64x64 -extent 64x64 -background transparent \) \
\( -clone 0 -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 128x128 -extent 128x128 -background transparent \) \
\( -clone 0 -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 256x256 -extent 256x256 -background transparent \) \
-delete 0 sefrocut.ico

# Also create the 256x256 PNG version for AppImage
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 256x256 -extent 256x256 -background transparent sefrocut.png

# Create macOS .icns file
echo "Creating macOS .icns file..."
mkdir -p sefrocut.iconset
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 16x16 -extent 16x16 -background transparent sefrocut.iconset/icon_16x16.png
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 32x32 -extent 32x32 -background transparent sefrocut.iconset/icon_16x16@2x.png
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 32x32 -extent 32x32 -background transparent sefrocut.iconset/icon_32x32.png
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 64x64 -extent 64x64 -background transparent sefrocut.iconset/icon_32x32@2x.png
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 128x128 -extent 128x128 -background transparent sefrocut.iconset/icon_128x128.png
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 256x256 -extent 256x256 -background transparent sefrocut.iconset/icon_128x128@2x.png
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 256x256 -extent 256x256 -background transparent sefrocut.iconset/icon_256x256.png
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 512x512 -extent 512x512 -background transparent sefrocut.iconset/icon_256x256@2x.png
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 512x512 -extent 512x512 -background transparent sefrocut.iconset/icon_512x512.png
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 1024x1024 -extent 1024x1024 -background transparent sefrocut.iconset/icon_512x512@2x.png

if command -v iconutil &> /dev/null; then
    echo "Converting iconset to .icns file..."
    iconutil -c icns sefrocut.iconset -o sefrocut.icns
    echo ".icns file created successfully"
else
    echo "WARNING: iconutil not available, skipping .icns creation"
    echo "On macOS, install Xcode command line tools: xcode-select --install"
fi

rm -rf sefrocut.iconset

rm mk_big.png
rm mk_small.png
