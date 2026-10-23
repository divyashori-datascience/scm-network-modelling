# Stalmart Inc. – Cross-Dock Network Modelling

HSLU · Data-driven Supply Chain Management and Logistics · Group 2, Topic 3
Case study by Kuehne+Nagel: *Group assignment "Network modelling"*, October 2026

Stalmart Inc., a US technology company, ships every order directly from 2 suppliers to 33 customers in 17 states, almost all as less-than-truckload (LTL). This project develops an adjusted network that routes freight through cross-docks so it can be consolidated into full truckloads (FTL), and calculates what that network costs.

## Scope

Following the adjusted brief, the project covers the **development of the adjusted network**:

| Deliverable | Covered |
| --- | --- |
| Visualisation of the network structure | ✓ |
| Descriptive statistics of the shipment structure | ✓ |
| To-be cost (year 1 and year 2) | ✓ |
| As-is network analysis | Out of scope (today's cost is used once, as a reference) |
| Recommendation (financial and qualitative) | Out of scope |
| Part 3 qualitative questions | Out of scope |

## Results at a glance

| Item | Result |
| --- | --- |
| Cross-docks (Part 1) | 3 of 5 candidates: **NY10006, TX75477, GA30113** |
| Consolidated loads | 4,896 (1,629 inbound, 3,267 outbound), replacing 6,923 single shipments |
| Share of leg-kg by full truck | 43% (57% inbound, 30% outbound) |
| To-be cost, year 1 | **$252.1M** (incl. $26.3M one-off set-up) |
| To-be cost, year 2 onward | **$225.8M** |
| Reference: today's direct network | $268.7M (−6.2% in year 1, −16.0% from year 2) |
| Clustering check | 27 of 33 customers (93% of kg) fall in the same region as in Part 1 |

## Method

**1. Data preparation.** The 2023 shipment data (6,923 shipments, 6.53M kg, 362 shipping days) was complete and consistent, so it needed preparation rather than cleaning; no row was removed or changed.

- Checks: no missing values, unique and continuous shipment IDs, all 33 customers and both suppliers match the distance tables, weights 10–17,450 kg.
- Location keys built from state + ZIP, in the same form as the distance tables (Connecticut ZIP 06492 is stored as `CT6492`).
- 595 rows that repeat another shipment on date, route and weight are kept as genuine repeat orders.
- 73 shipments heavier than one 7,000 kg truck are split across several trucks when costed.
- The unrounded LTL rates from the Excel `Part2_Input` sheet are used; band limits are read as inclusive.
- The scratch sheets `DemandPoints`, `Sheet3` and `Sheet7` hold demand figures that conflict with the shipments and are not used.

**2. Part 1 – greenfield location model.** A fixed-charge facility location model. All 31 combinations of the 5 candidate cross-docks are costed with the `Part1_Input` data: $0.05 per kg per km on both legs, processing cost per kg and one-off set-up cost per dock. Each customer is assigned to its cheapest open dock, and each supplier keeps its 2023 customers. Enumerating every combination gives the exact optimum.

**3. Clustering check.** Weighted k-means (scikit-learn) on customer locations, weighted by annual kg, for 1 to 5 centres. With 3 centres the clusters fall 4 km from NY10006 and 33 km from TX75477, an independent check on the Part 1 choice.

**4. Part 2 – brownfield costing.** A shipment-level simulation of the Part 1 network. On each leg, freight with the same origin, destination and ship date is pooled into one load. Each load takes the cheapest legal mode: FTL at $1 per truck-km once it reaches 5,250 kg (75% of a 7,000 kg truck), otherwise LTL from the `Part2_Input` rate card. Dock processing and set-up costs are added; set-up counts in year 1 only.

**Costing note.** Re-pricing all 31 networks with the Part 2 method ranks a single dock at GA30113 first ($225.0M in year 1, $214.2M after) and the Part 1 pick fourth, because a flat per-kg-km rate cannot value consolidation. This is reported as a methodological finding, not a recommendation.

## Repository structure

```
├── README.md
├── requirements.txt
├── src/
│   └── stalmart_network.py     # full analysis: data checks, Part 1, clustering, Part 2, costing note
├── data/
│   └── README.md               # where to place the case workbook
├── results/
│   └── model_output.txt        # output of the script, every figure used in the presentation
├── figures/
│   ├── network_map.png         # adjusted network on the US map
│   ├── flows_sankey.png        # supplier → cross-dock → customer region flows
│   └── cluster_map.png         # weighted k-means clusters vs candidate docks
└── interactive/
    └── network-model.html      # open in a browser: pick docks and shipping window, see cost and loads
```

## How to run

```bash
pip install -r requirements.txt
# place the case workbook at data/Network_modelling_assignment.xlsx
python src/stalmart_network.py
```

The script prints every figure used in the presentation (about 15 seconds). A different workbook path can be passed as the first argument.

## Assumptions

- Each customer is served by one cross-dock (single sourcing); each supplier keeps the customers it served in 2023.
- Consolidation is same-day on each leg; freight from both suppliers merges at the dock.
- Cross-dock capacity is unlimited, as stated in the case; supplier volumes (4,665 t and 1,864 t) stay within the 5,000 t capacity.
- Volumes and rates are held at 2023 levels in both years.
- Customer map positions are approximate, placed by ZIP code; they are used only for the clustering check and the figures, not for costs.

Sensitivity: with November and December (unusually light) raised to a normal month, year 2 cost is $234.3M; with volume ±20%, year 2 cost ranges from $202.1M to $241.2M.
