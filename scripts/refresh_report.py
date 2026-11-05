"""Download a UNHCR refresh candidate and build a separate, offline review preview.

Never replaces the accepted CSVs, notebook, input lock, report, or published site.
The review preview is not an adopted/rebuilt edition of the authored report.
"""
import argparse
from datetime import datetime, timezone
from html import escape
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from zipfile import ZipFile

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests

try:
    from . import refresh_explorer_data as explorer
except ImportError:
    import refresh_explorer_data as explorer

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "quarto-preview"
KEYS = ["Year", "Country of asylum (ISO)", "Country of origin (ISO)", "Cases / Persons"]
OUTCOMES = ["Recognized decisions", "Complementary protection", "Rejected decisions", "Otherwise closed", "Total decisions"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(old, new, columns):
    """Compare aligned activity cells; missing and reported zero remain different."""
    before = old.groupby(KEYS)[columns].sum(min_count=1)
    after = new.groupby(KEYS)[columns].sum(min_count=1)
    merged = before.merge(after, how="outer", left_index=True, right_index=True, suffixes=("_accepted", "_candidate"))
    changed = pd.Series(False, index=merged.index)
    for column in columns:
        a, b = merged[column+"_accepted"], merged[column+"_candidate"]
        changed |= ~(a.eq(b) | (a.isna() & b.isna()))
    return merged.loc[changed].reset_index()


def validate_origins(frame):
    if not set(KEYS).issubset(frame.columns) or frame[KEYS].isna().any().any():
        raise ValueError("Missing year/country/origin/unit identifiers in refresh candidate")
    if not frame["Country of origin (ISO)"].astype(str).str.fullmatch("[A-Z]{3}").all():
        raise ValueError("Unexpected origin identifiers; review source schema")


def ranking(frame, column, label):
    counts = frame.groupby(column).applied.sum(min_count=1).sort_values(ascending=False,kind="stable")
    names = frame.sort_values("Year").drop_duplicates(column,keep="last").set_index(column)[label]
    result = counts.rename("Applications").reset_index()
    result.insert(1,label,result[column].map(names))
    return result.head(20)


def country_rows(apps, decs):
    applications = apps.groupby(["Country of asylum (ISO)", "Year"]).applied.sum(min_count=1).rename("applications")
    decisions = decs.groupby(["Country of asylum (ISO)", "Year"])[OUTCOMES].sum(min_count=1)
    joined = applications.to_frame().join(decisions, how="outer")
    names = pd.concat([f[["Year", "Country of asylum (ISO)", "Country of asylum"]] for f in [apps,decs]])
    names = names.sort_values("Year").drop_duplicates("Country of asylum (ISO)",keep="last").set_index("Country of asylum (ISO)")["Country of asylum"]
    records = []
    for (country,year), row in joined.iterrows():
        complete = row[OUTCOMES].notna().all() and row[OUTCOMES[:-1]].sum() == row["Total decisions"] and row["Total decisions"] > 0
        denominator = row[OUTCOMES[:3]].sum() if complete else 0
        records.append({"country":country,"name":names.get(country,country),"year":int(year),
                        "applications":None if pd.isna(row.applications) else int(row.applications),
                        "decisions":None if pd.isna(row["Total decisions"]) else int(row["Total decisions"]),
                        "protection_rate":float(row[OUTCOMES[:2]].sum()/denominator) if denominator > 0 else None,
                        "closed_share":float(row["Otherwise closed"]/row["Total decisions"]) if complete else None})
    return records


def stock_snapshot(year_to, offline, accepted):
    if offline:
        return json.loads(accepted.read_text(encoding="utf-8"))
    url = requests.Request("GET", "https://api.unhcr.org/population/v1/population/", params={"yearFrom":2000,"yearTo":year_to,"limit":100}).prepare().url
    response = requests.get(url,timeout=(20,180)); response.raise_for_status()
    body = response.json()
    if int(body.get("maxPages",1)) != 1 or not isinstance(body.get("items"),list):
        raise ValueError("Unexpected population response or pagination")
    years = []
    for row in body["items"]:
        year = int(row["year"]); value = float(row["asylum_seekers"])
        if year < 2000 or year > year_to or not value.is_integer() or value < 0:
            raise ValueError("Invalid pending-stock year or count")
        if any(row.get(key) not in [None,"-"] for key in ["coa_iso","coo_iso"]):
            raise ValueError("Expected worldwide population aggregate, not country rows")
        years.append(year)
    if len(set(years)) != len(years) or not years:
        raise ValueError("Duplicate/empty population years")
    old = json.loads(accepted.read_text(encoding="utf-8"))
    old_years = {int(r['year']) for r in old['response']['items']}
    if not old_years.issubset(set(years)):
        raise ValueError("Pending stock lost previously available years")
    return {"source":"UNHCR population API, worldwide annual aggregate","url":url,
            "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"response":body}


def table(frame):
    return frame.to_html(index=False,escape=True,na_rep="Unavailable",border=0,classes="review-table",float_format=lambda v:f"{v:,.0f}")


def render_review(folder, old_frames, new_frames, old_stock, stock, audit):
    old_apps, old_decs = old_frames; apps, decs = new_frames
    assets = folder / "assets"; assets.mkdir()
    old_a = old_apps.groupby("Year").applied.sum(min_count=1)
    a = apps.groupby("Year").applied.sum(min_count=1)
    d = decs.groupby("Year")["Total decisions"].sum(min_count=1)
    stock_values = {int(r['year']):int(r['asylum_seekers']) for r in stock['response']['items']}
    with plt.rc_context({"font.family":"DejaVu Sans","text.color":"#20383b","font.size":11}):
        fig,axes = plt.subplots(1,2,figsize=(13,4.5),layout="constrained")
        axes[0].plot(a.index,a.values,color="#087f75",label="Candidate applications",lw=2.5)
        axes[0].plot(d.index,d.values,color="#8060a9",label="Candidate decisions",lw=2)
        axes[0].plot(old_a.index,old_a.values,color="#7a8a83",label="Accepted applications",ls="--",lw=1.3)
        axes[0].set_title("Reported applications and decisions",loc="left",pad=15)
        axes[1].plot(list(stock_values),list(stock_values.values()),color="#087f75",lw=2.5)
        axes[1].set_title("Observed asylum-seeker stock · persons",loc="left",pad=15)
        for ax in axes:
            ax.set_ylim(bottom=0); ax.spines[["top","right","left"]].set_visible(False)
            ax.grid(axis="y",color="#dce5df");ax.set_axisbelow(True)
            from matplotlib.ticker import FuncFormatter
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f"{v/1e6:g}m"))
            ax.tick_params(length=0,pad=8)
        axes[0].legend(frameon=False,fontsize=8)
        fig.savefig(assets/"candidate-trends.png",dpi=150,facecolor="white");plt.close(fig)
    yearly = pd.DataFrame({"Accepted applications":old_a,"Candidate applications":a,"Candidate decisions":d})
    yearly["Application revision"] = yearly["Candidate applications"]-yearly["Accepted applications"]
    yearly.index.name = "Year"
    yearly.reset_index().to_csv(folder/"worldwide-comparison.csv",index=False)
    records = country_rows(apps,decs)
    (folder/"country-years.json").write_text(json.dumps(records,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    pd.DataFrame(records).to_csv(folder/"candidate-country-years.csv",index=False)
    origin_totals = ranking(apps,"Country of origin (ISO)","Country of origin")
    receiving_totals = ranking(apps,"Country of asylum (ISO)","Country of asylum")
    baseline = country_rows(old_apps,old_decs)
    rate_changes = pd.DataFrame(baseline).merge(pd.DataFrame(records),on=["country","year"],suffixes=("_accepted","_candidate"))
    rate_changes["Protection rate revision (percentage points)"] = 100*(rate_changes.protection_rate_candidate-rate_changes.protection_rate_accepted)
    rate_changes = rate_changes.loc[rate_changes["Protection rate revision (percentage points)"].notna() & rate_changes["Protection rate revision (percentage points)"].abs().gt(1e-10)]
    rate_changes.to_csv(folder/"protection-rate-revisions.csv",index=False)
    rate_changes = rate_changes.assign(size=rate_changes["Protection rate revision (percentage points)"].abs()).sort_values("size",ascending=False).head(20)
    rate_changes = rate_changes[["name_candidate","year","Protection rate revision (percentage points)"]]
    rate_html = rate_changes.to_html(index=False,escape=True,border=0,float_format=lambda v:f"{v:+.1f}") if len(rate_changes) else "<p>No eligible aggregate protection-rate revisions were detected.</p>"
    year = audit["candidate_common_year"]
    if a.get(year,0) <= 0:
        raise ValueError("Candidate common-year application total must be positive")
    stock_year = max(stock_values)
    style = """body{font:17px/1.7 'Segoe UI',Arial,sans-serif;background:#fbfaf6;color:#20383b;margin:0}main{max-width:1100px;margin:auto;padding:2rem}h1,h2{font-family:Georgia,serif;line-height:1.2}h1{font-size:2.8rem}.notice{padding:1rem;background:#fff1d6;border-left:5px solid #bb8028}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin:2rem 0}.metric{background:#153b40;color:white;padding:1.2rem;border-radius:8px}.value{display:block;font:2.5rem Georgia,serif}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.85rem}td,th{text-align:left;padding:.5rem;border-bottom:1px solid #dce5df}th{white-space:nowrap}img{max-width:100%;height:auto}a{color:#256756}select{font:inherit;max-width:100%;padding:.4rem}#country-details{padding:1rem;border:1px solid #dce5df;margin:1rem 0}.note{font-size:.85rem;color:#526767}svg{max-width:100%;height:auto}h2{margin-top:2.5rem}@media(max-width:700px){main{padding:1rem}.metrics{grid-template-columns:1fr}h1{font-size:2.1rem}}"""
    html = f"""<!doctype html><html lang="en-GB"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>UNHCR refresh review</title><style>{style}</style><main>
<h1>UNHCR refresh review</h1><p class="notice"><strong>Review candidate — not an adopted report edition.</strong> The accepted report and notebook have not been changed. This page recalculates figures from the candidate data; the authored report's charts and commentary still require an edition rebuild before adoption.</p>
<p><strong>{escape(audit['mode'])}</strong> · Prepared {escape(audit['prepared_at_utc'])} · Status: <strong>{escape(audit['status'])}</strong>.</p>
<div class="metrics"><div class="metric"><span class="value">{stock_values[stock_year]/1e6:.1f}m</span>observed asylum-seeker stock · {stock_year}</div><div class="metric"><span class="value">{a[year]/1e6:.1f}m</span>reported applications · {year}</div><div class="metric"><span class="value">{100*d[year]/a[year]:.0f}</span>decisions per 100 applications · {year}</div></div>
<p>Accepted common endpoint: <strong>{audit['accepted_common_year']}</strong>; candidate common endpoint: <strong>{year}</strong>. Requests include years up to the previous calendar year, not current-year provisional releases. A requested year is not a guarantee of complete worldwide returns.</p>
<p>{audit['changed_application_cells']:,} application cells and {audit['changed_decision_cells']:,} decision cells changed at year–receiving country–origin–reporting unit level. Missing records and reported zeros remain distinct. Pending-stock series changed: <strong>{'yes' if audit['pending_changed'] else 'no'}</strong>. Changes in names/metadata are recorded separately from activity revisions through source hashes.</p>
<p>Top 20 membership changes: receiving countries added <strong>{escape(', '.join(audit['receiving_top20_added']) or 'none')}</strong>, removed <strong>{escape(', '.join(audit['receiving_top20_removed']) or 'none')}</strong>; origins added <strong>{escape(', '.join(audit['origin_top20_added']) or 'none')}</strong>, removed <strong>{escape(', '.join(audit['origin_top20_removed']) or 'none')}</strong>. Candidate rankings are listed below.</p>
<img src="assets/candidate-trends.png" alt="Candidate application and decision trends compared with accepted applications, and the candidate worldwide pending stock.">
<h2>What changed by year?</h2><div class="scroll">{table(yearly.reset_index())}</div>
<h2>Explore a receiving country</h2><label for="country">Receiving country </label><select id="country"></select><div id="country-details" aria-live="polite"></div><div id="country-chart"></div><div id="country-table" class="scroll"></div>
<h2>Largest revisions to protection rates</h2><p class="note">Same country and calendar year, accepted versus candidate source. Rates include refugee status and other protection, exclude closures, and require complete, positive, reconciled annual decision totals. New years and ineligible denominators are not treated as zero. Values are percentage-point revisions, not year-on-year changes.</p><div class="scroll">{rate_html}</div>
<h2>Candidate Top 20 receiving countries</h2><p>Ranked by all reported applications over the candidate period, not just the latest year. Rankings can change at an edition refresh.</p><div class="scroll">{table(receiving_totals)}</div>
<h2>Candidate Top 20 origins</h2><div class="scroll">{table(origin_totals)}</div>
<h2>Review and adoption</h2><ol><li>Check new years, coverage, revisions, ranking changes and outcome reconciliation in the audit files.</li><li>Rebuild and review the authored edition against the candidate sources, including the notebook-dependent galleries, fixed year labels, UK comparison alignment and commentary. Do not substitute CSVs beneath existing figures.</li><li>Approve that rebuilt edition explicitly before replacing the accepted report or publishing it.</li></ol>
<p class="note">This command performs the first step and supplies a numerical review preview; it does not automate the notebook-edition migration in the second step. UK/Home Office and World Bank snapshots are outside this UNHCR check and are not claimed to have been refreshed.</p>
<h2>Audit and downloads</h2><ul><li><a href="audit.json">Audit, provenance and coverage checks</a></li><li><a href="application-cell-changes.csv">Application cell revisions</a></li><li><a href="decision-cell-changes.csv">Decision cell revisions</a></li><li><a href="worldwide-comparison.csv">Worldwide comparison</a></li><li><a href="candidate-country-years.csv">All candidate country-year figures</a></li><li><a href="protection-rate-revisions.csv">Protection-rate revisions</a></li><li><a href="sources/source-snapshot.zip">Exact candidate application/decision source snapshot</a></li><li><a href="sources/pending-stock-series.json">Candidate population response and retrieval provenance</a></li></ul>
<p class="note">Applications and decisions combine original persons and cases without conversion, across reported procedures and application types. They are activity counts, not harmonised unique-person counts. Annual decisions concern claims from different application years. Closures count as processing output. Neither flow gaps nor ratios establish an observed backlog, waiting time or staff efficiency. The population stock retains its persons unit.</p>
<script id="review-data" type="application/json">{json.dumps(records,ensure_ascii=False,allow_nan=False).replace('<',chr(92)+'u003c')}</script>
<script>
const rows=JSON.parse(document.querySelector('#review-data').textContent), select=document.querySelector('#country');
const names=new Map(rows.map(r=>[r.country,r.name]));
for(const [code,name] of [...names].sort((a,b)=>a[1].localeCompare(b[1]))) {{const o=document.createElement('option');o.value=code;o.textContent=name+' ('+code+')';select.append(o)}}
select.value=names.has('GBR')?'GBR':[...names.keys()][0];
const num=x=>x==null?'Unavailable':x.toLocaleString('en-GB'), percent=x=>x==null?'Unavailable':(x*100).toFixed(x<.1?1:0)+'%';
function update(){{const observed=rows.filter(r=>r.country===select.value).sort((a,b)=>a.year-b.year), latest=observed.at(-1), byYear=new Map(observed.map(r=>[r.year,r])), selected=Array.from({{length:latest.year-observed[0].year+1}},(_,i)=>byYear.get(observed[0].year+i)||{{year:observed[0].year+i,applications:null,decisions:null,protection_rate:null,closed_share:null}});document.querySelector('#country-details').textContent=latest.name+' · '+latest.year+': '+num(latest.applications)+' applications; '+num(latest.decisions)+' decisions. Substantive protection rate: '+percent(latest.protection_rate)+'. Closure share of all decisions: '+percent(latest.closed_share)+'.';
const table=document.createElement('table'),head=table.createTHead().insertRow();for(const label of ['Year','Applications','Decisions','Protection rate','Closure share']){{const th=document.createElement('th');th.textContent=label;head.append(th)}}const body=table.createTBody();for(const r of [...selected].reverse()){{const tr=body.insertRow();for(const v of [r.year,num(r.applications),num(r.decisions),percent(r.protection_rate),percent(r.closed_share)])tr.insertCell().textContent=v}}document.querySelector('#country-table').replaceChildren(table);
const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 900 260');svg.setAttribute('role','img');svg.setAttribute('aria-label',latest.name+' annual reported applications and recorded decisions; gaps remain missing.');const max=Math.max(1,...selected.flatMap(r=>[r.applications??0,r.decisions??0]));const minY=selected[0].year,span=Math.max(1,latest.year-minY);const x=y=>55+(y-minY)/span*800,y=v=>210-v/max*170;
for(const [field,color,label] of [['applications','#087f75','Applications'],['decisions','#8060a9','Decisions']]){{let path='',active=false;for(const r of selected){{if(r[field]==null){{active=false;continue}}path+=(active?'L':'M')+x(r.year)+','+y(r[field]);active=true}}const p=document.createElementNS(ns,'path');p.setAttribute('d',path);p.setAttribute('fill','none');p.setAttribute('stroke',color);p.setAttribute('stroke-width','3');svg.append(p);const t=document.createElementNS(ns,'text');t.setAttribute('x',field==='applications'?55:230);t.setAttribute('y',20);t.setAttribute('fill',color);t.textContent=label;svg.append(t)}}
for(const [tx,ty,text] of [[55,245,minY],[820,245,latest.year],[5,50,num(max)],[20,215,'0']]){{const t=document.createElementNS(ns,'text');t.setAttribute('x',tx);t.setAttribute('y',ty);t.setAttribute('font-size','13');t.textContent=text;svg.append(t)}}document.querySelector('#country-chart').replaceChildren(svg);
}}select.addEventListener('change',update);update();
</script></main></html>"""
    (folder/"index.html").write_text(html,encoding="utf-8")


def run(offline=False, output=None):
    now = datetime.now(timezone.utc)
    output = Path(output) if output else ROOT/"artifacts/refresh-review"/now.strftime("%Y%m%dT%H%M%S%fZ")
    if output.exists():
        raise ValueError("Use a new output directory; existing refresh runs are never overwritten")
    output.mkdir(parents=True)
    accepted_hashes = {}
    try:
        lock = json.loads((SITE/"_inputs.json").read_text(encoding="utf-8"))
        old_frames = []
        for filename in ["asylum-applications.csv","asylum-decisions.csv"]:
            source = ROOT/filename; accepted_hashes[filename] = sha(source)
            if accepted_hashes[filename] != lock['inputs'][filename]:
                raise ValueError(f"Accepted input fingerprint changed: {filename}")
            frame = pd.read_csv(source); validate_origins(frame); old_frames.append(frame)
        sources = output/"sources";sources.mkdir()
        # Reuse the explorer's schema/count/coverage guards in an isolated destination.
        shutil.copy2(SITE/"data/explorer.json",sources/"explorer.json")
        original = explorer.DEST
        try:
            explorer.DEST = sources
            explorer.refresh(bundled=offline)
        finally:
            explorer.DEST = original
        new_frames = []
        with ZipFile(sources/"source-snapshot.zip") as z:
            for filename in ["asylum-applications.csv","asylum-decisions.csv"]:
                raw = z.read(filename)
                (sources/filename).write_bytes(raw)
                frame = pd.read_csv(BytesIO(raw));validate_origins(frame);new_frames.append(frame)
        accepted_stock = SITE/"data/pending-stock-series.json"
        old_stock = json.loads(accepted_stock.read_text(encoding="utf-8"))
        common = min(int(f.Year.max()) for f in new_frames)
        stock = stock_snapshot(common,offline,accepted_stock)
        (sources/"pending-stock-series.json").write_text(json.dumps(stock,indent=2),encoding="utf-8")
        metadata = json.loads((sources/"explorer.json").read_text(encoding="utf-8"))["metadata"]
        app_changes = compare(old_frames[0],new_frames[0],["applied"])
        dec_changes = compare(old_frames[1],new_frames[1],OUTCOMES)
        app_changes.to_csv(output/"application-cell-changes.csv",index=False)
        dec_changes.to_csv(output/"decision-cell-changes.csv",index=False)
        old_values = {int(r['year']):int(r['asylum_seekers']) for r in old_stock['response']['items']}
        values = {int(r['year']):int(r['asylum_seekers']) for r in stock['response']['items']}
        pending_changed = old_values != values
        old_common = min(int(f.Year.max()) for f in old_frames)
        changed = len(app_changes)>0 or len(dec_changes)>0 or pending_changed
        new_years = sorted((set(new_frames[0].Year) | set(new_frames[1].Year)) - (set(old_frames[0].Year) | set(old_frames[1].Year)))
        ranking_changes = {}
        for kind,column,label in [("receiving","Country of asylum (ISO)","Country of asylum"),("origin","Country of origin (ISO)","Country of origin")]:
            old_codes = set(ranking(old_frames[0],column,label)[column])
            new_codes = set(ranking(new_frames[0],column,label)[column])
            ranking_changes[kind+"_top20_added"] = sorted(new_codes-old_codes)
            ranking_changes[kind+"_top20_removed"] = sorted(old_codes-new_codes)
        audit = {"prepared_at_utc":now.strftime("%d %B %Y at %H:%M UTC"),
                 "mode":"Offline rehearsal using accepted snapshots; no new data downloaded" if offline else "Live UNHCR source check",
                 "status":"NEW YEARS — EDITION MIGRATION REQUIRED" if new_years else "REVISIONS — REVIEW REQUIRED" if changed else "NO ACTIVITY REVISIONS DETECTED",
                 "accepted_common_year":old_common,"candidate_common_year":common,
                 "new_years":[int(y) for y in new_years],
                 "changed_application_cells":len(app_changes),"changed_decision_cells":len(dec_changes),"pending_changed":pending_changed,
                 "accepted_sources":accepted_hashes,"candidate_sources":metadata['sources'],
                 "candidate_pending_sha256":sha(sources/"pending-stock-series.json"),
                 "downloaded_at_utc":metadata['downloaded_at_utc'],"outcome_total_mismatch_rows":metadata['outcome_total_mismatch_rows'],
                 "authored_report_rebuilt":False,"accepted_files_replaced":False,"published":False,
                 "external_sources":"Home Office/UK, World Bank and notebook charts are not refreshed by this review command."}
        audit.update(ranking_changes)
        (output/"audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
        render_review(output,old_frames,new_frames,old_stock,stock,audit)
        for filename, expected in accepted_hashes.items():
            if sha(ROOT/filename) != expected:
                raise ValueError("Accepted source changed during refresh; inspect concurrent changes")
        (output/"READY.txt").write_text("Review preview complete. No accepted files replaced and nothing published. See audit.json.\n",encoding="utf-8")
        print(audit['status'])
        print(f"Review preview: {output.resolve() / 'index.html'}")
        print("This is a source-change preview, not an adopted rebuild of the authored report.")
        return output
    except Exception as exc:
        (output/"FAILED.json").write_text(json.dumps({"error":str(exc),"accepted_files_replaced":False,"published":False},indent=2),encoding="utf-8")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--refresh",action="store_true",help="Download current UNHCR data into a separate review run")
    mode.add_argument("--offline",action="store_true",help="Rehearse with the accepted snapshots; never claim a fresh download")
    parser.add_argument("--output",type=Path,help="New directory for this run; must not already exist")
    args = parser.parse_args()
    try:
        run(offline=args.offline,output=args.output)
    except Exception as exc:
        print(f"Refresh failed: {exc}. Accepted report was not replaced.",file=sys.stderr)
        sys.exit(1)
