import json
from pathlib import Path

SHEET_IDS = {
    "Overview": 0,
    "Rankings": 188180825,
    "Doubles_Matches": 1884937433,
    "Singles_Matches": 333814208,
    "Players": 5451789,
}


def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return {
        "red": int(h[0:2], 16) / 255.0,
        "green": int(h[2:4], 16) / 255.0,
        "blue": int(h[4:6], 16) / 255.0,
    }


def repeat_cell(sheet_id, r1, r2, c1, c2, bg=None, fg=None, bold=None, italic=None, size=None, align=None, valign="MIDDLE", wrap="CLIP"):
    cell_format = {"verticalAlignment": valign, "wrapStrategy": wrap}
    fields = ["userEnteredFormat.verticalAlignment", "userEnteredFormat.wrapStrategy"]

    if bg:
        cell_format["backgroundColor"] = hex_to_rgb(bg)
        fields.append("userEnteredFormat.backgroundColor")

    if align:
        cell_format["horizontalAlignment"] = align
        fields.append("userEnteredFormat.horizontalAlignment")

    text_format = {"fontFamily": "Inter, Roboto, Arial"}
    tf_fields = ["userEnteredFormat.textFormat.fontFamily"]
    if fg:
        text_format["foregroundColor"] = hex_to_rgb(fg)
        tf_fields.append("userEnteredFormat.textFormat.foregroundColor")
    if bold is not None:
        text_format["bold"] = bold
        tf_fields.append("userEnteredFormat.textFormat.bold")
    if italic is not None:
        text_format["italic"] = italic
        tf_fields.append("userEnteredFormat.textFormat.italic")
    if size is not None:
        text_format["fontSize"] = size
        tf_fields.append("userEnteredFormat.textFormat.fontSize")

    cell_format["textFormat"] = text_format
    fields.extend(tf_fields)

    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": r1,
                "endRowIndex": r2,
                "startColumnIndex": c1,
                "endColumnIndex": c2,
            },
            "cell": {"userEnteredFormat": cell_format},
            "fields": ",".join(fields),
        }
    }


def set_borders(sheet_id, r1, r2, c1, c2, color="#CBD5E1", style="SOLID", outer_only=False):
    b = {"style": style, "color": hex_to_rgb(color)}
    req = {
        "range": {
            "sheetId": sheet_id,
            "startRowIndex": r1,
            "endRowIndex": r2,
            "startColumnIndex": c1,
            "endColumnIndex": c2,
        },
        "top": b,
        "bottom": b,
        "left": b,
        "right": b,
    }
    if not outer_only:
        req["innerHorizontal"] = b
        req["innerVertical"] = b
    return {"updateBorders": req}


def set_col_width(sheet_id, c1, c2, px):
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": c1,
                "endIndex": c2,
            },
            "properties": {"pixelSize": px},
            "fields": "pixelSize",
        }
    }


def set_row_height(sheet_id, r1, r2, px):
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "ROWS",
                "startIndex": r1,
                "endIndex": r2,
            },
            "properties": {"pixelSize": px},
            "fields": "pixelSize",
        }
    }


def merge_cells(sheet_id, r1, r2, c1, c2):
    return {
        "mergeCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": r1,
                "endRowIndex": r2,
                "startColumnIndex": c1,
                "endColumnIndex": c2,
            },
            "mergeType": "MERGE_ALL",
        }
    }


def freeze_sheet(sheet_id, rows=0, cols=0, hide_grid=False):
    props = {"gridProperties": {"frozenRowCount": rows, "frozenColumnCount": cols, "hideGridlines": hide_grid}}
    return {
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id, **props},
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount,gridProperties.hideGridlines",
        }
    }


def add_dropdown_validation(sheet_id, r1, r2, c1, c2, formula_range):
    return {
        "setDataValidation": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": r1,
                "endRowIndex": r2,
                "startColumnIndex": c1,
                "endColumnIndex": c2,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_RANGE",
                    "values": [{"userEnteredValue": formula_range}],
                },
                "showCustomUi": True,
                "strict": False,
            },
        }
    }


def unmerge_all(sheet_id, r1, r2, c1, c2):
    return {
        "unmergeCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": r1,
                "endRowIndex": r2,
                "startColumnIndex": c1,
                "endColumnIndex": c2,
            }
        }
    }


