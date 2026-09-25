#!/bin/sh
# Build the MeerK40t user manual.
#
# Two pdflatex passes: the first writes the table of contents and the
# cross-reference labels, the second resolves both. Auxiliary files land in
# build/ so the source directory stays clean; the PDF is copied next to this
# script.
set -e
cd "$(dirname "$0")"
mkdir -p build
pdflatex -interaction=nonstopmode -output-directory=build meerk40t_user_manual.tex >build/pass1.log
pdflatex -interaction=nonstopmode -output-directory=build meerk40t_user_manual.tex >build/pass2.log
cp build/meerk40t_user_manual.pdf ./meerk40t_user_manual.pdf
echo "Wrote $(pwd)/meerk40t_user_manual.pdf"
