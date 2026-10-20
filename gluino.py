import matplotlib.pyplot as plt

import csv

f = csv.reader(open('gluino.csv', 'r'))

masses = []
xsec = []
unc = []


for row in f:
    masses.append(float(row[0]))
    xsec.append(float(row[1]) * (10**3) * 300)
    unc.append(float(row[2]) * 0.01)


plt.plot(masses, xsec,label='Gluino Cross Section')
plt.errorbar(masses, xsec, yerr=unc, fmt='none', color='blue', label='Gluino Cross Section',alpha=0.1)
plt.yscale('log')
plt.xlabel('Gluino Mass (GeV)')
plt.ylabel('Expected Events')
plt.title('xsec [pb] * 300 [fb^-1] * 10^3')

plt.vlines(200, ymin=0.1, ymax=10**10, colors='red', linestyles='dashed', label='200 GeV')
plt.hlines(10**6, xmin=0, xmax=1000, colors='orange', linestyles='dashed', label='200 GeV')

plt.savefig('gluino_cross_section.pdf')