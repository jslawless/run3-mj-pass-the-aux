#!/bin/bash
# Run nanogen_to_h5.py on every mass point of an mcm_scan directory, writing all
# h5 files into one output directory.
#
#   ./make_all_h5.sh /eos/user/j/jlawless/mcm_scan /eos/user/j/jlawless/combsolver_h5
#   ./make_all_h5.sh <mcm_scan dir> <outdir> 900 1000     # just these masses
#   PYTHON=/opt/homebrew/anaconda3/bin/python ./make_all_h5.sh ...
#
# One nanogen_to_h5.py call per mass point, so a bad file costs only that point.
# Each point's cutflow is collected into <outdir>/summary.txt.

PYTHON=${PYTHON:-python3}
here=$(cd "$(dirname "$0")" && pwd)

if [ -z "$2" ]; then
    echo "usage: $0 <mcm_scan dir> <outdir> [mass ...]"
    exit 1
fi

scandir=$(cd "$1" && pwd) || exit 1
outdir=$2
shift 2
mkdir -p "$outdir" || exit 1
outdir=$(cd "$outdir" && pwd)

if [ $# -gt 0 ]; then
    dirs=""
    for m in "$@"; do dirs="$dirs $scandir/M-$m"; done
else
    dirs=$(for d in "$scandir"/M-*; do echo "${d##*/M-} $d"; done | sort -n | cut -d" " -f2-)
fi

summary="$outdir/summary.txt"
: > "$summary"
failed=""

for dir in $dirs; do
    m=${dir##*/M-}
    if ! ls "$dir"/RPV_M"${m}"_NANOGEN*.root > /dev/null 2>&1; then
        echo "[M-$m] no NANOGEN file in $dir, skipping (run run_nanogen.sh first)"
        failed="$failed $m"
        continue
    fi

    if "$PYTHON" "$here/nanogen_to_h5.py" --i "$dir" --o "$outdir" --masses "$m"; then
        cat "$outdir/RPV_GluinoGluinoto6Q_M-${m}_genjet_stats.txt" >> "$summary"
        echo >> "$summary"
    else
        echo "[M-$m] nanogen_to_h5.py failed"
        failed="$failed $m"
    fi
done

echo "h5 files in $outdir, cutflows in $summary"
if [ -n "$failed" ]; then
    echo "failed or skipped masses:$failed"
    exit 1
fi
