#!/usr/bin/env python3
"""Turn NANOGEN files into gen-level CombinatorialSolver training h5, one per mass.

Jets are AK4 GenJets with the slimmer's cuts (pT > 30, |eta| < 2.4, >= 6 jets,
HT > 550). Every event passing those cuts is written; truth is carried alongside
the jets, never used to select or drop them, so ISR/FSR jets stay in the inputs.

    ./nanogen_to_h5.py --i /eos/user/j/jlawless/mcm_scan --o h5/
    ./nanogen_to_h5.py --i M-900/RPV_M900_NANOGEN.root --o h5/

--i takes an mcm_scan directory (every M-*/RPV_M*_NANOGEN.root), mass-point
directories, or files. Files of the same mass are merged into one output.

Layout, readable by CombinatorialSolver/src/dataset.py:

    INPUTS/Source/{pt,eta,phi,mass,btag}  (N, max_jets) float32, pT-sorted, 0-padded
    INPUTS/Source/MASK                    (N, max_jets) bool
    TARGETS/g{1,2}/j{1,2,3}               (N,) int32 index into Source, -1 unless all_matched
    EventVars/normweight                  (N,) float32 genWeight
    EventVars/{all_matched,n_jets,ht,gluino_mass,run,lumi,event}

Truth comes from run3_mj_evaluator.truth_matching.truth_assignment, the same
matcher the evaluator's mass_resolution.py uses: status-23 quarks grouped by
gluino ancestor, each to its nearest jet within --dr-max, all six on distinct
jets. It is matched against the stored (clipped) jets, so the indices are
always valid Source slots.
"""
import argparse
import glob
import os
import re
import sys
from collections import defaultdict

import awkward as ak
import h5py
import numpy as np
import uproot

DEFAULT_EVALUATOR_SRC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "run3-mj-evaluator", "src")

JET_BRANCHES = ["GenJet_pt", "GenJet_eta", "GenJet_phi", "GenJet_mass"]
GEN_BRANCHES = ["GenPart_pdgId", "GenPart_status", "GenPart_genPartIdxMother",
                "GenPart_eta", "GenPart_phi", "GenPart_mass"]
ID_BRANCHES = ["run", "luminosityBlock", "event"]

MASS_RE = re.compile(r"RPV_M(\d+)_")
XSEC_RE = re.compile(r"After filter: final cross section = ([0-9.eE+-]+) \+- ([0-9.eE+-]+) pb")

# Leading-jet pool CombinatorialSolver trains on (configs/default.yaml num_jets).
COMBSOLVER_POOL = 7


def import_truth_matching(src):
    try:
        from run3_mj_evaluator import truth_matching
        return truth_matching
    except ImportError:
        pass
    sys.path.insert(0, os.path.abspath(src))
    try:
        from run3_mj_evaluator import truth_matching
    except ImportError:
        sys.exit("cannot import run3_mj_evaluator.truth_matching; point "
                 "--evaluator-src at run3-mj-evaluator/src (tried %s)" % src)
    return truth_matching


def find_inputs(paths):
    """{mass: [files]} from files, mass-point dirs or an mcm_scan dir."""
    files = []
    for path in paths:
        if os.path.isfile(path):
            files.append(path)
            continue
        hits = sorted(glob.glob(os.path.join(path, "RPV_M*_NANOGEN*.root")))
        hits += sorted(glob.glob(os.path.join(path, "M-*", "RPV_M*_NANOGEN*.root")))
        if not hits:
            print("warning: no NANOGEN files under %s" % path)
        files.extend(hits)

    by_mass = defaultdict(list)
    for f in files:
        m = MASS_RE.search(os.path.basename(f))
        if not m:
            sys.exit("cannot read a mass point from %s (expected RPV_M<mass>_...)" % f)
        by_mass[int(m.group(1))].append(f)
    return dict(sorted(by_mass.items()))


