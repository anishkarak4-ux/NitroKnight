"""Family 4: Structured Enterprise Invoices & QA Inspection Checklists."""

from __future__ import annotations

import copy
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from vtf.families.base import VisualTaskFamily, measure_text_bbox
from vtf.fonts import get_font
from vtf.schema import AnswerType, Difficulty, FamilyName, SceneElement, SceneManifest

VENDORS = ["Apex Components Ltd.", "Vertex Precision Supply", "NorthStar Industrial"]
INVOICE_ITEMS = [
    ("SKU-101", "Thermal Sensor Module"),
    ("SKU-204", "Optical Relay Switch"),
    ("SKU-309", "Power Regulator Board"),
    ("SKU-412", "Shielded Bus Harness"),
    ("SKU-518", "Precision Stepper Servo"),
    ("SKU-625", "Industrial Cooling Fan"),
]
CHECK_METRICS = [
    ("Voltage Ripple", "mV"),
    ("Core Temp", "C"),
    ("Line Pressure", "kPa"),
    ("Bus Latency", "ms"),
    ("Fan Speed", "RPM"),
    ("Frame Drift", "mm"),
]


class StructuredDocsTaskFamily(VisualTaskFamily):
    """Generates enterprise invoices and QA inspection matrices."""

    family_name = FamilyName.STRUCTURED_DOCS

    def generate_spec(self, seed: int, difficulty: Difficulty) -> dict[str, Any]:
        rng = random.Random(seed)
        if difficulty == Difficulty.EASY:
            return self._gen_invoice_spec(rng, difficulty, mode="cell_lookup")
        if difficulty == Difficulty.MEDIUM:
            if rng.choice([True, False]):
                return self._gen_invoice_spec(rng, difficulty, mode="checkbox_filter_sum")
            return self._gen_checklist_spec(rng, difficulty)
        # HARD: discrepancy audit or redacted abstention hallucination check
        mode = rng.choice(["discrepancy_audit", "redacted_audit"])
        return self._gen_invoice_spec(rng, difficulty, mode=mode)

    def _gen_invoice_spec(
        self, rng: random.Random, difficulty: Difficulty, *, mode: str
    ) -> dict[str, Any]:
        n_rows = 5 if difficulty != Difficulty.HARD else 6
        picked = rng.sample(INVOICE_ITEMS, n_rows)
        rows = []
        for sku, desc in picked:
            qty = rng.randint(2, 12)
            unit_price = rng.randint(12, 65)
            printed_total = qty * unit_price
            rows.append(
                {
                    "id": f"row_{sku}",
                    "sku": sku,
                    "desc": desc,
                    "qty": qty,
                    "unit_price": unit_price,
                    "printed_total": printed_total,
                    "approved": rng.choice([True, False]),
                }
            )

        if mode == "cell_lookup":
            target = rng.choice(rows)
            question = (
                f"In this invoice ledger, what is the Unit Price (in $) for item {target['sku']}?"
            )
            return {
                "subtype": "invoice_ledger",
                "difficulty": difficulty.value,
                "reasoning_type": "table_cell_lookup",
                "theme_name": "clean_ledger",
                "vendor": rng.choice(VENDORS),
                "invoice_no": f"INV-{rng.randint(4010, 9980)}",
                "rows": rows,
                "target_sku": target["sku"],
                "question": question,
            }

        if mode == "checkbox_filter_sum":
            # Ensure at least 2 approved and 1 unapproved
            rows[0]["approved"] = True
            rows[1]["approved"] = True
            rows[-1]["approved"] = False
            question = (
                "In this invoice ledger, what is the combined Total ($) of all line items "
                "whose Approved checkbox is checked?"
            )
            return {
                "subtype": "invoice_ledger",
                "difficulty": difficulty.value,
                "reasoning_type": "checkbox_filtered_sum",
                "theme_name": "clean_ledger",
                "vendor": rng.choice(VENDORS),
                "invoice_no": f"INV-{rng.randint(4010, 9980)}",
                "rows": rows,
                "question": question,
            }

        if mode == "redacted_audit":
            target = rng.choice(rows)
            question = (
                f"Inspect this invoice ledger for item {target['sku']}: if its Unit Price ($) is visibly readable, "
                "return the exact dollar integer; if the Unit Price cell is covered by a redaction bar, "
                "reply strictly with (CANNOT_DETERMINE)."
            )
            return {
                "subtype": "invoice_ledger",
                "difficulty": difficulty.value,
                "reasoning_type": "hallucination_abstention",
                "theme_name": "clean_ledger",
                "vendor": rng.choice(VENDORS),
                "invoice_no": f"INV-{rng.randint(4010, 9980)}",
                "rows": rows,
                "target_sku": target["sku"],
                "redacted": True,
                "question": question,
            }

        # discrepancy_audit: inject exact arithmetic error in ONE row
        bad_idx = rng.randrange(len(rows))
        rows[bad_idx]["printed_total"] += rng.choice([-25, 30, 45])
        question = (
            "Audit this invoice ledger: exactly ONE row has a Printed Total ($) that does NOT "
            "equal Qty x Unit Price. What is the SKU of that discrepant row?"
        )
        return {
            "subtype": "invoice_ledger",
            "difficulty": difficulty.value,
            "reasoning_type": "arithmetic_discrepancy_audit",
            "theme_name": "clean_ledger",
            "vendor": rng.choice(VENDORS),
            "invoice_no": f"INV-{rng.randint(4010, 9980)}",
            "rows": rows,
            "bad_sku": rows[bad_idx]["sku"],
            "question": question,
        }

    def _gen_checklist_spec(self, rng: random.Random, difficulty: Difficulty) -> dict[str, Any]:
        zones = ["Zone A", "Zone B"]
        checks = []
        for idx, (metric, unit) in enumerate(CHECK_METRICS):
            zone = zones[idx % 2]
            limit = rng.randint(40, 120)
            exceeds = rng.choice([True, False])
            measured = limit + rng.randint(5, 22) if exceeds else limit - rng.randint(4, 20)
            checks.append(
                {
                    "id": f"chk_{idx}",
                    "zone": zone,
                    "metric": metric,
                    "unit": unit,
                    "measured": measured,
                    "limit": limit,
                    "status": "FAIL" if exceeds else "PASS",
                }
            )
        target_zone = rng.choice(zones)
        question = (
            f"In this QA inspection checklist, how many metrics in {target_zone} have a Measured "
            f"value strictly greater than their Max Allowed limit?"
        )
        return {
            "subtype": "inspection_checklist",
            "difficulty": difficulty.value,
            "reasoning_type": "zone_threshold_violation_count",
            "theme_name": "qa_matrix",
            "checks": checks,
            "target_zone": target_zone,
            "question": question,
        }

    def render_spec(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        if spec["subtype"] == "invoice_ledger":
            return self._render_invoice(spec, out_path)
        return self._render_checklist(spec, out_path)

    def _render_invoice(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        w, h = 1120, 740
        img = Image.new("RGB", (w, h), "#F8FAFC")
        draw = ImageDraw.Draw(img)
        h1_font = get_font(24, bold=True)
        h2_font = get_font(15, bold=False)
        th_font = get_font(15, bold=True)
        td_font = get_font(15, bold=False)
        num_font = get_font(15, bold=True, mono=True)

        elements: list[SceneElement] = []
        # Card background
        draw.rounded_rectangle([36, 28, w - 36, h - 32], radius=14, fill="#FFFFFF", outline="#CBD5E1", width=2)
        title = f"Purchase Invoice Ledger — {spec['invoice_no']}"
        draw.text((64, 52), title, fill="#0F172A", font=h1_font)
        draw.text((64, 88), f"Vendor: {spec['vendor']}", fill="#475569", font=h2_font)
        elements.append(
            SceneElement(
                id="title",
                kind="title",
                label=title,
                bbox=measure_text_bbox(draw, (64, 52), title, h1_font),
                font_px=24.0,
                is_queried_text=True,
            )
        )

        # Table geometry
        tx0, ty0, tx1 = 64, 138, w - 64
        cols = [
            ("Approved", 110),
            ("SKU", 130),
            ("Item Description", 340),
            ("Qty", 100),
            ("Unit Price ($)", 150),
            ("Printed Total ($)", 162),
        ]
        row_h = 68
        # Header
        draw.rectangle([tx0, ty0, tx1, ty0 + 50], fill="#1E293B")
        cx = tx0
        for cname, cw in cols:
            draw.text((cx + cw / 2, ty0 + 25), cname, fill="#FFFFFF", font=th_font, anchor="mm")
            cx += cw

        for r_idx, row in enumerate(spec["rows"]):
            ry0 = ty0 + 50 + r_idx * row_h
            ry1 = ry0 + row_h
            bg = "#FFFFFF" if r_idx % 2 == 0 else "#F8FAFC"
            draw.rectangle([tx0, ry0, tx1, ry1], fill=bg, outline="#E2E8F0", width=1)

            cx = tx0
            # Col 0: drawn crisp checkbox
            cb_cx, cb_cy = cx + cols[0][1] / 2, (ry0 + ry1) / 2
            cb_box = (cb_cx - 13, cb_cy - 13, cb_cx + 13, cb_cy + 13)
            draw.rounded_rectangle(
                cb_box,
                radius=4,
                fill="#2563EB" if row["approved"] else "#FFFFFF",
                outline="#1E293B",
                width=2,
            )
            if row["approved"]:
                draw.line(
                    [(cb_cx - 7, cb_cy), (cb_cx - 2, cb_cy + 6), (cb_cx + 8, cb_cy - 6)],
                    fill="#FFFFFF",
                    width=3,
                )
            cx += cols[0][1]

            # Col 1: SKU
            draw.text((cx + cols[1][1] / 2, (ry0 + ry1) / 2), row["sku"], fill="#0F172A", font=num_font, anchor="mm")
            cx += cols[1][1]

            # Col 2: Desc
            draw.text((cx + 16, (ry0 + ry1) / 2), row["desc"], fill="#1E293B", font=td_font, anchor="lm")
            cx += cols[2][1]

            # Col 3: Qty
            draw.text((cx + cols[3][1] / 2, (ry0 + ry1) / 2), str(row["qty"]), fill="#0F172A", font=num_font, anchor="mm")
            cx += cols[3][1]

            # Col 4: Unit Price (or security redaction bar for hallucination abstention)
            is_redacted_row = bool(spec.get("redacted")) and row["sku"] == spec.get("target_sku")
            if is_redacted_row:
                rx0, ry_box0, rx1, ry_box1 = cx + 18, ry0 + 14, cx + cols[4][1] - 18, ry1 - 14
                draw.rounded_rectangle([rx0, ry_box0, rx1, ry_box1], radius=4, fill="#0F172A")
                draw.text(((rx0 + rx1) / 2, (ry_box0 + ry_box1) / 2), "REDACTED", fill="#F8FAFC", font=th_font, anchor="mm")
                elements.append(
                    SceneElement(
                        id=f"redaction_{row['sku']}",
                        kind="redaction_mask",
                        label=f"REDACTED {row['sku']}",
                        bbox=(float(rx0), float(ry_box0), float(rx1), float(ry_box1)),
                        font_px=15.0,
                        is_queried_text=True,
                    )
                )
            else:
                draw.text(
                    (cx + cols[4][1] / 2, (ry0 + ry1) / 2),
                    f"${row['unit_price']}",
                    fill="#0F172A",
                    font=num_font,
                    anchor="mm",
                )
            cx += cols[4][1]

            # Col 5: Printed Total
            if is_redacted_row:
                rx0, ry_box0, rx1, ry_box1 = cx + 18, ry0 + 14, cx + cols[5][1] - 18, ry1 - 14
                draw.rounded_rectangle([rx0, ry_box0, rx1, ry_box1], radius=4, fill="#0F172A")
                draw.text(((rx0 + rx1) / 2, (ry_box0 + ry_box1) / 2), "REDACTED", fill="#F8FAFC", font=th_font, anchor="mm")
            else:
                draw.text(
                    (cx + cols[5][1] / 2, (ry0 + ry1) / 2),
                    f"${row['printed_total']}",
                    fill="#0F172A",
                    font=num_font,
                    anchor="mm",
                )

            elements.append(
                SceneElement(
                    id=row["id"],
                    kind="table_row",
                    label=f"{row['sku']} qty={row['qty']} unit=${row['unit_price']} total=${row['printed_total']} approved={row['approved']}",
                    bbox=(float(tx0), float(ry0), float(tx1), float(ry1)),
                    font_px=15.0,
                    is_queried_text=True,
                    attributes=row,
                )
            )

        img.save(out_path)
        return SceneManifest(width=w, height=h, elements=elements)

    def _render_checklist(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        w, h = 1120, 740
        img = Image.new("RGB", (w, h), "#F8FAFC")
        draw = ImageDraw.Draw(img)
        h1_font = get_font(24, bold=True)
        th_font = get_font(15, bold=True)
        td_font = get_font(15, bold=False)
        num_font = get_font(15, bold=True, mono=True)

        elements: list[SceneElement] = []
        draw.rounded_rectangle([36, 28, w - 36, h - 32], radius=14, fill="#FFFFFF", outline="#CBD5E1", width=2)
        title = "Hardware QA Inspection Matrix"
        draw.text((64, 52), title, fill="#0F172A", font=h1_font)
        elements.append(
            SceneElement(
                id="title",
                kind="title",
                label=title,
                bbox=measure_text_bbox(draw, (64, 52), title, h1_font),
                font_px=24.0,
                is_queried_text=True,
            )
        )

        tx0, ty0, tx1 = 64, 128, w - 64
        cols = [("Zone", 150), ("Metric", 290), ("Measured", 180), ("Max Allowed", 180), ("Status", 192)]
        row_h = 76
        draw.rectangle([tx0, ty0, tx1, ty0 + 50], fill="#0F172A")
        cx = tx0
        for cname, cw in cols:
            draw.text((cx + cw / 2, ty0 + 25), cname, fill="#FFFFFF", font=th_font, anchor="mm")
            cx += cw

        for r_idx, chk in enumerate(spec["checks"]):
            ry0 = ty0 + 50 + r_idx * row_h
            ry1 = ry0 + row_h
            bg = "#FFFFFF" if r_idx % 2 == 0 else "#F8FAFC"
            draw.rectangle([tx0, ry0, tx1, ry1], fill=bg, outline="#E2E8F0", width=1)
            cx = tx0
            draw.text((cx + cols[0][1] / 2, (ry0 + ry1) / 2), chk["zone"], fill="#1E293B", font=th_font, anchor="mm")
            cx += cols[0][1]
            draw.text((cx + 20, (ry0 + ry1) / 2), chk["metric"], fill="#0F172A", font=td_font, anchor="lm")
            cx += cols[1][1]
            draw.text(
                (cx + cols[2][1] / 2, (ry0 + ry1) / 2),
                f"{chk['measured']} {chk['unit']}",
                fill="#0F172A",
                font=num_font,
                anchor="mm",
            )
            cx += cols[2][1]
            draw.text(
                (cx + cols[3][1] / 2, (ry0 + ry1) / 2),
                f"{chk['limit']} {chk['unit']}",
                fill="#334155",
                font=num_font,
                anchor="mm",
            )
            cx += cols[3][1]
            pill_bg = "#FEE2E2" if chk["status"] == "FAIL" else "#DCFCE7"
            pill_fg = "#991B1B" if chk["status"] == "FAIL" else "#166534"
            px0, py0, px1, py1 = cx + 46, ry0 + 20, cx + 146, ry1 - 20
            draw.rounded_rectangle([px0, py0, px1, py1], radius=8, fill=pill_bg, outline=pill_fg, width=2)
            draw.text(((px0 + px1) / 2, (py0 + py1) / 2), chk["status"], fill=pill_fg, font=th_font, anchor="mm")

            elements.append(
                SceneElement(
                    id=chk["id"],
                    kind="checklist_row",
                    label=f"{chk['zone']} {chk['metric']} {chk['measured']}/{chk['limit']}",
                    bbox=(float(tx0), float(ry0), float(tx1), float(ry1)),
                    font_px=15.0,
                    is_queried_text=True,
                    attributes=chk,
                )
            )

        img.save(out_path)
        return SceneManifest(width=w, height=h, elements=elements)

    def solve_spec(
        self, spec: dict[str, Any]
    ) -> tuple[Any, AnswerType, float, str, list[str], list[str], list[str]]:
        if spec["subtype"] == "invoice_ledger":
            rows = spec["rows"]
            rtype = spec["reasoning_type"]
            ref_ids = [r["id"] for r in rows]

            if rtype == "table_cell_lookup":
                sku = spec["target_sku"]
                row = next(r for r in rows if r["sku"] == sku)
                trace = [f"Located SKU={sku}; Unit Price=${row['unit_price']}."]
                return row["unit_price"], AnswerType.INTEGER, 0.0, "$", ref_ids, [row["id"]], trace

            if rtype == "checkbox_filtered_sum":
                approved = [r for r in rows if r["approved"]]
                total = sum(int(r["printed_total"]) for r in approved)
                ev_ids = [r["id"] for r in approved]
                trace = [
                    f"Approved SKUs: {[r['sku'] for r in approved]}.",
                    f"Summed printed totals: {[r['printed_total'] for r in approved]} -> ${total}.",
                ]
                return total, AnswerType.INTEGER, 0.0, "$", ref_ids, ev_ids, trace

            if rtype == "hallucination_abstention":
                sku = spec["target_sku"]
                row = next(r for r in rows if r["sku"] == sku)
                if spec.get("redacted"):
                    mask_id = f"redaction_{sku}"
                    trace = [
                        f"Located row {sku}; Unit Price & Printed Total are visibly obscured by a REDACTED bar.",
                        "Correct hallucination-resistant response is CANNOT_DETERMINE.",
                    ]
                    return "CANNOT_DETERMINE", AnswerType.STRING, 0.0, "", ref_ids + [mask_id], [row["id"], mask_id], trace
                trace = [
                    f"Located unredacted row {sku}; Unit Price is visibly readable (${row['unit_price']})."
                ]
                return str(row["unit_price"]), AnswerType.STRING, 0.0, "$", ref_ids, [row["id"]], trace

            # arithmetic_discrepancy_audit
            bad = [r for r in rows if int(r["qty"]) * int(r["unit_price"]) != int(r["printed_total"])]
            assert len(bad) == 1, f"Expected single discrepant row, got {bad}"
            trace = [
                f"Checked Qty * Unit Price vs Printed Total for all {len(rows)} rows.",
                f"Found single mismatch at {bad[0]['sku']}: {bad[0]['qty']}*{bad[0]['unit_price']} != {bad[0]['printed_total']}.",
            ]
            return bad[0]["sku"], AnswerType.STRING, 0.0, "", ref_ids, [bad[0]["id"]], trace

        # inspection_checklist
        checks = spec["checks"]
        tz = spec["target_zone"]
        hits = [c for c in checks if c["zone"] == tz and int(c["measured"]) > int(c["limit"])]
        ref_ids = [c["id"] for c in checks]
        ev_ids = [c["id"] for c in hits]
        trace = [
            f"Filtered {tz} checks where Measured > Max Allowed.",
            f"Matching rows: {[c['metric'] for c in hits]} -> count={len(hits)}.",
        ]
        return len(hits), AnswerType.INTEGER, 0.0, "", ref_ids, ev_ids, trace

    def make_counterfactual_spec(
        self, spec: dict[str, Any], seed: int
    ) -> tuple[dict[str, Any], str] | None:
        twin = copy.deepcopy(spec)
        if twin["subtype"] == "invoice_ledger":
            rows = twin["rows"]
            rtype = twin["reasoning_type"]
            if rtype == "table_cell_lookup":
                row = next(r for r in rows if r["sku"] == twin["target_sku"])
                row["unit_price"] += 15
                row["printed_total"] = row["qty"] * row["unit_price"]
                return twin, f"Updated Unit Price of {row['sku']} by +$15."
            if rtype == "checkbox_filtered_sum":
                unapproved = [r for r in rows if not r["approved"]]
                if unapproved:
                    unapproved[0]["approved"] = True
                    return twin, f"Checked Approved box on {unapproved[0]['sku']} (+${unapproved[0]['printed_total']})."
                rows[0]["approved"] = False
                return twin, f"Unchecked Approved box on {rows[0]['sku']}."
            if rtype == "hallucination_abstention":
                twin["redacted"] = not bool(twin.get("redacted"))
                sku = twin["target_sku"]
                state = "Restored visibility" if not twin["redacted"] else "Applied redaction bar"
                return twin, f"{state} on Unit Price for {sku}."
            # discrepancy_audit: fix old bad row and move discrepancy to another row
            old_bad = next(r for r in rows if r["sku"] == twin["bad_sku"])
            old_bad["printed_total"] = old_bad["qty"] * old_bad["unit_price"]
            new_bad = next(r for r in rows if r["sku"] != twin["bad_sku"])
            new_bad["printed_total"] += 35
            twin["bad_sku"] = new_bad["sku"]
            return twin, f"Fixed {old_bad['sku']} and injected arithmetic mismatch into {new_bad['sku']}."

        # inspection_checklist
        tz = twin["target_zone"]
        zone_rows = [c for c in twin["checks"] if c["zone"] == tz]
        target = zone_rows[0]
        if target["measured"] > target["limit"]:
            target["measured"] = max(5, target["limit"] - 10)
            target["status"] = "PASS"
        else:
            target["measured"] = target["limit"] + 12
            target["status"] = "FAIL"
        return twin, f"Flipped {target['metric']} in {tz} across Max Allowed limit."
