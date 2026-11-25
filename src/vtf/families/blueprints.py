"""Family 5: Architectural Floorplan Blueprints & Analog Instrument Gauges."""

from __future__ import annotations

import copy
import math
import random
from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from vtf.families.base import VisualTaskFamily, measure_text_bbox
from vtf.fonts import get_font
from vtf.schema import AnswerType, Difficulty, FamilyName, SceneElement, SceneManifest

ROOMS = ["Lobby", "Study", "Kitchen", "Storage", "Server", "Lab"]
GAUGE_LABELS = [
    ("Pressure", "PSI"),
    ("Coolant", "C"),
    ("Voltage", "V"),
]


class BlueprintsGaugesTaskFamily(VisualTaskFamily):
    """Generates architectural room blueprints and analog needle gauge panels."""

    family_name = FamilyName.BLUEPRINTS_GAUGES

    def generate_spec(self, seed: int, difficulty: Difficulty) -> dict[str, Any]:
        rng = random.Random(seed)
        if difficulty == Difficulty.EASY:
            return self._gen_floorplan_spec(rng, difficulty, ask_hops=False)
        if difficulty == Difficulty.MEDIUM:
            if rng.choice([True, False]):
                return self._gen_floorplan_spec(rng, difficulty, ask_hops=True)
            return self._gen_gauge_spec(rng, difficulty, exact_reading=False)
        return self._gen_gauge_spec(rng, difficulty, exact_reading=True)

    def _gen_floorplan_spec(
        self, rng: random.Random, difficulty: Difficulty, *, ask_hops: bool
    ) -> dict[str, Any]:
        names = list(ROOMS)
        rng.shuffle(names)
        rooms = []
        for idx, name in enumerate(names):
            r, c = divmod(idx, 3)
            rooms.append(
                {
                    "id": f"room_{name}",
                    "name": name,
                    "row": r,
                    "col": c,
                    "w_m": rng.randint(3, 8),
                    "h_m": rng.randint(3, 7),
                }
            )

        # Adjacent pairs in 2x3 grid: 3 horizontal + 4 vertical walls (total 7 walls)
        walls = [
            ((0, 0), (0, 1)),
            ((0, 1), (0, 2)),
            ((1, 0), (1, 1)),
            ((1, 1), (1, 2)),
            ((0, 0), (1, 0)),
            ((0, 1), (1, 1)),
            ((0, 2), (1, 2)),
        ]
        # Ensure connected spanning doorways + extra doorway for variation
        doors = {}
        for w_pair in walls:
            doors[w_pair] = rng.random() > 0.42
        # Guarantee spanning connectivity via BFS; force doors open if disconnected
        if not self._is_connected(doors):
            doors[((0, 0), (0, 1))] = True
            doors[((0, 1), (0, 2))] = True
            doors[((0, 0), (1, 0))] = True
            doors[((1, 0), (1, 1))] = True
            doors[((1, 1), (1, 2))] = True

        door_list = [
            {"id": f"door_{a[0]}{a[1]}_{b[0]}{b[1]}", "a": list(a), "b": list(b), "open": is_open}
            for (a, b), is_open in doors.items()
        ]

        if not ask_hops:
            pair = rng.sample(rooms, 2)
            question = (
                f"On this architectural floorplan blueprint, what is the combined floor area "
                f"(in sq m) of {pair[0]['name']} and {pair[1]['name']}?"
            )
            return {
                "subtype": "architectural_floorplan",
                "difficulty": difficulty.value,
                "reasoning_type": "blueprint_area_sum",
                "theme_name": "blueprint_cad",
                "rooms": rooms,
                "doors": door_list,
                "target_rooms": [pair[0]["name"], pair[1]["name"]],
                "question": question,
            }

        # Find pair with >= 2 doorway hops if possible
        start_room, end_room = rooms[0], rooms[-1]
        best_dist = -1
        for r1 in rooms:
            for r2 in rooms:
                if r1["name"] == r2["name"]:
                    continue
                d = self._bfs_hops(door_list, (r1["row"], r1["col"]), (r2["row"], r2["col"]))
                if d is not None and d > best_dist:
                    best_dist = d
                    start_room, end_room = r1, r2
        question = (
            f"On this floorplan blueprint, curved quarter-circle arcs indicate OPEN doorways while solid lines "
            f"are walls. Starting inside {start_room['name']}, what is the minimum number of open doorways "
            f"you must cross to reach {end_room['name']}?"
        )
        return {
            "subtype": "architectural_floorplan",
            "difficulty": difficulty.value,
            "reasoning_type": "blueprint_door_hops",
            "theme_name": "blueprint_cad",
            "rooms": rooms,
            "doors": door_list,
            "start_room": start_room["name"],
            "end_room": end_room["name"],
            "question": question,
        }

    def _is_connected(self, doors: dict[tuple[tuple[int, int], tuple[int, int]], bool]) -> bool:
        adj: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for (a, b), open_flag in doors.items():
            if open_flag:
                adj.setdefault(a, []).append(b)
                adj.setdefault(b, []).append(a)
        seen = {(0, 0)}
        q = deque([(0, 0)])
        while q:
            cur = q.popleft()
            for nxt in adj.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        return len(seen) == 6

    def _bfs_hops(
        self, doors: list[dict[str, Any]], start: tuple[int, int], end: tuple[int, int]
    ) -> int | None:
        adj: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for d in doors:
            if d["open"]:
                a, b = tuple(d["a"]), tuple(d["b"])
                adj.setdefault(a, []).append(b)
                adj.setdefault(b, []).append(a)
        seen = {start}
        q = deque([(start, 0)])
        while q:
            cur, dist = q.popleft()
            if cur == end:
                return dist
            for nxt in adj.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt, dist + 1))
        return None

    def _gen_gauge_spec(
        self, rng: random.Random, difficulty: Difficulty, *, exact_reading: bool
    ) -> dict[str, Any]:
        gauges = []
        for idx, (label, unit) in enumerate(GAUGE_LABELS):
            # Pick multiples of 5 strictly avoiding [66..79] danger boundary unless >80 or <=65
            if not exact_reading:
                in_danger = rng.choice([True, False])
                val = rng.choice([80, 85, 90, 95]) if in_danger else rng.choice([15, 25, 35, 45, 55, 65])
            else:
                val = rng.choice([15, 25, 35, 45, 55, 65, 80, 90])
            gauges.append(
                {
                    "id": f"gauge_{label.lower()}",
                    "name": label,
                    "unit": unit,
                    "value": val,
                    "danger_min": 75,
                }
            )

        if not exact_reading:
            question = (
                "Inspect the 3 analog dial gauges (each spans 0 to 100 with a red danger arc starting at 75). "
                "How many gauges have their needle pointing strictly inside the red danger zone (>= 75)?"
            )
            return {
                "subtype": "analog_gauge_cluster",
                "difficulty": difficulty.value,
                "reasoning_type": "gauge_danger_zone_count",
                "theme_name": "industrial_panel",
                "gauges": gauges,
                "question": question,
            }

        target = rng.choice(gauges)
        question = (
            f"Read the analog needle position on the '{target['name']} ({target['unit']})' gauge "
            f"(scale 0 to 100, major ticks every 20, minor ticks every 5). What value is the needle pointing to?"
        )
        return {
            "subtype": "analog_gauge_cluster",
            "difficulty": difficulty.value,
            "reasoning_type": "analog_needle_reading",
            "theme_name": "industrial_panel",
            "gauges": gauges,
            "target_gauge": target["name"],
            "question": question,
        }

    def render_spec(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        if spec["subtype"] == "architectural_floorplan":
            return self._render_floorplan(spec, out_path)
        return self._render_gauges(spec, out_path)

    def _render_floorplan(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        w, h = 1120, 680
        img = Image.new("RGB", (w, h), "#EFF6FF")
        draw = ImageDraw.Draw(img)
        title_font = get_font(22, bold=True)
        room_font = get_font(18, bold=True)
        dim_font = get_font(15, bold=True, mono=True)
        note_font = get_font(13, bold=False)

        # Blueprint grid lines
        for gx in range(0, w, 40):
            draw.line([(gx, 0), (gx, h)], fill="#DBEAFE", width=1)
        for gy in range(0, h, 40):
            draw.line([(0, gy), (w, gy)], fill="#DBEAFE", width=1)

        title = "Architectural Floorplan Blueprint (Scale Dimensions & Doorways)"
        draw.text((48, 22), title, fill="#0F172A", font=title_font)
        draw.text((48, 52), "Solid dark line = sealed wall | Curved arc gap = open doorway", fill="#334155", font=note_font)

        elements: list[SceneElement] = [
            SceneElement(
                id="title",
                kind="title",
                label=title,
                bbox=measure_text_bbox(draw, (48, 22), title, title_font),
                font_px=22.0,
                is_queried_text=True,
            )
        ]

        x0, y0 = 90, 100
        rw, rh = 310, 255
        # Room fills + labels
        for rm in spec["rooms"]:
            rx0 = x0 + rm["col"] * rw
            ry0 = y0 + rm["row"] * rh
            rx1 = rx0 + rw
            ry1 = ry0 + rh
            draw.rectangle([rx0, ry0, rx1, ry1], fill="#FFFFFF")
            cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
            draw.text((cx, cy - 18), rm["name"].upper(), fill="#0F172A", font=room_font, anchor="mm")
            dim_txt = f"{rm['w_m']}m x {rm['h_m']}m"
            draw.text((cx, cy + 16), dim_txt, fill="#1D4ED8", font=dim_font, anchor="mm")
            elements.append(
                SceneElement(
                    id=rm["id"],
                    kind="room",
                    label=f"{rm['name']} {dim_txt}",
                    bbox=(float(rx0), float(ry0), float(rx1), float(ry1)),
                    font_px=15.0,
                    is_queried_text=True,
                    attributes=rm,
                )
            )

        # Outer perimeter walls
        draw.rectangle([x0, y0, x0 + 3 * rw, y0 + 2 * rh], outline="#0F172A", width=6)

        # Internal walls and doorways
        for d in spec["doors"]:
            r1, c1 = d["a"]
            r2, c2 = d["b"]
            if r1 == r2:  # Vertical shared wall between (r1, c1) and (r1, c2)
                wx = x0 + c2 * rw
                wy0 = y0 + r1 * rh
                wy1 = wy0 + rh
                if not d["open"]:
                    draw.line([(wx, wy0), (wx, wy1)], fill="#0F172A", width=6)
                    bb = (float(wx - 4), float(wy0), float(wx + 4), float(wy1))
                else:
                    mid_y = (wy0 + wy1) / 2
                    gap = 34
                    draw.line([(wx, wy0), (wx, mid_y - gap)], fill="#0F172A", width=6)
                    draw.line([(wx, mid_y + gap), (wx, wy1)], fill="#0F172A", width=6)
                    # Draw open door leaf + 90-degree swing arc
                    draw.line([(wx, mid_y - gap), (wx + gap * 1.4, mid_y - gap)], fill="#0284C7", width=3)
                    draw.arc(
                        [wx - gap * 1.4, mid_y - gap * 2.4, wx + gap * 1.4, mid_y + gap * 0.4],
                        start=0,
                        end=90,
                        fill="#0284C7",
                        width=3,
                    )
                    bb = (float(wx - 20), float(mid_y - gap), float(wx + gap * 1.4), float(mid_y + gap))
            else:  # Horizontal shared wall between (r1, c1) and (r2, c1)
                wy = y0 + r2 * rh
                wx0 = x0 + c1 * rw
                wx1 = wx0 + rw
                if not d["open"]:
                    draw.line([(wx0, wy), (wx1, wy)], fill="#0F172A", width=6)
                    bb = (float(wx0), float(wy - 4), float(wx1), float(wy + 4))
                else:
                    mid_x = (wx0 + wx1) / 2
                    gap = 34
                    draw.line([(wx0, wy), (mid_x - gap, wy)], fill="#0F172A", width=6)
                    draw.line([(mid_x + gap, wy), (wx1, wy)], fill="#0F172A", width=6)
                    draw.line([(mid_x - gap, wy), (mid_x - gap, wy + gap * 1.4)], fill="#0284C7", width=3)
                    draw.arc(
                        [mid_x - gap * 2.4, wy - gap * 1.4, mid_x + gap * 0.4, wy + gap * 1.4],
                        start=0,
                        end=90,
                        fill="#0284C7",
                        width=3,
                    )
                    bb = (float(mid_x - gap), float(wy - 20), float(mid_x + gap), float(wy + gap * 1.4))

            elements.append(
                SceneElement(
                    id=d["id"],
                    kind="doorway",
                    label=f"open={d['open']}",
                    bbox=bb,
                    attributes=d,
                )
            )

        img.save(out_path)
        return SceneManifest(width=w, height=h, elements=elements)

    def _render_gauges(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        w, h = 1140, 660
        img = Image.new("RGB", (w, h), "#0F172A")
        draw = ImageDraw.Draw(img)
        title_font = get_font(23, bold=True)
        lbl_font = get_font(18, bold=True)
        tick_font = get_font(13, bold=True)
        sub_font = get_font(13, bold=False)

        title = "Industrial Instrument Panel — Analog Dial Gauges (0–100 Scale)"
        draw.text((44, 24), title, fill="#F8FAFC", font=title_font)
        draw.text((44, 56), "Major ticks = 20 units | Minor ticks = 5 units | Red arc = danger zone (75–100)", fill="#94A3B8", font=sub_font)

        elements: list[SceneElement] = [
            SceneElement(
                id="title",
                kind="title",
                label=title,
                bbox=measure_text_bbox(draw, (44, 24), title, title_font),
                font_px=23.0,
                is_queried_text=True,
            )
        ]

        centers = [(210, 345), (570, 345), (930, 345)]
        radius = 148
        # Value v in [0, 100] maps to angle from 150 deg (bottom-left) clockwise to 390 deg (bottom-right)
        # In Pillow image coords (y down, angle 0 = +x, 90 = +y down):
        # 135 deg is bottom-left! Sweeping clockwise across top (270 deg) to 405 deg (bottom-right) = 270 deg total!
        start_deg = 135.0
        sweep_deg = 270.0

        for g, (cx, cy) in zip(spec["gauges"], centers):
            # Panel bezel
            draw.ellipse([cx - radius - 14, cy - radius - 14, cx + radius + 14, cy + radius + 14], fill="#1E293B", outline="#475569", width=4)
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill="#FFFFFF", outline="#0F172A", width=3)

            # Danger arc [75, 100] -> angles
            a_danger0 = start_deg + (75.0 / 100.0) * sweep_deg
            a_danger1 = start_deg + sweep_deg
            arc_r = radius - 14
            draw.arc(
                [cx - arc_r, cy - arc_r, cx + arc_r, cy + arc_r],
                start=a_danger0,
                end=a_danger1,
                fill="#DC2626",
                width=12,
            )

            # Ticks every 5 units; labels every 20
            for val in range(0, 101, 5):
                ang = math.radians(start_deg + (val / 100.0) * sweep_deg)
                is_major = val % 20 == 0
                is_ten = val % 10 == 0
                r_out = radius - 8
                r_in = radius - (26 if is_major else (19 if is_ten else 14))
                x_out, y_out = cx + r_out * math.cos(ang), cy + r_out * math.sin(ang)
                x_in, y_in = cx + r_in * math.cos(ang), cy + r_in * math.sin(ang)
                draw.line([(x_in, y_in), (x_out, y_out)], fill="#0F172A", width=3 if is_major else 2)
                if is_major:
                    r_txt = radius - 42
                    tx, ty = cx + r_txt * math.cos(ang), cy + r_txt * math.sin(ang)
                    draw.text((tx, ty), str(val), fill="#0F172A", font=tick_font, anchor="mm")

            # Needle pointing strictly at g["value"]
            n_ang = math.radians(start_deg + (float(g["value"]) / 100.0) * sweep_deg)
            nx, ny = cx + (radius - 32) * math.cos(n_ang), cy + (radius - 32) * math.sin(n_ang)
            bx, by = cx - 22 * math.cos(n_ang), cy - 22 * math.sin(n_ang)
            draw.line([(bx, by), (nx, ny)], fill="#DC2626", width=5)
            draw.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill="#0F172A", outline="#F8FAFC", width=2)

            # Gauge title badge below dial
            cap = f"{g['name']} ({g['unit']})"
            draw.text((cx, cy + radius + 42), cap, fill="#F8FAFC", font=lbl_font, anchor="mm")

            elements.append(
                SceneElement(
                    id=g["id"],
                    kind="analog_gauge",
                    label=f"{cap}={g['value']}",
                    bbox=(float(cx - radius - 14), float(cy - radius - 14), float(cx + radius + 14), float(cy + radius + 58)),
                    font_px=18.0,
                    is_queried_text=True,
                    attributes=g,
                )
            )

        img.save(out_path)
        return SceneManifest(width=w, height=h, elements=elements)

    def solve_spec(
        self, spec: dict[str, Any]
    ) -> tuple[Any, AnswerType, float, str, list[str], list[str], list[str]]:
        if spec["subtype"] == "architectural_floorplan":
            rooms = spec["rooms"]
            if spec["reasoning_type"] == "blueprint_area_sum":
                t_names = spec["target_rooms"]
                picked = [r for r in rooms if r["name"] in t_names]
                areas = [int(r["w_m"]) * int(r["h_m"]) for r in picked]
                total = sum(areas)
                ref_ids = [r["id"] for r in picked]
                trace = [
                    f"Read room dimensions: {[(r['name'], r['w_m'], r['h_m']) for r in picked]}.",
                    f"Computed areas {areas} -> sum = {total} sq m.",
                ]
                return total, AnswerType.INTEGER, 0.0, "sq m", ref_ids, ref_ids, trace

            r_start = next(r for r in rooms if r["name"] == spec["start_room"])
            r_end = next(r for r in rooms if r["name"] == spec["end_room"])
            hops = self._bfs_hops(spec["doors"], (r_start["row"], r_start["col"]), (r_end["row"], r_end["col"]))
            assert hops is not None
            ref_ids = [r_start["id"], r_end["id"]] + [d["id"] for d in spec["doors"]]
            ev_ids = [r_start["id"], r_end["id"]]
            trace = [
                f"Found open doorway path from {r_start['name']} to {r_end['name']}.",
                f"Minimum doorways crossed = {hops}.",
            ]
            return hops, AnswerType.INTEGER, 0.0, "", ref_ids, ev_ids, trace

        gauges = spec["gauges"]
        if spec["reasoning_type"] == "gauge_danger_zone_count":
            hits = [g for g in gauges if int(g["value"]) >= int(g["danger_min"])]
            ref_ids = [g["id"] for g in gauges]
            ev_ids = [g["id"] for g in hits]
            trace = [
                f"Gauge values: {[(g['name'], g['value']) for g in gauges]} (danger >= 75).",
                f"In danger zone: {[g['name'] for g in hits]} -> count={len(hits)}.",
            ]
            return len(hits), AnswerType.INTEGER, 0.0, "", ref_ids, ev_ids, trace

        target = next(g for g in gauges if g["name"] == spec["target_gauge"])
        val = int(target["value"])
        trace = [f"Located analog needle on {target['name']} dial at {val} {target['unit']}."]
        return val, AnswerType.INTEGER, 4.0, target["unit"], [target["id"]], [target["id"]], trace

    def make_counterfactual_spec(
        self, spec: dict[str, Any], seed: int
    ) -> tuple[dict[str, Any], str] | None:
        twin = copy.deepcopy(spec)
        if twin["subtype"] == "architectural_floorplan":
            if twin["reasoning_type"] == "blueprint_area_sum":
                t_name = twin["target_rooms"][0]
                rm = next(r for r in twin["rooms"] if r["name"] == t_name)
                rm["w_m"] += 2
                return twin, f"Increased width of {t_name} by +2m."

            # blueprint_door_hops: find minimal-Hamming doorway edit shifting shortest hops while staying connected
            r_start = next(r for r in twin["rooms"] if r["name"] == twin["start_room"])
            r_end = next(r for r in twin["rooms"] if r["name"] == twin["end_room"])
            s_rc, e_rc = (r_start["row"], r_start["col"]), (r_end["row"], r_end["col"])
            doors_list = twin["doors"]
            base_hops = self._bfs_hops(doors_list, s_rc, e_rc)
            n_doors = len(doors_list)
            orig_states = [bool(d["open"]) for d in doors_list]
            # Sort all 2^7 masks by Hamming distance (1 flip, then 2 flips, etc.)
            masks = sorted(range(1, 1 << n_doors), key=lambda m: m.bit_count())
            for mask in masks:
                for idx in range(n_doors):
                    doors_list[idx]["open"] = (not orig_states[idx]) if (mask & (1 << idx)) else orig_states[idx]
                new_hops = self._bfs_hops(doors_list, s_rc, e_rc)
                if new_hops is not None and new_hops != base_hops:
                    changed_ids = [doors_list[i]["id"] for i in range(n_doors) if mask & (1 << i)]
                    return twin, (
                        f"Modified doorway(s) {', '.join(changed_ids)}, shifting shortest hops "
                        f"from {base_hops} to {new_hops}."
                    )
            for idx in range(n_doors):
                doors_list[idx]["open"] = orig_states[idx]
            return None

        gauges = twin["gauges"]
        if twin["reasoning_type"] == "gauge_danger_zone_count":
            g = gauges[0]
            if g["value"] >= 75:
                g["value"] = 45
                return twin, f"Moved {g['name']} needle out of danger zone ({spec['gauges'][0]['value']} -> 45)."
            g["value"] = 85
            return twin, f"Moved {g['name']} needle into danger zone ({spec['gauges'][0]['value']} -> 85)."

        g = next(x for x in gauges if x["name"] == twin["target_gauge"])
        old_v = g["value"]
        g["value"] = old_v + 25 if old_v <= 65 else old_v - 30
        return twin, f"Rotated {g['name']} needle from {old_v} to {g['value']}."
