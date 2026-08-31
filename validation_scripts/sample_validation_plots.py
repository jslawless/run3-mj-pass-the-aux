#!/usr/bin/env python

import argparse
import itertools
import ROOT
from DataFormats.FWLite import Events, Handle

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(1111)


def find_last_copy(gp):
    current = gp
    while True:
        ndau = current.numberOfDaughters()
        if ndau == 0:
            break
        daughters = [current.daughter(i) for i in range(ndau)]
        same_pdg = [d for d in daughters if d.pdgId() == current.pdgId()]
        if len(same_pdg) == 1 and len(daughters) == 1:
            current = same_pdg[0]
        else:
            break
    return current
 
def get_decay_daughters(gp):
    """Return the actual decay products of a gen particle (after skipping self-copies)."""
    last = find_last_copy(gp)
    return [last.daughter(i) for i in range(last.numberOfDaughters())]

def is_susy_pdgid(pdgid):
    """SUSY particles live in the 1000001-1000039 and 2000001-2000015 pdgId ranges
    (squarks/sleptons/gluino/neutralinos/charginos, and their '2000xxx' second-generation
    mass-eigenstate partners)."""
    a = abs(pdgid)
    return (1000001 <= a <= 1000039) or (2000001 <= a <= 2000015)
 
def resolve_decay_chain(gp):
    """Returns (intermediates, final_daughters):
      intermediates    -- list of intermediate SUSY GenParticles encountered along the chain
      final_daughters   -- list of final (non-SUSY) GenParticles ending the chain
    """
    intermediates = []
    final_daughters = []
 
    def _recurse(particle):
        last = find_last_copy(particle)
        ndau = last.numberOfDaughters()
        if ndau == 0:
            final_daughters.append(last)
            return
        for i in range(ndau):
            d = last.daughter(i)
            if is_susy_pdgid(d.pdgId()):
                intermediates.append(d)
                _recurse(d)
            else:
                final_daughters.append(d)
 
    _recurse(gp)
    return intermediates, final_daughters

def print_all_getters(obj):
    for name in sorted(dir(obj)):
        if name.startswith("_"):
            continue
        try:
            attr = getattr(obj, name)
            if callable(attr):
                val = attr()
            else:
                val = attr
            print("%-30s %s" % (name, val))
        except Exception:
            pass  # skip methods that need arguments or fail

def get_args():
    p = argparse.ArgumentParser(description="Plot Jet quantities from a CMS EDM ROOT file")
    p.add_argument("infile", help="Path to the EDM ROOT file (MiniAOD/AOD)")
    p.add_argument("--branches", action="store_true",
                   help="Print all branch names in the 'Events' TTree of the input file and exit, without making any plots."),
    p.add_argument("--dump", action="store_true",
                   help="Print all data members of the first jet found (via Dump()) and exit, without making any plots.")
    p.add_argument("--label", default="ak4GenJets",
                   help="Jet collection module label. ")
    p.add_argument("--type", default="reco::GenJet",
                   choices=["pat::Jet", "reco::PFJet"],
                   help="C++ type of the jet collection")
    p.add_argument("--max-events", type=int, default=-1,
                   help="Maximum number of events to process (-1 = all)")
    p.add_argument("--out", default="sample_validation_plots.pdf",
                   help="Output plot filename")
    p.add_argument("--plots-per-canvas", type=int, default=1,
                   help="Maximum number of histograms to draw per canvas/page. "
                        "If there are more histograms than this, output is split across "
                        "multiple pages of a multi-page PDF (default: 1).")
    p.add_argument("--genparticle-label", default="genParticles",
                   help="GenParticle collection module label")
    p.add_argument("--status", type=int, default=22,
                   help="Required gen particle status (default: 22, i.e. outgoing hard-process particle in Pythia8 convention).")
    p.add_argument("--dump-gluino-decay", action="store_true",
                   help="Find the first event with a selected gluino, print its full decay "
                        "chain (skipping self-copies) with daughter pdgIds/status/kinematics, "
                        "and exit without making any plots.")
    return p.parse_args()

