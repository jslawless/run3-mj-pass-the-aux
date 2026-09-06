# RPV gluino pair -> 6 quarks (lambda''_112, "UDD112"), prompt, 13.6 TeV Run 3.
#
# Single fragment for the full LHE -> GEN -> SIM chain.  Set MASS_POINT below;
# it selects the gridpack tarball and the SLHA gluino mass together.
#
#   cmsDriver.py Configuration/GenProduction/python/RPVGluinoGluinoToJets_UDD112_TuneCP5_13p6TeV_madgraphMLM-pythia8_wmLHEGS_cff.py \
#     --python_filename RPV_wmLHEGS_cfg.py \
#     --eventcontent RAWSIM,LHE --datatier GEN-SIM,LHE \
#     --fileout file:RPV_wmLHEGS.root \
#     --step LHE,GEN,SIM --geometry DB:Extended \
#     --conditions 150X_mcRun3_2024_realistic_v2 --beamspot DBrealistic \
#     --era Run3_2024 \
#     --customise Configuration/DataProcessing/Utils.addMonitoring \
#     --no_exec --mc -n 1000
#
# Production: MG5_aMC 2.9.18 + RPVMSSM_UFO, MLM-merged, undecayed gluino pairs
#   generate p p > go go /sups @0 ; + j @1 ; + j j @2
# Decay: Pythia8 from the SLHA table below; Majorana gluino, so the two modes
# are 50/50.

MASS_POINT   = 1000   # GeV. Drives GRIDPACK and the SLHA gluino mass.
N_EVENTS     = 1000   # must equal the cmsDriver -n
QCUT         = 50.    # MLM merging scale. run_card xqcut = 30. UNSETTLED, see note
GLUINO_WIDTH = 1.0    # GeV -> ctau ~ 2e-13 mm, prompt by fiat
NJETMAX      = 2      # highest-multiplicity ME is p p > go go j j
NQMATCH      = 4      # gridpack is 4-flavour (run_card maxjetflavor = 4)

# qCut note: 50 is the current working value. At M-1000 the surviving ME
# multiplicity fractions are 32/30/38 (0p/1p/2p) -- the series has not turned
# over, so this may need to rise. Pythia-side only: no gridpack rebuild.

GRIDPACK = ('/eos/user/j/jlawless/genproductions_scripts/bin/MadGraph5_aMCatNLO/'
            'RPV_GluinoGluinoto6Q_M-%d_el8_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz'
            % MASS_POINT)

SLHA_TABLE = """
BLOCK MASS  # everything except the gluino is decoupled
# PDG code           mass       particle
   1000001     1.00000000E+05   # ~d_L
   2000001     1.00000000E+05   # ~d_R
   1000002     1.00000000E+05   # ~u_L
   2000002     1.00000000E+05   # ~u_R
   1000003     1.00000000E+05   # ~s_L
   2000003     1.00000000E+05   # ~s_R
   1000004     1.00000000E+05   # ~c_L
   2000004     1.00000000E+05   # ~c_R
   1000005     1.00000000E+05   # ~b_1
   2000005     1.00000000E+05   # ~b_2
   1000006     1.00000000E+05   # ~t_1
   2000006     1.00000000E+05   # ~t_2
   1000011     1.00000000E+05   # ~e_L
   2000011     1.00000000E+05   # ~e_R
   1000012     1.00000000E+05   # ~nu_eL
   1000013     1.00000000E+05   # ~mu_L
   2000013     1.00000000E+05   # ~mu_R
   1000014     1.00000000E+05   # ~nu_muL
   1000015     1.00000000E+05   # ~tau_1
   2000015     1.00000000E+05   # ~tau_2
   1000016     1.00000000E+05   # ~nu_tauL
   1000021     %MGLUINO%        # ~g
   1000022     1.00000000E+05   # ~chi_10
   1000023     1.00000000E+05   # ~chi_20
   1000025     1.00000000E+05   # ~chi_30
   1000035     1.00000000E+05   # ~chi_40
   1000024     1.00000000E+05   # ~chi_1+
   1000037     1.00000000E+05   # ~chi_2+

# DECAY TABLE
#         PDG            Width
DECAY   1000001     0.00000000E+00   # sdown_L decays
DECAY   2000001     0.00000000E+00   # sdown_R decays
DECAY   1000002     0.00000000E+00   # sup_L decays
DECAY   2000002     0.00000000E+00   # sup_R decays
DECAY   1000003     0.00000000E+00   # sstrange_L decays
DECAY   2000003     0.00000000E+00   # sstrange_R decays
DECAY   1000004     0.00000000E+00   # scharm_L decays
DECAY   2000004     0.00000000E+00   # scharm_R decays
DECAY   1000005     0.00000000E+00   # sbottom1 decays
DECAY   2000005     0.00000000E+00   # sbottom2 decays
DECAY   1000006     0.00000000E+00   # stop1 decays
DECAY   2000006     0.00000000E+00   # stop2 decays
DECAY   1000011     0.00000000E+00   # selectron_L decays
DECAY   2000011     0.00000000E+00   # selectron_R decays
DECAY   1000012     0.00000000E+00   # snu_elL decays
DECAY   1000013     0.00000000E+00   # smuon_L decays
DECAY   2000013     0.00000000E+00   # smuon_R decays
DECAY   1000014     0.00000000E+00   # snu_muL decays
DECAY   1000015     0.00000000E+00   # stau_1 decays
DECAY   2000015     0.00000000E+00   # stau_2 decays
DECAY   1000016     0.00000000E+00   # snu_tauL decays
DECAY   1000021     %WGLUINO%        # gluino decays: RPV UDD, lambda''_112
#   BR                NDA  ID1   ID2   ID3
    5.00000000E-01    3      2     1     3   # BR(~g -> u    d    s)
    5.00000000E-01    3     -2    -1    -3   # BR(~g -> u~   d~   s~)
DECAY   1000022     0.00000000E+00   # neutralino1 decays
DECAY   1000023     0.00000000E+00   # neutralino2 decays
DECAY   1000024     0.00000000E+00   # chargino1+ decays
DECAY   1000025     0.00000000E+00   # neutralino3 decays
DECAY   1000035     0.00000000E+00   # neutralino4 decays
DECAY   1000037     0.00000000E+00   # chargino2+ decays
"""

