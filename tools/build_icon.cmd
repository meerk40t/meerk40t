@echo off
set ver=0.9.5.b7
echo Converting master image to a couple of smaller images
echo This requires imagemagick (https://imagemagick.org)
echo Superimposing Version information: '%ver%'
magick images\meerk40t.png -background white ^
( images\meerk40t_simple.png -background white -resize 16x16 -extent 16x16 ) ^
( images\meerk40t_simple.png -background white -resize 32x32 -extent 32x32 ) ^
( -clone 0 -resize 48x48 -extent 48x48 ) ^
( -clone 0 -resize 64x64 -extent 64x64 ) ^
( -clone 0 -gravity SouthEast -pointsize 96 -annotate 0 %ver% -resize 128x128 -extent 128x128 ) ^
( -clone 0 -gravity SouthEast -pointsize 96 -annotate 0 %ver% -resize 256x256 -extent 256x256 ) ^
-delete 0 -alpha off -colors 256 meerk40t.ico