def build_requests():
    reqs = []

    # =========================================================================
    # 1. OVERVIEW TAB (Club Overview, Podiums, Top 5 & Recent History)
    # =========================================================================
    sid = SHEET_IDS["Overview"]
    reqs.append(unmerge_all(sid, 0, 40, 0, 14))
    reqs.append(freeze_sheet(sid, rows=0, cols=0, hide_grid=True))
    reqs.append(repeat_cell(sid, 0, 40, 0, 14, bg="#F8FAFC", fg="#0F172A", size=10))

    # Column widths for Overview
    col_widths_ov = [
        (0, 1, 24),    # A: Left margin
        (1, 2, 130),   # B
        (2, 3, 145),   # C: Podium #2 Silver
        (3, 4, 165),   # D: Podium #1 Gold
        (4, 5, 145),   # E: Podium #3 Bronze
        (5, 6, 95),    # F
        (6, 7, 28),    # G: Center divider
        (7, 8, 130),   # H
        (8, 9, 145),   # I: Podium #2 Silver
        (9, 10, 165),  # J: Podium #1 Gold
        (10, 11, 145), # K: Podium #3 Bronze
        (11, 12, 95),  # L
        (12, 13, 24),  # M: Right margin
    ]
    for c1, c2, px in col_widths_ov:
        reqs.append(set_col_width(sid, c1, c2, px))

    reqs.append(set_row_height(sid, 0, 1, 14))
    reqs.append(set_row_height(sid, 1, 2, 44))  # App Header
    reqs.append(set_row_height(sid, 2, 6, 30))  # Club info card
    reqs.append(set_row_height(sid, 7, 8, 38))  # Ranking title
    reqs.append(set_row_height(sid, 9, 10, 36)) # Podium headers
    reqs.append(set_row_height(sid, 10, 16, 32))# Podium body rows
    reqs.append(set_row_height(sid, 18, 20, 32))# Top 5 headers
    reqs.append(set_row_height(sid, 20, 25, 28))# Top 5 rows
    reqs.append(set_row_height(sid, 26, 28, 34))# Recent matches header
    reqs.append(set_row_height(sid, 28, 33, 30))# Recent matches rows

    # Top App Bar (B2:L2)
    reqs.append(merge_cells(sid, 1, 2, 1, 10))
    reqs.append(merge_cells(sid, 1, 2, 10, 12))
    reqs.append(repeat_cell(sid, 1, 2, 1, 10, bg="#0F172A", fg="#FFFFFF", bold=True, size=15, align="LEFT"))
    reqs.append(repeat_cell(sid, 1, 2, 10, 12, bg="#0F172A", fg="#94A3B8", bold=True, size=12, align="RIGHT"))

    # Navigation & Club Info Card (B3:L6)
    for r_info in range(2, 6):
        reqs.append(merge_cells(sid, r_info, r_info + 1, 10, 12))
    reqs.append(repeat_cell(sid, 2, 6, 1, 12, bg="#FFFFFF", fg="#334155", size=10, align="LEFT"))
    reqs.append(repeat_cell(sid, 2, 3, 1, 12, bg="#F1F5F9", fg="#475569", bold=True, size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 2, 3, 3, 5, bg="#0F766E", fg="#FFFFFF", bold=True, size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 5, 6, 1, 12, bg="#F8FAFC", fg="#0F766E", bold=True, size=9, align="CENTER"))
    reqs.append(set_borders(sid, 1, 6, 1, 12, color="#CBD5E1", outer_only=True))

    # Ranking Section Banner (B8:L8)
    reqs.append(merge_cells(sid, 7, 8, 1, 6))
    reqs.append(merge_cells(sid, 7, 8, 9, 12))
    reqs.append(repeat_cell(sid, 7, 8, 1, 6, bg="#F8FAFC", fg="#0F172A", bold=True, size=15, align="LEFT"))
    reqs.append(repeat_cell(sid, 7, 8, 9, 12, bg="#CCFBF1", fg="#0F766E", bold=True, size=10, align="CENTER"))
    reqs.append(set_borders(sid, 7, 8, 9, 12, color="#14B8A6", outer_only=True))

    # Singles Podium Card (B10:F17) & Doubles Podium Card (H10:L17)
    for c_start in (1, 7):
        c_end = c_start + 5
        reqs.append(repeat_cell(sid, 9, 17, c_start, c_end, bg="#FFFFFF", fg="#1E293B", size=10, align="CENTER"))
        reqs.append(merge_cells(sid, 9, 10, c_start, c_start + 4))
        reqs.append(repeat_cell(sid, 9, 10, c_start, c_start + 4, bg="#1E293B", fg="#FFFFFF", bold=True, size=12, align="LEFT"))
        reqs.append(repeat_cell(sid, 9, 10, c_start + 4, c_end, bg="#1E293B", fg="#38BDF8", bold=True, size=14, align="CENTER"))

        # #1 Gold Column (c_start + 2, rows 10..15)
        c_gold = c_start + 2
        reqs.append(repeat_cell(sid, 10, 11, c_gold, c_gold + 1, bg="#FEF3C7", fg="#B45309", bold=True, size=10, align="CENTER"))
        reqs.append(repeat_cell(sid, 11, 12, c_gold, c_gold + 1, bg="#F59E0B", fg="#FFFFFF", bold=True, size=16, align="CENTER"))
        reqs.append(repeat_cell(sid, 12, 13, c_gold, c_gold + 1, bg="#FFFBEB", fg="#0F172A", bold=True, size=12, align="CENTER"))
        reqs.append(repeat_cell(sid, 13, 14, c_gold, c_gold + 1, bg="#FFFBEB", fg="#B45309", bold=True, size=14, align="CENTER"))
        reqs.append(repeat_cell(sid, 14, 15, c_gold, c_gold + 1, bg="#FFFBEB", fg="#475569", bold=False, size=9, align="CENTER"))
        reqs.append(set_borders(sid, 10, 15, c_gold, c_gold + 1, color="#F59E0B", outer_only=True))

        # #2 Silver Column (c_start + 1, rows 11..16)
        c_silver = c_start + 1
        reqs.append(repeat_cell(sid, 11, 12, c_silver, c_silver + 1, bg="#F1F5F9", fg="#475569", bold=True, size=9, align="CENTER"))
        reqs.append(repeat_cell(sid, 12, 13, c_silver, c_silver + 1, bg="#94A3B8", fg="#FFFFFF", bold=True, size=14, align="CENTER"))
        reqs.append(repeat_cell(sid, 13, 14, c_silver, c_silver + 1, bg="#F8FAFC", fg="#1E293B", bold=True, size=11, align="CENTER"))
        reqs.append(repeat_cell(sid, 14, 15, c_silver, c_silver + 1, bg="#F8FAFC", fg="#334155", bold=True, size=12, align="CENTER"))
        reqs.append(repeat_cell(sid, 15, 16, c_silver, c_silver + 1, bg="#F8FAFC", fg="#64748B", bold=False, size=9, align="CENTER"))
        reqs.append(set_borders(sid, 11, 16, c_silver, c_silver + 1, color="#94A3B8", outer_only=True))

        # #3 Bronze Column (c_start + 3, rows 11..16)
        c_bronze = c_start + 3
        reqs.append(repeat_cell(sid, 11, 12, c_bronze, c_bronze + 1, bg="#FFEDD5", fg="#9A3412", bold=True, size=9, align="CENTER"))
        reqs.append(repeat_cell(sid, 12, 13, c_bronze, c_bronze + 1, bg="#D97706", fg="#FFFFFF", bold=True, size=14, align="CENTER"))
        reqs.append(repeat_cell(sid, 13, 14, c_bronze, c_bronze + 1, bg="#FFF7ED", fg="#1E293B", bold=True, size=11, align="CENTER"))
        reqs.append(repeat_cell(sid, 14, 15, c_bronze, c_bronze + 1, bg="#FFF7ED", fg="#9A3412", bold=True, size=12, align="CENTER"))
        reqs.append(repeat_cell(sid, 15, 16, c_bronze, c_bronze + 1, bg="#FFF7ED", fg="#64748B", bold=False, size=9, align="CENTER"))
        reqs.append(set_borders(sid, 11, 16, c_bronze, c_bronze + 1, color="#D97706", outer_only=True))

        # Footer row (row 16..17)
        reqs.append(merge_cells(sid, 16, 17, c_start, c_end))
        reqs.append(repeat_cell(sid, 16, 17, c_start, c_end, bg="#F1F5F9", fg="#64748B", italic=True, size=9, align="CENTER"))
        reqs.append(set_borders(sid, 9, 17, c_start, c_end, color="#CBD5E1", outer_only=True))

    # Top 5 Leaderboard Snapshots (Rows 19..25)
    for c_start in (1, 7):
        c_end = c_start + 5
        reqs.append(merge_cells(sid, 18, 19, c_start, c_end))
        reqs.append(repeat_cell(sid, 18, 19, c_start, c_end, bg="#0F172A", fg="#FFFFFF", bold=True, size=11, align="LEFT"))
        reqs.append(repeat_cell(sid, 19, 20, c_start, c_end, bg="#E2E8F0", fg="#334155", bold=True, size=9, align="CENTER"))
        reqs.append(repeat_cell(sid, 20, 25, c_start, c_end, bg="#FFFFFF", fg="#1E293B", size=10, align="CENTER"))
        reqs.append(repeat_cell(sid, 20, 25, c_start + 2, c_start + 3, bg="#FFFFFF", fg="#0F172A", bold=True, size=10, align="LEFT"))
        reqs.append(repeat_cell(sid, 20, 25, c_start + 4, c_end, bg="#F8FAFC", fg="#0F766E", bold=True, size=11, align="CENTER"))
        # Highlight #1, #2, #3 rows
        reqs.append(repeat_cell(sid, 20, 21, c_start, c_start + 2, bg="#FEF3C7", fg="#B45309", bold=True, size=10, align="CENTER"))
        reqs.append(repeat_cell(sid, 21, 22, c_start, c_start + 2, bg="#F1F5F9", fg="#475569", bold=True, size=10, align="CENTER"))
        reqs.append(repeat_cell(sid, 22, 23, c_start, c_start + 2, bg="#FFEDD5", fg="#9A3412", bold=True, size=10, align="CENTER"))
        reqs.append(set_borders(sid, 18, 25, c_start, c_end, color="#CBD5E1", outer_only=False))

    # Recent Match History Section (Rows 27..33)
    reqs.append(merge_cells(sid, 26, 27, 1, 12))
    reqs.append(repeat_cell(sid, 26, 27, 1, 12, bg="#1E293B", fg="#FFFFFF", bold=True, size=11, align="LEFT"))
    reqs.append(merge_cells(sid, 27, 28, 5, 7))
    reqs.append(merge_cells(sid, 27, 28, 9, 12))
    reqs.append(repeat_cell(sid, 27, 28, 1, 12, bg="#E2E8F0", fg="#334155", bold=True, size=9, align="CENTER"))
    for r_idx in range(28, 33):
        reqs.append(merge_cells(sid, r_idx, r_idx + 1, 5, 7))
        reqs.append(merge_cells(sid, r_idx, r_idx + 1, 9, 12))
    reqs.append(repeat_cell(sid, 28, 33, 1, 12, bg="#FFFFFF", fg="#1E293B", size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 28, 33, 5, 7, bg="#F8FAFC", fg="#0F172A", bold=True, size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 28, 33, 9, 12, bg="#F8FAFC", fg="#334155", italic=False, size=9, align="LEFT"))
    reqs.append(set_borders(sid, 26, 33, 1, 12, color="#CBD5E1", outer_only=False))

    # =========================================================================
    # 2. RANKINGS TAB (Full Doubles & Singles Leaderboards)
    # =========================================================================
    sid = SHEET_IDS["Rankings"]
    reqs.append(unmerge_all(sid, 0, 30, 0, 15))
    reqs.append(freeze_sheet(sid, rows=6, cols=0, hide_grid=False))
    reqs.append(merge_cells(sid, 0, 1, 0, 15))
    reqs.append(merge_cells(sid, 1, 2, 0, 15))
    reqs.append(repeat_cell(sid, 0, 1, 0, 15, bg="#0F172A", fg="#FFFFFF", bold=True, size=14, align="LEFT"))
    reqs.append(repeat_cell(sid, 1, 2, 0, 15, bg="#1E293B", fg="#94A3B8", italic=True, size=10, align="LEFT"))

    # Search bar row (Row 3)
    reqs.append(merge_cells(sid, 2, 3, 0, 2))
    reqs.append(merge_cells(sid, 2, 3, 3, 8))
    reqs.append(merge_cells(sid, 2, 3, 8, 10))
    reqs.append(merge_cells(sid, 2, 3, 10, 15))
    reqs.append(repeat_cell(sid, 2, 3, 0, 2, bg="#F1F5F9", fg="#0F172A", bold=True, size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 2, 3, 2, 3, bg="#FFFFFF", fg="#0F766E", bold=True, size=11, align="LEFT"))
    reqs.append(repeat_cell(sid, 2, 3, 3, 8, bg="#F8FAFC", fg="#64748B", italic=True, size=9, align="LEFT"))
    reqs.append(repeat_cell(sid, 2, 3, 8, 10, bg="#F1F5F9", fg="#0F172A", bold=True, size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 2, 3, 10, 15, bg="#CCFBF1", fg="#0F766E", bold=True, size=10, align="LEFT"))
    reqs.append(set_borders(sid, 2, 3, 0, 15, color="#94A3B8", outer_only=False))

    # Leaderboard Section Banners (Row 5) & Column Headers (Row 6)
    for c_offset, header_bg in [(0, "#0F766E"), (8, "#1D4ED8")]:
        reqs.append(merge_cells(sid, 4, 5, c_offset, c_offset + 7))
        reqs.append(repeat_cell(sid, 4, 5, c_offset, c_offset + 7, bg=header_bg, fg="#FFFFFF", bold=True, size=12, align="LEFT"))
        reqs.append(repeat_cell(sid, 5, 6, c_offset, c_offset + 7, bg="#1E293B", fg="#FFFFFF", bold=True, size=10, align="CENTER"))
        reqs.append(repeat_cell(sid, 6, 26, c_offset, c_offset + 7, bg="#FFFFFF", fg="#1E293B", size=10, align="CENTER"))
        reqs.append(repeat_cell(sid, 6, 26, c_offset + 2, c_offset + 3, bg="#FFFFFF", fg="#0F172A", bold=True, size=11, align="LEFT"))
        reqs.append(repeat_cell(sid, 6, 26, c_offset + 6, c_offset + 7, bg="#F8FAFC", fg="#0F172A", bold=True, size=12, align="CENTER"))

        # Top 3 Podium Row Tints (#1 Gold, #2 Silver, #3 Bronze)
        reqs.append(repeat_cell(sid, 6, 7, c_offset, c_offset + 2, bg="#FEF3C7", fg="#B45309", bold=True, size=11, align="CENTER"))
        reqs.append(repeat_cell(sid, 6, 7, c_offset + 6, c_offset + 7, bg="#FEF3C7", fg="#B45309", bold=True, size=13, align="CENTER"))
        reqs.append(repeat_cell(sid, 7, 8, c_offset, c_offset + 2, bg="#F1F5F9", fg="#475569", bold=True, size=11, align="CENTER"))
        reqs.append(repeat_cell(sid, 7, 8, c_offset + 6, c_offset + 7, bg="#F1F5F9", fg="#334155", bold=True, size=12, align="CENTER"))
        reqs.append(repeat_cell(sid, 8, 9, c_offset, c_offset + 2, bg="#FFEDD5", fg="#9A3412", bold=True, size=11, align="CENTER"))
        reqs.append(repeat_cell(sid, 8, 9, c_offset + 6, c_offset + 7, bg="#FFEDD5", fg="#9A3412", bold=True, size=12, align="CENTER"))

        reqs.append(set_borders(sid, 4, 26, c_offset, c_offset + 7, color="#CBD5E1", outer_only=False))

    # Column widths & Row heights for Rankings
    for c_offset in (0, 8):
        reqs.append(set_col_width(sid, c_offset + 0, c_offset + 1, 60))   # Rank
        reqs.append(set_col_width(sid, c_offset + 1, c_offset + 2, 65))   # Avatar
        reqs.append(set_col_width(sid, c_offset + 2, c_offset + 3, 175))  # Player Name
        reqs.append(set_col_width(sid, c_offset + 3, c_offset + 4, 150))  # W / L / T
        reqs.append(set_col_width(sid, c_offset + 4, c_offset + 5, 75))   # Matches
        reqs.append(set_col_width(sid, c_offset + 5, c_offset + 6, 75))   # Win %
        reqs.append(set_col_width(sid, c_offset + 6, c_offset + 7, 90))   # Elo
    reqs.append(set_col_width(sid, 7, 8, 30))  # Divider col H
    reqs.append(set_row_height(sid, 0, 1, 38))
    reqs.append(set_row_height(sid, 2, 3, 34))
    reqs.append(set_row_height(sid, 4, 6, 32))
    reqs.append(set_row_height(sid, 6, 26, 32))

    # =========================================================================
    # 3. DOUBLES_MATCHES TAB
    # =========================================================================
    sid = SHEET_IDS["Doubles_Matches"]
    reqs.append(unmerge_all(sid, 0, 5, 0, 25))
    reqs.append(freeze_sheet(sid, rows=4, cols=0, hide_grid=False))
    reqs.append(merge_cells(sid, 0, 1, 0, 25))
    reqs.append(merge_cells(sid, 1, 2, 0, 25))
    reqs.append(repeat_cell(sid, 0, 1, 0, 25, bg="#0F172A", fg="#FFFFFF", bold=True, size=13, align="LEFT"))
    reqs.append(repeat_cell(sid, 1, 2, 0, 25, bg="#1E293B", fg="#94A3B8", italic=True, size=10, align="LEFT"))
    reqs.append(repeat_cell(sid, 3, 4, 0, 25, bg="#0F766E", fg="#FFFFFF", bold=True, size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 4, 5, 0, 25, bg="#F1F5F9", fg="#94A3B8", italic=True, size=9, align="CENTER"))
    reqs.append(repeat_cell(sid, 5, 55, 0, 25, bg="#FFFFFF", fg="#1E293B", size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 5, 55, 2, 6, bg="#F8FAFC", fg="#0F172A", bold=True, size=10, align="LEFT"))
    reqs.append(repeat_cell(sid, 5, 55, 20, 24, bg="#F8FAFC", fg="#0F766E", bold=True, size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 5, 55, 24, 25, bg="#FFFFFF", fg="#334155", size=9, align="LEFT"))
    reqs.append(set_borders(sid, 3, 55, 0, 25, color="#CBD5E1", outer_only=False))
    reqs.append(add_dropdown_validation(sid, 5, 55, 2, 6, "=Players!$A$4:$A$30"))
    reqs.append(set_col_width(sid, 0, 1, 65))
    reqs.append(set_col_width(sid, 1, 2, 100))
    reqs.append(set_col_width(sid, 2, 6, 145))
    reqs.append(set_col_width(sid, 6, 15, 65))
    reqs.append(set_col_width(sid, 15, 19, 95))
    reqs.append(set_col_width(sid, 19, 20, 130))
    reqs.append(set_col_width(sid, 20, 24, 75))
    reqs.append(set_col_width(sid, 24, 25, 360))

    # =========================================================================
    # 4. SINGLES_MATCHES TAB
    # =========================================================================
    sid = SHEET_IDS["Singles_Matches"]
    reqs.append(unmerge_all(sid, 0, 5, 0, 19))
    reqs.append(freeze_sheet(sid, rows=4, cols=0, hide_grid=False))
    reqs.append(merge_cells(sid, 0, 1, 0, 19))
    reqs.append(merge_cells(sid, 1, 2, 0, 19))
    reqs.append(repeat_cell(sid, 0, 1, 0, 19, bg="#0F172A", fg="#FFFFFF", bold=True, size=13, align="LEFT"))
    reqs.append(repeat_cell(sid, 1, 2, 0, 19, bg="#1E293B", fg="#94A3B8", italic=True, size=10, align="LEFT"))
    reqs.append(repeat_cell(sid, 3, 4, 0, 19, bg="#1D4ED8", fg="#FFFFFF", bold=True, size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 4, 5, 0, 19, bg="#F1F5F9", fg="#94A3B8", italic=True, size=9, align="CENTER"))
    reqs.append(repeat_cell(sid, 5, 55, 0, 19, bg="#FFFFFF", fg="#1E293B", size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 5, 55, 2, 4, bg="#F8FAFC", fg="#0F172A", bold=True, size=10, align="LEFT"))
    reqs.append(repeat_cell(sid, 5, 55, 16, 18, bg="#F8FAFC", fg="#1D4ED8", bold=True, size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 5, 55, 18, 19, bg="#FFFFFF", fg="#334155", size=9, align="LEFT"))
    reqs.append(set_borders(sid, 3, 55, 0, 19, color="#CBD5E1", outer_only=False))
    reqs.append(add_dropdown_validation(sid, 5, 55, 2, 4, "=Players!$A$4:$A$30"))
    reqs.append(set_col_width(sid, 0, 1, 65))
    reqs.append(set_col_width(sid, 1, 2, 100))
    reqs.append(set_col_width(sid, 2, 4, 155))
    reqs.append(set_col_width(sid, 4, 13, 65))
    reqs.append(set_col_width(sid, 13, 16, 95))
    reqs.append(set_col_width(sid, 16, 18, 80))
    reqs.append(set_col_width(sid, 18, 19, 320))

    # =========================================================================
    # 5. PLAYERS TAB
    # =========================================================================
    sid = SHEET_IDS["Players"]
    reqs.append(unmerge_all(sid, 0, 5, 0, 15))
    reqs.append(freeze_sheet(sid, rows=3, cols=0, hide_grid=False))
    reqs.append(merge_cells(sid, 0, 1, 0, 12))
    reqs.append(merge_cells(sid, 1, 2, 0, 12))
    reqs.append(merge_cells(sid, 0, 1, 12, 14))
    reqs.append(merge_cells(sid, 1, 2, 12, 14))
    reqs.append(repeat_cell(sid, 0, 1, 0, 12, bg="#0F172A", fg="#FFFFFF", bold=True, size=13, align="LEFT"))
    reqs.append(repeat_cell(sid, 1, 2, 0, 12, bg="#1E293B", fg="#94A3B8", italic=True, size=10, align="LEFT"))
    reqs.append(repeat_cell(sid, 0, 1, 12, 14, bg="#0F766E", fg="#FFFFFF", bold=True, size=12, align="LEFT"))
    reqs.append(repeat_cell(sid, 1, 2, 12, 14, bg="#115E59", fg="#CCFBF1", italic=True, size=9, align="LEFT"))
    reqs.append(repeat_cell(sid, 2, 3, 0, 12, bg="#1E293B", fg="#FFFFFF", bold=True, size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 2, 3, 12, 14, bg="#0F766E", fg="#FFFFFF", bold=True, size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 3, 30, 0, 12, bg="#FFFFFF", fg="#1E293B", size=10, align="CENTER"))
    reqs.append(repeat_cell(sid, 3, 30, 0, 1, bg="#F8FAFC", fg="#0F172A", bold=True, size=10, align="LEFT"))
    reqs.append(repeat_cell(sid, 3, 30, 6, 7, bg="#EFF6FF", fg="#1D4ED8", bold=True, size=11, align="CENTER"))
    reqs.append(repeat_cell(sid, 3, 30, 10, 11, bg="#F0FDFA", fg="#0F766E", bold=True, size=11, align="CENTER"))
    reqs.append(repeat_cell(sid, 3, 9, 12, 13, bg="#F8FAFC", fg="#334155", bold=True, size=10, align="LEFT"))
    reqs.append(repeat_cell(sid, 3, 9, 13, 14, bg="#FFFFFF", fg="#0F766E", bold=True, size=10, align="CENTER"))
    reqs.append(set_borders(sid, 2, 30, 0, 12, color="#CBD5E1", outer_only=False))
    reqs.append(set_borders(sid, 2, 9, 12, 14, color="#14B8A6", outer_only=False))
    reqs.append(set_col_width(sid, 0, 1, 165))
    reqs.append(set_col_width(sid, 1, 2, 100))
    reqs.append(set_col_width(sid, 2, 12, 85))
    reqs.append(set_col_width(sid, 12, 14, 175))

    return {"requests": reqs}


def main():
    payload = build_requests()
    out_path = Path("raw_format.json")
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['requests'])} formatting requests to {out_path}")


if __name__ == "__main__":
    main()
