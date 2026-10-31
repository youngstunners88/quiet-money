#!/bin/bash
# usage: render.sh file.blend outdir out.mp4   (frames then H.264 1080x1920 24fps)
set -e
blender -b --factory-startup "$1" -o "$2/f_####" -F PNG -a >/dev/null 2>&1
ffmpeg -y -loglevel error -framerate 24 -i "$2/f_%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 17 -preset medium -movflags +faststart "$3"
