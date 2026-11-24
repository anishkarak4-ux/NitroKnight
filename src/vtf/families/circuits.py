"""Family 3: Logic Gate Schematics & Directed Process Flow Networks."""

from __future__ import annotations

import copy
import heapq
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from vtf.families.base import VisualTaskFamily, measure_text_bbox
from vtf.fonts import get_font
from vtf.schema import AnswerType, Difficulty, FamilyName, SceneElement, SceneManifest

GATES = ["AND", "OR", "XOR", "NAND", "NOR"]


def _eval_gate(op: str, a: int, b: int | None = None) -> int:
    if op == "NOT":
        return 1 - a
    assert b is not None
    if op == "AND":
        return int(bool(a and b))
    if op == "OR":
        return int(bool(a or b))
    if op == "XOR":
        return int(a != b)
    if op == "NAND":
        return int(not (a and b))
    if op == "NOR":
        return int(not (a or b))
    raise ValueError(f"Unknown gate: {op}")


def _eval_circuit(inputs: dict[str, int], gates: list[dict[str, Any]]) -> dict[str, int]:
    signals = dict(inputs)
    for g in gates:
        a = signals[g["in1"]]
        b = signals[g["in2"]] if g.get("in2") else None
        signals[g["out"]] = _eval_gate(g["op"], a, b)
    return signals


