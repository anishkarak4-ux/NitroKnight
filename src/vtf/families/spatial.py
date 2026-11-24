"""Family 2: Warehouse Inventory Racks & Compositional Spatial Scenes (CLEVR-inspired)."""

from __future__ import annotations

import copy
import math
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from vtf.families.base import VisualTaskFamily, measure_text_bbox
from vtf.fonts import get_font
from vtf.schema import AnswerType, Difficulty, FamilyName, SceneElement, SceneManifest

COLORS = {
    "Red": "#DC2626",
    "Blue": "#2563EB",
    "Green": "#16A34A",
    "Amber": "#D97706",
    "Purple": "#7C3AED",
}
ITEM_TYPES = ["CPU", "SENSOR", "BATTERY", "VALVE", "OPTIC"]
TAGS = ["OK", "FRAGILE", "HOLD", "RUSH"]
SHAPES = ["circle", "square", "triangle", "diamond", "hexagon"]
PATTERNS = ["solid", "ringed", "striped"]


class SpatialInventoryTaskFamily(VisualTaskFamily):
    """Generates warehouse shelf racks and compositional geometric visual scenes."""

    family_name = FamilyName.SPATIAL_INVENTORY

    def generate_spec(self, seed: int, difficulty: Difficulty) -> dict[str, Any]:
        rng = random.Random(seed)
        if difficulty == Difficulty.EASY:
            return self._gen_warehouse_spec(rng, difficulty, ask_mode="filtered_count")
        if difficulty == Difficulty.MEDIUM:
            mode = rng.choice(["inventory_sum", "neighbor_lookup"])
            return self._gen_warehouse_spec(rng, difficulty, ask_mode=mode)
        # HARD: CLEVR-style compositional geometric scene (spatial relation or occlusion)
        mode = rng.choice(["spatial_relation", "occlusion_front"])
        return self._gen_geometric_spec(rng, difficulty, ask_mode=mode)

    def _gen_warehouse_spec(
        self, rng: random.Random, difficulty: Difficulty, *, ask_mode: str
    ) -> dict[str, Any]:
        shelves = ["Top", "Middle", "Bottom"]
        n_cols = 4 if difficulty == Difficulty.EASY else 5
        crates: list[dict[str, Any]] = []

        for r_idx, shelf in enumerate(shelves):
            for c_idx in range(n_cols):
                # Leave occasional empty slot unless neighbor lookup needs dense placement
                if ask_mode != "neighbor_lookup" and rng.random() < 0.15:
                    continue
                crates.append(
                    {
                        "id": f"crate_{shelf}_{c_idx}",
                        "shelf": shelf,
                        "row": r_idx,
                        "col": c_idx,
                        "color": rng.choice(list(COLORS.keys())),
                        "item": rng.choice(ITEM_TYPES),
                        "tag": rng.choice(TAGS),
                        "units": rng.randint(4, 24),
                    }
                )

        if ask_mode == "filtered_count":
            target_shelf = rng.choice(shelves)
            target_tag = rng.choice(["FRAGILE", "HOLD", "RUSH"])
            # Ensure at least 1 matching crate
            shelf_crates = [c for c in crates if c["shelf"] == target_shelf]
            if not any(c["tag"] == target_tag for c in shelf_crates) and shelf_crates:
                shelf_crates[0]["tag"] = target_tag
            question = (
                f"In this warehouse rack, how many crates on the {target_shelf} shelf "
                f"carry the '{target_tag}' tag?"
            )
            return {
                "subtype": "warehouse_rack",
                "difficulty": difficulty.value,
                "reasoning_type": "filtered_count",
                "theme_name": "warehouse_grid",
                "shelves": shelves,
                "n_cols": n_cols,
                "crates": crates,
                "target_shelf": target_shelf,
                "target_tag": target_tag,
                "question": question,
            }

        if ask_mode == "inventory_sum":
            target_color = rng.choice(["Red", "Blue", "Green", "Amber"])
            # Ensure at least 2 crates of target_color
            matching = [c for c in crates if c["color"] == target_color]
            while len(matching) < 2:
                pick = rng.choice(crates)
                pick["color"] = target_color
                matching = [c for c in crates if c["color"] == target_color]
            question = (
                f"What is the total number of units across all {target_color} crates "
                f"on the rack?"
            )
            return {
                "subtype": "warehouse_rack",
                "difficulty": difficulty.value,
                "reasoning_type": "filtered_inventory_sum",
                "theme_name": "warehouse_grid",
                "shelves": shelves,
                "n_cols": n_cols,
                "crates": crates,
                "target_color": target_color,
                "question": question,
            }

        # neighbor_lookup: unique anchor crate (color + tag) with a neighbor strictly to its right
        anchor_shelf = rng.choice(shelves)
        anchor_col = rng.randint(0, n_cols - 2)
        anchor = next(c for c in crates if c["shelf"] == anchor_shelf and c["col"] == anchor_col)
        right_nb = next(c for c in crates if c["shelf"] == anchor_shelf and c["col"] == anchor_col + 1)
        # Guarantee anchor (color + tag) is globally unique on the rack
        for c in crates:
            if c["id"] != anchor["id"] and c["color"] == anchor["color"] and c["tag"] == anchor["tag"]:
                c["tag"] = "OK" if anchor["tag"] != "OK" else "RUSH"
        # Ensure neighbor item differs slightly from anchor just for clarity
        if right_nb["item"] == anchor["item"]:
            right_nb["item"] = next(it for it in ITEM_TYPES if it != anchor["item"])
        question = (
            f"On the warehouse rack, what item type is stored in the crate immediately "
            f"to the right of the unique {anchor['color']} {anchor['tag']} crate?"
        )
        return {
            "subtype": "warehouse_rack",
            "difficulty": difficulty.value,
            "reasoning_type": "spatial_neighbor_lookup",
            "theme_name": "warehouse_grid",
            "shelves": shelves,
            "n_cols": n_cols,
            "crates": crates,
            "anchor_id": anchor["id"],
            "neighbor_id": right_nb["id"],
            "question": question,
        }

    def _gen_geometric_spec(
        self, rng: random.Random, difficulty: Difficulty, *, ask_mode: str
    ) -> dict[str, Any]:
        # 2 rows x 4 cols layout (with optional controlled overlap pair for occlusion)
        objects: list[dict[str, Any]] = []
        cols = 4
        rows = 2
        w, h = 1120, 680
        x_step = 230
        y_centers = [235, 475]
        x_start = 205

        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                objects.append(
                    {
                        "id": f"obj_{idx}",
                        "row": r,
                        "col": c,
                        "cx": x_start + c * x_step + rng.randint(-14, 14),
                        "cy": y_centers[r] + rng.randint(-12, 12),
                        "radius": rng.choice([46, 66]),
                        "shape": rng.choice(SHAPES),
                        "color": rng.choice(list(COLORS.keys())),
                        "pattern": rng.choice(PATTERNS),
                        "z": idx,
                    }
                )

        if ask_mode == "spatial_relation":
            row = rng.choice([0, 1])
            col = rng.randint(0, 2)
            anchor = next(o for o in objects if o["row"] == row and o["col"] == col)
            target = next(o for o in objects if o["row"] == row and o["col"] == col + 1)
            # Ensure anchor's (color, shape, pattern) signature is globally unique
            for o in objects:
                if o["id"] != anchor["id"] and (
                    o["color"] == anchor["color"]
                    and o["shape"] == anchor["shape"]
                    and o["pattern"] == anchor["pattern"]
                ):
                    o["color"] = next(col_n for col_n in COLORS if col_n != anchor["color"])
            # Ensure target color differs from anchor color so question never leaks the answer color
            if target["color"] == anchor["color"]:
                target["color"] = next(col_n for col_n in COLORS if col_n != anchor["color"])
            anchor["cy"] = y_centers[row]
            target["cy"] = y_centers[row]
            size_word = "large" if anchor["radius"] > 55 else "small"
            # Also guarantee no ambiguity on size if needed by ensuring unique (color, shape, pattern)
            question = (
                f"What color is the object immediately to the right of the "
                f"{anchor['pattern']} {anchor['color'].lower()} {anchor['shape']}?"
            )
            return {
                "subtype": "geometric_constellation",
                "difficulty": difficulty.value,
                "reasoning_type": "compositional_spatial_relation",
                "theme_name": "clevr_2d",
                "width": w,
                "height": h,
                "objects": objects,
                "anchor_id": anchor["id"],
                "target_id": target["id"],
                "question": question,
            }

        # occlusion_front: two shapes explicitly overlap (~25%) with distinct colors
        back_obj = objects[2]
        front_obj = objects[3]
        back_obj["cx"] = 670
        back_obj["cy"] = 250
        back_obj["radius"] = 64
        front_obj["cx"] = 740
        front_obj["cy"] = 275
        front_obj["radius"] = 64
        front_obj["pattern"] = "solid"
        back_obj["pattern"] = "solid"
        if front_obj["color"] == back_obj["color"]:
            front_obj["color"] = next(c for c in COLORS if c != back_obj["color"])
        # Ensure z order puts front_obj strictly after back_obj
        back_obj["z"] = 10
        front_obj["z"] = 20
        # Move other objects clear of the overlap cluster
        objects[6]["cy"] = 505
        objects[7]["cy"] = 505
        question = (
            f"In the overlapping pair in the upper-right region ({back_obj['color']} vs "
            f"{front_obj['color']}), which color shape is positioned in front?"
        )
        return {
            "subtype": "geometric_constellation",
            "difficulty": difficulty.value,
            "reasoning_type": "occlusion_depth_ordering",
            "theme_name": "clevr_2d",
            "width": w,
            "height": h,
            "objects": objects,
            "back_id": back_obj["id"],
            "front_id": front_obj["id"],
            "question": question,
        }

    def render_spec(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        if spec["subtype"] == "warehouse_rack":
            return self._render_warehouse(spec, out_path)
        return self._render_geometric(spec, out_path)

    def _render_warehouse(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        w, h = 1120, 680
        img = Image.new("RGB", (w, h), "#F1F5F9")
        draw = ImageDraw.Draw(img)
        title_font = get_font(24, bold=True)
        shelf_font = get_font(18, bold=True)
        item_font = get_font(17, bold=True)
        meta_font = get_font(14, bold=False)
        tag_font = get_font(12, bold=True)

        elements: list[SceneElement] = []
        title_text = "Warehouse Storage Bay — Live Inventory Snapshot"
        draw.text((40, 26), title_text, fill="#0F172A", font=title_font)
        elements.append(
            SceneElement(
                id="title",
                kind="title",
                label=title_text,
                bbox=measure_text_bbox(draw, (40, 26), title_text, title_font),
                font_px=24.0,
                is_queried_text=True,
            )
        )

        shelves: list[str] = spec["shelves"]
        n_cols: int = spec["n_cols"]
        rack_x0, rack_y0, rack_x1, rack_y1 = 150, 88, 1080, 635
        draw.rounded_rectangle([rack_x0, rack_y0, rack_x1, rack_y1], radius=12, fill="#E2E8F0", outline="#475569", width=3)

        shelf_h = (rack_y1 - rack_y0) / len(shelves)
        col_w = (rack_x1 - rack_x0 - 24) / n_cols

        for r_idx, shelf_name in enumerate(shelves):
            sy0 = rack_y0 + r_idx * shelf_h
            sy1 = sy0 + shelf_h
            # Shelf beam
            draw.rectangle([rack_x0, sy1 - 12, rack_x1, sy1], fill="#334155")
            # Shelf label on left
            draw.text((42, sy0 + shelf_h * 0.42), shelf_name, fill="#1E293B", font=shelf_font)
            elements.append(
                SceneElement(
                    id=f"shelf_{shelf_name}",
                    kind="shelf_label",
                    label=shelf_name,
                    bbox=measure_text_bbox(draw, (42, sy0 + shelf_h * 0.42), shelf_name, shelf_font),
                    font_px=18.0,
                    is_queried_text=True,
                )
            )

        crate_map = {(c["row"], c["col"]): c for c in spec["crates"]}
        for r_idx in range(len(shelves)):
            sy0 = rack_y0 + r_idx * shelf_h
            sy1 = sy0 + shelf_h - 14
            for c_idx in range(n_cols):
                cx0 = rack_x0 + 12 + c_idx * col_w + 8
                cx1 = cx0 + col_w - 16
                cy0 = sy0 + 16
                cy1 = sy1 - 6
                crate = crate_map.get((r_idx, c_idx))
                if crate is None:
                    draw.rounded_rectangle([cx0, cy0, cx1, cy1], radius=8, outline="#94A3B8", width=2)
                    draw.text(((cx0 + cx1) / 2, (cy0 + cy1) / 2), "EMPTY", fill="#64748B", font=meta_font, anchor="mm")
                    continue

                hex_col = COLORS[crate["color"]]
                draw.rounded_rectangle([cx0, cy0, cx1, cy1], radius=10, fill=hex_col, outline="#0F172A", width=2)
                # Inner crisp white card for text readability
                pad = 10
                draw.rounded_rectangle(
                    [cx0 + pad, cy0 + 28, cx1 - pad, cy1 - pad],
                    radius=6,
                    fill="#FFFFFF",
                    outline="#1E293B",
                    width=1,
                )
                # Top color label + tag badge
                draw.text((cx0 + 12, cy0 + 7), crate["color"].upper(), fill="#FFFFFF", font=tag_font)
                tag_bg = "#FEF08A" if crate["tag"] in {"FRAGILE", "RUSH"} else ("#FECACA" if crate["tag"] == "HOLD" else "#DCFCE7")
                tag_fg = "#0F172A"
                tb_x0, tb_y0, tb_x1, tb_y1 = cx1 - 74, cy0 + 5, cx1 - 8, cy0 + 23
                draw.rounded_rectangle([tb_x0, tb_y0, tb_x1, tb_y1], radius=4, fill=tag_bg)
                draw.text(((tb_x0 + tb_x1) / 2, (tb_y0 + tb_y1) / 2), crate["tag"], fill=tag_fg, font=tag_font, anchor="mm")

                # Item type and count inside white card
                mid_x = (cx0 + cx1) / 2
                draw.text((mid_x, cy0 + 56), crate["item"], fill="#0F172A", font=item_font, anchor="mm")
                units_txt = f"Qty: {crate['units']}"
                draw.text((mid_x, cy0 + 86), units_txt, fill="#334155", font=meta_font, anchor="mm")

                elements.append(
                    SceneElement(
                        id=crate["id"],
                        kind="crate",
                        label=f"{crate['color']} {crate['item']} ({crate['tag']}) x{crate['units']}",
                        bbox=(round(cx0, 1), round(cy0, 1), round(cx1, 1), round(cy1, 1)),
                        font_px=14.0,
                        is_queried_text=True,
                        attributes=crate,
                    )
                )

        img.save(out_path)
        return SceneManifest(width=w, height=h, elements=elements)

    def _render_geometric(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        w, h = int(spec["width"]), int(spec["height"])
        img = Image.new("RGB", (w, h), "#F8FAFC")
        draw = ImageDraw.Draw(img)
        title_font = get_font(22, bold=True)
        sub_font = get_font(14, bold=False)

        title = "Compositional Spatial Scene (Top-Down View)"
        draw.text((40, 24), title, fill="#0F172A", font=title_font)
        draw.text((40, 56), "Note: Striped/ringed patterns and depth order carry semantic meaning.", fill="#475569", font=sub_font)
        draw.rounded_rectangle([36, 92, w - 36, h - 36], radius=14, fill="#FFFFFF", outline="#CBD5E1", width=2)

        elements: list[SceneElement] = [
            SceneElement(
                id="title",
                kind="title",
                label=title,
                bbox=measure_text_bbox(draw, (40, 24), title, title_font),
                font_px=22.0,
                is_queried_text=True,
            )
        ]

        # Draw sorted by z-order so occlusion is explicit and deterministic
        ordered = sorted(spec["objects"], key=lambda o: o["z"])
        drawn_bboxes: list[tuple[str, tuple[float, float, float, float]]] = []

        for obj in ordered:
            cx, cy, r = float(obj["cx"]), float(obj["cy"]), float(obj["radius"])
            hex_col = COLORS[obj["color"]]
            pts = self._shape_polygon(obj["shape"], cx, cy, r)
            if obj["shape"] == "circle":
                bbox = (cx - r, cy - r, cx + r, cy + r)
                draw.ellipse(bbox, fill=hex_col, outline="#0F172A", width=3)
            else:
                draw.polygon(pts, fill=hex_col, outline="#0F172A", width=3)
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                bbox = (min(xs), min(ys), max(xs), max(ys))

            if obj["pattern"] == "ringed":
                ir = r * 0.42
                draw.ellipse((cx - ir, cy - ir, cx + ir, cy + ir), fill="#FFFFFF", outline="#0F172A", width=2)
            elif obj["pattern"] == "striped":
                for dy in (-r * 0.35, 0.0, r * 0.35):
                    draw.line((cx - r * 0.45, cy + dy, cx + r * 0.45, cy + dy), fill="#FFFFFF", width=4)

            drawn_bboxes.append((obj["id"], bbox))

        # Compute actual occlusion fraction against later-drawn (higher-z) objects
        for idx, obj in enumerate(ordered):
            oid, bb = drawn_bboxes[idx]
            area = max(1.0, (bb[2] - bb[0]) * (bb[3] - bb[1]))
            max_occ = 0.0
            for j in range(idx + 1, len(ordered)):
                _, later_bb = drawn_bboxes[j]
                ix0 = max(bb[0], later_bb[0])
                iy0 = max(bb[1], later_bb[1])
                ix1 = min(bb[2], later_bb[2])
                iy1 = min(bb[3], later_bb[3])
                if ix1 > ix0 and iy1 > iy0:
                    max_occ = max(max_occ, ((ix1 - ix0) * (iy1 - iy0)) / area)
            elements.append(
                SceneElement(
                    id=oid,
                    kind="geometric_object",
                    label=f"{obj['pattern']} {obj['color']} {obj['shape']}",
                    bbox=(round(bb[0], 1), round(bb[1], 1), round(bb[2], 1), round(bb[3], 1)),
                    occluded_fraction=round(max_occ, 3),
                    attributes=obj,
                )
            )

        img.save(out_path)
        return SceneManifest(width=w, height=h, elements=elements)

    def _shape_polygon(self, shape: str, cx: float, cy: float, r: float) -> list[tuple[float, float]]:
        if shape == "square":
            s = r * 0.88
            return [(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)]
        if shape == "triangle":
            return [(cx, cy - r), (cx + r * 0.95, cy + r * 0.82), (cx - r * 0.95, cy + r * 0.82)]
        if shape == "diamond":
            return [(cx, cy - r), (cx + r * 0.9, cy), (cx, cy + r), (cx - r * 0.9, cy)]
        # hexagon
        return [
            (cx + r * math.cos(math.radians(60 * k)), cy + r * math.sin(math.radians(60 * k)))
            for k in range(6)
        ]

    def solve_spec(
        self, spec: dict[str, Any]
    ) -> tuple[Any, AnswerType, float, str, list[str], list[str], list[str]]:
        subtype = spec["subtype"]
        if subtype == "warehouse_rack":
            crates = spec["crates"]
            rtype = spec["reasoning_type"]
            if rtype == "filtered_count":
                sh, tg = spec["target_shelf"], spec["target_tag"]
                matches = [c for c in crates if c["shelf"] == sh and c["tag"] == tg]
                ref_ids = [f"shelf_{sh}"] + [c["id"] for c in crates if c["shelf"] == sh]
                ev_ids = [c["id"] for c in matches]
                trace = [
                    f"Filtered crates on shelf='{sh}' with tag='{tg}'.",
                    f"Matched IDs: {ev_ids} -> count={len(matches)}.",
                ]
                return len(matches), AnswerType.INTEGER, 0.0, "", ref_ids, ev_ids, trace

            if rtype == "filtered_inventory_sum":
                col = spec["target_color"]
                matches = [c for c in crates if c["color"] == col]
                total = sum(int(c["units"]) for c in matches)
                ref_ids = [c["id"] for c in crates]
                ev_ids = [c["id"] for c in matches]
                trace = [
                    f"Found {len(matches)} crates with color='{col}': {[c['units'] for c in matches]}.",
                    f"Sum = {total}.",
                ]
                return total, AnswerType.INTEGER, 0.0, "units", ref_ids, ev_ids, trace

            # spatial_neighbor_lookup
            anchor_id = spec["anchor_id"]
            anchor = next(c for c in crates if c["id"] == anchor_id)
            nb = next(
                c for c in crates if c["row"] == anchor["row"] and c["col"] == anchor["col"] + 1
            )
            trace = [
                f"Located unique anchor {anchor_id} ({anchor['color']} {anchor['tag']}) at row={anchor['row']}, col={anchor['col']}.",
                f"Right neighbor {nb['id']} holds item='{nb['item']}'.",
            ]
            return nb["item"], AnswerType.STRING, 0.0, "", [anchor_id, nb["id"]], [nb["id"]], trace

        # geometric_constellation
        objects = spec["objects"]
        if spec["reasoning_type"] == "compositional_spatial_relation":
            anchor = next(o for o in objects if o["id"] == spec["anchor_id"])
            nb = next(o for o in objects if o["row"] == anchor["row"] and o["col"] == anchor["col"] + 1)
            trace = [
                f"Anchor {anchor['id']} is {anchor['pattern']} {anchor['color']} {anchor['shape']}.",
                f"Immediate right neighbor is {nb['id']} with color='{nb['color']}'.",
            ]
            return nb["color"], AnswerType.STRING, 0.0, "", [anchor["id"], nb["id"]], [nb["id"]], trace

        # occlusion_depth_ordering
        front = next(o for o in objects if o["id"] == spec["front_id"])
        back = next(o for o in objects if o["id"] == spec["back_id"])
        winner = front if front["z"] > back["z"] else back
        trace = [
            f"Compared z-order of overlapping pair: {back['id']}(z={back['z']}) vs {front['id']}(z={front['z']}).",
            f"Higher z-order (in front) is {winner['id']} ({winner['color']}).",
        ]
        return winner["color"], AnswerType.STRING, 0.0, "", [front["id"], back["id"]], [winner["id"]], trace

    def make_counterfactual_spec(
        self, spec: dict[str, Any], seed: int
    ) -> tuple[dict[str, Any], str] | None:
        twin = copy.deepcopy(spec)
        if twin["subtype"] == "warehouse_rack":
            crates = twin["crates"]
            rtype = twin["reasoning_type"]
            if rtype == "filtered_count":
                sh, tg = twin["target_shelf"], twin["target_tag"]
                non_match = [c for c in crates if c["shelf"] == sh and c["tag"] != tg]
                if non_match:
                    old_t = non_match[0]["tag"]
                    non_match[0]["tag"] = tg
                    return twin, f"Changed crate {non_match[0]['id']} tag from {old_t} to {tg}."
                match = [c for c in crates if c["shelf"] == sh and c["tag"] == tg]
                if match:
                    match[0]["tag"] = "OK" if tg != "OK" else "HOLD"
                    return twin, f"Changed crate {match[0]['id']} tag away from {tg}."
                return None

            if rtype == "filtered_inventory_sum":
                col = twin["target_color"]
                match = next(c for c in crates if c["color"] == col)
                match["units"] += 9
                return twin, f"Increased unit count of {match['id']} by +9."

            nb = next(c for c in crates if c["id"] == twin["neighbor_id"])
            old_item = nb["item"]
            nb["item"] = next(it for it in ITEM_TYPES if it != old_item)
            return twin, f"Changed right-neighbor item from {old_item} to {nb['item']}."

        objects = twin["objects"]
        if twin["reasoning_type"] == "compositional_spatial_relation":
            anchor = next(o for o in objects if o["id"] == twin["anchor_id"])
            nb = next(o for o in objects if o["id"] == twin["target_id"])
            old_c = nb["color"]
            nb["color"] = next(c for c in COLORS if c not in {old_c, anchor["color"]})
            return twin, f"Changed right-neighbor object color from {old_c} to {nb['color']}."

        front = next(o for o in objects if o["id"] == twin["front_id"])
        back = next(o for o in objects if o["id"] == twin["back_id"])
        front["z"], back["z"] = back["z"], front["z"]
        return twin, f"Swapped z-order so {back['color']} shape renders in front of {front['color']}."
