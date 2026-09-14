#!/usr/bin/env python3
"""Run each mass point's gen fragment and collect the four McM request numbers.

For every mass point: cmsDriver the fragment into a cfg, cmsRun it, and parse the
log for time/event, size/event, match efficiency and filter efficiency. Each mass
point runs in its own directory under --o, so every output it produces (the LHE
tier root, the GEN-SIM root, cmsgrid_final.lhe, the cfg, the log) lands there.
The CSV in the parent directory is rewritten after each point, so an interrupted
scan still leaves usable rows.

    ./scan_mcm_numbers.py --o /eos/user/j/jlawless/mcm_scan
    ./scan_mcm_numbers.py --o out --masses 1000 2000 --events 2000 --resume

Assumes a cmsenv'd area where the per-mass fragments are already installed under
Configuration/GenProduction/python/ (scram b). Gridpack paths come from the
fragments. Generate those fragments with the same event count as --events --
generateFragments.py --with-lhe --events N -- since the ExternalLHEProducer
nEvents must match the cmsDriver -n.
"""
import argparse
import csv
import math
import os
import subprocess
import sys

MASSES = [200, 300, 400, 500, 600, 700, 750, 800, 900, 1000, 1100, 1200,
          1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2200, 2400,
          2600, 2800, 3000]

FRAGMENT = ("Configuration/GenProduction/python/RPVGluinoGluinoToJets_UDD112_M-{mass}"
            "_TuneCP5_13p6TeV_madgraphMLM-pythia8_cff.py")

CSV_FIELDS = ["mass", "time per event", "size per event",
              "match efficiency", "filter efficiency"]


def cmsdriver_cmd(args, mass, cfg, fileout):
    return [
        "cmsDriver.py", FRAGMENT.format(mass=mass),
        "--python_filename", cfg,
        "--eventcontent", "RAWSIM,LHE",
        "--datatier", "GEN-SIM,LHE",
        "--fileout", "file:" + fileout,
        "--step", "LHE,GEN,SIM",
        "--geometry", "DB:Extended",
        "--conditions", args.conditions,
        "--beamspot", args.beamspot,
        "--era", args.era,
        "--customise", "Configuration/DataProcessing/Utils.addMonitoring",
        "--no_exec", "--mc", "-n", str(args.events),
    ]


def _cpu_total_loop(lines):
    """Seconds of CPU in the event loop: the 'Total loop' under 'CPU Summary'."""
    for i, line in enumerate(lines):
        if "CPU Summary" not in line:
            continue
        for follow in lines[i + 1:i + 8]:
            if "Total loop" in follow:
                return float(follow.split(":")[1])
    return None


def _genxsec_total(lines):
    """(passed, tried) from the GenXsecAnalyzer 'Total' row."""
    for line in lines:
        if not line.strip().startswith("Total"):
            continue
        toks = [t for t in line.split() if t != "+/-"]
        # Total xsec err passed nposw nnegw tried nposw nnegw xsec_m err acc err eff err
        if len(toks) < 9:
            continue
        try:
            return int(toks[3]), int(toks[6])
        except ValueError:
            continue
    return None, None


def _filter_eff(lines):
    """(value, error) from the line GenXsecAnalyzer flags for McM."""
    for line in lines:
        if "Filter efficiency (event-level)" not in line:
            continue
        rhs = line.split("=")[-1]
        toks = rhs.replace("+-", " ").split()
        try:
            return float(toks[0]), float(toks[1])
        except (IndexError, ValueError):
            return None, None
    return None, None


def parse_log(log_path):
    """Pull the raw quantities out of a cmsRun log. Missing values come back None."""
    with open(log_path, errors="replace") as fh:
        lines = fh.readlines()

    passed, tried = _genxsec_total(lines)
    filt, filt_err = _filter_eff(lines)
    cpu = _cpu_total_loop(lines)

    match_eff = match_err = None
    if passed is not None and tried:
        match_eff = passed / tried
        match_err = math.sqrt(match_eff * (1.0 - match_eff) / tried)

    return {
        "passed": passed, "tried": tried, "cpu_loop": cpu,
        "match_eff": match_eff, "match_eff_err": match_err,
        "filter_eff": filt, "filter_eff_err": filt_err,
    }


