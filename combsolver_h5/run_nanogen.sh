#!/bin/bash
# Run NANOGEN on every mass point's GEN-SIM file in an mcm_scan directory.
#
#   ./run_nanogen.sh /eos/user/j/jlawless/mcm_scan            # all M-* dirs
#   ./run_nanogen.sh /eos/user/j/jlawless/mcm_scan 900 1000   # just these masses
#
# Needs a cmsenv'd CMSSW_15_0_15 area. Reads M-<m>/RPV_M<m>_wmLHEGS.root and
# writes RPV_M<m>_NANOGEN{_cfg.py,.root,.log} next to it. The GEN-SIM already
# holds ak4GenJets and genParticles, so this only flattens them to GenJet_* and
# GenPart_* - no generation or simulation is redone.

CONDITIONS=150X_mcRun3_2024_realistic_v2
ERA=Run3_2024

if [ -z "$1" ]; then
    echo "usage: $0 <mcm_scan dir> [mass ...]"
    exit 1
fi
if [ -z "$CMSSW_BASE" ]; then
    echo "no CMSSW environment - run cmsenv first"
    exit 1
fi

scandir=$(cd "$1" && pwd)
shift

if [ $# -gt 0 ]; then
    dirs=""
    for m in "$@"; do dirs="$dirs $scandir/M-$m"; done
else
    dirs=$(for d in "$scandir"/M-*; do echo "${d##*/M-} $d"; done | sort -n | cut -d" " -f2-)
fi

for dir in $dirs; do
    m=${dir##*/M-}
    gensim="RPV_M${m}_wmLHEGS.root"
    cfg="RPV_M${m}_NANOGEN_cfg.py"
    out="RPV_M${m}_NANOGEN.root"
    log="RPV_M${m}_NANOGEN.log"

    if [ ! -f "$dir/$gensim" ]; then
        echo "[M-$m] no $gensim, skipping"
        continue
    fi

    echo "[M-$m] cmsDriver"
    (cd "$dir" && cmsDriver.py nanogen \
        --filein "file:$gensim" --fileout "file:$out" \
        --python_filename "$cfg" \
        --step NANOGEN --eventcontent NANOAODGEN --datatier NANOAOD \
        --conditions "$CONDITIONS" --era "$ERA" \
        --mc -n -1 --no_exec) || { echo "[M-$m] cmsDriver failed, skipping"; continue; }

    echo "[M-$m] cmsRun -> $dir/$log"
    if (cd "$dir" && cmsRun "$cfg" > "$log" 2>&1); then
        echo "[M-$m] done: $dir/$out"
    else
        echo "[M-$m] cmsRun failed, see $dir/$log"
    fi
done
