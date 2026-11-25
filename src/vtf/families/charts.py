"""Family 1: Financial & Operational Analytics Charts (ChartQA-inspired)."""

from __future__ import annotations

import copy
import random
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from vtf.families.base import VisualTaskFamily
from vtf.schema import AnswerType, Difficulty, FamilyName, SceneElement, SceneManifest

CHART_THEMES = [
    {
        "name": "corporate_slate",
        "bg": "#FFFFFF",
        "axes_bg": "#F8FAFC",
        "text": "#0F172A",
        "grid": "#CBD5E1",
        "palette": ["#2563EB", "#EA580C", "#0D9488", "#7C3AED"],
    },
    {
        "name": "editorial_warm",
        "bg": "#FFFDF9",
        "axes_bg": "#FFFBF2",
        "text": "#1C1917",
        "grid": "#E7E5E4",
        "palette": ["#B91C1C", "#0369A1", "#15803D", "#A16207"],
    },
    {
        "name": "nordic_cool",
        "bg": "#F8FAFC",
        "axes_bg": "#FFFFFF",
        "text": "#1E293B",
        "grid": "#E2E8F0",
        "palette": ["#0F766E", "#4338CA", "#DB2777", "#CA8A04"],
    },
]

DOMAIN_TEMPLATES = [
    {
        "title": "Quarterly Cloud Spend by Department",
        "ylabel": "Spend ($K)",
        "unit": "$K",
        "categories": ["Platform", "ML Infra", "Security", "Analytics", "Storage", "Mobile"],
        "periods": ["Q1", "Q2", "Q3", "Q4", "Q5"],
        "series": ["Compute", "Storage", "Network"],
    },
    {
        "title": "Regional Fulfillment Volume",
        "ylabel": "Orders (Thousands)",
        "unit": "K",
        "categories": ["North", "South", "East", "West", "Central", "Metro"],
        "periods": ["Jan", "Feb", "Mar", "Apr", "May"],
        "series": ["Express", "Standard", "Pickup"],
    },
    {
        "title": "Product Line Gross Revenue",
        "ylabel": "Revenue ($M)",
        "unit": "$M",
        "categories": ["Sensors", "Routers", "Gateways", "Displays", "Modules", "Cables"],
        "periods": ["2022", "2023", "2024", "2025", "2026"],
        "series": ["Enterprise", "SMB", "OEM"],
    },
]