def run_mass(args, mass):
    """Run one mass point. Returns a CSV row dict; values are '' on failure."""
    workdir = os.path.join(args.outdir, "M-%d" % mass)
    if not os.path.isdir(workdir):
        os.makedirs(workdir)

    cfg = "RPV_M%d_wmLHEGS_cfg.py" % mass
    fileout = "RPV_M%d_wmLHEGS.root" % mass
    log_name = "RPV_M%d_wmLHEGS.log" % mass
    log_path = os.path.join(workdir, log_name)
    sim_path = os.path.join(workdir, fileout)

    row = {"mass": mass, "time per event": "", "size per event": "",
           "match efficiency": "", "filter efficiency": ""}

    if args.resume and os.path.exists(log_path) and os.path.exists(sim_path):
        print("[M-%d] resume: reusing existing log" % mass)
    else:
        driver = cmsdriver_cmd(args, mass, cfg, fileout)
        print("[M-%d] cmsDriver" % mass)
        if args.dry_run:
            print("    " + " ".join(driver))
            print("    cmsRun %s  (cwd %s)" % (cfg, workdir))
            return row
        rc = subprocess.call(driver, cwd=workdir)
        if rc != 0:
            print("[M-%d] cmsDriver failed (rc=%d), skipping" % (mass, rc))
            return row

        print("[M-%d] cmsRun %d events -> %s" % (mass, args.events, log_path))
        with open(log_path, "w") as logfh:
            rc = subprocess.call(["cmsRun", cfg], cwd=workdir,
                                 stdout=logfh, stderr=subprocess.STDOUT)
        if rc != 0:
            print("[M-%d] cmsRun failed (rc=%d), see %s" % (mass, rc, log_path))
            return row

    vals = parse_log(log_path)
    missing = [k for k in ("passed", "cpu_loop", "match_eff", "filter_eff")
               if vals[k] is None]
    if missing:
        print("[M-%d] could not parse %s from %s" % (mass, ", ".join(missing), log_path))
        return row
    if not vals["passed"]:
        print("[M-%d] zero events passed matching; no numbers to report" % mass)
        return row

    if not os.path.exists(sim_path):
        print("[M-%d] GEN-SIM output %s missing; size per event unavailable"
              % (mass, sim_path))
        return row

    time_per_event = vals["cpu_loop"] / vals["passed"]
    size_per_event = os.path.getsize(sim_path) / 1024.0 / vals["passed"]

    print("[M-%d] %d/%d passed | %.3f s/ev | %.1f kB/ev | match %.4f +/- %.4f | filter %.4f"
          % (mass, vals["passed"], vals["tried"], time_per_event, size_per_event,
             vals["match_eff"], vals["match_eff_err"], vals["filter_eff"]))

    row["time per event"] = "%.3f" % time_per_event
    row["size per event"] = "%.1f" % size_per_event
    row["match efficiency"] = "%.4f" % vals["match_eff"]
    row["filter efficiency"] = "%.4f" % vals["filter_eff"]
    return row


def write_csv(path, rows):
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--o", "--outdir", dest="outdir", required=True,
                   help="parent output directory; one subdirectory per mass point")
    p.add_argument("--masses", type=int, nargs="+", default=MASSES,
                   help="mass points to run")
    p.add_argument("--events", type=int, default=1000,
                   help="events per mass point (cmsDriver -n)")
    p.add_argument("--csv", default="mcm_numbers.csv",
                   help="CSV filename, written inside --o")
    p.add_argument("--conditions", default="150X_mcRun3_2024_realistic_v2")
    p.add_argument("--era", default="Run3_2024")
    p.add_argument("--beamspot", default="DBrealistic")
    p.add_argument("--resume", action="store_true",
                   help="reuse an existing log+GEN-SIM instead of re-running")
    p.add_argument("--dry-run", action="store_true",
                   help="print the commands without running them")
    args = p.parse_args()

    if not args.dry_run and not os.environ.get("CMSSW_BASE"):
        sys.exit("CMSSW_BASE is not set: run this from a cmsenv'd area.")

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)
    csv_path = os.path.join(args.outdir, args.csv)

    rows = []
    for mass in args.masses:
        rows.append(run_mass(args, mass))
        if not args.dry_run:
            write_csv(csv_path, rows)

    if not args.dry_run:
        done = sum(1 for r in rows if r["time per event"] != "")
        print("\n%d/%d mass points complete -> %s" % (done, len(rows), csv_path))


if __name__ == "__main__":
    main()
