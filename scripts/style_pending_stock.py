"""Render the observed worldwide stock from a dated, saved UNHCR response."""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview"


def main():
    snapshot = json.loads((DEST / "data/pending-stock-series.json").read_text(encoding="utf-8"))
    items = sorted(snapshot["response"]["items"], key=lambda row: int(row["year"]))
    years = np.array([int(row["year"]) for row in items])
    values = np.array([row["asylum_seekers"] for row in items])
    headline = json.loads((DEST / "data/pending-stock-2025.json").read_text(encoding="utf-8"))
    if years.tolist() != list(range(2000, 2026)) or not np.all(values > 0):
        raise ValueError("Expected 26 positive annual observed stocks.")
    if values[-1] != headline["pending_persons"]:
        raise ValueError("Stock chart and 2025 headline must reconcile.")
    if any(row["coa"] != "-" or row["coo"] != "-" for row in items):
        raise ValueError("Expected worldwide aggregate records, without country subdivisions.")
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 11, "text.color": "#20383b"}):
        fig, ax = plt.subplots(figsize=(12, 5.8), layout="constrained")
        fig.set_facecolor("white")
        ax.fill_between(years, values, color="#e5eeec", alpha=1)
        ax.plot(years, values, color="#256f68", linewidth=2.8, solid_capstyle="round")
        ax.scatter(years, values, s=12, color="#256f68", zorder=3)
        ax.scatter(years[-1], values[-1], s=75, color="#256f68", edgecolor="white", linewidth=2, zorder=4)
        ax.annotate(f"{values[-1]/1e6:.1f} million\n{values[-1]:,} people · end-2025",
                    xy=(years[-1], values[-1]), xytext=(2015.3, values[-1]*1.13),
                    arrowprops={"arrowstyle": "-", "color": "#62978d", "connectionstyle": "angle3,angleA=0,angleB=90"},
                    fontsize=13, color="#20383b", linespacing=1.6,
                    bbox={"boxstyle":"round,pad=.65", "fc":"#f0f5f2", "ec":"none"})
        ax.set(xlim=(1999.5, 2026), ylim=(0, max(values)*1.35),
               xticks=[2000, 2005, 2010, 2015, 2020, 2025], ylabel="People awaiting an asylum decision")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value/1e6:g}m"))
        ax.set_title("The unresolved asylum caseload", loc="left", fontsize=20, pad=28)
        ax.text(0, 1.025, "Observed UNHCR end-year asylum-seeker stock · Worldwide, 2000–2025",
                transform=ax.transAxes, fontsize=10, color="#526767")
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color("#d6e1dc")
        ax.tick_params(length=0, pad=9, colors="#526767")
        ax.grid(axis="y", color="#dce5e1", linewidth=.7)
        ax.set_axisbelow(True)
        fig.savefig(DEST / "assets/observed-pending.png", dpi=170, facecolor="white")
        plt.close(fig)
    print(f"Styled 26 observed stocks; end-2025 reconciles to {values[-1]:,} persons.")


if __name__ == "__main__":
    main()