def read_events(files):
    """Concatenate the needed branches from every file of one mass point."""
    with uproot.open(files[0] + ":Events") as tree:
        keys = set(tree.keys())
    missing = [b for b in JET_BRANCHES + GEN_BRANCHES + ID_BRANCHES if b not in keys]
    if missing:
        sys.exit("%s is missing branches: %s" % (files[0], ", ".join(missing)))
    weight = next((b for b in ("genWeight", "Generator_weight") if b in keys), None)
    branches = JET_BRANCHES + GEN_BRANCHES + ID_BRANCHES + ([weight] if weight else [])
    events = uproot.concatenate([f + ":Events" for f in files], branches, library="ak")
    return events, weight


def xsec_from_log(files, mass):
    """Matched cross section from the wmLHEGS log next to the input, if any."""
    for f in files:
        log = os.path.join(os.path.dirname(os.path.abspath(f)), "RPV_M%d_wmLHEGS.log" % mass)
        if not os.path.exists(log):
            continue
        with open(log, errors="replace") as fh:
            for line in fh:
                m = XSEC_RE.search(line)
                if m:
                    return float(m.group(1)), float(m.group(2))
    return None, None


def pad(arr, width, fill=0.0):
    return ak.to_numpy(ak.fill_none(ak.pad_none(arr, width, axis=1, clip=True), fill))


def process_mass(mass, files, args, truth_matching):
    events, weight_branch = read_events(files)
    n_total = len(events)

    pt, eta = events["GenJet_pt"], events["GenJet_eta"]
    jet_cut = (pt > args.jet_pt) & (abs(eta) < args.jet_eta)
    order = ak.argsort(pt[jet_cut], axis=1, ascending=False)
    jets = {b: events[b][jet_cut][order] for b in JET_BRANCHES}

    n_jets = ak.to_numpy(ak.num(jets["GenJet_pt"], axis=1))
    ht = ak.to_numpy(ak.sum(jets["GenJet_pt"], axis=1))
    pass_njets = n_jets >= args.min_jets
    keep = pass_njets & (ht > args.ht)

    events = events[keep]
    jets = {b: v[keep] for b, v in jets.items()}
    n_jets, ht = n_jets[keep], ht[keep]
    n_kept = len(events)

    W = args.max_jets
    src = {name: pad(jets["GenJet_" + name], W).astype(np.float32)
           for name in ("pt", "eta", "phi", "mass")}
    mask = pad(ak.ones_like(jets["GenJet_pt"], dtype=bool), W, False).astype(bool)

    targets = np.full((n_kept, 2, 3), -1, dtype=np.int32)
    ok = np.zeros(n_kept, dtype=bool)
    gluino_mass = np.full(n_kept, np.nan, dtype=np.float32)
    if n_kept:
        idx, ok = truth_matching.truth_assignment(
            events, src["eta"], src["phi"], mask,
            spec=truth_matching.RPV_GLUINO, dr_max=args.dr_max)
        targets[ok] = idx[ok]
        gluino_mass = truth_matching.resonance_mass(events).astype(np.float32)

    in_pool = ok & (targets.reshape(n_kept, 6) < COMBSOLVER_POOL).all(axis=1)

    if weight_branch:
        normweight = ak.to_numpy(events[weight_branch]).astype(np.float32)
    else:
        normweight = np.ones(n_kept, dtype=np.float32)

    xsec, xsec_err = xsec_from_log(files, mass)

    os.makedirs(args.outdir, exist_ok=True)
    out = os.path.join(args.outdir, "RPV_GluinoGluinoto6Q_M-%d_genjet.h5" % mass)
    with h5py.File(out, "w") as hf:
        for name, arr in src.items():
            hf.create_dataset("INPUTS/Source/" + name, data=arr)
        hf.create_dataset("INPUTS/Source/btag", data=np.zeros((n_kept, W), dtype=np.float32))
        hf.create_dataset("INPUTS/Source/MASK", data=mask)
        for g in range(2):
            for j in range(3):
                hf.create_dataset("TARGETS/g%d/j%d" % (g + 1, j + 1), data=targets[:, g, j])
        ev = {
            "normweight": normweight,
            "all_matched": ok,
            "n_jets": n_jets.astype(np.int32),
            "ht": ht.astype(np.float32),
            "gluino_mass": gluino_mass,
            "run": ak.to_numpy(events["run"]).astype(np.uint32),
            "lumi": ak.to_numpy(events["luminosityBlock"]).astype(np.uint32),
            "event": ak.to_numpy(events["event"]).astype(np.uint64),
        }
        for name, arr in ev.items():
            hf.create_dataset("EventVars/" + name, data=arr)

        hf.attrs["level"] = "gen"
        hf.attrs["jet_algorithm"] = "ak4GenJets (NANOGEN GenJet)"
        hf.attrs["process"] = "p p > go go (+ up to 2 j), go -> u d s (Pythia)"
        hf.attrs["mass"] = mass
        hf.attrs["max_jets"] = W
        hf.attrs["cuts"] = "jet pT>%g, |eta|<%g, n_jets>=%d, HT>%g" % (
            args.jet_pt, args.jet_eta, args.min_jets, args.ht)
        hf.attrs["truth"] = ("status-23 quarks grouped by gluino ancestor, nearest "
                             "jet within dR<%g, six distinct jets; -1 unless all_matched"
                             % args.dr_max)
        hf.attrs["dr_max"] = args.dr_max
        hf.attrs["spanet_target_structure"] = "g1: j1,j2,j3; g2: j1,j2,j3"
        hf.attrs["source_files"] = [os.path.abspath(f) for f in files]
        hf.attrs["nevents_total"] = n_total
        hf.attrs["nevents_selected"] = n_kept
        if xsec is not None:
            hf.attrs["xsec_match_pb"] = xsec
            hf.attrs["xsec_match_err_pb"] = xsec_err

    stats = cutflow_text(mass, files, n_total, int(pass_njets.sum()), n_kept,
                         int(ok.sum()), int(in_pool.sum()), args, xsec, xsec_err)
    with open(out.replace(".h5", "_stats.txt"), "w") as fh:
        fh.write(stats + "\n")
    print(stats + "\n  -> %s\n" % out)
    return n_kept


