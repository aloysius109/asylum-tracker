export const outcomes = [
  ["recognised", "Recognised refugee status", "#00a98f"],
  ["other_protection", "Other protection", "#f4c542"],
  ["rejected", "Rejected", "#ef6655"],
  ["closed", "Otherwise closed", "#8574bd"]
];

export function countryYears(data, country) {
  const fields = ["applications", "decisions", "recognised", "other_protection", "rejected", "closed"];
  const found = new Map();
  for (const row of data.rows.filter(d => d.country === country && ["P", "C"].includes(d.unit))) {
    if (!found.has(row.year)) found.set(row.year, []);
    found.get(row.year).push(row);
  }
  return Array.from({length: data.metadata.year_to_available - data.metadata.year_from + 1}, (_, i) => {
    const year = data.metadata.year_from + i;
    const sources = found.get(year) || [];
    return Object.assign({country, unit: "P+C", year}, Object.fromEntries(fields.map(key => {
      const values = sources.map(row => row[key]).filter(value => value != null);
      return [key, values.length ? values.reduce((sum, value) => sum + value, 0) : null];
    })));
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
