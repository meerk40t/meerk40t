@echo off
set ver=0.9.7b4
echo Converting master image to a couple of smaller images
echo This requires imagemagick (https://imagemagick.org)
echo Superimposing Version information: '%ver%'
magick images\meerk40t.png -fuzz 10% -transparent green1 mk_big.png
magick images\meerk40t_simple.png -fuzz 10% -transparent green1 mk_small.png

magick mk_big.png ^
( mk_small.png -resize 16x16 -extent 16x16 -background transparent ) ^
( mk_small.png -resize 32x32 -extent 32x32 -background transparent ) ^
( -clone 0 -resize 48x48 -extent 48x48 -background transparent ) ^
( -clone 0 -resize 64x64 -extent 64x64 -background transparent ) ^
( -clone 0 -fill red -gravity SouthEast -pointsize 96 -annotate 0 %ver% -resize 128x128 -extent 128x128 -background transparent ) ^
( -clone 0 -fill red -gravity SouthEast -pointsize 96 -annotate 0 %ver% -resize 256x256 -extent 256x256 -background transparent ) ^
-delete 0 meerk40t.ico

del mk_big.png
del mk_small.png