export const endpoint="https://www.gov.uk/api/content/government/publications/migrants-detected-crossing-the-english-channel-in-small-boats/migrants-detected-crossing-the-english-channel-in-small-boats-last-7-days";
const months=["January","February","March","April","May","June","July","August","September","October","November","December"];
export function parse(payload) {
  const doc=new DOMParser().parseFromString(payload.details.body,"text/html"),records=[];
  for (const row of doc.querySelectorAll("tr")) {
    const cells=Array.from(row.querySelectorAll("th,td")).map(cell=>cell.textContent.trim());
    const match=cells[0]?.match(/^(\d{1,2}) ([A-Za-z]+) (\d{4})$/);
    if (!match) continue;
    const month=months.indexOf(match[2]),date=new Date(Date.UTC(Number(match[3]),month,Number(match[1])));
    if (month<0||date.getUTCDate()!==Number(match[1])) throw new Error("Invalid observation date.");
    const values=cells.slice(1,3).map(value=>value.replaceAll(",",""));
    if (values.length!==2||!values.every(value=>/^\d+$/.test(value))) throw new Error("Daily counts unavailable or schema changed.");
    records.push({date:date.toISOString().slice(0,10),arrivals:Number(values[0]),boats:Number(values[1])});
  }
  records.sort((a,b)=>a.date.localeCompare(b.date));
  if (records.length!==7||new Set(records.map(d=>d.date)).size!==7||Date.parse(records[6].date)-Date.parse(records[0].date)!==6*86400000) throw new Error("Expected seven consecutive daily records.");
  return records;
}
const format=date=>new Date(date).toLocaleDateString("en-GB",{day:"numeric",month:"long",year:"numeric",timeZone:"UTC"});
export function mount(container,snapshot,Plot,width) {
  let rows=snapshot.latest7,disposed=false;
  const button=document.createElement("button");button.type="button";button.className="btn btn-outline-primary";button.textContent="Refresh latest seven days from GOV.UK";
  const status=document.createElement("p");status.className="reading-note";status.setAttribute("role","status");status.setAttribute("aria-live","polite");
  const display=document.createElement("div");container.className="small-boats-live";container.append(button,status,display);
  function draw() {
    const total=rows.reduce((sum,row)=>sum+row.arrivals,0),boats=rows.reduce((sum,row)=>sum+row.boats,0);
    const note=document.createElement("p");note.className="explorer-status";note.textContent=total.toLocaleString("en-GB")+" people detected arriving · "+boats.toLocaleString("en-GB")+" boats · "+format(rows[0].date)+" to "+format(rows[6].date)+". Provisional operational data.";
    const chart=Plot.plot({width:Math.min(width,1000),height:300,marginLeft:70,
      ariaLabel:"Latest seven days of official small-boat arrivals",
      x:{type:"band",label:"Observation date",tickFormat:d=>new Date(d).toLocaleDateString("en-GB",{day:"numeric",month:"short",timeZone:"UTC"})},
      y:{label:"People detected arriving",grid:true},marks:[Plot.barY(rows,{x:"date",y:"arrivals",fill:"#256f68",title:d=>format(d.date)+": "+d.arrivals.toLocaleString("en-GB")+" people, "+d.boats+" boats"})]});
    const table=document.createElement("table");table.className="table table-sm small-boats-table";
    const head=table.createTHead().insertRow();for(const label of ["Date","People arriving","Boats"]){const cell=document.createElement("th");cell.scope="col";cell.textContent=label;head.append(cell);}
    const body=table.createTBody();for(const row of rows){const tr=body.insertRow();for(const value of [format(row.date),row.arrivals.toLocaleString("en-GB"),row.boats.toLocaleString("en-GB")])tr.insertCell().textContent=value;}
    display.replaceChildren(note,chart,table);
  }
  status.textContent="Saved fallback snapshot, retrieved "+format(snapshot.metadata.retrieved_at_utc)+". Attempting the live official daily feed…";draw();
  async function refresh() {
    button.disabled=true;
    try {
      const response=await fetch(endpoint,{cache:"no-store",signal:AbortSignal.timeout(12000)});
      if (!response.ok)throw new Error("Official feed unavailable.");
      const payload=await response.json(),fresh=parse(payload);
      if (disposed)return;
      if (fresh[6].date<rows[6].date)throw new Error("Official feed is older than the saved snapshot.");
      rows=fresh;draw();
      status.textContent="Live GOV.UK daily feed · publication updated "+format(payload.public_updated_at||payload.details.public_timestamp)+" · checked "+new Date().toLocaleString("en-GB",{day:"numeric",month:"long",year:"numeric",hour:"2-digit",minute:"2-digit",timeZone:"UTC",hour12:false})+" UTC. Historical charts below remain a separately dated snapshot.";
    } catch(error) {
      if (!disposed)status.textContent="Live refresh unavailable. Retaining the last available figures through "+format(rows[6].date)+"; saved snapshot retrieved "+format(snapshot.metadata.retrieved_at_utc)+". Use the official source links for the newest publication.";
    } finally {if (!disposed)button.disabled=false;}
  }
  button.addEventListener("click",refresh);refresh();
  return ()=>{disposed=true;};
}
