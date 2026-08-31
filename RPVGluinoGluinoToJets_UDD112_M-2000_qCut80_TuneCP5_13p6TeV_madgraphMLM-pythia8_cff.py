# ---------------------------------------------------------------------------
# RPV gluino pair production, gluino -> u d s  (lambda''_112, "UDD112"), prompt.
#
#   Production : MadGraph5_aMC@NLO 2.9.18 + RPVMSSM_UFO
#                  generate p p > go go      @0
#                  add process p p > go go j  @1       (MLM merged)
#                  add process p p > go go j j @2
#                -> the gridpack contains UNDECAYED gluino pairs.
#   Decay      : Pythia8, from the SLHA table below.  The gluino is a Majorana
#                fermion, so BR(go -> u d s) = BR(go -> u~ d~ s~) = 0.5.
#   Tune       : CP5, Run-3 13.6 TeV (MCTunesRun3ECM13p6TeV).
#
# Modelled on the following fragments in this repository:
#   genFragments/Hadronizer/13p6TeV/Hadronizer_TuneCP5_13p6TeV_MLM_5f_max1j_LHE_qCut50_pythia8_cff.py
#       -- used by RPVStopStopToJets_UDD323_M-*_TuneCP5_13p6TeV_madgraphMLM-pythia8
#          (requestTickets/Run3/Jets+X/20231229_dgadkari_st_jj_rpv_UDD323)
#   genFragments/Hadronizer/13p6TeV/LLstau/LLstau_M400_ctau1mm_TuneCP5_13p6TeV_pythia8_cff.py
#       -- gridpack + SLHATableForPythia8 + MLM in one fragment
#
# CMSSW hands SLHATableForPythia8 to Pythia as an external SLHA file, which
# takes precedence over the param_card embedded in the LHE header.  The gluino
# mass here MUST therefore agree with the gridpack's param_card, or the LHE
# resonance mass and the decay table will disagree.
# ---------------------------------------------------------------------------

MASS_POINT   = 2000  # GeV -- gluino mass; must match the gridpack param_card
GLUINO_WIDTH = 1.0     # GeV -> ctau ~ 2e-13 mm, i.e. prompt decay
NJETMAX      = 2       # highest-multiplicity ME is p p > go go j j
QCUT         = 80.   # MLM merging scale; gridpack run_card has xqcut = 30

SLHA_TABLE = """
BLOCK MASS  # Mass spectrum: everything except the gluino is decoupled
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
            'JetMatching:qCut = %.0f' % QCUT,   # this is the actual merging scale
            'JetMatching:nQmatch = 5',          # 5-flavour scheme
            'JetMatching:nJetMax = %d' % NJETMAX,  # partons in the highest-multiplicity ME
            'JetMatching:doShowerKt = off',     # off for MLM matching
            '6:m0 = 172.5',
            '1000021:mayDecay = on',            # decay the gluino from the LHE
            'Check:abortIfVeto = on',
        ),
        parameterSets = cms.vstring('pythia8CommonSettings',
                                    'pythia8CP5Settings',
                                    'pythia8PSweightsSettings',
                                    'processParameters',
                                    )
    )
)

# ---------------------------------------------------------------------------
# Uncomment for --step LHE; leave commented for --step GEN with --filein, and
# for McM.
#
# externalLHEProducer = cms.EDProducer("ExternalLHEProducer",
#     args = cms.vstring('/eos/user/j/jlawless/genproductions_scripts/bin/MadGraph5_aMCatNLO/'
#         'RPV_GluinoGluinoto6Q_M-2000_el8_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz'),
#     nEvents = cms.untracked.uint32(20000),
#     numberOfParameters = cms.uint32(1),
#     outputFile = cms.string('cmsgrid_final.lhe'),
#     scriptName = cms.FileInPath('GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh')
# )
# ---------------------------------------------------------------------------
