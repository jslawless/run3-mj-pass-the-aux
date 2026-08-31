#!/usr/bin/env python3
"""Fan a qCut scan out to condor.

Takes the LHE-tier root file produced locally by the --step LHE job, renders one
GEN fragment per qCut from RPVGluinoGluinoToJets_UDD112_GEN_cff.py.in, turns each
into a cfg with cmsDriver, and submits one condor job per cfg.

    ./submit_gen_qcut_scan.py RPV_M300_LHE.root
    ./submit_gen_qcut_scan.py RPV_M300_LHE.root --qcuts 30 50 80 110 --dry-run

The mass point is read from the LHE filename unless --mass is given.  Run from
lxplus inside a cmsenv'd area, from /eos/user/... or /afs (not /tmp) so condor
does not fall back to spool mode.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, 'RPVGluinoGluinoToJets_UDD112_GEN_cff.py.in')
FRAGMENT_NAME = ('RPVGluinoGluinoToJets_UDD112_M-{mass}_qCut{qcut}'
                 '_TuneCP5_13p6TeV_madgraphMLM-pythia8_cff.py')

CONDITIONS = '150X_mcRun3_2024_realistic_v2'
ERA = 'Run3_2024'
BEAMSPOT = 'DBrealistic'

WRAPPER = """#!/bin/bash
# Sets up the submitter's CMSSW area, then runs one GEN cfg in the job scratch.
set -euo pipefail
CFG="$1"
SCRATCH="$PWD"
echo "host   : $(hostname)"
echo "scratch: $SCRATCH"
echo "cfg    : $CFG"
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "{cmssw_base}"
eval `scramv1 runtime -sh`
cd "$SCRATCH"
cmsRun "$CFG"
ls -l *.root
"""

SUBMIT = """universe                = vanilla
executable              = run_gen.sh
arguments               = $(cfg)
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
transfer_input_files    = $(cfg), {lhe}
transfer_output_files   = $(outroot)
output                  = logs/$(cfg).$(ClusterId).$(ProcId).out
error                   = logs/$(cfg).$(ClusterId).$(ProcId).err
log                     = logs/scan.$(ClusterId).log
request_cpus            = {nthreads}
request_memory          = {memory}
request_disk            = 20000000
+JobFlavour             = "{flavour}"

queue cfg,outroot from joblist.txt
"""


def run(cmd, **kw):
    print('+ ' + ' '.join(cmd))
    subprocess.run(cmd, check=True, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('lhe', help='LHE-tier root file from the --step LHE job')
    ap.add_argument('--mass', type=int, default=None,
                    help='gluino mass in GeV (default: parsed from the LHE filename)')
    ap.add_argument('--qcuts', type=int, nargs='+', default=[30, 50, 80, 110])
    ap.add_argument('--nthreads', type=int, default=4)
    ap.add_argument('--memory', type=int, default=4000, help='MB per job')
    ap.add_argument('--flavour', default='workday',
                    help='condor JobFlavour (espresso/microcentury/longlunch/workday/...)')
    ap.add_argument('--workdir', default=None,
                    help='where cfgs, logs and submit files go (default gen_qcut_scan_M<mass>)')
    ap.add_argument('--dry-run', action='store_true',
                    help='build everything but do not condor_submit')
    args = ap.parse_args()

    cmssw_base = os.environ.get('CMSSW_BASE')
    if not cmssw_base:
        sys.exit('CMSSW_BASE is not set -- cmsenv first.')
    if not os.path.exists(TEMPLATE):
        sys.exit('template not found: %s' % TEMPLATE)

    lhe = os.path.abspath(args.lhe)
    if not os.path.exists(lhe):
        sys.exit('LHE file not found: %s' % lhe)

    mass = args.mass
    if mass is None:
        m = re.search(r'M-?(\d+)', os.path.basename(lhe))
        if not m:
            sys.exit('cannot read the mass from %r -- pass --mass' % os.path.basename(lhe))
        mass = int(m.group(1))
    print('mass point : %d GeV' % mass)
    print('qCut scan  : %s' % ', '.join(str(q) for q in args.qcuts))
    print('LHE input  : %s' % lhe)

    workdir = os.path.abspath(args.workdir or 'gen_qcut_scan_M%d' % mass)
    os.makedirs(os.path.join(workdir, 'logs'), exist_ok=True)

    # 1. render one fragment per qCut into the CMSSW python area
    gendir = os.path.join(cmssw_base, 'src', 'Configuration', 'GenProduction', 'python')
    os.makedirs(gendir, exist_ok=True)
    template = open(TEMPLATE).read()
    fragments = {}
    for q in args.qcuts:
        body = template.replace('%MASS%', str(mass)).replace('%QCUT%', '%d.' % q)
        assert '%MASS%' not in body and '%QCUT%' not in body
        name = FRAGMENT_NAME.format(mass=mass, qcut=q)
        with open(os.path.join(gendir, name), 'w') as fh:
            fh.write(body)
        fragments[q] = name
        print('fragment   : %s' % name)

    # 2. one scram b so cmsDriver can import them
    run(['scram', 'b', '-j', '8'], cwd=os.path.join(cmssw_base, 'src'))

    # 3. one cfg per qCut.  --filein is the bare basename: condor lands the LHE
    #    file in the job scratch next to the cfg.
    joblist = []
    for q in args.qcuts:
        cfg = 'GEN_M%d_qCut%d_cfg.py' % (mass, q)
        outroot = 'GEN_M%d_qCut%d.root' % (mass, q)
        run(['cmsDriver.py', 'Configuration/GenProduction/python/' + fragments[q],
             '--python_filename', cfg,
             '--eventcontent', 'RAWSIM', '--datatier', 'GEN',
             '--filein', 'file:' + os.path.basename(lhe),
             '--fileout', 'file:' + outroot,
             '--step', 'GEN',
             '--conditions', CONDITIONS,
             '--beamspot', BEAMSPOT, '--era', ERA,
             '--customise', 'Configuration/DataProcessing/Utils.addMonitoring',
             '--nThreads', str(args.nthreads),
             '--no_exec', '--mc', '-n', '-1'], cwd=workdir)
        joblist.append((cfg, outroot))

    # 4. condor inputs
    with open(os.path.join(workdir, 'joblist.txt'), 'w') as fh:
        for cfg, outroot in joblist:
            fh.write('%s, %s\n' % (cfg, outroot))

    wrapper = os.path.join(workdir, 'run_gen.sh')
    with open(wrapper, 'w') as fh:
        fh.write(WRAPPER.format(cmssw_base=cmssw_base))
    os.chmod(wrapper, 0o755)

    subfile = os.path.join(workdir, 'submit_gen_M%d.sub' % mass)
    with open(subfile, 'w') as fh:
        fh.write(SUBMIT.format(lhe=lhe, nthreads=args.nthreads,
                               memory=args.memory, flavour=args.flavour))

    print('\nprepared %d jobs in %s' % (len(joblist), workdir))
    for cfg, outroot in joblist:
        print('  %-28s -> %s' % (cfg, outroot))

    if args.dry_run:
        print('\n--dry-run: not submitting.  To submit:')
        print('  cd %s && condor_submit %s' % (workdir, os.path.basename(subfile)))
        return

    if not shutil.which('condor_submit'):
        sys.exit('condor_submit not on PATH -- are you on lxplus?')
    run(['condor_submit', os.path.basename(subfile)], cwd=workdir)
    print('\ncondor_q -nobatch    # to watch')


if __name__ == '__main__':
    main()
