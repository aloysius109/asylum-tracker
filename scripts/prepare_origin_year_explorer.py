"""Top application/grant origins from the same ZIP snapshots as Country Explorer."""
import hashlib
import json
from pathlib import Path
import zipfile
import pandas as pd
import pycountry

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview"
KEYS = ["Country of asylum (ISO)", "Year", "Country of origin (ISO)"]
OUTCOMES = ["Recognized decisions", "Complementary protection", "Rejected decisions", "Otherwise closed", "Total decisions"]


def main():
    archive = DEST / "data/source-snapshot.zip"
    explorer = json.loads((DEST/"data/explorer.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(archive) as z:
        apps = pd.read_csv(z.open("asylum-applications.csv"))
        decs = pd.read_csv(z.open("asylum-decisions.csv"))
    for frame in [apps,decs]:
        if not frame["Cases / Persons"].isin(["P","C"]).all():
            raise ValueError("Unexpected reporting unit in origin-year source.")
    applications = apps.groupby(KEYS).applied.sum(min_count=1).rename("applications")
    decisions = decs.groupby(KEYS)[OUTCOMES].sum(min_count=1)
    combined = applications.to_frame().join(decisions,how="outer").reset_index()
    fields = {"Recognized decisions":"recognised","Complementary protection":"other_protection","Rejected decisions":"rejected","Otherwise closed":"closed","Total decisions":"decisions"}
    combined = combined.rename(columns=fields)
    groups,origin_codes = {},set()
    for (country,year), frame in combined.groupby(KEYS[:2],sort=True):
        frame = frame.set_index(KEYS[2])
        any_protection = frame.recognised+frame.other_protection
        ranked_apps = frame.applications.dropna().loc[lambda x:x>0].sort_values(ascending=False,kind="stable").head(3).index.tolist()
        ranked_refugee = frame.recognised.dropna().loc[lambda x:x>0].sort_values(ascending=False,kind="stable").head(3).index.tolist()
        ranked_protection = any_protection.dropna().loc[lambda x:x>0].sort_values(ascending=False,kind="stable").head(3).index.tolist()
        records={}
        for origin in sorted(set(ranked_apps+ranked_refugee+ranked_protection)):
            row=frame.loc[origin]
            records[origin]={key:None if pd.isna(row[key]) else int(row[key]) for key in ["applications",*fields.values()]}
            origin_codes.add(origin)
        summary={key:None if frame[key].notna().sum()==0 else int(frame[key].sum()) for key in ["applications",*fields.values()]}
        # Refuse a mismatch with the existing receiving-country explorer.
        expected=[r for r in explorer["rows"] if r["country"]==country and r["year"]==int(year)]
        for key in summary:
            values=[r[key] for r in expected if r[key] is not None]
            if summary[key] != (sum(values) if values else None):
                raise ValueError(f"Origin sums differ from Country Explorer: {country}, {year}, {key}")
        groups.setdefault(country,{})[str(int(year))]={"summary":summary,"applications":ranked_apps,"refugee":ranked_refugee,"protection":ranked_protection,"origins":records}
    overall_applications={}
    overall = apps.groupby([KEYS[0],KEYS[2]]).applied.sum(min_count=1)
    for country, values in overall.groupby(level=0):
        top = values.droplevel(0).loc[lambda x:x>0].sort_values(ascending=False,kind="stable").head(3)
        overall_applications[country]=[{"origin":code,"applications":int(count)} for code,count in top.items()]
        origin_codes.update(top.index)
    origins={}
    for code in sorted(origin_codes):
        country=pycountry.countries.get(alpha_3=code)
        origins[code]={"name":"Unknown origin" if code=="UNK" else country.name if country else code,
                       "alpha2":country.alpha_2.lower() if country else None}
    payload={"metadata":{**explorer["metadata"],"source_zip_sha256":hashlib.sha256(archive.read_bytes()).hexdigest()},"origins":origins,"groups":groups,"overall_applications":overall_applications}
    (DEST/"data/origin-year-explorer.json").write_text(json.dumps(payload,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")
    print(f"Prepared {sum(len(g) for g in groups.values())} country-year groups; all totals reconcile to Country Explorer; {len(origins)} featured origins.")


if __name__ == "__main__":
    main()
