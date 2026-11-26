"""Descriptive statistics and figures for the report (class balance, records per
patient, attribute distributions per class, the structural artefacts, Bio sharing).
Everything goes to results/tables and results/figures.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"

LABS = ["got", "gpt", "alb", "tbil", "dbil", "che", "ttt", "ztt", "tcho", "tp"]
COLORS = {0: "#2a78d6", 1: "#eb6834"}
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"


def style(ax, title=None, ylabel=None):
    ax.set_facecolor("#fcfcfb")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, fontsize=10, color=INK, loc="left")
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8, color=MUTED)


def grouped_bars(ax, table, title, xlabel):
    cats = list(table.index)
    x = range(len(cats))
    w = 0.38
    for i, cls in enumerate((0, 1)):
        vals = table[cls].values
        ax.bar([xi + (i - 0.5) * (w + 0.02) for xi in x], vals, width=w,
               color=COLORS[cls], label=f"Type {cls}", linewidth=0)
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(c) for c in cats])
    ax.set_xlabel(xlabel, fontsize=8, color=MUTED)
    style(ax, title)


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    pat = pd.read_csv(DATA / "dispat.csv")
    bio = pd.read_csv(DATA / "Bio.csv")
    ind = pd.read_csv(DATA / "indis.csv")
    inf = pd.read_csv(DATA / "inf.csv")
    r11 = pd.read_csv(DATA / "rel11.csv")
    r12 = pd.read_csv(DATA / "rel12.csv")
    r13 = pd.read_csv(DATA / "rel13.csv")
    types = pat.set_index("m_id")["Type"]

    # 1. Class balance
    balance = pat["Type"].value_counts().sort_index().rename("patients").to_frame()
    balance["share"] = (balance["patients"] / len(pat)).round(3)
    balance.to_csv(TABLES / "class_balance.csv", index_label="Type")
    fig, ax = plt.subplots(figsize=(3.2, 2.6))
    ax.bar([0, 1], balance["patients"], color=[COLORS[0], COLORS[1]], width=0.6, linewidth=0)
    for i, v in enumerate(balance["patients"]):
        ax.text(i, v + 4, str(v), ha="center", fontsize=9, color=INK)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Type 0", "Type 1"])
    style(ax, "Patients per class (n = 500)")
    fig.tight_layout()
    fig.savefig(FIGURES / "class_balance.png", dpi=200)
    plt.close(fig)

    # 2. Records per patient
    counts = pd.DataFrame({
        "n_bio": r11.groupby("m_id").size(),
        "n_lab": r12.groupby("m_id").size(),
        "n_dur": r13.groupby("m_id").size(),
    }).reindex(pat["m_id"]).fillna(0).astype(int)
    counts["Type"] = types
    summary = counts.groupby("Type").agg(
        patients=("n_lab", "size"),
        lab_mean=("n_lab", "mean"), lab_median=("n_lab", "median"), lab_max=("n_lab", "max"),
        lab_zero=("n_lab", lambda s: int((s == 0).sum())),
        bio_mean=("n_bio", "mean"), bio_max=("n_bio", "max"),
        bio_ge2=("n_bio", lambda s: int((s >= 2).sum())),
        dur_present=("n_dur", "sum"),
    ).round(2)
    summary.to_csv(TABLES / "records_per_patient.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.8))
    for ax, col, title in ((axes[0], "n_lab", "Lab records per patient"),
                           (axes[1], "n_bio", "Bio links per patient")):
        data = [counts.loc[counts.Type == c, col] for c in (0, 1)]
        bp = ax.boxplot(data, widths=0.5, patch_artist=True, showfliers=True,
                        medianprops=dict(color=INK, linewidth=1.2),
                        flierprops=dict(marker="o", markersize=3, markerfacecolor=MUTED,
                                        markeredgecolor="none"))
        for patch, c in zip(bp["boxes"], (0, 1)):
            patch.set_facecolor(COLORS[c])
            patch.set_alpha(0.75)
            patch.set_linewidth(0)
        ax.set_xticks([1, 2])
        ax.set_xticklabels(["Type 0", "Type 1"])
        style(ax, title, "count")
    fig.tight_layout()
    fig.savefig(FIGURES / "records_per_patient.png", dpi=200)
    plt.close(fig)

    # 3. Patient-level attributes
    rows = []
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.8), gridspec_kw={"width_ratios": [1, 2.5]})
    for ax, attr in zip(axes, ("sex", "age")):
        ct = pd.crosstab(pat[attr], pat["Type"])
        for cat, r in ct.iterrows():
            rows.append({"attribute": attr, "code": cat, "type0": int(r.get(0, 0)),
                         "type1": int(r.get(1, 0)),
                         "share_type1": round(r.get(1, 0) / r.sum(), 3)})
        grouped_bars(ax, ct, f"Patients by {attr} and class", f"{attr} code")
    axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "class_conditional_patient.png", dpi=200)
    plt.close(fig)
    pd.DataFrame(rows).to_csv(TABLES / "class_conditional_patient.csv", index=False)

    # 4. Bio attributes (link level: one row per patient-Bio link)
    bl = r11.merge(bio, on="b_id").merge(pat[["m_id", "Type"]], on="m_id")
    rows = []
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.8))
    for ax, attr in zip(axes, ("fibros", "activity")):
        ct = pd.crosstab(bl[attr], bl["Type"])
        for cat, r in ct.iterrows():
            rows.append({"attribute": attr, "code": cat, "type0": int(r.get(0, 0)),
                         "type1": int(r.get(1, 0)),
                         "share_type1": round(r.get(1, 0) / r.sum(), 3)})
        grouped_bars(ax, ct, f"Patient-Bio links by {attr} and class", f"{attr} code")
    axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "class_conditional_bio.png", dpi=200)
    plt.close(fig)
    pd.DataFrame(rows).to_csv(TABLES / "class_conditional_bio.csv", index=False)

    # 5. Lab attributes (record level)
    ll = r12.merge(ind, on="in_id").merge(pat[["m_id", "Type"]], on="m_id")
    rows = []
    fig, axes = plt.subplots(2, 5, figsize=(12, 5))
    for ax, attr in zip(axes.flat, LABS):
        ct = pd.crosstab(ll[attr], ll["Type"])
        for cat, r in ct.iterrows():
            rows.append({"attribute": attr, "code": cat, "type0": int(r.get(0, 0)),
                         "type1": int(r.get(1, 0)),
                         "share_type1": round(r.get(1, 0) / r.sum(), 3)})
        share = ct.div(ct.sum(axis=1), axis=0)
        ax.bar(range(len(share)), share[0], color=COLORS[0], width=0.7, linewidth=0,
               label="Type 0")
        ax.bar(range(len(share)), share[1], bottom=share[0], color=COLORS[1], width=0.7,
               linewidth=0, label="Type 1")
        ax.axhline(206 / 500 if False else ll["Type"].eq(0).mean(), color=INK,
                   linewidth=0.8, linestyle=":")
        ax.set_xticks(range(len(share)))
        ax.set_xticklabels([str(c) for c in share.index])
        ax.set_ylim(0, 1)
        style(ax, f"{attr} (n = {len(ll)} records)", "share of records")
    axes[0, 0].legend(frameon=False, fontsize=7, loc="lower left")
    fig.suptitle("Class composition of lab records per code (dotted = overall Type 0 share)",
                 fontsize=10, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(FIGURES / "class_conditional_labs.png", dpi=200)
    plt.close(fig)
    pd.DataFrame(rows).to_csv(TABLES / "class_conditional_labs.csv", index=False)

    # 6. Duration
    dl = r13.merge(inf, on="a_id").merge(pat[["m_id", "Type"]], on="m_id")
    ct = pd.crosstab(dl["dur"], dl["Type"]).reindex(columns=[0, 1], fill_value=0)
    ct.to_csv(TABLES / "class_conditional_duration.csv")

    # 7. Structural artefacts: features that occur in exactly one class
    pos_only = []

    def record(name, mask):
        sub = counts[mask]
        pos_only.append({"feature": name, "type0": int((sub.Type == 0).sum()),
                         "type1": int((sub.Type == 1).sum()),
                         "share_of_type1": round((sub.Type == 1).sum() / 294, 3)})

    record("has a duration record", counts.n_dur >= 1)
    record(">= 2 Bio links", counts.n_bio >= 2)
    record("> 21 lab records", counts.n_lab > 21)
    for attr, code in (("fibros", 0), ("activity", 0), ("activity", 4)):
        ids = set(bl[bl[attr] == code].m_id)
        record(f"linked to a Bio row with {attr} = {code}", counts.index.isin(ids))
    for attr, code in (("che", 0), ("che", 2)):
        ids = set(ll[ll[attr] == code].m_id)
        record(f"has a lab record with {attr} = {code}", counts.index.isin(ids))
    union = (counts.n_dur >= 1) | (counts.n_bio >= 2)
    record("duration record OR >= 2 Bio links", union)
    art = pd.DataFrame(pos_only)
    art.to_csv(TABLES / "artefacts.csv", index=False)

    fig, ax = plt.subplots(figsize=(7, 3.2))
    y = range(len(art))
    ax.barh(y, art.type1, color=COLORS[1], height=0.6, linewidth=0, label="Type 1")
    ax.barh(y, -art.type0, color=COLORS[0], height=0.6, linewidth=0, label="Type 0")
    for i, r in art.iterrows():
        ax.text(r.type1 + 3, i, str(r.type1), va="center", fontsize=8, color=INK)
        if r.type0:
            ax.text(-r.type0 - 3, i, str(r.type0), va="center", ha="right", fontsize=8, color=INK)
    ax.set_yticks(list(y))
    ax.set_yticklabels(art.feature, fontsize=8)
    ax.axvline(0, color="#c3c2b7", linewidth=0.8)
    ax.invert_yaxis()
    ax.set_xlim(-60, 300)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.yaxis.grid(False)
    ax.set_xlabel("patients (Type 0 drawn to the left, Type 1 to the right)", fontsize=8, color=MUTED)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    style(ax, "Patients covered by structural features, by class")
    fig.tight_layout()
    fig.savefig(FIGURES / "artefacts.png", dpi=200)
    plt.close(fig)

    # 8. Bio sharing
    share = r11.groupby("b_id").size().rename("patients_linked").to_frame()
    share = share.join(bio.set_index("b_id"))
    share.sort_values("patients_linked", ascending=False).to_csv(TABLES / "bio_sharing.csv")

    print("EDA tables:", sorted(p.name for p in TABLES.glob("*.csv")))
    print("EDA figures:", sorted(p.name for p in FIGURES.glob("*.png")))
    print(summary)
    print(art)


if __name__ == "__main__":
    main()
