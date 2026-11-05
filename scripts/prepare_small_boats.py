"""Saved Home Office daily small-boat arrivals, with an explicit refresh command."""
import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"quarto-preview"
DATA=DEST/"data/uk/small-boats"
LANDING="https://www.gov.uk/api/content/government/publications/migrants-detected-crossing-the-english-channel-in-small-boats"
DAILY=LANDING+"/migrants-detected-crossing-the-english-channel-in-small-boats-last-7-days"


class Table(HTMLParser):
    def __init__(self):
        super().__init__();self.rows=[];self.row=[];self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=="tr":self.row=[]
        if tag in ["th","td"]:self.cell=""
    def handle_data(self,data):
        if self.cell is not None:self.cell+=data
    def handle_endtag(self,tag):
        if tag in ["th","td"] and self.cell is not None:self.row.append(self.cell.strip());self.cell=None
        if tag=="tr" and self.row:self.rows.append(self.row)


def parse_daily(payload):
    table=Table();table.feed(payload["details"]["body"])
    records=[]
    for row in table.rows:
        try:date=dt.datetime.strptime(row[0],"%d %B %Y").date()
        except ValueError:continue
        counts=[]
        for value in row[1:3]:
            value=value.replace(",","")
            if not value.isdigit():raise ValueError("Daily arrival/boat counts must be non-negative integers.")
            counts.append(int(value))
        records.append({"date":date.isoformat(),"arrivals":counts[0],"boats":counts[1]})
    records=sorted(records,key=lambda row:row["date"])
    dates=[dt.date.fromisoformat(row["date"]) for row in records]
    if len(records)!=7 or len(set(dates))!=7 or (dates[-1]-dates[0]).days!=6:
        raise ValueError("Expected seven consecutive daily observations.")
    return records


def build(landing,daily,ods,downloaded):
    table=pd.read_excel(io.BytesIO(ods),sheet_name="SB_01",engine="odf")
    required=["Date","Migrants arrived","Boats arrived"]
    if not set(required).issubset(table):raise ValueError("Small-boats source schema changed.")
    dates=pd.to_datetime(table.Date,errors="coerce")
    table=table.loc[dates.notna(),required].copy();table.Date=dates.loc[dates.notna()]
    if table.Date.duplicated().any():raise ValueError("Duplicate historical dates.")
    for key in required[1:]:
        table[key]=pd.to_numeric(table[key],errors="raise")
        if table[key].isna().any() or (table[key]<0).any() or (table[key]%1!=0).any():
            raise ValueError("Invalid historical arrival count.")
    latest=parse_daily(daily)
    records={row.Date.date().isoformat():{"date":row.Date.date().isoformat(),"arrivals":int(row["Migrants arrived"]),"boats":int(row["Boats arrived"])} for _,row in table.iterrows()}
    overlaps=sum(row["date"] in records for row in latest)
    # New daily operational figures replace overlapping weekly snapshot dates.
    records.update({row["date"]:row for row in latest})
    records=sorted(records.values(),key=lambda row:row["date"])
    expected=pd.date_range(records[0]["date"],records[-1]["date"],freq="D")
    if len(expected)!=len(records):raise ValueError("Gap between historical and daily snapshots; refresh refused.")
    return {"metadata":{"retrieved_at_utc":downloaded,"landing_api":LANDING,"daily_api":DAILY,
            "landing_updated_at":landing.get("public_updated_at"),"daily_updated_at":daily.get("public_updated_at"),
            "history_through":table.Date.max().date().isoformat(),"data_through":records[-1]["date"],
            "daily_overrides":overlaps,"provisional":True,"time_series_sha256":hashlib.sha256(ods).hexdigest()},
            "latest7":latest,"rows":records}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--refresh",action="store_true");args=parser.parse_args()
    DATA.mkdir(exist_ok=True)
    if args.refresh:
        def get(url):
            response=requests.get(url,timeout=45);response.raise_for_status();return response
        landing=get(LANDING).json();daily=get(DAILY).json()
        attachment=next(a for a in landing["details"]["attachments"] if a.get("url","").endswith(".ods"))
        ods=get(attachment["url"]).content
        downloaded=dt.datetime.now(dt.timezone.utc).isoformat()
    else:
        landing=json.loads((DATA/"landing.json").read_text(encoding="utf-8"));daily=json.loads((DATA/"daily.json").read_text(encoding="utf-8"));ods=(DATA/"time-series.ods").read_bytes()
        attachment=next(a for a in landing["details"]["attachments"] if a.get("url","").endswith(".ods"))
        prior=DATA/"comparison.json"
        downloaded=json.loads(prior.read_text())["metadata"]["retrieved_at_utc"] if prior.exists() else dt.datetime.now(dt.timezone.utc).isoformat()
    payload=build(landing,daily,ods,downloaded)
    payload["metadata"]["time_series_url"]=attachment["url"]
    # Validate everything before replacing the reader-facing snapshot.
    if args.refresh:
        (DATA/"landing.json").write_text(json.dumps(landing,indent=2)+"\n",encoding="utf-8")
        (DATA/"daily.json").write_text(json.dumps(daily,indent=2)+"\n",encoding="utf-8")
        (DATA/"time-series.ods").write_bytes(ods)
    (DATA/"comparison.json").write_text(json.dumps(payload,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")
    pd.DataFrame(payload["rows"]).to_csv(DATA/"daily-arrivals.csv",index=False)
    print(f"Validated {len(payload['rows'])} daily observations through {payload['metadata']['data_through']}; latest seven-day total {sum(row['arrivals'] for row in payload['latest7']):,}.")


if __name__=="__main__":main()
