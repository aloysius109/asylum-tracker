const keys = ["recognised", "other_protection", "rejected", "closed"];
const labels = ["Refugee status", "Other protection", "Rejected", "Otherwise closed"];
const colours = ["#00a98f", "#f4c542", "#ef6655", "#8574bd"];

export function percent(value) {
  if (value == null || !Number.isFinite(value)) return "Unavailable";
  const p = value * 100;
  if (p === 0) return "0%";
  if (Math.abs(p) < .1) return (p < 0 ? ">−0.1%" : "<0.1%");
  return p.toFixed(Math.abs(Number(p.toFixed(1))) < 10 ? 1 : 0) + "%";
}

export function rates(row) {
  const valid = keys.every(key => Number.isFinite(row[key]) && row[key] >= 0) &&
    row.decisions > 0 && keys.reduce((sum, key) => sum + row[key], 0) === row.decisions;
  const substantive = valid ? row.recognised + row.other_protection + row.rejected : 0;
  return {...row, valid,
    ...Object.fromEntries(keys.map(key => [key + "_share", valid ? row[key] / row.decisions : null])),
    refugee_rate: substantive > 0 ? row.recognised / substantive : null,
    protection_rate: substantive > 0 ? (row.recognised + row.other_protection) / substantive : null};
}

export function overall(rows) {
  const eligible = rows.filter(row => rates(row).valid);
  const totals = Object.fromEntries([...keys, "decisions"].map(key => [key, eligible.reduce((sum, row) => sum + row[key], 0)]));
  return {...rates(totals), years: eligible.length, from: eligible[0]?.year, to: eligible.at(-1)?.year};
}

export function pie(row, name) {
  const card = document.createElement("div");
  card.className = "grant-pie";
  if (!row.valid) {
    card.textContent = "No complete, reconciled positive decision total is available.";
    return card;
  }
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 240 240");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", name + ": overall recorded decision outcomes");
  let angle = -Math.PI / 2;
  const list = document.createElement("ul");
  keys.forEach((key, i) => {
    const share = row[key + "_share"];
    const end = angle + share * Math.PI * 2;
    if (share > 0) {
      const shape = document.createElementNS(ns, share >= 1 ? "circle" : "path");
      if (share >= 1) {
        shape.setAttribute("cx", "120"); shape.setAttribute("cy", "120"); shape.setAttribute("r", "108");
      } else {
        shape.setAttribute("d", `M120,120 L${120+108*Math.cos(angle)},${120+108*Math.sin(angle)} A108,108 0 ${share>.5?1:0},1 ${120+108*Math.cos(end)},${120+108*Math.sin(end)} Z`);
      }
      shape.setAttribute("fill", colours[i]);
      shape.setAttribute("stroke", "white");
      const title = document.createElementNS(ns, "title");
      title.textContent = `${labels[i]}: ${percent(share)} (${row[key].toLocaleString("en-GB")})`;
      shape.append(title); svg.append(shape);
      if (share >= .05) {
        const text = document.createElementNS(ns, "text");
        text.setAttribute("x", 120 + 72*Math.cos((angle+end)/2));
        text.setAttribute("y", 120 + 72*Math.sin((angle+end)/2));
        text.setAttribute("text-anchor", "middle"); text.setAttribute("dominant-baseline", "middle");
        text.setAttribute("font-size", "15"); text.setAttribute("fill", "#173b40");
        text.textContent = percent(share); svg.append(text);
      }
    }
    angle = end;
    const item = document.createElement("li");
    const swatch = document.createElement("span"); swatch.style.background = colours[i]; swatch.className = "grant-swatch";
    item.append(swatch, `${labels[i]}: ${percent(share)}`);
    list.append(item);
  });
  card.append(svg, list);
  return card;
}

export function csv(rows) {
  const fields = ["year", "unit", ...keys, "decisions", ...keys.map(key => key + "_share"), "refugee_rate", "protection_rate"];
  return fields.join(",") + "\n" + rows.map(row => fields.map(key => row[key] == null ? "" : String(row[key])).join(",")).join("\n") + "\n";
}