def cutflow_text(mass, files, n_total, n_njets, n_kept, n_matched, n_pool,
                 args, xsec, xsec_err):
    def row(label, n, ref):
        pct = 100.0 * n / ref if ref else 0.0
        return "  %-52s %8d  (%5.1f%%)" % (label, n, pct)

    lines = [
        "M-%d  (%d file%s)" % (mass, len(files), "" if len(files) == 1 else "s"),
        row("events in NANOGEN", n_total, n_total),
        row(">= %d jets (pT>%g, |eta|<%g)" % (args.min_jets, args.jet_pt, args.jet_eta),
            n_njets, n_total),
        row("HT > %g  -> written" % args.ht, n_kept, n_total),
        row("all six quarks matched (of written)", n_matched, n_kept),
        row("  ...all within leading %d jets (of written)" % COMBSOLVER_POOL, n_pool, n_kept),
    ]
    if xsec is not None:
        lines.append("  xsec after matching: %.4g +- %.2g pb" % (xsec, xsec_err))
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--i", "--input", dest="inputs", nargs="+", required=True,
                   help="mcm_scan dir, M-* dirs, or NANOGEN root files")
    p.add_argument("--o", "--outdir", dest="outdir", required=True)
    p.add_argument("--masses", type=int, nargs="+", help="only these mass points")
    p.add_argument("--max-jets", type=int, default=20, help="Source width (padded)")
    p.add_argument("--dr-max", type=float, default=0.4, help="quark-jet match radius")
    p.add_argument("--jet-pt", type=float, default=30.0)
    p.add_argument("--jet-eta", type=float, default=2.4)
    p.add_argument("--min-jets", type=int, default=6)
    p.add_argument("--ht", type=float, default=550.0)
    p.add_argument("--evaluator-src", default=DEFAULT_EVALUATOR_SRC,
                   help="run3-mj-evaluator/src, for truth_matching (default: sibling checkout)")
    args = p.parse_args()

    truth_matching = import_truth_matching(args.evaluator_src)
    by_mass = find_inputs(args.inputs)
    if args.masses:
        by_mass = {m: f for m, f in by_mass.items() if m in args.masses}
    if not by_mass:
        sys.exit("no input files found")

    for mass, files in by_mass.items():
        process_mass(mass, files, args, truth_matching)


if __name__ == "__main__":
    main()
