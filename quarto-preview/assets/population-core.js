export const metrics=[
  ["applications","Applications","#164b63"],
  ["recognised","Refugee-status grants","#00a98f"],
  ["other_protection","Other-protection grants","#d6a500"],
  ["protection_total","Any protection (refugee + other)","#317a65"],
  ["rejected","Refusals","#ef6655"],
  ["closed","Otherwise closed","#8574bd"]
];

export function countryName(country) {
  return ({GBR:"United Kingdom",USA:"United States",RUS:"Russia",TUR:"Türkiye"}[country.iso]||country.name);
}

export function countryYears(data,country,mode) {
  const source=data.rows.filter(row=>row.country===country&&(mode==="P"?row.unit==="P":["P","C"].includes(row.unit)));
  const first=data.metadata.asylum_source.year_from,last=data.metadata.asylum_source.year_to_available;
  return Array.from({length:last-first+1},(_,i)=>{
    const year=first+i,parts=source.filter(row=>row.year===year);
    // Population belongs to a country-year, not a reporting unit: never sum it.
    const population=data.rows.find(row=>row.country===country&&row.year===year&&row.population>0)?.population??null;
    const result={country,year,population,population_year:population?year:null,reporting_units:mode==="P"?"P":"P+C"};
    for (const key of ["applications","recognised","other_protection","rejected","closed"]) {
      const values=parts.map(row=>row[key]).filter(value=>value!=null);
      result[key]=values.length?values.reduce((sum,value)=>sum+value,0):null;
    }
    result.protection_total=result.recognised!=null&&result.other_protection!=null?result.recognised+result.other_protection:null;
    for (const [key] of metrics) {
      result[key+"_per_100k"]=population&&result[key]!=null?result[key]/population*100000:null;
      result["residents_per_"+key]=population&&result[key]>0?population/result[key]:null;
    }
    return result;
  });
}

export function display(value) {
  if (value==null||!Number.isFinite(value)) return "Unavailable";
  if (value>0&&value<.1) return "<0.1";
  return value.toLocaleString("en-GB",{minimumFractionDigits:0,maximumFractionDigits:1});
}