import FWCore.ParameterSet.Config as cms
from Configuration.Generator.Pythia8CommonSettings_cfi import *
from Configuration.Generator.MCTunesRun3ECM13p6TeV.PythiaCP5Settings_cfi import *
from Configuration.Generator.PSweightsPythia.PythiaPSweightsSettings_cfi import *

slhatable = SLHA_TABLE.replace('%MGLUINO%', '%e' % MASS_POINT)
slhatable = slhatable.replace('%WGLUINO%', '%e' % GLUINO_WIDTH)

externalLHEProducer = cms.EDProducer("ExternalLHEProducer",
    args = cms.vstring(GRIDPACK),
    nEvents = cms.untracked.uint32(N_EVENTS),
    numberOfParameters = cms.uint32(1),
    outputFile = cms.string('cmsgrid_final.lhe'),
    scriptName = cms.FileInPath('GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh')
)

generator = cms.EDFilter("Pythia8ConcurrentHadronizerFilter",
    maxEventsToPrint = cms.untracked.int32(1),
    pythiaPylistVerbosity = cms.untracked.int32(1),
    filterEfficiency = cms.untracked.double(1.0),
    pythiaHepMCVerbosity = cms.untracked.bool(False),
    comEnergy = cms.double(13600.),
    SLHATableForPythia8 = cms.string('%s' % slhatable),
    PythiaParameters = cms.PSet(
        pythia8CommonSettingsBlock,
        pythia8CP5SettingsBlock,
        pythia8PSweightsSettingsBlock,
        processParameters = cms.vstring(
            'JetMatching:setMad = off',
            'JetMatching:scheme = 1',
            'JetMatching:merge = on',
            'JetMatching:jetAlgorithm = 2',
            'JetMatching:etaJetMax = 5.',
            'JetMatching:coneRadius = 1.',
            'JetMatching:slowJetPower = 1',
            'JetMatching:qCut = %.0f' % QCUT,
            'JetMatching:nQmatch = %d' % NQMATCH,
            'JetMatching:nJetMax = %d' % NJETMAX,
            'JetMatching:doShowerKt = off',
            '6:m0 = 172.5',
            '1000021:mayDecay = on',
            'Check:abortIfVeto = on',
        ),
        parameterSets = cms.vstring('pythia8CommonSettings',
                                    'pythia8CP5Settings',
                                    'pythia8PSweightsSettings',
                                    'processParameters',
                                    )
    )
)

ProductionFilterSequence = cms.Sequence(generator)
