"""Stalmart cross-dock network study: one script from the case workbook to every number in the deck.

Usage:  python src/stalmart_network.py [path/to/Network_modelling_assignment.xlsx]
Needs:  pandas, numpy, openpyxl, scikit-learn
"""
import sys, itertools, math
import numpy as np, pandas as pd

XLSX = sys.argv[1] if len(sys.argv) > 1 else 'data/Network_modelling_assignment.xlsx'

# ---------------------------------------------------------------- 1. load and check the data
df = pd.read_excel(XLSX, sheet_name='ShipmentData', header=1)
df['Origin'] = df['Origin State'].str.strip() + df['Origin Zip'].astype(str)
df['Dest'] = df['DestinationState'].str.strip() + df['DestinationZip'].astype(int).astype(str)  # CT 06492 -> CT6492, as in the tables
df['Date'] = pd.to_datetime(df['ShipDate']); df['Weight'] = df['Weight'].astype(float)

raw = pd.read_excel(XLSX, sheet_name='Part1_Input', header=None)
SUP = ['GA30043', 'CA91720']
XD = ['NC27695', 'NY10006', 'TX75477', 'GA30113', 'IL61849']
CUST = [raw.iloc[r, 4] for r in range(7, 40)]
d_sc = pd.DataFrame(raw.iloc[7:40, 5:7].values.astype(float), index=CUST, columns=SUP)     # supplier -> customer km
d_sx = pd.DataFrame(raw.iloc[7:12, 10:12].values.astype(float), index=XD, columns=SUP)     # supplier -> dock km
d_xc = pd.DataFrame(raw.iloc[7:40, 15:20].values.astype(float), index=CUST, columns=XD)    # dock -> customer km
CAPEX = dict(zip(raw.iloc[3:8, 22], raw.iloc[3:8, 23].astype(float)))
PROC = dict(zip(raw.iloc[14:19, 22], raw.iloc[14:19, 23].astype(float)))
VAR = float(raw.iloc[24, 21])

p2 = pd.read_excel(XLSX, sheet_name='Part2_Input', header=None)
LTL = p2.iloc[5:11, 4:9].values.astype(float)            # unrounded Excel rates
KM_B, KG_B = [50, 250, 500, 1000, 1500], [500, 1000, 2000, 5000]
FTL_RATE, FTL_CAP, FTL_MIN = 1.0, 7000.0, 5250.0

checks = {
    'shipments': len(df), 'total kg': df.Weight.sum(), 'missing values': int(df.isna().sum().sum()),
    'duplicate IDs': int(df.ShipmentID.duplicated().sum()),
    'look-alike rows': int(df.drop(columns=['ShipmentID']).duplicated().sum()),
    'shipping days': df.Date.nunique(), 'min / max kg': (df.Weight.min(), df.Weight.max()),
    'shipments over 7,000 kg': int((df.Weight > FTL_CAP).sum()),
    'customers matched': f"{len(set(df.Dest) & set(CUST))} of {df.Dest.nunique()}",
    'supplier kg': df.groupby('Origin').Weight.sum().to_dict(),
}

# ---------------------------------------------------------------- 2. cost functions
def band(v, bounds):
    for i, b in enumerate(bounds):
        if v <= b: return i          # upper band limit inclusive
    return len(bounds)

def ltl(w, km): return w * km * LTL[band(km, KM_B), band(w, KG_B)]

