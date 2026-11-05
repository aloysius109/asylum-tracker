"""Match saved World Bank population estimates to exact UNHCR country-years."""
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"quarto-preview"
DATA=DEST/"data/population"


def main():
    provenance=json.loads((DATA/"sources.json").read_text(encoding="utf-8"))
    for source in provenance["sources"]:
        if hashlib.sha256((DATA/source["file"]).read_bytes()).hexdigest()!=source["sha256"]:
            raise ValueError("Population download hash changed.")
    wb_countries=json.loads((DATA/"countries.json").read_text(encoding="utf-8"))[1]
    allowed={country["id"] for country in wb_countries if country["region"]["id"]!="NA"}
    raw=json.loads((DATA/"population.json").read_text(encoding="utf-8"))[1]
    populations={}
    for row in raw:
        code=row["countryiso3code"]
        if code not in allowed:
            continue
        key=(code,int(row["date"]))
        if key in populations:
            raise ValueError("Duplicate country-year population record.")
        value=row["value"]
        populations[key]=int(value) if value is not None and value>0 else None
    explorer=json.loads((DEST/"data/explorer.json").read_text(encoding="utf-8"))
    countries={country["iso"]:country["name"] for country in explorer["countries"]}
    ranks=pd.read_csv(DEST/"data/processing-productivity.csv").country.drop_duplicates().tolist()
    records=[]
    for row in explorer["rows"]:
        pop=populations.get((row["country"],row["year"]))
        records.append({**row,"population":pop,"population_year":row["year"] if pop else None})
    csv=pd.DataFrame(records)
    for key in ["applications","recognised","other_protection","rejected","closed"]:
        csv[key+"_per_100k"]=csv[key]/csv.population.where(csv.population>0)*100000
        csv["residents_per_"+key]=csv.population/csv[key].where(csv[key]>0)
    csv["protection_total"]=csv.recognised+csv.other_protection
    csv["protection_total_per_100k"]=csv.protection_total/csv.population.where(csv.population>0)*100000
    csv["residents_per_protection_total"]=csv.population/csv.protection_total.where(csv.protection_total>0)
    csv.to_csv(DATA/"asylum-population-comparison.csv",index=False)
    matched=[row["year"] for row in records if row["population"] and row["applications"] is not None and row["unit"]=="P"]
    payload={"metadata":{"population_source":provenance,"asylum_source":explorer["metadata"],"default_year":max(matched),"no_population_imputation":True},
             "countries":explorer["countries"],"top20":ranks,"rows":records}
    (DATA/"comparison.json").write_text(json.dumps(payload,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")
    print(f"Matched same-year population for {sum(row['population'] is not None for row in records)} of {len(records)} reporting-unit records; latest shared year {max(matched)}. No cross-year filling.")


if __name__=="__main__":
    main()
