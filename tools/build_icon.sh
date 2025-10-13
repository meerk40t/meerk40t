#!/bin/bash
# This script builds the Meerk40t icon in various sizes.
if [ ! -d images ]; then
    echo "Please run this script from the root of the meerk40t repository."
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
convert images/meerk40t.png -fuzz 10% -transparent green1 mk_big.png
convert images/meerk40t_simple.png -fuzz 10% -transparent green1 mk_small.png

convert mk_big.png \
\( mk_small.png -resize 16x16 -extent 16x16 -background transparent \) \
\( mk_small.png -resize 32x32 -extent 32x32 -background transparent \) \
\( -clone 0 -resize 48x48 -extent 48x48 -background transparent \) \
\( -clone 0 -resize 64x64 -extent 64x64 -background transparent \) \
\( -clone 0 -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 128x128 -extent 128x128 -background transparent \) \
\( -clone 0 -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 256x256 -extent 256x256 -background transparent \) \
-delete 0 meerk40t.ico

# Also create the 256x256 PNG version for AppImage
convert mk_big.png -fill red -gravity SouthEast -pointsize 96 -annotate 0 $VER -resize 256x256 -extent 256x256 -background transparent meerk40t.png

rm mk_big.png
rm mk_small.png
