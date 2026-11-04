export const outcomes = [
  ["recognised", "Recognised refugee status", "#008a53"],
  ["other_protection", "Other protection", "#d6a500"],
  ["rejected", "Rejected", "#b74a43"],
  ["closed", "Otherwise closed", "#7a7a7a"]
];

export function countryYears(data, country, unit) {
  const found = new Map(data.rows.filter(d => d.country === country && d.unit === unit).map(d => [d.year, d]));
  return Array.from({length: data.metadata.year_to_available - data.metadata.year_from + 1}, (_, i) => {
    const year = data.metadata.year_from + i;
    return found.get(year) || {
      country, unit, year, applications: null, decisions: null, recognised: null,
      other_protection: null, rejected: null, closed: null
    };
  });
}

export function csvFor(rows) {
  const columns = ["country", "unit", "year", "applications", "decisions", "recognised", "other_protection", "rejected", "closed"];
  const escape = value => value == null ? "" : '"' + String(value).replaceAll('"', '""') + '"';
  return columns.join(",") + "\r\n" + rows.map(row => columns.map(key => escape(row[key])).join(",")).join("\r\n") + "\r\n";
}

export function sourceLink(dataset, country, metadata) {
  const url = new URL("https://api.unhcr.org/population/v1/" + dataset + "/");
  url.search = new URLSearchParams({
    yearFrom: metadata.year_from, yearTo: metadata.requested_year_to,
    coa: country, coo_all: "true", cf_type: "ISO", download: "true"
  });
  return url.href;
}
