"""Official small-boat asylum grant rates: decision periods and arrival cohorts."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"quarto-preview"
DATA=DEST/"data/uk/small-boats"
GROUPS={"Grant of Protection":"protection_grants","Grant of Other Leave":"other_leave_grants","Refused":"refused",
        "Withdrawn":"withdrawn","Administrative Outcome":"administrative","Awaiting initial decision":"pending"}


def main():
    summary_source=DEST/"data/uk/source.json"
    detail_source=DATA/"nationalities-source.json"
    for path,meta_path in [(DEST/"data/uk/asylum-summary-jun-2026.ods",summary_source),(DATA/"nationalities-jun-2026.xlsx",detail_source)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=json.loads(meta_path.read_text())["sha256"]:
            raise ValueError("Official source hash changed.")
    raw=pd.read_excel(DEST/"data/uk/asylum-summary-jun-2026.ods",sheet_name="Asy_02d",header=None,engine="odf")
    header=next(i for i,row in raw.iterrows() if row.iloc[0]=="Nationality")
    table=raw.iloc[header+1:].copy();table.columns=raw.iloc[header]
    latest=[]
    for _,row in table.iterrows():
        if pd.isna(row["Nationality"]):continue
        record={"nationality":row["Nationality"]}
        for key,year in [("previous",2025),("current",2026)]:
            record[key+"_rate"]=float(row[f"Grant rate - year ending June {year} (cases)"])
            record[key+"_decisions_main"]=int(row[f"Initial decisions - year ending June {year} (cases)"])
            record[key+"_decisions_people"]=int(row[f"Initial decisions - year ending June {year} (people)"])
        record["change_pp"]=(record["current_rate"]-record["previous_rate"])*100
        latest.append(record)
    if len(latest)!=11 or any(not 0<=row[key]<=1 for row in latest for key in ["current_rate","previous_rate"]):
        raise ValueError("Expected ten published nationalities and the all-nationalities row.")
    raw_counts=pd.read_excel(DEST/"data/uk/asylum-summary-jun-2026.ods",sheet_name="Asy_02c",header=None,engine="odf")
    h=next(i for i,row in raw_counts.iterrows() if row.iloc[0]=="Outcome")
    rows=raw_counts.iloc[h+1:].set_index(0)
    all_row=next(row for row in latest if row["nationality"]=="All nationalities")
    for key,year in [("previous",2025),("current",2026)]:
        column=next(i for i,value in raw_counts.iloc[h].items() if str(value)==f"Year ending June {year} (cases)")
        grant=int(rows.loc["Grants",column]);refused=int(rows.loc["Refused",column])
        if grant+refused!=all_row[key+"_decisions_main"] or not np.isclose(grant/(grant+refused),all_row[key+"_rate"],rtol=0,atol=1e-12):
            raise ValueError("Published overall rates differ from official main-applicant grant/refusal counts.")
    detailed=pd.read_excel(DATA/"nationalities-jun-2026.xlsx",sheet_name="Data_IER_D03",header=1)
    main=detailed.loc[detailed["Applicant type"].str.strip().str.casefold().eq("main applicant")].copy()
    if set(main["Asylum Case Outcome Group"])-set(GROUPS):raise ValueError("Unrecognised case outcome group.")
    counts=pd.to_numeric(main.Outcomes,errors="raise")
    if counts.isna().any() or (counts<0).any() or (counts%1!=0).any():raise ValueError("Invalid linked outcome count.")
    if not set(main.Year).issubset(set(range(2018,2026))):raise ValueError("Review arrival-cohort dates before using a new edition.")
    cohorts=[];exports=[]
    selections=[("all","All arrival cohorts · 2018–2025",pd.Series(True,index=main.index))]
    selections += [(str(year),f"Arrived in {year}",main.Year.eq(year)) for year in sorted(main.Year.unique(),reverse=True)]
    for key,label,mask in selections:
        selected=main.loc[mask]
        grouped=selected.groupby(["Nationality","Asylum Case Outcome Group"]).Outcomes.sum().unstack(fill_value=0).reindex(columns=list(GROUPS),fill_value=0)
        records=[]
        for nationality,row in grouped.iterrows():
            record={"nationality":nationality,**{target:int(row[source]) for source,target in GROUPS.items()}}
            record["grants"]=record["protection_grants"]+record["other_leave_grants"]
            record["decided"]=record["grants"]+record["refused"]
            record["total_statuses"]=sum(record[target] for target in GROUPS.values())
            record["grant_rate"]=record["grants"]/record["decided"] if record["decided"] else None
            record["pending_share"]=record["pending"]/record["total_statuses"] if record["total_statuses"] else None
            records.append(record);exports.append({"arrival_cohort":key,**record})
        records.sort(key=lambda row:(-row["decided"],row["nationality"]))
        total={target:sum(row[target] for row in records) for target in GROUPS.values()}
        total["grants"]=total["protection_grants"]+total["other_leave_grants"]
        total["decided"]=total["grants"]+total["refused"]
        total["grant_rate"]=total["grants"]/total["decided"] if total["decided"] else None
        total["total_statuses"]=sum(total[target] for target in GROUPS.values())
        if total["total_statuses"]!=int(selected.Outcomes.sum()):raise ValueError("Linked outcomes were lost or duplicated.")
        cohorts.append({"id":key,"label":label,"summary":total,"rows":records})
    result={"metadata":{"summary_source":json.loads(summary_source.read_text()),"linked_source":json.loads(detail_source.read_text()),
                        "latest_table":"Asy_02d","cohort_table":"Data_IER_D03","main_applicants_only":True,
                        "recent_cohort_outcomes_through":"2026-07-15","older_cohorts_not_revised_in_release":True},"latest":latest,"cohorts":cohorts}
    (DATA/"grant-rates.json").write_text(json.dumps(result,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")
    pd.DataFrame(latest).to_csv(DATA/"published-nationality-grant-rates.csv",index=False)
    pd.DataFrame(exports).to_csv(DATA/"arrival-cohort-grant-rates.csv",index=False)
    print(f"Parsed 10 published nationality comparisons and {len(cohorts)} linked cohort selections; overall published rate {all_row['current_rate']:.0%} reconciles to main-applicant counts.")


if __name__=="__main__":main()
