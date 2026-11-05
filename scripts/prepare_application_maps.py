"""Interactive Top 20 maps from pinned application counts and bundled boundaries."""
import copy
import hashlib
from html import escape
import json
import math
from pathlib import Path
import folium
import pandas as pd
import pycountry

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview"


def centre(geometry):
    """Area centroid of the largest exterior polygon; a display anchor, not a flow location."""
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    def stats(polygon):
        ring = polygon[0]
        pairs = list(zip(ring,ring[1:]+ring[:1]))
        cross = [a[0]*b[1]-b[0]*a[1] for a,b in pairs]
        area = sum(cross)
        if not area:
            return 0,ring[0][1],ring[0][0]
        x = sum((a[0]+b[0])*c for (a,b),c in zip(pairs,cross))/(3*area)
        y = sum((a[1]+b[1])*c for (a,b),c in zip(pairs,cross))/(3*area)
        return abs(area),y,x
    _,lat,lon = max(map(stats,polygons))
    return [lat,lon]


def percentage(value):
    return f"{value:.1%}" if 0 < value < .1 else f"{value:.0%}"


def main():
    lock = json.loads((DEST / "_inputs.json").read_text(encoding="utf-8"))
    source = ROOT / "asylum-applications.csv"
    if hashlib.sha256(source.read_bytes()).hexdigest() != lock["inputs"][source.name]:
        raise ValueError("Maps require pinned application inputs.")
    apps = pd.read_csv(source)
    world = int(apps.applied.sum())
    geography = json.loads((ROOT/"world-countries.json").read_text(encoding="utf-8"))
    features = {f["id"]:f for f in geography["features"]}
    scales = [apps.groupby(column).applied.sum().nlargest(20) for column in ["Country of asylum (ISO)","Country of origin (ISO)"]]
    maximum = max(float(values.max()) for values in scales)
    folder = DEST/"maps"
    folder.mkdir(exist_ok=True)
    parts = ['''---
title: "Applications on the map"
subtitle: "Where reported asylum applications are received, and where they originate."
toc: false
page-layout: full
---

Two views of the same **2000–2025** application records. Highlighted countries belong to each period-wide Top 20. **Circle area represents application volume**, on the same size scale in both maps. Hover over a country or circle for its rank, exact volume, and share of all recorded applications; click a circle for details. Zoom and pan to explore nearby countries.

These are application events, not unique applicants. Original persons- and case-reported values are combined without conversion. Origins identify reported countries of origin, rather than application submission locations or travel routes. Boundary shapes provide geographic context; historical reporting codes need not match today's boundaries exactly. Circle positions are approximate display anchors, not application office locations.

''']
    rows = []
    for kind, heading, values, colour in zip(["receiving","origin"],["Top 20 receiving countries","Top 20 reported origins"],scales,["#008f80","#8574bd"]):
        total = int(values.sum())
        m = folium.Map(location=[22,10],zoom_start=2,min_zoom=1,max_zoom=7,tiles=None,
                       max_bounds=True,prefer_canvas=True,control_scale=True)
        m.default_js = [("leaflet", "../assets/vendor/maps/leaflet.js"), ("jquery", "../assets/vendor/maps/jquery.min.js")]
        m.default_css = [("leaflet_css", "../assets/vendor/maps/leaflet.css")]
        m.get_root().header.add_child(folium.Element('<style>.leaflet-container.leaflet-container {background:#eaf0f2;} .leaflet-tooltip {font:13px/1.6 Arial;color:#20383b;border-radius:6px;}</style>'))
        folium.GeoJson(geography,name="World boundaries",style_function=lambda f:{"fillColor":"#eef1ec","color":"#c9d4ce","weight":.6,"fillOpacity":1},smooth_factor=.5).add_to(m)
        selected = []
        table = []
        unlocated = []
        for rank,(code,count) in enumerate(values.items(),1):
            country = pycountry.countries.get(alpha_3=code)
            label = "Unknown origin" if code=="UNK" else country.name if country else code
            share = float(count)/world
            row = {"dimension":kind,"rank":rank,"country":code,"name":label,"applications":int(count),"share_percent":share*100,"mapped":code in features}
            rows.append(row)
            table.append(f"| {rank} | {label} ({code}) | {int(count):,} | {percentage(share)} |")
            if code not in features:
                unlocated.append(row)
                continue
            feature = copy.deepcopy(features[code])
            detail = f"{label} ({code}) · #{rank} · {int(count):,} applications · {percentage(share)} of worldwide records"
            feature["properties"]={"Country":label,"Rank":rank,"Applications":f"{int(count):,}","Worldwide share":f"{percentage(share)}"}
            selected.append(feature)
            popup = f"<strong>{escape(label)} ({code})</strong><br>Rank {rank}<br>{int(count):,} reported applications<br>{percentage(share)} of all recorded applications<br>2000–2025"
            folium.CircleMarker(centre(feature["geometry"]),radius=34*math.sqrt(float(count)/maximum),
                                color=colour,fill=True,fill_color=colour,fill_opacity=.55,weight=1.5,
                                tooltip=detail,popup=folium.Popup(popup,max_width=280)).add_to(m)
        folium.GeoJson({"type":"FeatureCollection","features":selected},name=heading,
                       style_function=lambda f,c=colour:{"fillColor":c,"color":c,"weight":1,"fillOpacity":.13},
                       highlight_function=lambda f:{"weight":2.5,"fillOpacity":.3},
                       tooltip=folium.GeoJsonTooltip(fields=["Country","Rank","Applications","Worldwide share"],sticky=False),
                       smooth_factor=.5).add_to(m)
        m.get_root().html.add_child(folium.Element(f'<div style="position:fixed;bottom:55px;left:12px;z-index:999;background:white;padding:9px 13px;border:1px solid #d8e2da;border-radius:6px;font:12px/1.6 Arial;color:#20383b">{escape(heading)} · 2000–2025<br>Circle area = reported application volume<br>Bundled world boundaries · UNHCR application records</div>'))
        m.save(folder/f"{kind}.html")
        note = ""
        if unlocated:
            note = "\n\n**Not plotted:** "+"; ".join(f"{x['name']}: **{x['applications']:,} applications** ({x['share_percent']:.1f}% of worldwide records)" for x in unlocated)+". It remains part of the Top 20 total; no substitute country is added."
        parts.append(f'''## {heading} {{#{kind}-map}}

**{total/1e6:.1f} million applications · {total/world:.0%} of all recorded applications worldwide.**

<iframe class="application-map" src="maps/{kind}.html" title="Interactive map of {heading.lower()}, 2000 to 2025" loading="lazy"></iframe>

[Open map full-screen](maps/{kind}.html)
{note}

::: {{.callout-note collapse="true" title="Exact country totals and map accessibility alternative"}}

| Rank | Country | Applications | Worldwide share |
|---:|---|---:|---:|
'''+"\n".join(table)+"\n\n:::\n")
    parts.append('''[Download both Top 20 rankings and exact shares (CSV)](data/application-map-totals.csv) · [Origins & destinations](origins.qmd) · [Country Explorer](explore.qmd)

The maps use the bundled world-countries.json boundary file and the fixed application snapshot, rather than live map tiles. Leaflet and jQuery are bundled locally, so viewing these maps needs no external library or map-tile requests. Exact country tables provide a text alternative.
''')
    (DEST/"maps.qmd").write_text("\n".join(parts),encoding="utf-8")
    pd.DataFrame(rows).to_csv(DEST/"data/application-map-totals.csv",index=False)
    assert len(rows)==40 and sum(row["mapped"] for row in rows)==39
    print("Prepared two maps: 20 receiving countries and 19 located origins; Unknown origin remains in the ranking.")


if __name__ == "__main__":
    main()
