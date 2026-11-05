"""Reproducible descriptive commentary from the report's saved sources; no causal claims."""
import hashlib
import json
import re
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "quarto-preview"
FIELDS = ["Recognized decisions", "Complementary protection", "Rejected decisions", "Otherwise closed"]
TOTAL = "Total decisions"
DEST = "Country of asylum (ISO)"
ORIGIN = "Country of origin (ISO)"
EVIDENCE = {}


def number(x):
    return f"{x:,.0f}"


def pct(x):
    return "<0.1%" if 0 < abs(x) < .001 else f"{x*100:.1f}%" if abs(x) < .1 else f"{x*100:,.0f}%"


def change(series, year=2025, baseline=2019):
    if year not in series or baseline not in series or pd.isna(series[year]) or pd.isna(series[baseline]) or series[baseline] <= 0:
        return f"A comparable {baseline}-to-{year} application change is unavailable."
    value = series[year] / series[baseline] - 1
    return f"Applications in {year} were {pct(abs(value))} {'higher' if value >= 0 else 'lower'} than in {baseline} ({number(series[baseline])})."


def rate(row):
    if row[FIELDS + [TOTAL]].isna().any() or (row[FIELDS] < 0).any() or row[TOTAL] <= 0 or row[FIELDS].sum() != row[TOTAL]:
        return None
    substantive = row[FIELDS[:3]].sum()
    if substantive <= 0:
        return None
    return {"protection": float(row[FIELDS[:2]].sum() / substantive), "refugee": float(row[FIELDS[0]] / substantive), "closed": float(row[FIELDS[3]] / row[TOTAL]), "substantive": int(substantive)}


def rates_text(decs):
    annual = decs.groupby("Year")[FIELDS + [TOTAL]].sum(min_count=1)
    valid = {int(y): r for y, row in annual.iterrows() if (r := rate(row)) is not None}
    if not valid:
        return "No complete, reconciled annual decision total supports a protection-rate comparison."
    year = max(valid)
    r = valid[year]
    text = f"In {year}, the substantive protection rate was {pct(r['protection'])}, across {number(r['substantive'])} grants and refusals; closures accounted for {pct(r['closed'])} of all recorded decisions."
    earlier = next((y for y in [year-1, year-5] if y in valid), None)
    if earlier is not None:
        diff = (r['protection'] - valid[earlier]['protection']) * 100
        text += f" That protection rate was {abs(diff):.1f} percentage points {'higher' if diff >= 0 else 'lower'} than in {earlier} ({pct(valid[earlier]['protection'])})."
    if year < 2025:
        text += f" No eligible 2025 rate is available; {year} is the latest reconciled year."
    return text


def put(name, text):
    (SITE / name).write_text(text + "\n", encoding="utf-8")


def include_once(page, include, anchor):
    path = SITE / page
    text = path.read_text(encoding="utf-8")
    directive = "{{< include " + include + " >}}"
    if directive not in text:
        if anchor not in text:
            raise ValueError(f"Commentary anchor missing: {page}: {anchor}")
        text = text.replace(anchor, directive + "\n\n" + anchor, 1)
        path.write_text(text, encoding="utf-8")


