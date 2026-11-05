"""Recorded nationalities of small-boat arrivals from official IER_D01 data."""
import hashlib
import json
from pathlib import Path
import folium
from branca.element import Element, MacroElement, Template
import pandas as pd
import pycountry
from prepare_application_maps import centre

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"quarto-preview"
DATA=DEST/"data/uk/small-boats"
ALIASES={"Congo (Democratic Republic)":"COD","Ivory Coast":"CIV","Gambia, The":"GMB","Myanmar (Burma)":"MMR",
         "Russia":"RUS","Turkey":"TUR","Tanzania":"TZA","Syria":"SYR","Iran":"IRN","Vietnam":"VNM","St Lucia":"LCA","Palestine":"PSE","Kosovo":"XKX"}
NON_GEOGRAPHIC={"British overseas citizens","Not currently recorded","Other and unknown","Refugee","Stateless","Cyprus (Northern part of)"}


def main():
    source=DATA/"nationalities-jun-2026.xlsx"
    provenance=json.loads((DATA/"nationalities-source.json").read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest()!=provenance["sha256"]:
        raise ValueError("Nationality workbook changed from the saved official source.")
    frame=pd.read_excel(source,sheet_name="Data_IER_D01",header=1)
    required={"Year","Quarter","Method of entry","Nationality","Sex","Age Group","Number of detections"}
    if not required.issubset(frame):raise ValueError("Official nationality schema changed.")
    frame=frame.loc[frame["Method of entry"].eq("Small boat arrivals")].copy()
    if frame.duplicated(["Quarter","Nationality","Sex","Age Group"]).any():raise ValueError("Duplicate demographic source rows.")
    counts=pd.to_numeric(frame["Number of detections"],errors="raise")
    if counts.isna().any() or (counts<0).any() or (counts%1!=0).any():raise ValueError("Non-integer or missing arrival counts.")
    frame["Number of detections"]=counts
    frame["period"]=pd.PeriodIndex(frame.Quarter.str.replace(" ",""),freq="Q")
    start,end=frame.period.min(),frame.period.max()
    if str(end)!="2026Q2":raise ValueError("Review period labels before using a different official edition.")
    geography=json.loads((ROOT/"world-countries.json").read_text(encoding="utf-8"))
    features={f["id"]:f for f in geography["features"]}
    by_name={f["properties"]["name"]:f for f in geography["features"]}
    wb=json.loads((DEST/"data/population/countries.json").read_text(encoding="utf-8"))[1]
    capitals={c["id"]:[float(c["latitude"]),float(c["longitude"])] for c in wb if c.get("latitude") and c.get("longitude") and c["region"]["id"]!="NA"}
    locations={}
    for label in sorted(frame.Nationality.unique()):
        code=None
        if label not in NON_GEOGRAPHIC:
            code=ALIASES.get(label)
            if not code:
                try:code=pycountry.countries.lookup(label).alpha_3
                except LookupError:pass
        shape=(features.get(code) or by_name.get(label)) if code else None
        if label=="Kosovo" and not shape:shape=by_name.get("Kosovo")
        point=centre(shape["geometry"]) if shape else capitals.get(code)
        locations[label]={"iso":code,"location":point}
    selections=[("latest12","Year ending June 2026 · July 2025–June 2026",frame.period.between(end-3,end))]
    for year in sorted(frame.Year.unique(),reverse=True):
        label=f"{year} · January–June only" if year==2026 else f"{year} · full calendar year"
        selections.append((str(year),label,frame.Year.eq(year)))
    selections.append(("all","All available · January 2018–June 2026",pd.Series(True,index=frame.index)))
    periods=[];exports=[]
    for key,label,mask in selections:
        values=frame.loc[mask].groupby("Nationality")["Number of detections"].sum().sort_values(ascending=False,kind="stable")
        total=int(values.sum())
        rows=[]
        for nationality,count in values.items():
            if count<=0:continue
            point=locations[nationality]
            row={"nationality":nationality,"arrivals":int(count),"share":float(count)/total,"iso":point["iso"],"location":point["location"],"mapped":point["location"] is not None}
            rows.append(row);exports.append({"period":key,"period_label":label,**{k:v for k,v in row.items() if k!="location"}})
        if sum(row["arrivals"] for row in rows)!=total:raise ValueError("Nationality counts must conserve all arrivals.")
        periods.append({"id":key,"label":label,"total":total,"mapped_arrivals":sum(row["arrivals"] for row in rows if row["mapped"]),"rows":rows})
    payload={"metadata":{"source":provenance,"table":"Data_IER_D01","method_filter":"Small boat arrivals","data_through":"2026-06-30","nationality_not_departure_country":True},"periods":periods,"default_period":"latest12"}
    (DATA/"nationality-map.json").write_text(json.dumps(payload,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")
    pd.DataFrame(exports).to_csv(DATA/"nationality-map.csv",index=False)
    m=folium.Map(location=[25,20],zoom_start=2,min_zoom=1,max_zoom=7,tiles=None,prefer_canvas=True,control_scale=True)
    m.default_js=[("leaflet","../assets/vendor/maps/leaflet.js")]
    m.default_css=[("leaflet_css","../assets/vendor/maps/leaflet.css")]
    m.get_root().header.add_child(Element('<style>.leaflet-container.leaflet-container{background:#eaf0f2}.leaflet-tooltip{font:13px/1.6 Arial;color:#20383b}</style>'))
    folium.GeoJson(geography,style_function=lambda f:{"fillColor":"#f6f7f2","color":"#ccd7d0","weight":.6,"fillOpacity":1},smooth_factor=.5).add_to(m)
    maximum=max(row["arrivals"] for period in periods for row in period["rows"])
    encoded=json.dumps(payload,separators=(",",":"),allow_nan=False).replace("<","\\u003c")
    script='''(function(){
      const data=PAYLOAD;
      const selected=data.periods.find(p=>p.id===new URLSearchParams(location.search).get('period'))||data.periods.find(p=>p.id===data.default_period);
      window.smallBoatNationalityPeriod=selected;
      for(const row of selected.rows){
        if(!row.mapped)continue;
        const label=document.createElement('div');label.textContent=row.nationality+': '+row.arrivals.toLocaleString('en-GB')+' detected arrivals · '+(row.share<.001?'<0.1%':(row.share*100).toFixed(row.share<.1?1:0)+'%')+' of the selected period';
        L.circleMarker(row.location,{radius:Math.max(3,32*Math.sqrt(row.arrivals/MAXIMUM)),color:'#256f68',weight:1.3,fillColor:'#35a092',fillOpacity:.65}).bindTooltip(label).bindPopup(label.cloneNode(true)).addTo(MAPNAME);
      }
      const legend=L.control({position:'bottomright'});legend.onAdd=function(){
        const node=L.DomUtil.create('div');node.style='background:white;padding:10px 13px;border:1px solid #d8e2da;border-radius:6px;font:12px/1.6 Arial;color:#20383b;max-width:260px';
        node.textContent=selected.label+' · Recorded nationality, not a travel route. Circles scaled by arrivals (minimum 3px for visibility).';return node;};legend.addTo(MAPNAME);
    })();'''.replace("PAYLOAD",encoded).replace("MAXIMUM",str(maximum)).replace("MAPNAME",m.get_name())
    overlay=MacroElement()
    overlay.script=script
    overlay._template=Template("{% macro script(this, kwargs) %}{{ this.script | safe }}{% endmacro %}")
    m.add_child(overlay)
    (DEST/"maps").mkdir(exist_ok=True)
    m.save(DEST/"maps/small-boats-nationalities.html")
    current=periods[0]
    print(f"Prepared {len(periods)} selectable periods; latest 12 months {current['total']:,} arrivals, {current['mapped_arrivals']:,} located; all categories retained.")


if __name__=="__main__":main()