class ChartsTaskFamily(VisualTaskFamily):
    """Generates varied analytical charts with exact pixel bounding boxes."""

    family_name = FamilyName.CHARTS

    def generate_spec(self, seed: int, difficulty: Difficulty) -> dict[str, Any]:
        rng = random.Random(seed)
        theme = copy.deepcopy(rng.choice(CHART_THEMES))
        domain = copy.deepcopy(rng.choice(DOMAIN_TEMPLATES))

        if difficulty == Difficulty.EASY:
            subtype = rng.choice(["vertical_bar", "horizontal_bar"])
            n_cats = rng.randint(5, 6)
            cats = domain["categories"][:n_cats]
            vals = self._unique_values(rng, n_cats, low=18, high=95, min_gap=4)
            show_values = True
            ask_max = rng.choice([True, False])
            reasoning_type = "extrema_max" if ask_max else "extrema_min"
            kind_word = "highest" if ask_max else "lowest"
            question = (
                f"In the chart '{domain['title']}', which category has the {kind_word} "
                f"{domain['ylabel'].split('(')[0].strip().lower()}?"
            )
            return {
                "subtype": subtype,
                "difficulty": difficulty.value,
                "reasoning_type": reasoning_type,
                "theme_name": theme["name"],
                "theme": theme,
                "title": domain["title"],
                "ylabel": domain["ylabel"],
                "unit": domain["unit"],
                "categories": cats,
                "series_names": ["Primary"],
                "values": {"Primary": vals},
                "show_values": show_values,
                "rotate_x": rng.choice([0, 20]),
                "ask_max": ask_max,
                "question": question,
            }

        if difficulty == Difficulty.MEDIUM:
            subtype = rng.choice(["grouped_bar", "line_series"])
            if subtype == "grouped_bar":
                n_cats = 4
                cats = domain["categories"][:n_cats]
                s_names = domain["series"][:2]
                v1 = self._unique_values(rng, n_cats, low=22, high=92, min_gap=4)
                v2 = self._unique_values(rng, n_cats, low=20, high=90, min_gap=4)
                # Ensure distinct per-category gap for unambiguous comparison
                while len({abs(a - b) for a, b in zip(v1, v2)}) < n_cats:
                    v2 = self._unique_values(rng, n_cats, low=20, high=90, min_gap=4)
                target_idx = rng.randrange(n_cats)
                target_cat = cats[target_idx]
                show_values = rng.choice([True, False])
                if rng.choice([True, False]):
                    reasoning_type = "series_difference"
                    question = (
                        f"In '{domain['title']}', for {target_cat}, what is the absolute "
                        f"difference between {s_names[0]} and {s_names[1]} (in {domain['unit']})?"
                    )
                    threshold = None
                else:
                    reasoning_type = "threshold_count"
                    all_vals = v1 + v2
                    sorted_v = sorted(all_vals)
                    mid_i = len(sorted_v) // 2
                    threshold = int((sorted_v[mid_i - 1] + sorted_v[mid_i]) // 2)
                    # Guarantee no bar sits directly on the threshold line
                    for arr in (v1, v2):
                        for idx, val in enumerate(arr):
                            if val == threshold:
                                arr[idx] = val + 2
                    question = (
                        f"In '{domain['title']}', how many bars across both series exceed "
                        f"the dashed target threshold of {threshold} {domain['unit']}?"
                    )
                return {
                    "subtype": subtype,
                    "difficulty": difficulty.value,
                    "reasoning_type": reasoning_type,
                    "theme_name": theme["name"],
                    "theme": theme,
                    "title": domain["title"],
                    "ylabel": domain["ylabel"],
                    "unit": domain["unit"],
                    "categories": cats,
                    "series_names": s_names,
                    "values": {s_names[0]: v1, s_names[1]: v2},
                    "show_values": show_values,
                    "threshold": threshold,
                    "target_category": target_cat,
                    "rotate_x": 0,
                    "question": question,
                }

            # line_series
            periods = domain["periods"]
            s_names = domain["series"][:2]
            v1 = [rng.randint(25, 85) for _ in periods]
            v2 = [rng.randint(25, 85) for _ in periods]
            # Guarantee distinct net growth between series
            while (v1[-1] - v1[0]) == (v2[-1] - v2[0]):
                v2[-1] += rng.choice([-6, 6])
            reasoning_type = "net_growth_leader"
            question = (
                f"In '{domain['title']}', which series had the larger net increase from "
                f"{periods[0]} to {periods[-1]}?"
            )
            return {
                "subtype": "line_series",
                "difficulty": difficulty.value,
                "reasoning_type": reasoning_type,
                "theme_name": theme["name"],
                "theme": theme,
                "title": f"{domain['title']} Over Time",
                "ylabel": domain["ylabel"],
                "unit": domain["unit"],
                "categories": periods,
                "series_names": s_names,
                "values": {s_names[0]: v1, s_names[1]: v2},
                "show_values": rng.choice([True, False]),
                "rotate_x": 0,
                "question": question,
            }

        # HARD: stacked_bar, dual_metric_combo, or OCR-proof unlabeled_visual_gap
        subtype = rng.choice(["unlabeled_visual_gap", "stacked_bar", "dual_metric_combo"])
        if subtype == "unlabeled_visual_gap":
            n_cats = 4
            cats = domain["categories"][:n_cats]
            s_names = domain["series"][:2]
            v1 = self._unique_values(rng, n_cats, low=25, high=92, min_gap=6)
            v2 = self._unique_values(rng, n_cats, low=22, high=90, min_gap=6)
            gaps = [abs(a - b) for a, b in zip(v1, v2)]
            max_i = int(np.argmax(gaps))
            # Enforce a strong >= 14 unit visual separation over runner-up gap (no OCR numbers!)
            for i in range(n_cats):
                if i != max_i and gaps[max_i] - gaps[i] < 14:
                    if v1[max_i] >= v2[max_i]:
                        v1[max_i] = min(98, v1[max_i] + 15)
                        v2[max_i] = max(12, v2[max_i] - 10)
                    else:
                        v2[max_i] = min(98, v2[max_i] + 15)
                        v1[max_i] = max(12, v1[max_i] - 10)
                    gaps[max_i] = abs(v1[max_i] - v2[max_i])
            question = (
                f"In '{domain['title']}' (no numeric values are printed on the bars), "
                f"which category shows the LARGEST visual height gap between {s_names[0]} and {s_names[1]}?"
            )
            return {
                "subtype": "unlabeled_visual_gap",
                "difficulty": difficulty.value,
                "reasoning_type": "unlabeled_bar_gap_comparison",
                "theme_name": theme["name"],
                "theme": theme,
                "title": domain["title"],
                "ylabel": domain["ylabel"],
                "unit": domain["unit"],
                "categories": cats,
                "series_names": s_names,
                "values": {s_names[0]: v1, s_names[1]: v2},
                "show_values": False,
                "rotate_x": 0,
                "question": question,
            }

        if subtype == "stacked_bar":
            n_cats = 5
            cats = domain["categories"][:n_cats]
            s_names = domain["series"][:3]
            values: dict[str, list[int]] = {}
            for s in s_names:
                values[s] = [rng.randint(15, 42) for _ in range(n_cats)]
            totals = [sum(values[s][i] for s in s_names) for i in range(n_cats)]
            # Ensure unique maximum total with gap >= 4
            max_i = int(np.argmax(totals))
            for i in range(n_cats):
                if i != max_i and totals[max_i] - totals[i] < 4:
                    values[s_names[0]][max_i] += 5
                    totals[max_i] += 5
            ask_total_val = rng.choice([True, False])
            if ask_total_val:
                reasoning_type = "stacked_extrema_and_sum"
                question = (
                    f"In '{domain['title']}', what is the combined total value (across all 3 segments) "
                    f"of the highest-total category?"
                )
            else:
                reasoning_type = "stacked_extrema_category"
                question = (
                    f"In '{domain['title']}', which category has the largest combined total "
                    f"across all 3 stacked segments?"
                )
            return {
                "subtype": "stacked_bar",
                "difficulty": difficulty.value,
                "reasoning_type": reasoning_type,
                "theme_name": theme["name"],
                "theme": theme,
                "title": domain["title"],
                "ylabel": domain["ylabel"],
                "unit": domain["unit"],
                "categories": cats,
                "series_names": s_names,
                "values": values,
                "show_values": True,
                "ask_total_val": ask_total_val,
                "rotate_x": 15,
                "question": question,
            }

        # dual_metric_combo: bars (volume) + line (defect/latency rate %)
        periods = domain["periods"]
        vols = self._unique_values(rng, len(periods), low=40, high=115, min_gap=5)
        rates = self._unique_values(rng, len(periods), low=4, high=15, min_gap=2)
        vol_thresh = 75
        rate_thresh = 8
        # Ensure clean separation from thresholds
        vols = [v + 3 if abs(v - vol_thresh) <= 2 else v for v in vols]
        rates = [r + 2 if r == rate_thresh else r for r in rates]
        # Force at least one qualifying period for clean, meaningful questions
        qual = [i for i in range(len(periods)) if vols[i] > vol_thresh and rates[i] < rate_thresh]
        if not qual:
            vols[1] = 96
            rates[1] = 4
        reasoning_type = "dual_axis_conditional_count"
        question = (
            f"In '{domain['title']}', how many periods have Volume strictly above "
            f"{vol_thresh} AND Defect Rate strictly below {rate_thresh}%?"
        )
        return {
            "subtype": "dual_metric_combo",
            "difficulty": difficulty.value,
            "reasoning_type": reasoning_type,
            "theme_name": theme["name"],
            "theme": theme,
            "title": f"{domain['title']} vs Defect Rate",
            "ylabel": "Volume",
            "ylabel_right": "Defect Rate (%)",
            "unit": "",
            "categories": periods,
            "series_names": ["Volume", "Defect Rate (%)"],
            "values": {"Volume": vols, "Defect Rate (%)": rates},
            "vol_thresh": vol_thresh,
            "rate_thresh": rate_thresh,
            "show_values": True,
            "rotate_x": 0,
            "question": question,
        }

    def _unique_values(
        self, rng: random.Random, count: int, *, low: int, high: int, min_gap: int
    ) -> list[int]:
        vals: list[int] = []
        attempts = 0
        while len(vals) < count and attempts < 500:
            attempts += 1
            cand = rng.randint(low, high)
            if all(abs(cand - existing) >= min_gap for existing in vals):
                vals.append(cand)
        while len(vals) < count:
            vals.append(low + len(vals) * min_gap)
        rng.shuffle(vals)
        return vals

    def render_spec(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        theme = spec["theme"]
        cats = spec["categories"]
        series_names = spec["series_names"]
        values = spec["values"]
        subtype = spec["subtype"]
        show_values = bool(spec.get("show_values", True))

        dpi = 120
        fig, ax = plt.subplots(figsize=(9.6, 5.8), dpi=dpi)
        elements: list[SceneElement] = []

        try:
            fig.patch.set_facecolor(theme["bg"])
            ax.set_facecolor(theme["axes_bg"])
            ax.tick_params(colors=theme["text"], labelsize=10.5)
            for spine in ["top", "right"]:
                if subtype != "dual_metric_combo" or spine == "top":
                    ax.spines[spine].set_visible(False)
            ax.spines["left"].set_color(theme["text"])
            ax.spines["bottom"].set_color(theme["text"])

            title_obj = ax.set_title(
                spec["title"], fontsize=14, fontweight="bold", color=theme["text"], pad=14
            )

            tracked_artists: list[tuple[str, str, str, Any, dict[str, Any]]] = []
            ax2 = None

            if subtype == "vertical_bar":
                vals = values[series_names[0]]
                x = np.arange(len(cats))
                bars = ax.bar(
                    x,
                    vals,
                    width=0.58,
                    color=theme["palette"][0],
                    edgecolor=theme["text"],
                    linewidth=0.7,
                    zorder=3,
                )
                ax.set_xticks(x)
                ax.set_xticklabels(cats, rotation=spec.get("rotate_x", 0))
                ax.set_ylabel(spec["ylabel"], color=theme["text"], fontsize=11)
                ax.yaxis.grid(True, linestyle="--", alpha=0.6, color=theme["grid"], zorder=0)
                ax.set_ylim(0, max(vals) * 1.18)
                for idx, (cat, bar, v) in enumerate(zip(cats, bars, vals)):
                    eid = f"bar_{cat}"
                    tracked_artists.append((eid, "bar", cat, bar, {"category": cat, "value": v}))
                    if show_values:
                        txt = ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            v + max(vals) * 0.02,
                            str(v),
                            ha="center",
                            va="bottom",
                            fontsize=10,
                            fontweight="bold",
                            color=theme["text"],
                            zorder=4,
                        )
                        tracked_artists.append(
                            (f"val_{cat}", "value_label", str(v), txt, {"category": cat})
                        )

            elif subtype == "horizontal_bar":
                vals = values[series_names[0]]
                y = np.arange(len(cats))
                bars = ax.barh(
                    y,
                    vals,
                    height=0.58,
                    color=theme["palette"][1],
                    edgecolor=theme["text"],
                    linewidth=0.7,
                    zorder=3,
                )
                ax.set_yticks(y)
                ax.set_yticklabels(cats)
                ax.invert_yaxis()
                ax.set_xlabel(spec["ylabel"], color=theme["text"], fontsize=11)
                ax.xaxis.grid(True, linestyle="--", alpha=0.6, color=theme["grid"], zorder=0)
                ax.set_xlim(0, max(vals) * 1.18)
                for cat, bar, v in zip(cats, bars, vals):
                    eid = f"bar_{cat}"
                    tracked_artists.append((eid, "bar", cat, bar, {"category": cat, "value": v}))
                    if show_values:
                        txt = ax.text(
                            v + max(vals) * 0.015,
                            bar.get_y() + bar.get_height() / 2,
                            str(v),
                            ha="left",
                            va="center",
                            fontsize=10,
                            fontweight="bold",
                            color=theme["text"],
                            zorder=4,
                        )
                        tracked_artists.append(
                            (f"val_{cat}", "value_label", str(v), txt, {"category": cat})
                        )

            elif subtype in {"grouped_bar", "unlabeled_visual_gap"}:
                x = np.arange(len(cats))
                width = 0.36
                all_v = [v for s in series_names for v in values[s]]
                ax.set_ylim(0, max(all_v) * 1.22)
                ax.yaxis.grid(True, linestyle="--", alpha=0.6, color=theme["grid"], zorder=0)
                ax.set_ylabel(spec["ylabel"], color=theme["text"], fontsize=11)
                ax.set_xticks(x)
                ax.set_xticklabels(cats)

                for s_idx, s_name in enumerate(series_names):
                    offset = (s_idx - 0.5) * width
                    bars = ax.bar(
                        x + offset,
                        values[s_name],
                        width=width,
                        label=s_name,
                        color=theme["palette"][s_idx],
                        edgecolor=theme["text"],
                        linewidth=0.6,
                        zorder=3,
                    )
                    for cat, bar, v in zip(cats, bars, values[s_name]):
                        eid = f"bar_{s_name}_{cat}"
                        tracked_artists.append(
                            (eid, "bar", f"{s_name}:{cat}", bar, {"series": s_name, "category": cat, "value": v})
                        )
                        if show_values:
                            txt = ax.text(
                                bar.get_x() + bar.get_width() / 2,
                                v + max(all_v) * 0.018,
                                str(v),
                                ha="center",
                                va="bottom",
                                fontsize=9,
                                fontweight="bold",
                                color=theme["text"],
                                zorder=4,
                            )
                            tracked_artists.append(
                                (f"val_{s_name}_{cat}", "value_label", str(v), txt, {})
                            )

                if spec.get("threshold") is not None:
                    t_val = spec["threshold"]
                    line = ax.axhline(
                        t_val, color="#DC2626", linestyle="--", linewidth=1.8, zorder=5,
                        label=f"Target ({t_val})",
                    )
                    tracked_artists.append(("threshold_line", "threshold", str(t_val), line, {"threshold": t_val}))
                ax.legend(frameon=True, facecolor=theme["bg"], edgecolor=theme["grid"], loc="upper right")

            elif subtype == "line_series":
                x = np.arange(len(cats))
                all_v = [v for s in series_names for v in values[s]]
                ax.set_ylim(min(all_v) * 0.75, max(all_v) * 1.18)
                ax.yaxis.grid(True, linestyle="--", alpha=0.6, color=theme["grid"], zorder=0)
                ax.set_ylabel(spec["ylabel"], color=theme["text"], fontsize=11)
                ax.set_xticks(x)
                ax.set_xticklabels(cats)

                for s_idx, s_name in enumerate(series_names):
                    ys = values[s_name]
                    (line,) = ax.plot(
                        x,
                        ys,
                        marker="o",
                        markersize=8,
                        linewidth=2.5,
                        color=theme["palette"][s_idx],
                        label=s_name,
                        zorder=3,
                    )
                    tracked_artists.append(
                        (f"series_{s_name}", "line", s_name, line, {"series": s_name, "values": ys})
                    )
                    if show_values:
                        dy = 2.6 if s_idx == 0 else -4.2
                        for xi, yi, cat in zip(x, ys, cats):
                            txt = ax.text(
                                xi,
                                yi + dy,
                                str(yi),
                                ha="center",
                                va="center",
                                fontsize=9,
                                fontweight="bold",
                                color=theme["palette"][s_idx],
                                zorder=4,
                            )
                            tracked_artists.append(
                                (f"val_{s_name}_{cat}", "value_label", str(yi), txt, {})
                            )
                ax.legend(frameon=True, facecolor=theme["bg"], edgecolor=theme["grid"], loc="upper left")

            elif subtype == "stacked_bar":
                x = np.arange(len(cats))
                bottom = np.zeros(len(cats))
                totals = [sum(values[s][i] for s in series_names) for i in range(len(cats))]
                ax.set_ylim(0, max(totals) * 1.2)
                ax.yaxis.grid(True, linestyle="--", alpha=0.6, color=theme["grid"], zorder=0)
                ax.set_ylabel(spec["ylabel"], color=theme["text"], fontsize=11)
                ax.set_xticks(x)
                ax.set_xticklabels(cats, rotation=spec.get("rotate_x", 0))

                for s_idx, s_name in enumerate(series_names):
                    ys = np.array(values[s_name], dtype=float)
                    bars = ax.bar(
                        x,
                        ys,
                        bottom=bottom,
                        width=0.55,
                        label=s_name,
                        color=theme["palette"][s_idx],
                        edgecolor=theme["bg"],
                        linewidth=1.0,
                        zorder=3,
                    )
                    for i, (cat, bar, v) in enumerate(zip(cats, bars, values[s_name])):
                        eid = f"seg_{s_name}_{cat}"
                        tracked_artists.append(
                            (eid, "bar_segment", f"{s_name}:{cat}", bar, {"series": s_name, "category": cat, "value": v})
                        )
                        if show_values:
                            txt = ax.text(
                                bar.get_x() + bar.get_width() / 2,
                                bottom[i] + v / 2,
                                str(v),
                                ha="center",
                                va="center",
                                fontsize=9,
                                fontweight="bold",
                                color="#FFFFFF",
                                zorder=4,
                            )
                            tracked_artists.append(
                                (f"val_{s_name}_{cat}", "value_label", str(v), txt, {})
                            )
                    bottom = bottom + ys
                ax.legend(frameon=True, facecolor=theme["bg"], edgecolor=theme["grid"], loc="upper right")

            elif subtype == "dual_metric_combo":
                x = np.arange(len(cats))
                vols = values["Volume"]
                rates = values["Defect Rate (%)"]
                bars = ax.bar(
                    x, vols, width=0.5, color=theme["palette"][0], alpha=0.85, label="Volume", zorder=2
                )
                ax.set_ylabel("Volume", color=theme["palette"][0], fontsize=11, fontweight="bold")
                ax.set_ylim(0, max(vols) * 1.25)
                ax.set_xticks(x)
                ax.set_xticklabels(cats)
                ax.yaxis.grid(True, linestyle="--", alpha=0.5, color=theme["grid"], zorder=0)
                ax.axhline(spec["vol_thresh"], color=theme["palette"][0], linestyle=":", linewidth=1.6)

                for cat, bar, v in zip(cats, bars, vols):
                    tracked_artists.append((f"vol_{cat}", "bar", cat, bar, {"category": cat, "volume": v}))
                    txt = ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        max(vols) * 0.045,
                        str(v),
                        ha="center",
                        va="bottom",
                        fontsize=9.5,
                        fontweight="bold",
                        color="#FFFFFF",
                        zorder=4,
                    )
                    tracked_artists.append((f"vol_txt_{cat}", "value_label", str(v), txt, {}))

                ax2 = ax.twinx()
                ax2.spines["top"].set_visible(False)
                ax2.spines["right"].set_color(theme["palette"][1])
                ax2.tick_params(axis="y", colors=theme["palette"][1], labelsize=10)
                ax2.set_ylabel("Defect Rate (%)", color=theme["palette"][1], fontsize=11, fontweight="bold")
                ax2.set_ylim(0, max(rates) * 1.35)
                (line,) = ax2.plot(
                    x, rates, color=theme["palette"][1], marker="s", markersize=7, linewidth=2.4,
                    label="Defect Rate (%)", zorder=5
                )
                ax2.axhline(spec["rate_thresh"], color=theme["palette"][1], linestyle="--", linewidth=1.5)
                tracked_artists.append(("rate_line", "line", "Defect Rate (%)", line, {}))
                for xi, r, cat in zip(x, rates, cats):
                    txt = ax2.text(
                        xi,
                        r + max(rates) * 0.05,
                        f"{r}%",
                        ha="center",
                        va="bottom",
                        fontsize=9,
                        fontweight="bold",
                        color=theme["palette"][1],
                        zorder=6,
                    )
                    tracked_artists.append((f"rate_txt_{cat}", "value_label", f"{r}%", txt, {}))

                h1, l1 = ax.get_legend_handles_labels()
                h2, l2 = ax2.get_legend_handles_labels()
                ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=True, facecolor=theme["bg"])

            fig.tight_layout(pad=1.6)
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            width_px, height_px = fig.canvas.get_width_height()

            def _to_bbox(artist: Any) -> tuple[float, float, float, float]:
                bb = artist.get_window_extent(renderer=renderer)
                x0, y0, x1, y1 = float(bb.x0), float(height_px - bb.y1), float(bb.x1), float(height_px - bb.y0)
                if x1 <= x0:
                    x0, x1 = x0 - 2.0, x0 + 2.0
                if y1 <= y0:
                    y0, y1 = y0 - 2.0, y0 + 2.0
                return (round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1))

            elements.append(
                SceneElement(
                    id="chart_title",
                    kind="title",
                    label=spec["title"],
                    bbox=_to_bbox(title_obj),
                    font_px=14.0 * dpi / 72.0,
                    is_queried_text=True,
                )
            )
            xmin, xmax = sorted(ax.get_xlim())
            ymin, ymax = sorted(ax.get_ylim())
            for idx, tick in enumerate(ax.get_xticklabels()):
                txt = tick.get_text()
                pos_x = float(tick.get_position()[0])
                if txt and (xmin - 1e-6 <= pos_x <= xmax + 1e-6):
                    elements.append(
                        SceneElement(
                            id=f"xtick_{txt}",
                            kind="axis_tick",
                            label=txt,
                            bbox=_to_bbox(tick),
                            font_px=10.5 * dpi / 72.0,
                            is_queried_text=True,
                        )
                    )
            for idx, tick in enumerate(ax.get_yticklabels()):
                txt = tick.get_text()
                pos_y = float(tick.get_position()[1])
                if txt and (ymin - 1e-6 <= pos_y <= ymax + 1e-6):
                    is_cat_tick = subtype == "horizontal_bar"
                    elements.append(
                        SceneElement(
                            id=f"ytick_{txt}" if is_cat_tick else f"ytick_{idx}",
                            kind="axis_tick",
                            label=txt,
                            bbox=_to_bbox(tick),
                            font_px=10.5 * dpi / 72.0,
                            is_queried_text=is_cat_tick,
                        )
                    )

            for eid, kind, label, artist, attrs in tracked_artists:
                elements.append(
                    SceneElement(
                        id=eid,
                        kind=kind,
                        label=label,
                        bbox=_to_bbox(artist),
                        font_px=(9.5 * dpi / 72.0) if kind == "value_label" else None,
                        is_queried_text=(kind == "value_label"),
                        attributes=attrs,
                    )
                )

            fig.savefig(out_path, dpi=dpi, facecolor=theme["bg"])
            return SceneManifest(width=int(width_px), height=int(height_px), elements=elements)
        finally:
            plt.close(fig)

    def solve_spec(
        self, spec: dict[str, Any]
    ) -> tuple[Any, AnswerType, float, str, list[str], list[str], list[str]]:
        subtype = spec["subtype"]
        cats: list[str] = spec["categories"]
        s_names: list[str] = spec["series_names"]
        values: dict[str, list[int]] = spec["values"]
        unit = str(spec.get("unit", ""))

        if subtype in {"vertical_bar", "horizontal_bar"}:
            vals = values[s_names[0]]
            ask_max = bool(spec["ask_max"])
            best_idx = int(np.argmax(vals) if ask_max else np.argmin(vals))
            ans = cats[best_idx]
            ref_ids = ["chart_title"] + [f"bar_{c}" for c in cats] + [f"xtick_{c}" for c in cats if subtype == "vertical_bar"]
            ev_ids = [f"bar_{ans}"]
            trace = [
                f"Read all bar values: {dict(zip(cats, vals))}.",
                f"Identified {'maximum' if ask_max else 'minimum'} value {vals[best_idx]} at '{ans}'.",
            ]
            return ans, AnswerType.STRING, 0.0, "", ref_ids, ev_ids, trace

        if subtype == "unlabeled_visual_gap":
            gaps = {c: abs(values[s_names[0]][i] - values[s_names[1]][i]) for i, c in enumerate(cats)}
            winner = max(gaps, key=lambda k: gaps[k])
            ref_ids = [f"bar_{s}_{c}" for s in s_names for c in cats] + [f"xtick_{c}" for c in cats]
            ev_ids = [f"bar_{s_names[0]}_{winner}", f"bar_{s_names[1]}_{winner}"]
            trace = [
                f"Visual gaps (|{s_names[0]} - {s_names[1]}|): {gaps}.",
                f"Largest unlabeled visual gap is '{winner}' ({gaps[winner]}).",
            ]
            return winner, AnswerType.STRING, 0.0, "", ref_ids, ev_ids, trace

        if subtype == "grouped_bar":
            rtype = spec["reasoning_type"]
            if rtype == "series_difference":
                tcat = spec["target_category"]
                idx = cats.index(tcat)
                a, b = values[s_names[0]][idx], values[s_names[1]][idx]
                ans = abs(a - b)
                tol = 0.0 if spec.get("show_values", True) else 3.0
                ref_ids = [f"bar_{s_names[0]}_{tcat}", f"bar_{s_names[1]}_{tcat}", f"xtick_{tcat}"]
                trace = [
                    f"Looked up '{tcat}': {s_names[0]}={a}, {s_names[1]}={b}.",
                    f"Computed |{a} - {b}| = {ans}.",
                ]
                return ans, AnswerType.INTEGER, tol, unit, ref_ids, ref_ids[:2], trace

            # threshold_count
            thresh = int(spec["threshold"])
            hits = []
            for s in s_names:
                for c, v in zip(cats, values[s]):
                    if v > thresh:
                        hits.append(f"bar_{s}_{c}")
            ref_ids = ["threshold_line"] + [f"bar_{s}_{c}" for s in s_names for c in cats]
            trace = [
                f"Threshold = {thresh}.",
                f"Checked {len(s_names)*len(cats)} bars; {len(hits)} exceed {thresh}: {hits}.",
            ]
            return len(hits), AnswerType.INTEGER, 0.0, "", ref_ids, hits, trace

        if subtype == "line_series":
            deltas = {s: values[s][-1] - values[s][0] for s in s_names}
            winner = max(deltas, key=lambda k: deltas[k])
            ref_ids = [f"series_{s}" for s in s_names] + [f"xtick_{cats[0]}", f"xtick_{cats[-1]}"]
            ev_ids = [f"series_{winner}"]
            trace = [
                f"Computed net change ({cats[0]} -> {cats[-1]}): {deltas}.",
                f"Winner with larger increase: '{winner}'.",
            ]
            return winner, AnswerType.STRING, 0.0, "", ref_ids, ev_ids, trace

        if subtype == "stacked_bar":
            totals = {c: sum(values[s][i] for s in s_names) for i, c in enumerate(cats)}
            best_cat = max(totals, key=lambda k: totals[k])
            ref_ids = [f"seg_{s}_{c}" for s in s_names for c in cats] + [f"xtick_{c}" for c in cats]
            ev_ids = [f"seg_{s}_{best_cat}" for s in s_names]
            if spec.get("ask_total_val"):
                ans = totals[best_cat]
                trace = [f"Category totals: {totals}.", f"Max total is {ans} at '{best_cat}'."]
                return ans, AnswerType.INTEGER, 0.0, unit, ref_ids, ev_ids, trace
            trace = [f"Category totals: {totals}.", f"Highest-total category: '{best_cat}'."]
            return best_cat, AnswerType.STRING, 0.0, "", ref_ids, ev_ids, trace

        # dual_metric_combo
        vols = values["Volume"]
        rates = values["Defect Rate (%)"]
        vt, rt = int(spec["vol_thresh"]), int(spec["rate_thresh"])
        matches = [cats[i] for i in range(len(cats)) if vols[i] > vt and rates[i] < rt]
        ref_ids = [f"vol_{c}" for c in cats] + ["rate_line"] + [f"xtick_{c}" for c in cats]
        ev_ids = [f"vol_{c}" for c in matches]
        trace = [
            f"Volume > {vt} AND Defect Rate < {rt}%.",
            f"Matching periods: {matches} (count={len(matches)}).",
        ]
        return len(matches), AnswerType.INTEGER, 0.0, "", ref_ids, ev_ids, trace

    def make_counterfactual_spec(
        self, spec: dict[str, Any], seed: int
    ) -> tuple[dict[str, Any], str] | None:
        twin = copy.deepcopy(spec)
        subtype = twin["subtype"]
        cats = twin["categories"]
        s_names = twin["series_names"]
        values = twin["values"]

        if subtype in {"vertical_bar", "horizontal_bar"}:
            vals = values[s_names[0]]
            ask_max = bool(twin["ask_max"])
            order = np.argsort(vals)
            if ask_max:
                best_i, runner_i = int(order[-1]), int(order[-2])
                vals[runner_i] = vals[best_i] + 10
                delta = f"Raised '{cats[runner_i]}' from {spec['values'][s_names[0]][runner_i]} to {vals[runner_i]} above '{cats[best_i]}'."
            else:
                best_i, runner_i = int(order[0]), int(order[1])
                vals[runner_i] = max(5, vals[best_i] - 8)
                if vals[runner_i] >= vals[best_i]:
                    vals[best_i] = vals[runner_i] + 8
                delta = f"Lowered '{cats[runner_i]}' below '{cats[best_i]}' to flip minimum."
            return twin, delta

        if subtype == "unlabeled_visual_gap":
            gaps = {i: abs(values[s_names[0]][i] - values[s_names[1]][i]) for i in range(len(cats))}
            order = sorted(gaps, key=lambda idx: gaps[idx])
            best_i, runner_i = order[-1], order[-2]
            values[s_names[0]][best_i] = 50
            values[s_names[1]][best_i] = 52
            values[s_names[0]][runner_i] = 94
            values[s_names[1]][runner_i] = 16
            return twin, f"Swapped gap leader from '{cats[best_i]}' to '{cats[runner_i]}'."

        if subtype == "grouped_bar":
            if twin["reasoning_type"] == "series_difference":
                idx = cats.index(twin["target_category"])
                old_v = values[s_names[0]][idx]
                values[s_names[0]][idx] = old_v + 17
                return twin, f"Increased {s_names[0]} for {cats[idx]} by +17."
            thresh = int(twin["threshold"])
            for s in s_names:
                for i, v in enumerate(values[s]):
                    if v < thresh:
                        values[s][i] = thresh + 11
                        return twin, f"Moved bar ({s}, {cats[i]}) above threshold {thresh}."
            return None

        if subtype == "line_series":
            deltas = {s: values[s][-1] - values[s][0] for s in s_names}
            loser = min(deltas, key=lambda k: deltas[k])
            winner = max(deltas, key=lambda k: deltas[k])
            values[loser][-1] = values[loser][0] + deltas[winner] + 12
            return twin, f"Boosted final endpoint of '{loser}' to overtake '{winner}'."

        if subtype == "stacked_bar":
            totals = [sum(values[s][i] for s in s_names) for i in range(len(cats))]
            order = np.argsort(totals)
            best_i, second_i = int(order[-1]), int(order[-2])
            boost = (totals[best_i] - totals[second_i]) + 14
            values[s_names[0]][second_i] += boost
            return twin, f"Added +{boost} to segment '{s_names[0]}' of '{cats[second_i]}' so it surpasses '{cats[best_i]}'."

        # dual_metric_combo
        vt, rt = int(twin["vol_thresh"]), int(twin["rate_thresh"])
        for i, c in enumerate(cats):
            if values["Volume"][i] > vt and values["Defect Rate (%)"][i] < rt:
                values["Defect Rate (%)"][i] = rt + 3
                return twin, f"Raised Defect Rate for '{c}' to {rt + 3}% (>= {rt}%) so it no longer qualifies."
        values["Volume"][0] = vt + 20
        values["Defect Rate (%)"][0] = max(1, rt - 3)
        return twin, f"Updated '{cats[0]}' to qualify under both thresholds."
