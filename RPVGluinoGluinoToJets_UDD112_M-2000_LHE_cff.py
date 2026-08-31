# LHE step only for the RPV_GluinoGluinoto6Q M-2000 gridpack.
#   cmsDriver.py Configuration/GenProduction/python/RPVGluinoGluinoToJets_UDD112_M-2000_LHE_cff.py \
#     --step LHE --eventcontent LHE --datatier LHE \
#     --fileout file:RPV_M2000_LHE.root -n 20000 ...
import FWCore.ParameterSet.Config as cms

externalLHEProducer = cms.EDProducer("ExternalLHEProducer",
    args = cms.vstring('/eos/user/j/jlawless/genproductions_scripts/bin/MadGraph5_aMCatNLO/'
        'RPV_GluinoGluinoto6Q_M-2000_el8_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz'),
    nEvents = cms.untracked.uint32(20000),
    numberOfParameters = cms.uint32(1),
    outputFile = cms.string('cmsgrid_final.lhe'),
    scriptName = cms.FileInPath('GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh')
)