class LogicCircuitsTaskFamily(VisualTaskFamily):
    """Generates boolean logic circuits and open/blocked directed flow graphs."""

    family_name = FamilyName.LOGIC_CIRCUITS

    def generate_spec(self, seed: int, difficulty: Difficulty) -> dict[str, Any]:
        rng = random.Random(seed)
        if difficulty == Difficulty.EASY:
            return self._gen_circuit_spec(rng, difficulty, n_inputs=3, sensitivity_mode=False)
        if difficulty == Difficulty.MEDIUM:
            if rng.choice([True, False]):
                return self._gen_circuit_spec(rng, difficulty, n_inputs=4, sensitivity_mode=False)
            return self._gen_flow_spec(rng, difficulty)
        # HARD: either sensitivity diagnosis on 4-input multi-stage circuit or complex flow network
        if rng.choice([True, False]):
            return self._gen_circuit_spec(rng, difficulty, n_inputs=4, sensitivity_mode=True)
        return self._gen_flow_spec(rng, difficulty)

    def _gen_circuit_spec(
        self,
        rng: random.Random,
        difficulty: Difficulty,
        *,
        n_inputs: int,
        sensitivity_mode: bool,
    ) -> dict[str, Any]:
        pin_names = ["A", "B", "C", "D"][:n_inputs]
        for _attempt in range(100):
            inputs = {p: rng.randint(0, 1) for p in pin_names}
            if n_inputs == 3:
                gates = [
                    {"id": "G1", "op": rng.choice(GATES), "in1": "A", "in2": "B", "out": "N1", "col": 1, "row": 0},
                    {"id": "G2", "op": "NOT", "in1": "C", "in2": None, "out": "N2", "col": 1, "row": 1},
                    {"id": "G3", "op": rng.choice(GATES), "in1": "N1", "in2": "N2", "out": "Q", "col": 2, "row": 0},
                ]
            else:
                gates = [
                    {"id": "G1", "op": rng.choice(GATES), "in1": "A", "in2": "B", "out": "N1", "col": 1, "row": 0},
                    {"id": "G2", "op": rng.choice(GATES), "in1": "C", "in2": "D", "out": "N2", "col": 1, "row": 1},
                    {"id": "G3", "op": "NOT", "in1": "N1", "in2": None, "out": "N3", "col": 2, "row": 0},
                    {"id": "G4", "op": rng.choice(GATES), "in1": "N3", "in2": "N2", "out": "Q", "col": 3, "row": 0},
                ]

            base_q = _eval_circuit(inputs, gates)["Q"]
            if not sensitivity_mode:
                question = (
                    "Trace the logic schematic from the labeled input pins on the left to output Q on the right. "
                    "What is the binary output value (0 or 1) at pin Q?"
                )
                return {
                    "subtype": "boolean_logic_circuit",
                    "difficulty": difficulty.value,
                    "reasoning_type": "circuit_signal_tracing",
                    "theme_name": "schematic_clean",
                    "inputs": inputs,
                    "gates": gates,
                    "base_q": base_q,
                    "question": question,
                }

            # Sensitivity mode: find a unique single pin flip that changes Q
            sensitive = []
            for p in pin_names:
                alt = dict(inputs)
                alt[p] = 1 - alt[p]
                if _eval_circuit(alt, gates)["Q"] != base_q:
                    sensitive.append(p)
            if len(sensitive) == 1:
                question = (
                    "In this logic schematic, which SINGLE input pin (A, B, C, or D), if flipped alone "
                    "(0->1 or 1->0) while all other inputs remain unchanged, changes the final output Q?"
                )
                return {
                    "subtype": "boolean_logic_circuit",
                    "difficulty": difficulty.value,
                    "reasoning_type": "circuit_fault_sensitivity",
                    "theme_name": "schematic_clean",
                    "inputs": inputs,
                    "gates": gates,
                    "base_q": base_q,
                    "sensitive_pin": sensitive[0],
                    "question": question,
                }

        # Fallback guaranteed unique sensitivity configuration
        inputs = {"A": 1, "B": 1, "C": 0, "D": 1}
        gates = [
            {"id": "G1", "op": "AND", "in1": "A", "in2": "B", "out": "N1", "col": 1, "row": 0},
            {"id": "G2", "op": "OR", "in1": "C", "in2": "D", "out": "N2", "col": 1, "row": 1},
            {"id": "G3", "op": "NOT", "in1": "N1", "in2": None, "out": "N3", "col": 2, "row": 0},
            {"id": "G4", "op": "OR", "in1": "N3", "in2": "N2", "out": "Q", "col": 3, "row": 0},
        ]
        # Let's avoid guaranteed non-sensitivity fallback and pick exact unique XOR/AND mix:
        # G1: A AND B (1&1=1), G2: C AND D (0&1=0), G3: NOT N1 (=0), G4: N3 OR N2 (=0).
        # Flipping A->0 makes N1=0, N3=1, Q=1; flipping B->0 makes N1=0, N3=1, Q=1 (2 pins).
        # Instead make G1=AND(A,B)=1, G2=AND(C,D)=1 (C=1,D=1), G3=NOT(N1)=0, G4=AND(N3,N2)=0 -> Wait:
        # Make G1=OR(1,0)=1, G2=AND(1,1)=1, G3=NOT(1)=0, G4=XOR(0,1)=1. Flip C->0 -> N2=0 -> Q=0; flip D->0 -> N2=0 -> Q=0.
        # To make ONLY C sensitive: A=1, B=1, C=0, D=1; G1=OR(A,B)=1, G2=AND(C,D)=0, G3=NOT(N1)=0, G4=OR(N3,N2)=0!
        # Wait: flip A->0: OR(0,1)=1 (Q=0). flip B->0: OR(1,0)=1 (Q=0). flip D->0: AND(0,0)=0 (Q=0). flip C->1: AND(1,1)=1 -> Q=1! UNIQUE!
        inputs = {"A": 1, "B": 1, "C": 0, "D": 1}
        gates = [
            {"id": "G1", "op": "OR", "in1": "A", "in2": "B", "out": "N1", "col": 1, "row": 0},
            {"id": "G2", "op": "AND", "in1": "C", "in2": "D", "out": "N2", "col": 1, "row": 1},
            {"id": "G3", "op": "NOT", "in1": "N1", "in2": None, "out": "N3", "col": 2, "row": 0},
            {"id": "G4", "op": "OR", "in1": "N3", "in2": "N2", "out": "Q", "col": 3, "row": 0},
        ]
        return {
            "subtype": "boolean_logic_circuit",
            "difficulty": difficulty.value,
            "reasoning_type": "circuit_fault_sensitivity",
            "theme_name": "schematic_clean",
            "inputs": inputs,
            "gates": gates,
            "base_q": 0,
            "sensitive_pin": "C",
            "question": (
                "In this logic schematic, which SINGLE input pin (A, B, C, or D), if flipped alone "
                "(0->1 or 1->0) while all other inputs remain unchanged, changes the final output Q?"
            ),
        }

    def _gen_flow_spec(self, rng: random.Random, difficulty: Difficulty) -> dict[str, Any]:
        # Fixed clean DAG coordinates with variable costs and OPEN/BLOCKED statuses
        nodes = [
            {"id": "S", "x": 110, "y": 350},
            {"id": "M1", "x": 420, "y": 185},
            {"id": "M2", "x": 420, "y": 515},
            {"id": "N1", "x": 740, "y": 185},
            {"id": "N2", "x": 740, "y": 515},
            {"id": "T", "x": 1030, "y": 350},
        ]
        edge_defs = [
            ("S", "M1"),
            ("S", "M2"),
            ("M1", "N1"),
            ("M1", "N2"),
            ("M2", "N1"),
            ("M2", "N2"),
            ("N1", "T"),
            ("N2", "T"),
        ]

        for _ in range(100):
            edges = []
            for idx, (u, v) in enumerate(edge_defs):
                edges.append(
                    {
                        "id": f"E_{u}_{v}",
                        "u": u,
                        "v": v,
                        "cost": rng.randint(3, 18),
                        "open": rng.random() > 0.28,
                    }
                )
            # Ensure at least one open path and distinct shortest vs second-shortest cost
            paths = self._all_open_paths(edges)
            if len(paths) >= 2:
                paths.sort(key=lambda p: p[0])
                if paths[0][0] < paths[1][0]:
                    return {
                        "subtype": "directed_flow_network",
                        "difficulty": difficulty.value,
                        "reasoning_type": "constrained_shortest_path",
                        "theme_name": "network_diagram",
                        "nodes": nodes,
                        "edges": edges,
                        "question": (
                            "In this directed routing diagram, green solid arrows are OPEN and red dashed arrows "
                            "are BLOCKED. What is the minimum total cost to travel from node S to node T using ONLY OPEN arrows?"
                        ),
                    }

        # Deterministic safe fallback
        edges = [
            {"id": "E_S_M1", "u": "S", "v": "M1", "cost": 6, "open": True},
            {"id": "E_S_M2", "u": "S", "v": "M2", "cost": 4, "open": True},
            {"id": "E_M1_N1", "u": "M1", "v": "N1", "cost": 5, "open": True},
            {"id": "E_M1_N2", "u": "M1", "v": "N2", "cost": 9, "open": True},
            {"id": "E_M2_N1", "u": "M2", "v": "N1", "cost": 3, "open": False},
            {"id": "E_M2_N2", "u": "M2", "v": "N2", "cost": 8, "open": True},
            {"id": "E_N1_T", "u": "N1", "v": "T", "cost": 4, "open": True},
            {"id": "E_N2_T", "u": "N2", "v": "T", "cost": 6, "open": True},
        ]
        return {
            "subtype": "directed_flow_network",
            "difficulty": difficulty.value,
            "reasoning_type": "constrained_shortest_path",
            "theme_name": "network_diagram",
            "nodes": nodes,
            "edges": edges,
            "question": (
                "In this directed routing diagram, green solid arrows are OPEN and red dashed arrows "
                "are BLOCKED. What is the minimum total cost to travel from node S to node T using ONLY OPEN arrows?"
            ),
        }

    def _all_open_paths(self, edges: list[dict[str, Any]]) -> list[tuple[int, list[str]]]:
        adj: dict[str, list[tuple[str, int]]] = {}
        for e in edges:
            if e["open"]:
                adj.setdefault(e["u"], []).append((e["v"], int(e["cost"])))
        out: list[tuple[int, list[str]]] = []

        def dfs(curr: str, cost: int, path: list[str]) -> None:
            if curr == "T":
                out.append((cost, list(path)))
                return
            for nxt, w in adj.get(curr, []):
                dfs(nxt, cost + w, path + [nxt])

        dfs("S", 0, ["S"])
        return out

    def render_spec(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        if spec["subtype"] == "boolean_logic_circuit":
            return self._render_circuit(spec, out_path)
        return self._render_flow(spec, out_path)

    def _render_circuit(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        w, h = 1160, 700
        img = Image.new("RGB", (w, h), "#F8FAFC")
        draw = ImageDraw.Draw(img)
        title_font = get_font(22, bold=True)
        pin_font = get_font(18, bold=True, mono=True)
        gate_font = get_font(17, bold=True)
        lbl_font = get_font(13, bold=True)

        elements: list[SceneElement] = []
        title = "Digital Logic Schematic"
        draw.text((40, 24), title, fill="#0F172A", font=title_font)
        elements.append(
            SceneElement(
                id="title",
                kind="title",
                label=title,
                bbox=measure_text_bbox(draw, (40, 24), title, title_font),
                font_px=22.0,
                is_queried_text=True,
            )
        )

        inputs: dict[str, int] = spec["inputs"]
        gates: list[dict[str, Any]] = spec["gates"]
        pin_names = list(inputs.keys())

        # Compute clean grid positions
        pin_y_map = (
            {pin_names[0]: 175, pin_names[1]: 315, pin_names[2]: 495}
            if len(pin_names) == 3
            else {"A": 150, "B": 265, "C": 435, "D": 550}
        )
        pin_out_xy: dict[str, tuple[float, float]] = {}

        for p, val in inputs.items():
            px0, py0, px1, py1 = 64, pin_y_map[p] - 26, 174, pin_y_map[p] + 26
            fill = "#DBEAFE" if val == 1 else "#E2E8F0"
            edge = "#1D4ED8" if val == 1 else "#475569"
            draw.rounded_rectangle([px0, py0, px1, py1], radius=8, fill=fill, outline=edge, width=2)
            txt = f"{p} = {val}"
            draw.text(((px0 + px1) / 2, (py0 + py1) / 2), txt, fill="#0F172A", font=pin_font, anchor="mm")
            pin_out_xy[p] = (float(px1), float((py0 + py1) / 2))
            elements.append(
                SceneElement(
                    id=f"pin_{p}",
                    kind="input_pin",
                    label=txt,
                    bbox=(float(px0), float(py0), float(px1), float(py1)),
                    font_px=18.0,
                    is_queried_text=True,
                    attributes={"pin": p, "value": val},
                )
            )

        max_col = max(g["col"] for g in gates)
        col_x = {1: 350, 2: 610, 3: 845}
        row_y_2 = {0: 235, 1: 495}
        gate_w, gate_h = 128, 84

        for g_idx, g in enumerate(gates):
            gx = col_x[g["col"]]
            if g["col"] == max_col:
                gy = 350
            elif len([x for x in gates if x["col"] == g["col"]]) == 1:
                gy = 235
            else:
                gy = row_y_2[g["row"]]

            gx0, gy0, gx1, gy1 = gx, gy - gate_h / 2, gx + gate_w, gy + gate_h / 2
            in1_xy = (float(gx0), float(gy - 18 if g.get("in2") else gy))
            in2_xy = (float(gx0), float(gy + 18)) if g.get("in2") else None
            out_xy = (float(gx1), float(gy))

            # Draw wires from sources with staggered x_mid tracks so wires never overlap
            src1 = pin_out_xy[g["in1"]]
            mid_x1 = src1[0] + (in1_xy[0] - src1[0]) * (0.42 + 0.1 * (g_idx % 3))
            self._draw_orthogonal_wire(draw, src1, in1_xy, mid_x1, "#334155")
            if in2_xy is not None and g.get("in2"):
                src2 = pin_out_xy[g["in2"]]
                mid_x2 = src2[0] + (in2_xy[0] - src2[0]) * (0.62 - 0.08 * (g_idx % 2))
                self._draw_orthogonal_wire(draw, src2, in2_xy, mid_x2, "#334155")

            # Draw gate box with unmistakable label
            gate_fill = "#FEF3C7" if g["op"] == "NOT" else "#ECFDF5"
            gate_outline = "#B45309" if g["op"] == "NOT" else "#047857"
            draw.rounded_rectangle([gx0, gy0, gx1, gy1], radius=12, fill=gate_fill, outline=gate_outline, width=3)
            draw.text(((gx0 + gx1) / 2, (gy0 + gy1) / 2 - 8), g["op"], fill="#0F172A", font=gate_font, anchor="mm")
            draw.text(((gx0 + gx1) / 2, (gy0 + gy1) / 2 + 16), g["id"], fill="#475569", font=lbl_font, anchor="mm")

            # Output wire label
            pin_out_xy[g["out"]] = out_xy
            if g["out"] != "Q":
                draw.text((gx1 + 10, gy - 16), g["out"], fill="#334155", font=lbl_font)

            elements.append(
                SceneElement(
                    id=g["id"],
                    kind="logic_gate",
                    label=f"{g['id']}:{g['op']}",
                    bbox=(float(gx0), float(gy0), float(gx1), float(gy1)),
                    font_px=17.0,
                    is_queried_text=True,
                    attributes=g,
                )
            )

        # Output pin Q
        q_src = pin_out_xy["Q"]
        qx0, qy0, qx1, qy1 = 1025, q_src[1] - 28, 1105, q_src[1] + 28
        draw.line([q_src, (float(qx0), q_src[1])], fill="#0F172A", width=3)
        draw.rounded_rectangle([qx0, qy0, qx1, qy1], radius=10, fill="#EDE9FE", outline="#6D28D9", width=3)
        draw.text(((qx0 + qx1) / 2, (qy0 + qy1) / 2), "Q = ?", fill="#4C1D95", font=pin_font, anchor="mm")
        elements.append(
            SceneElement(
                id="pin_Q",
                kind="output_pin",
                label="Q",
                bbox=(float(qx0), float(qy0), float(qx1), float(qy1)),
                font_px=18.0,
                is_queried_text=True,
            )
        )

        img.save(out_path)
        return SceneManifest(width=w, height=h, elements=elements)

    def _draw_orthogonal_wire(
        self,
        draw: ImageDraw.ImageDraw,
        p1: tuple[float, float],
        p2: tuple[float, float],
        mid_x: float,
        color: str,
    ) -> None:
        draw.line([p1, (mid_x, p1[1]), (mid_x, p2[1]), p2], fill=color, width=3)
        r = 4
        draw.ellipse((p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r), fill=color)
        draw.ellipse((p2[0] - r, p2[1] - r, p2[0] + r, p2[1] + r), fill=color)

    def _render_flow(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        w, h = 1160, 700
        img = Image.new("RGB", (w, h), "#FFFFFF")
        draw = ImageDraw.Draw(img)
        title_font = get_font(22, bold=True)
        node_font = get_font(18, bold=True)
        cost_font = get_font(14, bold=True)

        elements: list[SceneElement] = []
        title = "Directed Process Flow Network (OPEN = Green Solid, BLOCKED = Red Dashed)"
        draw.text((36, 24), title, fill="#0F172A", font=title_font)
        elements.append(
            SceneElement(
                id="title",
                kind="title",
                label=title,
                bbox=measure_text_bbox(draw, (36, 24), title, title_font),
                font_px=22.0,
                is_queried_text=True,
            )
        )

        node_map = {n["id"]: n for n in spec["nodes"]}
        # Draw edges first
        for e in spec["edges"]:
            u, v = node_map[e["u"]], node_map[e["v"]]
            ux, uy, vx, vy = float(u["x"]), float(u["y"]), float(v["x"]), float(v["y"])
            dx, dy = vx - ux, vy - uy
            dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
            # Shorten start/end to node circle boundary (r=34)
            sx, sy = ux + 36 * dx / dist, uy + 36 * dy / dist
            ex, ey = vx - 38 * dx / dist, vy - 38 * dy / dist
            col = "#16A34A" if e["open"] else "#DC2626"

            if e["open"]:
                draw.line([(sx, sy), (ex, ey)], fill=col, width=4)
            else:
                # Dashed red line
                steps = 12
                for k in range(0, steps, 2):
                    p0 = (sx + (ex - sx) * k / steps, sy + (ey - sy) * k / steps)
                    p1 = (sx + (ex - sx) * (k + 1) / steps, sy + (ey - sy) * (k + 1) / steps)
                    draw.line([p0, p1], fill=col, width=3)

            # Arrowhead
            ang = 0.42
            ux_b, uy_b = -dx / dist, -dy / dist
            import math
            for sgn in (1, -1):
                ax = ex + 14 * (ux_b * math.cos(sgn * ang) - uy_b * math.sin(sgn * ang))
                ay = ey + 14 * (ux_b * math.sin(sgn * ang) + uy_b * math.cos(sgn * ang))
                draw.line([(ex, ey), (ax, ay)], fill=col, width=4)

            # Place edge cost pill shifted along edge to avoid center crossing overlap (M1->N2 vs M2->N1)
            t_pos = 0.34 if (e["u"], e["v"]) in {("M1", "N2"), ("M2", "N1")} else 0.5
            mx = sx + (ex - sx) * t_pos
            my = sy + (ey - sy) * t_pos
            lbl = f"{e['cost']}" if e["open"] else f"{e['cost']} X"
            pw, ph = 52 if not e["open"] else 38, 26
            pill = (mx - pw / 2, my - ph / 2, mx + pw / 2, my + ph / 2)
            draw.rounded_rectangle(pill, radius=6, fill="#DCFCE7" if e["open"] else "#FEE2E2", outline=col, width=2)
            draw.text((mx, my), lbl, fill="#0F172A", font=cost_font, anchor="mm")
            elements.append(
                SceneElement(
                    id=e["id"],
                    kind="edge",
                    label=f"{e['u']}->{e['v']}:{lbl}",
                    bbox=pill,
                    font_px=14.0,
                    is_queried_text=True,
                    attributes=e,
                )
            )

        # Draw nodes on top
        for n in spec["nodes"]:
            nx, ny, nr = float(n["x"]), float(n["y"]), 34.0
            n_fill = "#DBEAFE" if n["id"] in {"S", "T"} else "#F1F5F9"
            n_edge = "#1D4ED8" if n["id"] in {"S", "T"} else "#334155"
            bb = (nx - nr, ny - nr, nx + nr, ny + nr)
            draw.ellipse(bb, fill=n_fill, outline=n_edge, width=3)
            draw.text((nx, ny), n["id"], fill="#0F172A", font=node_font, anchor="mm")
            elements.append(
                SceneElement(
                    id=f"node_{n['id']}",
                    kind="node",
                    label=n["id"],
                    bbox=bb,
                    font_px=18.0,
                    is_queried_text=True,
                )
            )

        img.save(out_path)
        return SceneManifest(width=w, height=h, elements=elements)

    def solve_spec(
        self, spec: dict[str, Any]
    ) -> tuple[Any, AnswerType, float, str, list[str], list[str], list[str]]:
        if spec["subtype"] == "boolean_logic_circuit":
            inputs = spec["inputs"]
            gates = spec["gates"]
            sigs = _eval_circuit(inputs, gates)
            ref_ids = [f"pin_{p}" for p in inputs] + [g["id"] for g in gates] + ["pin_Q"]
            if spec["reasoning_type"] == "circuit_signal_tracing":
                trace = [f"Inputs: {inputs}", f"Signals propagated: {sigs}", f"Output Q = {sigs['Q']}."]
                return sigs["Q"], AnswerType.INTEGER, 0.0, "", ref_ids, ["pin_Q", gates[-1]["id"]], trace

            # circuit_fault_sensitivity
            base_q = sigs["Q"]
            hits = []
            for p in inputs:
                alt = dict(inputs)
                alt[p] = 1 - alt[p]
                if _eval_circuit(alt, gates)["Q"] != base_q:
                    hits.append(p)
            assert len(hits) == 1, f"Expected unique sensitive pin, got {hits}"
            trace = [
                f"Base signals: {sigs} (Q={base_q}).",
                f"Tested flipping each input pin independently; only pin '{hits[0]}' flips Q.",
            ]
            return hits[0], AnswerType.STRING, 0.0, "", ref_ids, [f"pin_{hits[0]}"], trace

        # directed_flow_network (Dijkstra)
        edges = spec["edges"]
        adj: dict[str, list[tuple[str, int, str]]] = {}
        for e in edges:
            if e["open"]:
                adj.setdefault(e["u"], []).append((e["v"], int(e["cost"]), e["id"]))
        pq: list[tuple[int, str, list[str]]] = [(0, "S", [])]
        best: dict[str, int] = {}
        win_edges: list[str] = []
        win_cost = -1
        while pq:
            cost, node, eids = heapq.heappop(pq)
            if node == "T":
                win_cost = cost
                win_edges = eids
                break
            if node in best and best[node] <= cost:
                continue
            best[node] = cost
            for nxt, w, eid in adj.get(node, []):
                heapq.heappush(pq, (cost + w, nxt, eids + [eid]))

        ref_ids = [f"node_{n['id']}" for n in spec["nodes"]] + [e["id"] for e in edges]
        trace = [
            f"Ran Dijkstra over {sum(1 for e in edges if e['open'])} OPEN edges.",
            f"Shortest open path uses {win_edges} with total cost = {win_cost}.",
        ]
        return win_cost, AnswerType.INTEGER, 0.0, "", ref_ids, win_edges, trace

    def make_counterfactual_spec(
        self, spec: dict[str, Any], seed: int
    ) -> tuple[dict[str, Any], str] | None:
        twin = copy.deepcopy(spec)
        if twin["subtype"] == "boolean_logic_circuit":
            if twin["reasoning_type"] == "circuit_signal_tracing":
                base_q = _eval_circuit(twin["inputs"], twin["gates"])["Q"]
                for p in twin["inputs"]:
                    alt = dict(twin["inputs"])
                    alt[p] = 1 - alt[p]
                    if _eval_circuit(alt, twin["gates"])["Q"] != base_q:
                        twin["inputs"] = alt
                        return twin, f"Flipped input pin {p} ({spec['inputs'][p]} -> {alt[p]}), changing Q."
                # If no single input flips Q, change final gate to NOT-or-XOR-flipped op
                last_g = twin["gates"][-1]
                alt_op = "NOR" if last_g["op"] in {"OR", "AND"} else "OR"
                last_g["op"] = alt_op
                if _eval_circuit(twin["inputs"], twin["gates"])["Q"] != base_q:
                    return twin, f"Changed final gate {last_g['id']} to {alt_op}, flipping Q."
                return None

            # sensitivity counterfactual: switch to a schematic where a different pin is uniquely sensitive
            if spec.get("sensitive_pin") != "A":
                twin["inputs"] = {"A": 0, "B": 1, "C": 1, "D": 1}
                twin["gates"] = [
                    {"id": "G1", "op": "AND", "in1": "A", "in2": "B", "out": "N1", "col": 1, "row": 0},
                    {"id": "G2", "op": "OR", "in1": "C", "in2": "D", "out": "N2", "col": 1, "row": 1},
                    {"id": "G3", "op": "NOT", "in1": "N1", "in2": None, "out": "N3", "col": 2, "row": 0},
                    {"id": "G4", "op": "AND", "in1": "N3", "in2": "N2", "out": "Q", "col": 3, "row": 0},
                ]
                twin["sensitive_pin"] = "A"
                return twin, "Updated schematic so pin A becomes the unique sensitive input."

            twin["inputs"] = {"A": 1, "B": 1, "C": 0, "D": 1}
            twin["gates"] = [
                {"id": "G1", "op": "OR", "in1": "A", "in2": "B", "out": "N1", "col": 1, "row": 0},
                {"id": "G2", "op": "AND", "in1": "C", "in2": "D", "out": "N2", "col": 1, "row": 1},
                {"id": "G3", "op": "NOT", "in1": "N1", "in2": None, "out": "N3", "col": 2, "row": 0},
                {"id": "G4", "op": "OR", "in1": "N3", "in2": "N2", "out": "Q", "col": 3, "row": 0},
            ]
            twin["sensitive_pin"] = "C"
            return twin, "Updated schematic so pin C becomes the unique sensitive input."

        # directed_flow_network: find shortest open path edges and boost or block one edge to change min cost
        _, _, _, _, _, win_edges, _ = self.solve_spec(spec)
        base_cost = self.solve_spec(spec)[0]
        for eid in win_edges:
            edge = next(e for e in twin["edges"] if e["id"] == eid)
            edge["open"] = False
            if self._all_open_paths(twin["edges"]):
                new_cost = self.solve_spec(twin)[0]
                if new_cost != base_cost:
                    return twin, f"Marked edge {eid} as BLOCKED, shifting minimum cost from {base_cost} to {new_cost}."
            edge["open"] = True
            edge["cost"] += 11
            new_cost = self.solve_spec(twin)[0]
            if new_cost != base_cost:
                return twin, f"Increased cost of edge {eid} by +11, changing minimum cost."
        return None
