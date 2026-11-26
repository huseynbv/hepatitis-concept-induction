"""Puts the DL-Learner and baseline results side by side (summary tables and the
figures used in the report).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"
BLUE, ORANGE, AQUA, YELLOW, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6"
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"


def style(ax, title=None, ylabel=None, xlabel=None):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, fontsize=10, color=INK, loc="left")
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8, color=MUTED)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=8, color=MUTED)


def main():
    runs = pd.read_csv(TABLES / "dl_runs.csv")
    ev = pd.read_csv(TABLES / "concept_eval.csv")
    base = pd.read_csv(TABLES / "baseline_eval.csv")
    anytime = pd.read_csv(TABLES / "dl_anytime.csv")

    best = ev[ev["rank"] == 1].merge(
        runs[["run_id", "group", "language", "algorithm", "time_budget_s", "max_depth",
              "noise", "expansion_penalty", "accuracy_method", "search_time_s",
              "descriptions_tested", "search_tree_nodes", "reasoner_init_s", "n_improvements"]],
        on="run_id", how="left")
    cols = ["run_id", "group", "kb", "algorithm", "language", "time_budget_s", "max_depth", "noise",
            "expansion_penalty", "accuracy_method", "concept", "length", "depth", "roles",
            "train_accuracy", "train_f1", "test_accuracy", "test_precision", "test_recall", "test_f1",
            "search_time_s", "descriptions_tested", "search_tree_nodes", "reasoner_init_s"]
    best = best[cols].sort_values("run_id")
    best.to_csv(TABLES / "summary_dl.csv", index=False)

    grp = best.groupby("group").agg(runs=("run_id", "size"),
                                    best_test_f1=("test_f1", "max"),
                                    mean_test_f1=("test_f1", "mean"),
                                    mean_length=("length", "mean")).round(3)
    grp.to_csv(TABLES / "summary_by_group.csv")

    comp = []
    for _, r in best.iterrows():
        comp.append({"approach": f"DL-Learner {r.algorithm.upper()} {r.language} ({r.run_id})",
                     "kb_or_features": r.kb, "model": r.concept, "size": f"length {r.length}",
                     "train_accuracy": r.train_accuracy, "train_f1": r.train_f1,
                     "test_accuracy": r.test_accuracy, "test_precision": r.test_precision,
                     "test_recall": r.test_recall, "test_f1": r.test_f1})
    for _, r in base.iterrows():
        comp.append({"approach": f"{r.model} ({r.feature_set})", "kb_or_features": r.feature_set,
                     "model": r.best_params, "size": r.model_size,
                     "train_accuracy": r.train_accuracy, "train_f1": r.train_f1,
                     "test_accuracy": r.test_accuracy, "test_precision": r.test_precision,
                     "test_recall": r.test_recall, "test_f1": r.test_f1})
    pd.DataFrame(comp).to_csv(TABLES / "summary_comparison.csv", index=False)

    # language figure
    lang = best[best.group == "language"].copy()
    lang["language"] = pd.Categorical(lang.language, ["EL", "ALC", "ALCQ", "ALCD", "FULL"], ordered=True)
    lang = lang.sort_values("language")
    if len(lang):
        fig, axes = plt.subplots(1, 2, figsize=(7.5, 2.8))
        x = range(len(lang))
        axes[0].bar([i - 0.2 for i in x], lang.train_f1, width=0.38, color=BLUE, label="train F1", linewidth=0)
        axes[0].bar([i + 0.2 for i in x], lang.test_f1, width=0.38, color=ORANGE, label="test F1", linewidth=0)
        axes[0].set_xticks(list(x))
        axes[0].set_xticklabels(lang.language.astype(str))
        axes[0].set_ylim(0.5, 1.0)
        axes[0].legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
        style(axes[0], "Best concept per hypothesis language", "F1")
        axes[1].bar(list(x), lang.length, width=0.5, color=VIOLET, linewidth=0)
        axes[1].set_xticks(list(x))
        axes[1].set_xticklabels(lang.language.astype(str))
        style(axes[1], "Length of the best concept", "concept length")
        fig.tight_layout()
        fig.savefig(FIGURES / "dl_language.png", dpi=200)
        plt.close(fig)

    # anytime curves
    sel = runs[runs.group.isin(["runtime", "language"]) & (runs.language == "ALC")]["run_id"].tolist()
    fig, ax = plt.subplots(figsize=(6, 3))
    colors = [BLUE, ORANGE, AQUA, YELLOW, VIOLET]
    for c, run_id in zip(colors, sel):
        a = anytime[anytime.run_id == run_id].sort_values("after_s")
        if len(a) == 0:
            continue
        end = runs.loc[runs.run_id == run_id, "search_time_s"].iloc[0]
        xs = list(a.after_s) + [end]
        ys = list(a.train_acc) + [a.train_acc.iloc[-1]]
        ax.step(xs, ys, where="post", color=c, linewidth=2, label=run_id)
        ax.plot(a.after_s, a.train_acc, "o", color=c, markersize=4)
    ax.set_xscale("log")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    style(ax, "CELOE anytime behaviour: best training accuracy vs search time", "training accuracy",
          "search time (s, log scale)")
    fig.tight_layout()
    fig.savefig(FIGURES / "dl_anytime.png", dpi=200)
    plt.close(fig)

    # concepts vs trees/forests
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    items = []
    for kb_name, fs, label in (("hepatitis_v2.owl", "relational", "full KB / all features"),
                               ("hepatitis_v2_noinf.owl", "no_artefact", "without duration table / artefact features")):
        dl = best[best.kb == kb_name].sort_values("test_f1", ascending=False).head(1)
        dt = base[(base.feature_set == fs) & (base.model == "decision_tree")]
        rf = base[(base.feature_set == fs) & (base.model == "random_forest")]
        items.append((label, [("DL concept", float(dl.test_f1.iloc[0]) if len(dl) else 0),
                              ("decision tree", float(dt.test_f1.iloc[0])),
                              ("random forest", float(rf.test_f1.iloc[0]))]))
    maj = float(base[(base.model == "majority")].test_f1.iloc[0])
    width = 0.25
    for gi, (label, vals) in enumerate(items):
        for vi, (name, v) in enumerate(vals):
            ax.bar(gi + (vi - 1) * width, v, width=width - 0.03,
                   color=[AQUA, BLUE, ORANGE][vi], label=name if gi == 0 else None, linewidth=0)
            ax.text(gi + (vi - 1) * width, v + 0.01, f"{v:.2f}", ha="center", fontsize=8, color=INK)
    ax.axhline(maj, color=MUTED, linestyle=":", linewidth=1)
    ax.text(1.42, maj + 0.01, "majority class", fontsize=7, color=MUTED, ha="right")
    ax.set_xticks([0, 1])
    ax.set_xticklabels([i[0] for i in items])
    ax.set_ylim(0.5, 1.0)
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncol=3)
    style(ax, "Test F1 on the same 100 held-out patients", "test F1")
    fig.tight_layout()
    fig.savefig(FIGURES / "dl_vs_baseline.png", dpi=200)
    plt.close(fig)

    # train vs test for every concept
    fig, ax = plt.subplots(figsize=(4.2, 3.8))
    ok = ev.dropna(subset=["length"])
    ax.scatter(ok.train_accuracy, ok.test_accuracy, s=14, c=ok.length, cmap="Blues", vmin=0,
               edgecolors="none", alpha=0.85)
    ax.plot([0.5, 1], [0.5, 1], color=MUTED, linewidth=0.8, linestyle="--")
    style(ax, "Train vs test accuracy (all top-10 concepts)", "test accuracy", "training accuracy")
    ax.text(0.52, 0.95, "shade = concept length", fontsize=7, color=MUTED)
    fig.tight_layout()
    fig.savefig(FIGURES / "generalisation.png", dpi=200)
    plt.close(fig)

    print(best[["run_id", "language", "concept", "length", "train_accuracy", "test_accuracy", "test_f1"]]
          .to_string(index=False))
    print("\n", grp)


if __name__ == "__main__":
    main()