def main():
    args = get_args()

    # Handle/label for the jet collection
    jetType = "vector<%s>" % args.type
    jetHandle = Handle(jetType)
    jetLabel = args.label

    # Handle/label for gen particles (used to count gluinos, pdgId == 1000021)
    GLUINO_PDGID = 1000021
    STATUS = args.status
    genHandle = Handle("vector<reco::GenParticle>")
    genLabel = args.genparticle_label

    # Histograms declaration
    hists = {
        "njets":  ROOT.TH1F("h_njets",  "Jets per event;n_{jets};Events", 20, 0, 20),
        "pt":     ROOT.TH1F("h_pt",     "Jet p_{T};p_{T} [GeV];Jets", 100, 0, 1500),
        "eta":    ROOT.TH1F("h_eta",    "Jet #eta;#eta;Jets",         100, -5, 5),
        "phi":    ROOT.TH1F("h_phi",    "Jet #phi;#phi [rad];Jets",   100, -3.2, 3.2),
        "mass":   ROOT.TH1F("h_mass",   "Jet mass;mass [GeV];Jets",   100, 0, 100),
        "energy": ROOT.TH1F("h_energy", "Jet energy;E [GeV];Jets",    100, 0, 1000),
        "nconst": ROOT.TH1F("h_nconst", "Jet n constituents;nConstituents;Jets",  100, 0, 100),#nConstituents
        "ndaugh": ROOT.TH1F("h_ndaugh", "Jet n daughters;nDaughters;Jets",        100, 0, 100),#numberOfDaughters
        "ht":     ROOT.TH1F("h_ht",     "Jet H_{T};H_{T} [GeV];Events",           100, 0, 4000),
        "ngluino": ROOT.TH1F("h_ngluino", "Number of gluinos per event;n_{#tilde{g}};Events",       30, 0, 30),
        "ngluino_sx": ROOT.TH1F("h_ngluino_sx", "Number of gluinos per event;n_{#tilde{g}};Events", 10, 0, 10),
        "ngluino_vs_status": ROOT.TH2F("h_ngluino_vs_status", "status vs n_{#tilde{g}} per event;n_{#tilde{g}};status", 30, 0, 30, 50, 20, 70),
        "gluino_mass": ROOT.TH1F("h_gluino_mass", "Gluino mass;mass [GeV];Gluinos", 100, 0, 3000),
        "gluino_ndaughters": ROOT.TH1F("h_gluino_ndaughters", "Number of gluino decay daughters;n_{daughters};Gluinos", 10, 0, 10),
        "m3j": ROOT.TH1F("h_m3j", "Average 3-jet system mass (mass difference method); <M_{3j}> [GeV];Events",
                          100, 0, 3000)
    }
    for h in hists.values():
        h.SetDirectory(0)
    hists["ngluino_vs_status"].SetStats(0)

    print("Opening file: %s" % args.infile)

    if args.branches:
        f = ROOT.TFile.Open(args.infile)
        if not f or f.IsZombie():
            print("Could not open file: %s" % args.infile)
            return
        tree = f.Get("Events")
        if not tree:
            print("No 'Events' TTree found in file.")
            f.Close()
            return
        branches = sorted(b.GetName() for b in tree.GetListOfBranches())
        print("Found %d branches in 'Events' tree:\n" % len(branches))
        for name in branches:
            print(name)
        f.Close()
        return

    events = Events(args.infile)
    print("Total events in file: %d" % events.size())

    if args.dump:
        for event in events:
            event.getByLabel(jetLabel, jetHandle)
            if not jetHandle.isValid():
                continue
            jets = jetHandle.product()
            if len(jets) == 0:
                continue
            print_all_getters(jets[0])
            # print("Dumping all data members of the first '%s' (%s) found:\n" % (jetLabel, args.type))
            # jets[0].Dump()
            return
        print("No jets found in collection '%s' -- nothing to dump." % jetLabel)
        return

    if args.dump_gluino_decay is not None:
        gluino_pt_min = 20.0
        iter_events=0
        for event in events:
            event.getByLabel(genLabel, genHandle)
            if not genHandle.isValid():
                continue
            genparticles = genHandle.product()
            gluinos = [gp for gp in genparticles
                       if gp.pdgId() == GLUINO_PDGID
                       and gp.status() == args.status
                       and gp.pt() > gluino_pt_min]
            if not gluinos:
                continue
 
            print("Event %d -> Found %d gluino(s) passing status==%d, pt>%.1f in this event:\n"
                  % (iter_events, len(gluinos), args.status, gluino_pt_min))
            for idx, gp in enumerate(gluinos):
                print("  Gluino #%d: pt=%.1f eta=%.2f phi=%.2f mass=%.2f status=%d"
                      % (idx, gp.pt(), gp.eta(), gp.phi(), gp.mass(), gp.status()))
                last = find_last_copy(gp)
                if last is not gp:
                    print("  -> last self-copy: pt=%.1f eta=%.2f phi=%.2f mass=%.2f status=%d"
                          % (last.pt(), last.eta(), last.phi(), last.mass(), last.status()))
                # daughters = get_decay_daughters(gp)
                intermediates, daughters = resolve_decay_chain(gp)
                print("  -> %d decay daughter(s):" % len(daughters))
                ##############
                if intermediates:
                    print("  -> %d intermediate SUSY particle(s) in the chain:" % len(intermediates))
                    for sp in intermediates:
                        print("       pdgId=%-8d status=%-4d pt=%-8.2f eta=%-6.2f phi=%-6.2f mass=%.3f"
                              % (sp.pdgId(), sp.status(), sp.pt(), sp.eta(), sp.phi(), sp.mass()))
                else:
                    print("  -> no intermediate SUSY particles")
                print("  -> %d final decay daughter(s):" % len(daughters))
                for d in daughters:
                    print("       pdgId=%-6d status=%-4d pt=%-8.2f eta=%-6.2f phi=%-6.2f mass=%.3f"
                          % (d.pdgId(), d.status(), d.pt(), d.eta(), d.phi(), d.mass()))
                #################
                if daughters:
                    p4_sum = daughters[0].p4()
                    for d in daughters[1:]:
                        p4_sum = p4_sum + d.p4()
                    print("  -> invariant mass of daughters: %.2f GeV\n" % p4_sum.M())
            # return
            iter_events+=1
            if iter_events>=args.max_events:
                return
 
        print("No event with a selected gluino found -- nothing to dump.")
        return

    n_events = 0
    n_total = events.size() if args.max_events < 0 else min(events.size(), args.max_events)
    print("Processing %d events, jet collection '%s' (%s)" % (n_total, jetLabel, args.type))

    jet_pt_min, jet_eta_max = 20., 2.4
    gen_status = args.status

    for event in events:
        if args.max_events > 0 and n_events >= args.max_events:
            break
        n_events += 1

        event.getByLabel(jetLabel, jetHandle)
        if not jetHandle.isValid():
            continue
        jets = jetHandle.product()

        sel_jets = [j for j in jets if j.pt() > jet_pt_min and abs(j.eta()) < jet_eta_max]

        hists["njets"].Fill(len(sel_jets))

        ht = 0.0
        for jet in sel_jets:
            hists["pt"].Fill(jet.pt())
            hists["eta"].Fill(jet.eta())
            hists["phi"].Fill(jet.phi())
            hists["mass"].Fill(jet.mass())
            hists["energy"].Fill(jet.energy())
            try:
                hists["nconst"].Fill(jet.nConstituents())
                hists["ndaugh"].Fill(jet.numberOfDaughters())
            except AttributeError:
                pass  # not available for all jet types
            ht += jet.pt()

        hists["ht"].Fill(ht)

         # --- 3-jet mass reconstruction ---
        if len(sel_jets) >= 6:
            leading6 = sorted(sel_jets, key=lambda j: j.pt(), reverse=True)[:6]
            best_diff = None
            best_masses = None
            for combo in itertools.combinations(range(6), 3):
                if 0 not in combo:
                    continue  # skip the complementary combo (already covered by its pair)
                other = tuple(i for i in range(6) if i not in combo)
 
                # the 3-jet four-momenta
                p4_a = leading6[combo[0]].p4()
                for i in combo[1:]:
                    p4_a = p4_a + leading6[i].p4()
                # the other 3-jet four-momenta
                p4_b = leading6[other[0]].p4()
                for i in other[1:]:
                    p4_b = p4_b + leading6[i].p4()
 
                # 3-jet mass difference method
                m_a, m_b = p4_a.M(), p4_b.M()
                diff = abs(m_a - m_b)
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_masses = (m_a, m_b)
 
            if best_masses is not None:
                avg_mass = 0.5 * (best_masses[0] + best_masses[1])
                hists["m3j"].Fill(avg_mass)

        event.getByLabel(genLabel, genHandle)
        if genHandle.isValid():
            genparticles = genHandle.product()
            #and gp.status() == 62 (22, 44, 52, 62)
            n_gluino = sum(1 for gp in genparticles
                           if gp.pdgId() == GLUINO_PDGID
                           and gp.pt() > jet_pt_min
                           and abs(gp.eta()) < jet_eta_max)
            n_gluino_sx = sum(1 for gp in genparticles
                           if gp.pdgId() == GLUINO_PDGID
                           and gp.pt() > jet_pt_min
                           and abs(gp.eta()) < jet_eta_max
                           and (gp.status() == gen_status))
            hists["ngluino"].Fill(n_gluino)
            hists["ngluino_sx"].Fill(n_gluino_sx)
            gluino_candidates = [gp for gp in genparticles 
                            if gp.pdgId() == GLUINO_PDGID
                            and gp.pt() > jet_pt_min
                            and abs(gp.eta()) < jet_eta_max]
            n_gluino_candidates = sum(1 for gp in gluino_candidates)
            for gp in gluino_candidates:
                hists["gluino_mass"].Fill(gp.mass())
                # daughters = get_decay_daughters(gp)
                intermediates, daughters = resolve_decay_chain(gp)
                hists["gluino_ndaughters"].Fill(len(daughters))
            for gp in gluino_candidates:
                hists["ngluino_vs_status"].Fill(n_gluino, gp.status())

        if n_events % 1000 == 0:
            print("  processed %d events..." % n_events)

    print("Done. Processed %d events." % n_events)

    # Draw everything, split across as many canvases/pages as needed
    order = ["njets", "pt", "eta", "phi", "mass", "energy", "nconst", "ndaugh", "ht",
              "ngluino", "ngluino_vs_status", "ngluino_sx", "gluino_ndaughters", "m3j"
            ]
    # order = ["gluino_ndaughters", "gluino_daughter_pdgid", "gluino_daughters_mass", "intermediate_pdgid", "intermediate_mass"]
    draw_opts = {"ngluino_vs_status": "COLZ"}
    logy_keys = {"pt", "energy", "ht"}
 
    n_per_canvas = max(1, args.plots_per_canvas)
    chunks = [order[i:i + n_per_canvas] for i in range(0, len(order), n_per_canvas)]

    is_pdf = args.out.lower().endswith(".pdf")
    canvases = []  # keep references alive until all Print() calls are done
 
    for page, keys in enumerate(chunks):
        ncols = int(ROOT.TMath.Ceil(ROOT.TMath.Sqrt(len(keys))))
        nrows = int(ROOT.TMath.Ceil(float(len(keys)) / ncols))
 
        c = ROOT.TCanvas("c%d" % page, "sample validation plots (page %d)" % (page + 1),
                          500 * ncols, 400 * nrows)
        c.Divide(ncols, nrows)
        canvases.append(c)
 
        for i, key in enumerate(keys, start=1):
            c.cd(i)
            h = hists[key]
            if isinstance(h, ROOT.TH2):
                h.Draw(draw_opts.get(key, "COLZ"))
            else:
                h.SetLineWidth(2)
                h.SetLineColor(ROOT.kAzure + 2)
                h.Draw(draw_opts.get(key, "HIST"))
                ROOT.gPad.SetLogy(key in logy_keys)

            label = ROOT.TLatex()
            label.SetNDC(True)
            label.SetTextSize(0.040)
            label.SetTextFont(42)
            sel_label = "p_{T} > %.0f, |#eta| < %.1f" % (jet_pt_min, jet_eta_max)
            if key == "ngluino_sx":
                sel_label = "p_{T} > %.0f, |#eta| < %.1f, status=%.0f" % (jet_pt_min, jet_eta_max, gen_status)
            label.DrawLatex(0.12, 0.92, sel_label)
            ROOT.SetOwnership(label, False)  # keep it alive after the loop
 
        if is_pdf and len(chunks) > 1:
            if page == 0:
                c.Print(args.out + "(")
            elif page == len(chunks) - 1:
                c.Print(args.out + ")")
            else:
                c.Print(args.out)
        else:
            # single page, or non-PDF output: one file per page
            if len(chunks) == 1:
                c.SaveAs(args.out)
            else:
                c.SaveAs("jet_%s.png" % (order[page]))
                # base, ext = args.out.rsplit(".", 1)
                # c.SaveAs("%s_page%d.%s" % (base, page + 1, ext))

 
    print("Saved plots to %s (%d page(s), %d plots/canvas)" %
          (args.out, len(chunks), n_per_canvas))

    # Also keep an individual .root file with the histograms for later use
    root_out = args.out.rsplit(".", 1)[0] + ".root"
    fout = ROOT.TFile(root_out, "RECREATE")
    for h in hists.values():
        h.Write()
    fout.Close()
    print("Saved histograms to %s" % root_out)


if __name__ == "__main__":
    main()