def move(w, km):
    """Cheapest legal mode for a pooled load: full trucks (from 5,250 kg) plus LTL remainder, or all-LTL."""
    full = int(w // FTL_CAP); rem = w - full * FTL_CAP
    if full == 0 and rem < FTL_MIN: return ltl(w, km), 0, 0.0
    c, t, fk = full * km * FTL_RATE, full, full * FTL_CAP
    if rem >= FTL_MIN: c += km * FTL_RATE; t += 1; fk += rem
    elif rem > 0: c += ltl(rem, km)
    return (ltl(w, km), 0, 0.0) if ltl(w, km) < c else (c, t, fk)

# ---------------------------------------------------------------- 3. today's network (reference)
df['km'] = [d_sc.loc[c, s] for s, c in zip(df.Origin, df.Dest)]
ASIS = sum(move(w, k)[0] for w, k in zip(df.Weight, df.km))

# ---------------------------------------------------------------- 4. Part 1: greenfield, all 31 networks
dem = df.groupby(['Dest', 'Origin']).Weight.sum().unstack().reindex(CUST).fillna(0)[SUP]   # 64 supplier-customer pairs
tot = dem.sum(1)
def part1(S):
    assign, parts = {}, np.zeros(3)
    for c in CUST:
        opt = {x: (sum(dem.loc[c, s] * d_sx.loc[x, s] for s in SUP) * VAR, tot[c] * d_xc.loc[c, x] * VAR, tot[c] * PROC[x]) for x in S}
        x = min(opt, key=lambda k: sum(opt[k])); assign[c] = x; parts += opt[x]
    cap = sum(CAPEX[x] for x in S)
    return dict(S=S, inb=parts[0], outb=parts[1], proc=parts[2], capex=cap, total=parts.sum() + cap, assign=assign)
P1 = sorted((part1(S) for n in range(1, 6) for S in itertools.combinations(XD, n)), key=lambda r: r['total'])
BEST = P1[0]

# ---------------------------------------------------------------- 5. clustering check (weighted k-means)
from sklearn.cluster import KMeans
LATLON = {'GA30303': (33.75, -84.39), 'TX74134': (36.12, -95.85), 'IN46228': (39.85, -86.20), 'CT6492': (41.45, -72.82), 'TX78040': (27.52, -99.50),
          'MO63101': (38.63, -90.19), 'AL35020': (33.40, -86.95), 'MI49120': (41.83, -86.25), 'TX77001': (29.76, -95.37), 'GA30005': (34.08, -84.23),
          'IL60164': (41.92, -87.90), 'NC27602': (35.77, -78.64), 'AL35040': (33.10, -86.75), 'TX76102': (32.75, -97.33), 'MS39501': (30.37, -89.09),
          'KY40391': (37.99, -84.18), 'MI48150': (42.37, -83.37), 'IN46224': (39.79, -86.26), 'AL35601': (34.61, -86.98), 'GA30026': (33.96, -84.07),
          'TN37201': (36.16, -86.78), 'TN37912': (36.00, -83.98), 'FL32099': (30.33, -81.66), 'NC28739': (35.32, -82.46), 'AL36867': (32.47, -85.00),
          'NY10007': (40.714, -74.007), 'SC29501': (34.20, -79.77), 'VA20170': (38.97, -77.39), 'AR72113': (34.87, -92.40), 'AR72703': (36.12, -94.15),
          'IL62702': (39.80, -89.65), 'MO63026': (38.51, -90.45), 'MO63089': (38.47, -90.88), 'NC27695': (35.78, -78.67), 'NY10006': (40.709, -74.013),
          'TX75477': (33.5, -96.3), 'GA30113': (33.80, -85.18), 'IL61849': (40.03, -87.96)}   # approximate, by ZIP
def km_xy(k): la, lo = LATLON[k]; return np.array([lo * math.cos(math.radians(37)) * 111.32, la * 110.57])
Xc = np.array([km_xy(c) for c in CUST]); Wc = tot.values
elbow, K3 = {}, None
for k in range(1, 6):
    km = min((KMeans(n_clusters=k, n_init=1, random_state=s).fit(Xc, sample_weight=Wc) for s in range(20)), key=lambda m: m.inertia_)
    dist = np.linalg.norm(Xc - km.cluster_centers_[km.labels_], axis=1); elbow[k] = (dist * Wc).sum() / Wc.sum()
    if k == 3: K3 = km
near = {i: min(XD, key=lambda x: np.linalg.norm(km_xy(x) - cc)) for i, cc in enumerate(K3.cluster_centers_)}
gap = {near[i]: np.linalg.norm(km_xy(near[i]) - cc) for i, cc in enumerate(K3.cluster_centers_)}
agree = [c for c, l in zip(CUST, K3.labels_) if near[l] == BEST['assign'][c]]

# ---------------------------------------------------------------- 6. Part 2: brownfield costing with same-day pooling
def part2(assign):
    d = df[['Date', 'Origin', 'Dest', 'Weight']].copy(); d['x'] = d.Dest.map(assign); rows = []
    for (dt, o, x), w in d.groupby(['Date', 'Origin', 'x']).Weight.sum().items():
        c, t, fk = move(w, d_sx.loc[x, o]); rows.append(('in', o, x, w, d_sx.loc[x, o], c, t, fk))
    for (dt, x, cu), w in d.groupby(['Date', 'x', 'Dest']).Weight.sum().items():
        c, t, fk = move(w, d_xc.loc[cu, x]); rows.append(('out', x, cu, w, d_xc.loc[cu, x], c, t, fk))
    L = pd.DataFrame(rows, columns=['leg', 'frm', 'to', 'w', 'km', 'cost', 'trucks', 'ftl_kg'])
    L['dock'] = np.where(L.leg == 'in', L.to, L.frm)
    proc = float((d.Weight * d.x.map(PROC)).sum()); cap = sum(CAPEX[x] for x in set(assign.values()))
    return L, proc, cap
L, proc, cap = part2(BEST['assign'])
inb, outb = L[L.leg == 'in'].cost.sum(), L[L.leg == 'out'].cost.sum()
Y2 = inb + outb + proc; Y1 = Y2 + cap

# re-price every network with Part 2 rates (costing note)
p2rank = sorted(((sum(part2(r['assign'])[0].cost) + part2(r['assign'])[1] + r['capex'], '+'.join(r['S'])) for r in P1))
one = [v for v in p2rank if v[1] == 'GA30113'][0]

# ---------------------------------------------------------------- 7. print every deck figure
M = lambda v: f'${v/1e6:,.1f}M'
print('\nDATA (slide 2)'); [print(f'  {k}: {v}') for k, v in checks.items()]
print('\nPART 1 (slide 4): best set per number of docks')
for n in range(1, 6):
    r = next(r for r in P1 if len(r['S']) == n)
    print(f"  {n}: {' + '.join(r['S']):30s} in {M(r['inb'])}  out {M(r['outb'])}  proc {M(r['proc'])}  set-up {M(r['capex'])}  total {M(r['total'])}")
print('\nCLUSTERING (slide 5)')
print('  avg km to nearest centre:', {k: round(v) for k, v in elbow.items()})
print('  centre to nearest dock (km):', {k: round(v) for k, v in gap.items()})
print(f"  same dock as Part 1: {len(agree)} of 33 customers, {tot[agree].sum()/tot.sum():.0%} of kg")
print('\nPART 2 (slides 9-13)')
for leg in ['in', 'out']:
    s = L[L.leg == leg]
    print(f"  {leg}: {len(s):,} loads, {len(s)/df.Date.nunique():.1f}/day, mean {s.w.mean():,.0f} kg, FTL share {s.ftl_kg.sum()/s.w.sum():.0%}, "
          f"{int(s.trucks.sum())} trucks, ${s.cost.sum()/s.w.sum():.1f}/kg")
print(f"  loads total {len(L):,}, FTL share of leg-kg {L.ftl_kg.sum()/L.w.sum():.0%}")
for x in BEST['S']:
    I, O = L[(L.leg == 'in') & (L.dock == x)], L[(L.leg == 'out') & (L.dock == x)]
    print(f"  {x}: in {M(I.cost.sum())}  out {M(O.cost.sum())}  inbound FTL {I.ftl_kg.sum()/I.w.sum():.0%}  outbound FTL {O.ftl_kg.sum()/O.w.sum():.0%}")
print(f"  cost: inbound {M(inb)}  outbound {M(outb)}  processing {M(proc)}  set-up {M(cap)}")
print(f"  YEAR 1 {M(Y1)}   YEAR 2+ {M(Y2)}   reference today {M(ASIS)}  ({Y1/ASIS-1:+.1%} / {Y2/ASIS-1:+.1%})")
print('\nCOSTING NOTE (slide 15)')
print(f"  Part 2 rank of the Part 1 pick: {[v[1] for v in p2rank].index('+'.join(BEST['S']))+1} of 31; "
      f"single GA30113: rank {[v[1] for v in p2rank].index('GA30113')+1}, year 1 {M(one[0])}, year 2+ {M(one[0]-CAPEX['GA30113'])}")