def main():
    lock = json.loads((SITE / "_inputs.json").read_text(encoding="utf-8"))
    frames = []
    for name in ["asylum-applications.csv", "asylum-decisions.csv"]:
        path = ROOT / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != lock["inputs"][name]:
            raise ValueError(f"Changed commentary source: {name}")
        frames.append(pd.read_csv(path))
    apps, decs = frames
    ranking = pd.read_csv(SITE / "data/processing-productivity.csv").drop_duplicates("country")
    origins = pd.read_csv(SITE / "assets/origins/application-volumes.csv")
    names = apps.drop_duplicates(DEST).set_index(DEST)["Country of asylum"].to_dict()
    names.update(dict(zip(ranking.country, ranking.name)))
    for _, item in ranking.iterrows():
        code, name = item.country, item['name']
        a = apps.loc[apps[DEST].eq(code)]
        d = decs.loc[decs[DEST].eq(code)]
        annual = a.groupby("Year").applied.sum(min_count=1)
        decisions = d.groupby("Year")[TOTAL].sum(min_count=1)
        latest = int(annual.index.max())
        peak = int(annual.idxmax())
        peak_note = f"The latest year, {latest}, was the recorded peak, with {number(annual[latest])} applications." if peak == latest else f"The largest annual volume was {number(annual[peak])} in {peak}; {latest} recorded {number(annual[latest])}."
        text = f"**{name}: scale and change.** Across 2000–2025, the extract records {number(annual.sum())} applications. {peak_note} {change(annual, latest)}"
        if latest in decisions and pd.notna(decisions[latest]) and annual[latest] > 0:
            ratio = decisions[latest] / annual[latest] * 100
            text += f" In {latest}, {number(decisions[latest])} recorded decisions equated to {ratio:.0f} per 100 applications, so recorded output {'exceeded' if ratio >= 100 else 'fell below'} incoming volume."
        text += " " + change(annual, latest, latest-1)
        recent_years = annual.index.intersection(decisions.index)
        recent_years = recent_years[recent_years >= 2021]
        comparable = [y for y in recent_years if pd.notna(annual[y]) and pd.notna(decisions[y])]
        if comparable:
            shortfalls = sum(annual[y] > decisions[y] for y in comparable)
            text += f" Applications exceeded recorded decisions in {shortfalls} of {len(comparable)} comparable years during 2021-2025."
        top = a.loc[a.Year.eq(latest)].groupby("Country of origin").applied.sum(min_count=1).nlargest(3)
        text += " The leading recorded origins that year were " + ", ".join(f"{n.strip()} ({number(v)})" for n,v in top.items()) + "."
        text += "\n\n" + rates_text(d)
        put(f"_commentary-receiving-{code.lower()}.qmd", text)
        EVIDENCE[code] = {"applications_by_year": {str(k): int(v) for k,v in annual.items()}, "decisions_by_year": {str(k): None if pd.isna(v) else int(v) for k,v in decisions.items()}}
    for _, item in origins.iterrows():
        code, name = item.origin, item['name']
        frame = apps.loc[apps[ORIGIN].eq(code)]
        annual = frame.groupby("Year").applied.sum(min_count=1)
        year = int(annual.index.max()); peak = int(annual.idxmax())
        peak_note = f"The latest year, {year}, was the recorded peak, with {number(annual[year])} applications." if peak == year else f"Annual volume peaked at {number(annual[peak])} in {peak}, compared with {number(annual[year])} in {year}."
        text = f"**{name}: how applications changed.** The extract records {number(annual.sum())} applications during 2000–2025. {peak_note} {change(annual, year)}"
        text += " " + change(annual, year, year-1)
        destinations = frame.loc[frame.Year.eq(year)].groupby(DEST).applied.sum(min_count=1).sort_values(ascending=False)
        top = destinations.head(3)
        text += f" In {year}, the leading destinations were " + ", ".join(f"{names.get(c,c)} ({number(v)}; {pct(v/annual[year])})" for c,v in top.items()) + "."
        before = frame.loc[frame.Year.eq(2019)].groupby(DEST).applied.sum(min_count=1)
        if len(top) and before.sum() > 0 and top.index[0] in before:
            lead = top.index[0]
            text += f" {names.get(lead,lead)} received {pct(top.iloc[0]/annual[year])} of this origin's applications in {year}, versus {pct(before[lead]/before.sum())} in 2019: a change in destination distribution, not evidence that the same people moved between asylum systems."
        origin_rates = rates_text(decs.loc[decs[ORIGIN].eq(code)])
        text += "\n\nAcross receiving countries, " + origin_rates[0].lower() + origin_rates[1:]
        if code == "UNK":
            text += " Unknown origin is a reporting category, not a nationality; its trend can reflect changes in recording as well as activity."
        put(f"_commentary-origin-{code.lower()}.qmd", text)
        EVIDENCE['origin-'+code] = {str(k): int(v) for k,v in annual.items()}
    # Attach compact profiles directly to each existing gallery card, idempotently.
    for page, pattern, kind in [("_receiving-gallery.qmd", r"(\[Open full-size chart\]\(assets/receiving/([a-z]+)\.png\))", "receiving"), ("productivity.qmd", r"(\[Open full-size chart\]\(assets/productivity/([a-z]+)\.png\))", "receiving"), ("origins.qmd", r"(\[Open full-size chart\]\(assets/origins/([a-z]+)\.png\?v=contrast2\))", "origin")]:
        path = SITE / page; text = path.read_text(encoding="utf-8")
        def insert(match):
            directive = "{{< include _commentary-" + kind + "-" + match[2] + ".qmd >}}"
            return match[0] if directive in text else directive + "\n\n" + match[0]
        path.write_text(re.sub(pattern, insert, text), encoding="utf-8")
    worldwide = apps.groupby("Year").applied.sum(min_count=1)
    world_decs = decs.groupby("Year")[TOTAL].sum(min_count=1)
    peak = int(worldwide.idxmax())
    recent = change(worldwide)
    y2024 = change(worldwide, 2025, 2024)
    stock = json.loads((SITE / "data/pending-stock-series.json").read_text(encoding="utf-8"))
    stock_years = {int(r["year"]): int(r["asylum_seekers"]) for r in stock["response"]["items"]}
    put("_commentary-worldwide.qmd", f"""## The worldwide pattern: growth, peaks and processing pressure {{#worldwide-commentary}}

Reported applications rose from **{number(worldwide[2019])} in 2019 to {number(worldwide[2025])} in 2025**. {recent} The recent expansion was not a continuous rise: the series peaked at **{number(worldwide[peak])} in {peak}**. {y2024} This distinction matters: a high level of demand and a growing unresolved caseload can coexist with a fall in new applications.

In 2025, **{number(world_decs[2025])} decisions** were recorded against **{number(worldwide[2025])} applications**: {world_decs[2025]/worldwide[2025]*100:.0f} decisions per 100 applications. Applications exceeded decisions in **{int((worldwide > world_decs).sum())} of the 26 years**. Persistent shortfalls indicate processing pressure, although the difference is not an observed backlog. The separate end-year stock series is the appropriate evidence for unresolved claims; see [what remains unresolved](#pending).

**The stock of unresolved claims has also expanded.** The separately reported end-year asylum-seeker population rose from **{number(stock_years[2019])} in 2019 to {number(stock_years[2025])} in 2025** ({pct(stock_years[2025]/stock_years[2019]-1)} higher), including a {pct(abs(stock_years[2025]/stock_years[2024]-1))} {"rise" if stock_years[2025]>=stock_years[2024] else "fall"} from 2024. Unlike the mixed-unit application totals, this stock is reported in persons. It is not obtained by summing annual flow gaps.

**Read the changes as reported activity.** The series combines persons and cases, application types and procedures, and changing source coverage. It counts application events rather than unique people. Growth in these totals cannot on its own identify the causes of migration, demonstrate onward movement, or establish that future pressure must increase.
""")
    # Use the same refreshed ZIP source and strict annual eligibility as the Grant Rates page.
    archive = SITE / "data/source-snapshot.zip"
    with zipfile.ZipFile(archive) as z:
        fresh = pd.read_csv(z.open("asylum-decisions.csv"))
    annual = fresh.groupby([DEST,"Year"])[FIELDS+[TOTAL]].sum(min_count=1)
    comparisons = []; grant_profiles = []
    for _, item in ranking.iterrows():
        code = item.country; subset = fresh.loc[fresh[DEST].eq(code)]
        grant_profiles.append(f'::: {{.callout-note collapse="true" title="{item["name"]}: grant-rate commentary"}}\n{rates_text(subset)}\n:::')
        if (code,2024) in annual.index and (code,2025) in annual.index:
            prev, now = rate(annual.loc[(code,2024)]), rate(annual.loc[(code,2025)])
            if prev and now and min(prev['substantive'],now['substantive']) >= 500:
                comparisons.append((abs(now['protection']-prev['protection']),item['name'],prev,now))
    comparisons.sort(reverse=True)
    changed = "\n\n".join(f"- **{name}:** protection rate {pct(prev['protection'])} in 2024 → {pct(now['protection'])} in 2025 ({(now['protection']-prev['protection'])*100:+.1f} percentage points); substantive decisions {number(prev['substantive'])} → {number(now['substantive'])}." for _,name,prev,now in comparisons[:5])
    # Same-origin cross-country contrasts, restricted to material eligible denominators.
    origin_contrasts = []
    detailed = fresh.loc[fresh.Year.eq(2025) & fresh[DEST].isin(ranking.country)].groupby([ORIGIN,DEST])[FIELDS+[TOTAL]].sum(min_count=1)
    for code in origins.origin.head(8):
        if code not in detailed.index.get_level_values(0) or code == 'UNK': continue
        candidates = [(country,r) for country,row in detailed.loc[code].iterrows() if (r := rate(row)) and r['substantive'] >= 500]
        if len(candidates) < 2: continue
        low = min(candidates,key=lambda x:x[1]['protection']); high = max(candidates,key=lambda x:x[1]['protection'])
        origin_name = origins.loc[origins.origin.eq(code),'name'].iloc[0]
        origin_contrasts.append(f"- **{origin_name}, 2025:** among {len(candidates)} eligible Top 20 destinations, the protection rate ranged from {pct(low[1]['protection'])} in {names.get(low[0],low[0])} ({number(low[1]['substantive'])} substantive decisions) to {pct(high[1]['protection'])} in {names.get(high[0],high[0])} ({number(high[1]['substantive'])}).")
    put("_commentary-grants.qmd", """## How protection rates differ and change {#grant-commentary}

**An overall rate mixes policy, procedure and the claims being decided.** A change can arise because the nationalities or types of claims changed, because older claims were decided, or because decision practices changed. The descriptive comparisons below establish differences, not their causes. Closures are excluded from substantive rates and shown separately on this page.

### Largest recent changes in the Top 20

These are the five largest absolute 2024–2025 changes among the fixed Top 20 receiving countries with complete, reconciled annual totals and at least 500 substantive decisions in **both** years. Selection by change is descriptive; it is not a statistical significance test. Missing or unreconciled years are excluded.

""" + changed + "\n\n### Comparing the same recorded origin\n\nThese examples cover known origins among the eight largest recorded origins by period application volume, where at least two destinations meet the denominator rule. The comparisons hold recorded origin and calendar year constant. They show the lowest and highest protection rates among eligible Top 20 destinations, requiring at least 500 substantive decisions in each country–origin cell. They still do not hold individual circumstances, procedure, reporting unit or claim vintage constant.\n\n" + "\n".join(origin_contrasts) + "\n\n### Reading each receiving country's change\n\nThe following profiles use the same refreshed decision snapshot and annual reconciliation rules as the interactive charts. Each compares its latest eligible year with the preceding year where available, otherwise five years earlier. A latest eligible year before 2025 is identified explicitly.\n\n" + "\n\n".join(grant_profiles) + "\n\n[Source definitions and eligibility](methods.qmd#decision-rates). Rates are weighted by decision counts, not averaged across years.\n")
    # UK official calendar-year comparison; keep scopes explicit.
    uk = pd.read_csv(SITE / "data/uk/annual-comparison.csv").set_index("year")
    now, earlier = uk.loc[2025], uk.loc[2019]
    rw = apps.loc[apps[DEST].eq("RWA")].groupby("Year").applied.sum(min_count=1)
    rd = decs.loc[decs[DEST].eq("RWA")].groupby("Year")[FIELDS+[TOTAL]].sum(min_count=1)
    rw_rate = rate(rd.loc[2025])
    peer_rates = []
    for code in ["GBR", "DEU", "FRA"]:
        row = decs.loc[decs[DEST].eq(code) & decs.Year.eq(2025), FIELDS + [TOTAL]].sum(min_count=1)
        r = rate(row)
        if r: peer_rates.append(f"{names[code]} ({pct(r['protection'])}; {number(r['substantive'])} substantive decisions)")
    uk_all_apps = apps.loc[apps[DEST].eq("GBR") & apps.Year.eq(2025)].applied.sum()
    uk_all_dec = decs.loc[decs[DEST].eq("GBR") & decs.Year.eq(2025),TOTAL].sum()
    peers=[]
    for c in ['DEU','FRA','CAN']:
        ca=apps.loc[apps[DEST].eq(c)&apps.Year.eq(2025)].applied.sum(min_count=1)
        cd=decs.loc[decs[DEST].eq(c)&decs.Year.eq(2025),TOTAL].sum(min_count=1)
        if ca > 0 and pd.notna(cd): peers.append(f"{names[c]} ({cd/ca*100:.0f})")
    put("_commentary-uk.qmd", f"""## What the UK trends show {{#uk-commentary}}

The Home Office calendar-year series records **{number(now.ho_claimants_people)} people claiming asylum in 2025**, compared with **{number(earlier.ho_claimants_people)} in 2019** ({pct(abs(now.ho_claimants_people/earlier.ho_claimants_people-1))} {'higher' if now.ho_claimants_people >= earlier.ho_claimants_people else 'lower'}). In 2025 it recorded **{number(now.ho_initial_decisions_people)} initial decisions**. Initial decision output exceeded that year's claims, but those decisions include claims lodged earlier; this is not the fraction of 2025 applicants who were processed.

The published main-applicant initial grant rate was **{pct(now.ho_published_grant_rate_main_applicants)} in 2025**, versus **{pct(earlier.ho_published_grant_rate_main_applicants)} in 2019**. This official rate has its own applicant scope: it should not be reconstructed from the all-people grant and decision counts. The separately dated small-boat rates below concern a specific arrival group, rather than everyone claiming asylum in the UK.

**Cross-country context uses the broader UNHCR extract.** On that common reported-activity basis, the UK recorded {number(uk_all_apps)} applications and {number(uk_all_dec)} decisions in 2025, or {uk_all_dec/uk_all_apps*100:.0f} decisions per 100 applications. The corresponding ratios were {', '.join(peers)}. These contrasts show flows relative to demand, not staff efficiency or waiting times. They combine persons and cases and different procedure mixes; the first-instance persons-only comparison below has a deliberately narrower scope.

Source: the saved [Home Office asylum tables](https://www.gov.uk/government/statistical-data-sets/immigration-system-statistics-data-tables) and pinned UNHCR extracts used on this page. Compare calendar years with calendar years; rolling years ending June are labelled separately.
""")
    put("_commentary-rwanda.qmd", f"""### Rwanda in context: a smaller and unevenly reported system

Rwanda recorded **{number(rw[2025])} applications and {number(rd.loc[2025,TOTAL])} decisions in 2025**. Application volume was below the **{number(rw[2023])} recorded in 2023**, rather than following an uninterrupted upward trend. In 2025, decisions amounted to **{rd.loc[2025,TOTAL]/rw[2025]*100:.0f} per 100 applications**, compared with **{uk_all_dec/uk_all_apps*100:.0f} in the UK** on the same broad UNHCR reported-activity basis. A low annual ratio can reflect the timing of decisions or reporting, as well as an imbalance between inflow and output; it is not a measured processing time or an observed backlog.

All **{number(rd.loc[2025,TOTAL])}** recorded Rwanda decisions in 2025 were refugee-status recognitions, yielding a **{pct(rw_rate['protection'])} substantive protection rate** in this extract. For context, the same broad extract records 2025 substantive protection rates of {", ".join(peer_rates)}. These are aggregate contrasts, not a matched-origin comparison. That describes the reported decisions, not every applicant's eventual outcome. The origin cards below help put the rate in context: a different claimant mix from the UK, a smaller decision denominator and different procedures prevent treating the two aggregate rates as equivalent chances of success. Nor does this domestic activity establish how Rwanda would have processed people relocated from the UK under the former partnership.
""")
    EVIDENCE['grant_changes'] = [{"country":name,"2024":prev,"2025":now} for _,name,prev,now in comparisons]
    include_once("worldwide.qmd" if (SITE / "worldwide.qmd").exists() else "index.qmd", "_commentary-worldwide.qmd", "## Is processing output keeping up?")
    include_once("grants.qmd", "_commentary-grants.qmd", "## Find a country")
    include_once("uk.qmd", "_commentary-uk.qmd", "{{< include")
    include_once("_rwanda-context.qmd", "_commentary-rwanda.qmd", "{{< include _rwanda-headlines.qmd >}}")
    EVIDENCE['pending_stock']=stock_years
    EVIDENCE['worldwide']={str(y):int(v) for y,v in worldwide.items()}
    EVIDENCE['sources']={"pinned":lock['inputs'],"grant_zip_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"description":"Mixed-unit reported activity; strict reconciled grant denominators; generated by prepare_commentary.py"}
    (SITE / "data/commentary-evidence.json").write_text(json.dumps(EVIDENCE,ensure_ascii=False,allow_nan=False,indent=2),encoding="utf-8")
    include_once("origins.qmd", "_commentary-profile-guide.qmd", "## Explore another country of origin")
    include_once("explore.qmd", "_commentary-profile-guide.qmd", "{{< include _receiving-gallery.qmd >}}")
    put("_commentary-profile-guide.qmd", "**About the country commentary.** The gallery profiles describe the fixed 2000-2025 UNHCR extract, not a forecast. Changes compare reported application activity with 2019 where available; peaks are the largest recorded annual totals. Grant rates exclude closures and use complete, positive, reconciled decision totals; they concern decisions made, not outcomes for that year\'s arrivals. Procedures, persons/cases mixes and coverage can change. Missing observations remain unavailable rather than being filled with zero. The Grant Rates page separately identifies its refreshed snapshot. [Methods and definitions](methods.qmd).")
    print(f"Prepared {len(ranking)} receiving profiles, {len(origins)} origin profiles, worldwide, grant-rate and UK/Rwanda commentary.")
    print(f"Worldwide annual peak: {peak}; 2025 vs 2019: {worldwide[2025]/worldwide[2019]-1:.3%}; 2025 vs 2024: {worldwide[2025]/worldwide[2024]-1:.3%}")
    print(changed.encode("ascii", errors="replace").decode("ascii"))


if __name__ == "__main__":
    main()
