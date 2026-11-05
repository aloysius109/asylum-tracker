export function overallOrigins(records, origins, metadata) {
  const box=document.createElement("div");box.className="overall-origin-list";
  const heading=document.createElement("p");heading.textContent="Top application origins · "+metadata.year_from+"–"+metadata.year_to_available;box.append(heading);
  for (const record of records) {
    const label=origins[record.origin],row=document.createElement("p");row.title=record.applications.toLocaleString("en-GB")+" reported applications";
    if (label.alpha2) {
      const image=document.createElement("img");image.src="assets/flags/"+label.alpha2+".svg";image.alt="";image.width=22;image.height=16;image.loading="lazy";image.onerror=()=>image.hidden=true;row.append(image);
    }
    row.append(label.name+" ("+record.origin+")");box.append(row);
  }
  return box;
}

export function cards(group, origins, mode, grants) {
  const grid=document.createElement("div"); grid.className="origin-year-grid";
  const number=value=>value==null?"Unavailable":value.toLocaleString("en-GB");
  for (const [key,title] of [["applications","Top 3 origins by applications"],[mode,mode==="refugee"?"Top 3 origins granted refugee status":"Top 3 origins granted any protection"]]) {
    const panel=document.createElement("section");panel.className="origin-year-panel";
    const heading=document.createElement("h4");heading.textContent=title;panel.append(heading);
    const codes=group?.[key] || [];
    if (!codes.length) {const p=document.createElement("p");p.textContent="No positive reported counts are available for this selection.";panel.append(p);}
    for (const [index,code] of codes.entries()) {
      const record=group.origins[code],label=origins[code],rate=grants.rates(record);
      const card=document.createElement("div");card.className="ranked-origin";
      const name=document.createElement("p");name.className="ranked-origin-name";
      const rank=document.createElement("span");rank.className="ranked-origin-position";rank.textContent=String(index+1);
      name.append(rank);
      if (label.alpha2) {
        const flag=document.createElement("img");flag.src="assets/flags/"+label.alpha2+".svg";flag.alt="";flag.width=30;flag.height=21;flag.loading="lazy";
        flag.onerror=()=>flag.hidden=true;name.append(flag);
      }
      name.append(label.name+" ("+code+")");
      const count=document.createElement("p");count.className="ranked-origin-volume";
      const value=key==="applications"?record.applications:mode==="refugee"?record.recognised:record.recognised+record.other_protection;
      count.textContent=number(value)+(key==="applications"?" applications":mode==="refugee"?" refugee-status grants":" protection grants");
      const detail=document.createElement("p");detail.className="ranked-origin-rates";
      detail.textContent="Refugee rate: "+grants.percent(rate.refugee_rate)+" · Total protection rate: "+grants.percent(rate.protection_rate)+" (substantive decisions). Closure share: "+grants.percent(rate.closed_share)+" of all decisions.";
      card.append(name,count,detail);panel.append(card);
    }
    grid.append(panel);
  }
  return grid;
}
