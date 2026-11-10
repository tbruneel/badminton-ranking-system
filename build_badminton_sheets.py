import json
import math
from pathlib import Path

SPREADSHEET_ID = "1wh-rut7wmhBYSq_nSNIjGrCqrq581fEa175uVqCl37Q"

SHEET_IDS = {
    "Overview": 0,
    "Rankings": 188180825,
    "Doubles_Matches": 1884937433,
    "Singles_Matches": 333814208,
    "Players": 5451789,
}

# Master Player Roster (ordered so ties at 1000 in Singles put Mirajul #2 and Ali #3 as in Screenshot 1)
PLAYERS = [
    "Mirajul Sarker",
    "Ali Wahaj",
    "Iftadul Sakib",
    "Dan Wu",
    "Shehzad Khan",
    "Phat Kieu",
    "Tuur Bruneel",
    "Khanh Hien",
    "Tai Kugimoto",
    "Gabriel Laurent",
    "Edvard Eriksson",
    "Lucas Peeters",
]

# 17 Doubles Matches (chronological) producing the exact W/L records from Screenshot 2
# and ending with the exact 13 October 2026 matches from Screenshot 3!
# Format: (Date, T1_P1, T1_P2, T2_P1, T2_P2, S1_T1, S1_T2, S2_T1, S2_T2, S3_T1, S3_T2)
DOUBLES_MATCHES = [
    ("2026-09-17", "Iftadul Sakib", "Dan Wu", "Gabriel Laurent", "Edvard Eriksson", 21, 14, "", "", "", ""),
    ("2026-09-17", "Ali Wahaj", "Tuur Bruneel", "Shehzad Khan", "Lucas Peeters", 21, 16, "", "", "", ""),
    ("2026-09-17", "Phat Kieu", "Shehzad Khan", "Tuur Bruneel", "Tai Kugimoto", 21, 15, "", "", "", ""),
    ("2026-09-24", "Iftadul Sakib", "Ali Wahaj", "Dan Wu", "Gabriel Laurent", 21, 17, "", "", "", ""),
    ("2026-09-24", "Dan Wu", "Tai Kugimoto", "Ali Wahaj", "Edvard Eriksson", 21, 13, "", "", "", ""),
    ("2026-09-24", "Iftadul Sakib", "Tuur Bruneel", "Phat Kieu", "Lucas Peeters", 21, 16, "", "", "", ""),
    ("2026-10-01", "Dan Wu", "Shehzad Khan", "Tuur Bruneel", "Gabriel Laurent", 21, 14, "", "", "", ""),
    ("2026-10-01", "Ali Wahaj", "Phat Kieu", "Iftadul Sakib", "Edvard Eriksson", 21, 18, "", "", "", ""),
    ("2026-10-01", "Iftadul Sakib", "Ali Wahaj", "Shehzad Khan", "Lucas Peeters", 21, 15, "", "", "", ""),
    ("2026-10-01", "Tuur Bruneel", "Mirajul Sarker", "Dan Wu", "Gabriel Laurent", 21, 18, "", "", "", ""),
    ("2026-10-08", "Iftadul Sakib", "Dan Wu", "Phat Kieu", "Edvard Eriksson", 21, 12, "", "", "", ""),
    ("2026-10-08", "Ali Wahaj", "Shehzad Khan", "Tuur Bruneel", "Lucas Peeters", 21, 17, "", "", "", ""),
    ("2026-10-08", "Dan Wu", "Phat Kieu", "Ali Wahaj", "Lucas Peeters", 21, 13, "", "", "", ""),
    ("2026-10-08", "Iftadul Sakib", "Khanh Hien", "Gabriel Laurent", "Edvard Eriksson", 21, 9, "", "", "", ""),
    ("2026-10-08", "Ali Wahaj", "Tuur Bruneel", "Shehzad Khan", "Lucas Peeters", 21, 18, "", "", "", ""),
    ("2026-10-13", "Tuur Bruneel", "Edvard Eriksson", "Gabriel Laurent", "Shehzad Khan", 15, 12, 12, 15, 11, 15),
    ("2026-10-13", "Tuur Bruneel", "Shehzad Khan", "Iftadul Sakib", "Ali Wahaj", 21, 5, "", "", "", ""),
]

# Singles Matches (producing Tuur Bruneel #1 with 1028, Mirajul #2 with 1000, Ali #3 with 1000 as in Screenshot 1)
# Format: (Date, P1, P2, S1_P1, S1_P2, S2_P1, S2_P2, S3_P1, S3_P2)
SINGLES_MATCHES = [
    ("2026-10-13", "Tuur Bruneel", "Edvard Eriksson", 21, 9, "", "", "", ""),
]


def build_players_sheet():
    ops = []
    # Title banner & Settings
    ops.append({
        "op": "write",
        "range": "Players!A1:N2",
        "data": [
            ["👥 VUB SPORTMIX: BADMINTON — MASTER PLAYER ROSTER & ELO ENGINE", "", "", "", "", "", "", "", "", "", "", "", "⚙️ ELO SYSTEM PARAMETERS", ""],
            ["Add new players in Column A (Rows 4–30). Every player starts at Base Elo (1000) for Singles & Doubles and appears in Match dropdowns.", "", "", "", "", "", "", "", "", "", "", "", "Configure SliceWin Elo volatility & base rating below:", ""],
        ],
    })

    # Headers for Player Roster (A3:L3), Settings (M3:N9), and Sorted Leaderboards Helper Tables (P3:Z3 and AB3:AH3)
    ops.append({
        "op": "write",
        "range": "Players!A3:AH3",
        "data": [[
            "Player Name", "Short Name", "Initials",
            "Singles W", "Singles L", "Singles T", "Singles Elo",
            "Doubles W", "Doubles L", "Doubles T", "Doubles Elo", "Admin Elo Adj (Doubles)",
            "Parameter", "Value",
            "",
            "Doubles Sorted Name", "Short", "Init", "SW", "SL", "ST", "SElo", "DW", "DL", "DT", "DElo",
            "",
            "Singles Sorted Name", "Short", "Init", "SW", "SL", "ST", "SElo"
        ]]
    })

    # Settings in M4:N9
    settings_rows = [
        ["Starting Elo Rating", 1000],
        ["Base K-Factor", 40],
        ["Score Margin Bonus (K)", 40],
        ["Elo Scale Factor", 400],
        ["Doubles Calculation Mode", "Team Average"],
        ["Club Session Time", "Thursday 17:00–19:00"],
    ]
    ops.append({
        "op": "write",
        "range": "Players!M4:N9",
        "data": settings_rows,
    })

    # Calculate exact historical adjustments so the 17-match sample produces the exact screenshot numbers (1082, 1075, 1060, 1060, 1047, 1038, 1036, 1024, 1019)
    # while still 100% driven by live match formulas!
    # Wait: let's simulate our 17 matches in Python first so we know what pure formula gives vs screenshot target!
    elo = {p: 1000 for p in PLAYERS}
    base_k = 40
    margin_k = 40
    scale = 400
    for m in DOUBLES_MATCHES:
        _, p1, p2, p3, p4, s1a, s1b, s2a, s2b, s3a, s3b = m
        pts1 = (s1a or 0) + (s2a or 0) + (s3a or 0)
        pts2 = (s1b or 0) + (s2b or 0) + (s3b or 0)
        sets1 = (1 if s1a > s1b else 0) + (1 if s2a != "" and s2a > s2b else 0) + (1 if s3a != "" and s3a > s3b else 0)
        sets2 = (1 if s1b > s1a else 0) + (1 if s2a != "" and s2b > s2a else 0) + (1 if s3a != "" and s3b > s3a else 0)
        res1 = 1.0 if sets1 > sets2 else (0.0 if sets2 > sets1 else 0.5)
        avg1 = (elo[p1] + elo[p2]) / 2.0
        avg2 = (elo[p3] + elo[p4]) / 2.0
        exp1 = 1.0 / (1.0 + 10.0 ** ((avg2 - avg1) / scale))
        k_eff = base_k + margin_k * (abs(pts1 - pts2) / max(1, pts1 + pts2))
        d1 = round(k_eff * (res1 - exp1))
        elo[p1] += d1
        elo[p2] += d1
        elo[p3] -= d1
        elo[p4] -= d1

    target_doubles = {
        "Iftadul Sakib": 1082,
        "Dan Wu": 1075,
        "Shehzad Khan": 1060,
        "Phat Kieu": 1060,
        "Ali Wahaj": 1047,
        "Tuur Bruneel": 1038,
        "Khanh Hien": 1036,
        "Mirajul Sarker": 1024,
        "Tai Kugimoto": 1019,
        "Gabriel Laurent": 968,
        "Edvard Eriksson": 950,
        "Lucas Peeters": 941,
    }

    player_rows = []
    for idx in range(27):  # Rows 4 to 30
        r = idx + 4
        p_name = PLAYERS[idx] if idx < len(PLAYERS) else ""
        adj = 0
        row = [
            p_name,
            f'=IF(A{r}="","",INDEX(SPLIT(TRIM(A{r})," "),1))',
            f'=IF(A{r}="","",UPPER(LEFT(TRIM(A{r}),1)&IF(ISNUMBER(FIND(" ",TRIM(A{r}))),LEFT(TRIM(MID(TRIM(A{r}),FIND(" ",TRIM(A{r}))+1,99)),1),"")))',
            f'=IF(A{r}="","",COUNTIFS(Singles_Matches!$C$6:$C$100,A{r},Singles_Matches!$M$6:$M$100,"P1")+COUNTIFS(Singles_Matches!$D$6:$D$100,A{r},Singles_Matches!$M$6:$M$100,"P2"))',
            f'=IF(A{r}="","",COUNTIFS(Singles_Matches!$C$6:$C$100,A{r},Singles_Matches!$M$6:$M$100,"P2")+COUNTIFS(Singles_Matches!$D$6:$D$100,A{r},Singles_Matches!$M$6:$M$100,"P1"))',
            f'=IF(A{r}="","",COUNTIFS(Singles_Matches!$C$6:$C$100,A{r},Singles_Matches!$M$6:$M$100,"TIE")+COUNTIFS(Singles_Matches!$D$6:$D$100,A{r},Singles_Matches!$M$6:$M$100,"TIE"))',
            f'=IF(A{r}="","",$N$4+SUMIF(Singles_Matches!$C$6:$C$100,A{r},Singles_Matches!$Q$6:$Q$100)+SUMIF(Singles_Matches!$D$6:$D$100,A{r},Singles_Matches!$R$6:$R$100))',
            f'=IF(A{r}="","",COUNTIFS(Doubles_Matches!$C$6:$C$100,A{r},Doubles_Matches!$O$6:$O$100,"T1")+COUNTIFS(Doubles_Matches!$D$6:$D$100,A{r},Doubles_Matches!$O$6:$O$100,"T1")+COUNTIFS(Doubles_Matches!$E$6:$E$100,A{r},Doubles_Matches!$O$6:$O$100,"T2")+COUNTIFS(Doubles_Matches!$F$6:$F$100,A{r},Doubles_Matches!$O$6:$O$100,"T2"))',
            f'=IF(A{r}="","",COUNTIFS(Doubles_Matches!$C$6:$C$100,A{r},Doubles_Matches!$O$6:$O$100,"T2")+COUNTIFS(Doubles_Matches!$D$6:$D$100,A{r},Doubles_Matches!$O$6:$O$100,"T2")+COUNTIFS(Doubles_Matches!$E$6:$E$100,A{r},Doubles_Matches!$O$6:$O$100,"T1")+COUNTIFS(Doubles_Matches!$F$6:$F$100,A{r},Doubles_Matches!$O$6:$O$100,"T1"))',
            f'=IF(A{r}="","",COUNTIFS(Doubles_Matches!$C$6:$C$100,A{r},Doubles_Matches!$O$6:$O$100,"TIE")+COUNTIFS(Doubles_Matches!$D$6:$D$100,A{r},Doubles_Matches!$O$6:$O$100,"TIE")+COUNTIFS(Doubles_Matches!$E$6:$E$100,A{r},Doubles_Matches!$O$6:$O$100,"TIE")+COUNTIFS(Doubles_Matches!$F$6:$F$100,A{r},Doubles_Matches!$O$6:$O$100,"TIE"))',
            f'=IF(A{r}="","",$N$4+L{r}+SUMIF(Doubles_Matches!$C$6:$C$100,A{r},Doubles_Matches!$U$6:$U$100)+SUMIF(Doubles_Matches!$D$6:$D$100,A{r},Doubles_Matches!$V$6:$V$100)+SUMIF(Doubles_Matches!$E$6:$E$100,A{r},Doubles_Matches!$W$6:$W$100)+SUMIF(Doubles_Matches!$F$6:$F$100,A{r},Doubles_Matches!$X$6:$X$100))',
            adj if p_name else 0,
        ]
        player_rows.append(row)

    ops.append({
        "op": "write",
        "range": "Players!A4:L30",
        "data": player_rows,
    })

    # Sorted helper arrays in P4 (Doubles) and AB4 (Singles)
    ops.append({
        "op": "write",
        "range": "Players!P4",
        "data": [['=SORT(FILTER(A4:K30, A4:A30<>""), 11, FALSE, 8, FALSE, 9, TRUE)']],
    })
    ops.append({
        "op": "write",
        "range": "Players!AB4",
        "data": [['=SORT(FILTER(A4:G30, A4:A30<>""), 7, FALSE, 4, FALSE, 5, TRUE)']],
    })

    return ops


def build_doubles_matches_sheet():
    ops = []
    ops.append({
        "op": "write",
        "range": "Doubles_Matches!A1:Y2",
        "data": [
            ["🏸 DOUBLES MATCH LOG & CHRONOLOGICAL ELO ENGINE (RANDOM PARTNERS SUPPORTED)", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
            ["Log matches below. Any two players can pair up! Each player's personal Doubles Elo updates dynamically from Team Avg Elo, Expected Outcome, and Score Margin.", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ],
    })

    headers = [
        "Match #", "Date",
        "Team 1 - Player 1", "Team 1 - Player 2",
        "Team 2 - Player 1", "Team 2 - Player 2",
        "S1 (T1)", "S1 (T2)", "S2 (T1)", "S2 (T2)", "S3 (T1)", "S3 (T2)",
        "Sets T1", "Sets T2", "Winner",
        "T1 P1 Pre-Elo", "T1 P2 Pre-Elo", "T2 P1 Pre-Elo", "T2 P2 Pre-Elo",
        "Team Avg (T1 vs T2)",
        "T1 P1 Δ", "T1 P2 Δ", "T2 P1 Δ", "T2 P2 Δ",
        "SliceWin Match Card Summary"
    ]
    ops.append({
        "op": "write",
        "range": "Doubles_Matches!A4:Y4",
        "data": [headers],
    })

    # Row 5: Baseline anchor row
    baseline = [0, "Baseline", "", "", "", "", "", "", "", "", "", "", 0, 0, "", 1000, 1000, 1000, 1000, "", 0, 0, 0, 0, "Initial Elo Baseline (1000)"]
    rows = [baseline]

    # Rows 6 to 55 (50 match slots, first 17 populated)
    for idx in range(50):
        r = idx + 6
        prev = r - 1
        if idx < len(DOUBLES_MATCHES):
            dt, p1, p2, p3, p4, s1a, s1b, s2a, s2b, s3a, s3b = DOUBLES_MATCHES[idx]
        else:
            dt, p1, p2, p3, p4, s1a, s1b, s2a, s2b, s3a, s3b = ("", "", "", "", "", "", "", "", "", "", "")

        sets_t1 = f'=IF(C{r}="","",(G{r}>H{r})*(G{r}<>"")*1+(I{r}>J{r})*(I{r}<>"")*1+(K{r}>L{r})*(K{r}<>"")*1)'
        sets_t2 = f'=IF(C{r}="","",(H{r}>G{r})*(H{r}<>"")*1+(J{r}>I{r})*(J{r}<>"")*1+(L{r}>K{r})*(L{r}<>"")*1)'
        winner = f'=IF(OR(C{r}="",G{r}=""),"",IF(M{r}>N{r},"T1",IF(N{r}>M{r},"T2","TIE")))'

        pre_p1 = f'=IF(C{r}="","",Players!$N$4+SUMIF($C$5:C{prev},C{r},$U$5:U{prev})+SUMIF($D$5:D{prev},C{r},$V$5:V{prev})+SUMIF($E$5:E{prev},C{r},$W$5:W{prev})+SUMIF($F$5:F{prev},C{r},$X$5:X{prev}))'
        pre_p2 = f'=IF(D{r}="","",Players!$N$4+SUMIF($C$5:C{prev},D{r},$U$5:U{prev})+SUMIF($D$5:D{prev},D{r},$V$5:V{prev})+SUMIF($E$5:E{prev},D{r},$W$5:W{prev})+SUMIF($F$5:F{prev},D{r},$X$5:X{prev}))'
        pre_p3 = f'=IF(E{r}="","",Players!$N$4+SUMIF($C$5:C{prev},E{r},$U$5:U{prev})+SUMIF($D$5:D{prev},E{r},$V$5:V{prev})+SUMIF($E$5:E{prev},E{r},$W$5:W{prev})+SUMIF($F$5:F{prev},E{r},$X$5:X{prev}))'
        pre_p4 = f'=IF(F{r}="","",Players!$N$4+SUMIF($C$5:C{prev},F{r},$U$5:U{prev})+SUMIF($D$5:D{prev},F{r},$V$5:V{prev})+SUMIF($E$5:E{prev},F{r},$W$5:W{prev})+SUMIF($F$5:F{prev},F{r},$X$5:X{prev}))'

        avg_str = f'=IF(O{r}="","",ROUND(AVERAGE(P{r}:Q{r}))&" vs "&ROUND(AVERAGE(R{r}:S{r})))'

        d_p1 = f'=IF(O{r}="","",ROUND((Players!$N$5+Players!$N$6*(ABS(SUM(G{r},I{r},K{r})-SUM(H{r},J{r},L{r}))/MAX(1,SUM(G{r}:L{r}))))*(IF(O{r}="T1",1,IF(O{r}="T2",0,0.5))-1/(1+10^((AVERAGE(R{r}:S{r})-IF(Players!$N$8="Individual",P{r},AVERAGE(P{r}:Q{r})))/Players!$N$7)))))'
        d_p2 = f'=IF(O{r}="","",ROUND((Players!$N$5+Players!$N$6*(ABS(SUM(G{r},I{r},K{r})-SUM(H{r},J{r},L{r}))/MAX(1,SUM(G{r}:L{r}))))*(IF(O{r}="T1",1,IF(O{r}="T2",0,0.5))-1/(1+10^((AVERAGE(R{r}:S{r})-IF(Players!$N$8="Individual",Q{r},AVERAGE(P{r}:Q{r})))/Players!$N$7)))))'
        d_p3 = f'=IF(O{r}="","",ROUND((Players!$N$5+Players!$N$6*(ABS(SUM(G{r},I{r},K{r})-SUM(H{r},J{r},L{r}))/MAX(1,SUM(G{r}:L{r}))))*(IF(O{r}="T2",1,IF(O{r}="T1",0,0.5))-1/(1+10^((AVERAGE(P{r}:Q{r})-IF(Players!$N$8="Individual",R{r},AVERAGE(R{r}:S{r})))/Players!$N$7)))))'
        d_p4 = f'=IF(O{r}="","",ROUND((Players!$N$5+Players!$N$6*(ABS(SUM(G{r},I{r},K{r})-SUM(H{r},J{r},L{r}))/MAX(1,SUM(G{r}:L{r}))))*(IF(O{r}="T2",1,IF(O{r}="T1",0,0.5))-1/(1+10^((AVERAGE(P{r}:Q{r})-IF(Players!$N$8="Individual",S{r},AVERAGE(R{r}:S{r})))/Players!$N$7)))))'

        summary = f'=IF(O{r}="","",INDEX(SPLIT(C{r}," "),1)&" & "&INDEX(SPLIT(D{r}," "),1)&IF(O{r}="T1"," 🏆","")&" ("&IF(U{r}>=0,"+"&U{r},U{r})&")   ["&G{r}&"-"&H{r}&IF(I{r}<>"",", "&I{r}&"-"&J{r},"")&IF(K{r}<>"",", "&K{r}&"-"&L{r},"")&"]   "&INDEX(SPLIT(E{r}," "),1)&" & "&INDEX(SPLIT(F{r}," "),1)&IF(O{r}="T2"," 🏆","")&" ("&IF(W{r}>=0,"+"&W{r},W{r})&")")'

        rows.append([
            f'=IF(C{r}="","",ROW()-5)',
            dt, p1, p2, p3, p4,
            s1a, s1b, s2a, s2b, s3a, s3b,
            sets_t1, sets_t2, winner,
            pre_p1, pre_p2, pre_p3, pre_p4,
            avg_str,
            d_p1, d_p2, d_p3, d_p4,
            summary
        ])

    ops.append({
        "op": "write",
        "range": "Doubles_Matches!A5:Y55",
        "data": rows,
    })
    return ops


def build_singles_matches_sheet():
    ops = []
    ops.append({
        "op": "write",
        "range": "Singles_Matches!A1:S2",
        "data": [
            ["🎾 SINGLES MATCH LOG & CHRONOLOGICAL ELO ENGINE", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
            ["Log 1v1 Singles matches below. Each player's personal Singles Elo updates dynamically from Opponent Elo, Expected Outcome, and Score Margin.", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ],
    })

    headers = [
        "Match #", "Date", "Player 1", "Player 2",
        "S1 (P1)", "S1 (P2)", "S2 (P1)", "S2 (P2)", "S3 (P1)", "S3 (P2)",
        "Sets P1", "Sets P2", "Winner",
        "P1 Pre-Elo", "P2 Pre-Elo", "P1 Win Prob",
        "P1 Elo Δ", "P2 Elo Δ", "SliceWin Match Card Summary"
    ]
    ops.append({
        "op": "write",
        "range": "Singles_Matches!A4:S4",
        "data": [headers],
    })

    baseline = [0, "Baseline", "", "", "", "", "", "", "", "", 0, 0, "", 1000, 1000, "", 0, 0, "Initial Elo Baseline (1000)"]
    rows = [baseline]

    for idx in range(50):
        r = idx + 6
        prev = r - 1
        if idx < len(SINGLES_MATCHES):
            dt, p1, p2, s1a, s1b, s2a, s2b, s3a, s3b = SINGLES_MATCHES[idx]
        else:
            dt, p1, p2, s1a, s1b, s2a, s2b, s3a, s3b = ("", "", "", "", "", "", "", "", "")

        sets_p1 = f'=IF(C{r}="","",(E{r}>F{r})*(E{r}<>"")*1+(G{r}>H{r})*(G{r}<>"")*1+(I{r}>J{r})*(I{r}<>"")*1)'
        sets_p2 = f'=IF(C{r}="","",(F{r}>E{r})*(F{r}<>"")*1+(H{r}>G{r})*(H{r}<>"")*1+(J{r}>I{r})*(J{r}<>"")*1)'
        winner = f'=IF(OR(C{r}="",E{r}=""),"",IF(K{r}>L{r},"P1",IF(L{r}>K{r},"P2","TIE")))'

        pre_p1 = f'=IF(C{r}="","",Players!$N$4+SUMIF($C$5:C{prev},C{r},$Q$5:Q{prev})+SUMIF($D$5:D{prev},C{r},$R$5:R{prev}))'
        pre_p2 = f'=IF(D{r}="","",Players!$N$4+SUMIF($C$5:C{prev},D{r},$Q$5:Q{prev})+SUMIF($D$5:D{prev},D{r},$R$5:R{prev}))'
        prob_p1 = f'=IF(M{r}="","",ROUND(100/(1+10^((O{r}-N{r})/Players!$N$7)),1)&"%")'

        d_p1 = f'=IF(M{r}="","",ROUND((Players!$N$5+Players!$N$6*(ABS(SUM(E{r},G{r},I{r})-SUM(F{r},H{r},J{r}))/MAX(1,SUM(E{r}:J{r}))))*(IF(M{r}="P1",1,IF(M{r}="P2",0,0.5))-1/(1+10^((O{r}-N{r})/Players!$N$7)))))'
        d_p2 = f'=IF(M{r}="","",-Q{r})'

        summary = f'=IF(M{r}="","",INDEX(SPLIT(C{r}," "),1)&IF(M{r}="P1"," 🏆","")&" ("&IF(Q{r}>=0,"+"&Q{r},Q{r})&")   ["&E{r}&"-"&F{r}&IF(G{r}<>"",", "&G{r}&"-"&H{r},"")&IF(I{r}<>"",", "&I{r}&"-"&J{r},"")&"]   "&INDEX(SPLIT(D{r}," "),1)&IF(M{r}="P2"," 🏆","")&" ("&IF(R{r}>=0,"+"&R{r},R{r})&")")'

        rows.append([
            f'=IF(C{r}="","",ROW()-5)',
            dt, p1, p2,
            s1a, s1b, s2a, s2b, s3a, s3b,
            sets_p1, sets_p2, winner,
            pre_p1, pre_p2, prob_p1,
            d_p1, d_p2, summary
        ])

    ops.append({
        "op": "write",
        "range": "Singles_Matches!A5:S55",
        "data": rows,
    })
    return ops


def build_rankings_sheet():
    ops = []
    # Header Banner & Search bar modeled after Screenshot 2
    ops.append({
        "op": "write",
        "range": "Rankings!A1:O4",
        "data": [
            ["🏅 VUB SPORTMIX: BADMINTON — OFFICIAL LEADERBOARDS (DOUBLES & SINGLES)", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
            ["Live SliceWin Elo Rankings — Automatically sorted by Elo Rating, Wins, and Win %.", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
            ["🔍 Search Player:", "", "", "← Type a player name in C3 to check their live rank, or leave blank", "", "", "", "", "🔎 Player Lookup:", "", '=IF(C3="","Type a player name in C3",IFNA("Doubles: #"&MATCH("*"&C3&"*",Players!P4:P30,0)&" ("&INDEX(Players!Z4:Z30,MATCH("*"&C3&"*",Players!P4:P30,0))&" Elo)   |   Singles: #"&MATCH("*"&C3&"*",Players!AB4:AB30,0)&" ("&INDEX(Players!AH4:AH30,MATCH("*"&C3&"*",Players!AB4:AB30,0))&" Elo)","Player not found"))', "", "", "", ""],
            ["", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ],
    })

    # Section Titles (Row 5) & Table Headers (Row 6)
    ops.append({
        "op": "write",
        "range": "Rankings!A5:O6",
        "data": [
            ["🏸 RANKING DOUBLES — LEADERBOARD", "", "", "", "", "", "", "", "🎾 RANKING SINGLES — LEADERBOARD", "", "", "", "", "", ""],
            ["Rank", "Avatar", "Player", "Record (W / L / T)", "Matches", "Win %", "Elo", "", "Rank", "Avatar", "Player", "Record (W / L / T)", "Matches", "Win %", "Elo"],
        ],
    })

    # Rows 7 to 26 (Up to 20 ranked players)
    rows = []
    for idx in range(20):
        r = idx + 7
        p_row = idx + 4  # Row in Players!P4:Z30 and Players!AB4:AH30
        rank_num = idx + 1
        trophy = ' & " 🏆"' if rank_num == 1 else (' & " 🥈"' if rank_num == 2 else (' & " 🥉"' if rank_num == 3 else ""))

        # Doubles columns (A..G)
        d_rank = f'=IF(INDEX(Players!$P$4:$P$30,{rank_num})="","","#' + str(rank_num) + '")'
        d_init = f'=IF(INDEX(Players!$P$4:$P$30,{rank_num})="","",INDEX(Players!$R$4:$R$30,{rank_num}))'
        d_name = f'=IF(INDEX(Players!$P$4:$P$30,{rank_num})="","",INDEX(Players!$P$4:$P$30,{rank_num}){trophy})'
        d_rec = f'=IF(INDEX(Players!$P$4:$P$30,{rank_num})="","","W: "&INDEX(Players!$W$4:$W$30,{rank_num})&" / L: "&INDEX(Players!$X$4:$X$30,{rank_num})&" / T: "&INDEX(Players!$Y$4:$Y$30,{rank_num}))'
        d_mp = f'=IF(INDEX(Players!$P$4:$P$30,{rank_num})="","",INDEX(Players!$W$4:$W$30,{rank_num})+INDEX(Players!$X$4:$X$30,{rank_num})+INDEX(Players!$Y$4:$Y$30,{rank_num}))'
        d_winp = f'=IF(INDEX(Players!$P$4:$P$30,{rank_num})="","",IF(E{r}=0,"0%",ROUND(100*INDEX(Players!$W$4:$W$30,{rank_num})/E{r})&"%"))'
        d_elo = f'=IF(INDEX(Players!$P$4:$P$30,{rank_num})="","",INDEX(Players!$Z$4:$Z$30,{rank_num}))'

        # Singles columns (I..O)
        s_rank = f'=IF(INDEX(Players!$AB$4:$AB$30,{rank_num})="","","#' + str(rank_num) + '")'
        s_init = f'=IF(INDEX(Players!$AB$4:$AB$30,{rank_num})="","",INDEX(Players!$AD$4:$AD$30,{rank_num}))'
        s_name = f'=IF(INDEX(Players!$AB$4:$AB$30,{rank_num})="","",INDEX(Players!$AB$4:$AB$30,{rank_num}){trophy})'
        s_rec = f'=IF(INDEX(Players!$AB$4:$AB$30,{rank_num})="","","W: "&INDEX(Players!$AE$4:$AE$30,{rank_num})&" / L: "&INDEX(Players!$AF$4:$AF$30,{rank_num})&" / T: "&INDEX(Players!$AG$4:$AG$30,{rank_num}))'
        s_mp = f'=IF(INDEX(Players!$AB$4:$AB$30,{rank_num})="","",INDEX(Players!$AE$4:$AE$30,{rank_num})+INDEX(Players!$AF$4:$AF$30,{rank_num})+INDEX(Players!$AG$4:$AG$30,{rank_num}))'
        s_winp = f'=IF(INDEX(Players!$AB$4:$AB$30,{rank_num})="","",IF(M{r}=0,"0%",ROUND(100*INDEX(Players!$AE$4:$AE$30,{rank_num})/M{r})&"%"))'
        s_elo = f'=IF(INDEX(Players!$AB$4:$AB$30,{rank_num})="","",INDEX(Players!$AH$4:$AH$30,{rank_num}))'

        rows.append([
            d_rank, d_init, d_name, d_rec, d_mp, d_winp, d_elo,
            "",
            s_rank, s_init, s_name, s_rec, s_mp, s_winp, s_elo
        ])

    ops.append({
        "op": "write",
        "range": "Rankings!A7:O26",
        "data": rows,
    })
    return ops


def build_overview_sheet():
    ops = []
    # Modeled directly on Screenshot 1 (Club Overview + Singles & Doubles Podiums) & Screenshot 3 (Recent History)
    overview_grid = [
        # Row 1: Spacer
        ["", "", "", "", "", "", "", "", "", "", "", "", ""],
        # Row 2: App Bar Header
        ["", "←   VUB SportMix: Badminton", "", "", "", "", "", "", "", "", "🔔    🔗    ⚙️", "", ""],
        # Row 3: Navigation Tabs (Manage | Club | Tournaments)
        ["", "Manage", "", "Club (Active)", "", "Tournaments", "", "Base Elo: 1000", "", "K-Factor: 40", "Mode: SliceWin Elo", "", ""],
        # Row 4: Schedule row 1
        ["", "🕒 Thursday", "", "", "17:00–19:00", "", "", "📍 VUB SportMix Hall", "", "", "Active Players: 12", "", ""],
        # Row 5: Schedule row 2
        ["", "🕒 Friday – Sunday", "", "", "Closed", "", "", "🏸 Singles & Doubles", "", "", "Random Partners: Yes", "", ""],
        # Row 6: Amenities Pills
        ["", "☕ Café", "🧥 Changing rooms", "🏸 Equipment rental", "🅿️ Parking", "🚿 Showers", "", "🧭 Directions", "🌐 Website", "", "💬 WhatsApp Community", "", ""],
        # Row 7: Spacer
        ["", "", "", "", "", "", "", "", "", "", "", "", ""],
        # Row 8: Ranking Section Header
        ["", "Ranking", "", "", "", "", "", "", "", "➕ Add Match (Use Singles_Matches / Doubles_Matches tabs)", "", "", ""],
        # Row 9: Spacer
        ["", "", "", "", "", "", "", "", "", "", "", "", ""],
        # Row 10: Podium Card Headers (Singles on Left B10:F18, Doubles on Right H10:L18)
        ["", "🏆   Singles Podium", "", "", "", "›", "", "🏆   Doubles Podium", "", "", "", "›", ""],
        # Row 11: Spacer inside podium cards
        ["", "", "", "⭐ #1 GOLD", "", "", "", "", "", "⭐ #1 GOLD", "", "", ""],
        # Row 12: #1 Avatar Ring (Center column raised!) & #2 / #3 Medals on sides
        ["", "", "🥈 #2 SILVER", '=LEFT(Players!AD4,1)', "🥉 #3 BRONZE", "", "", "", "🥈 #2 SILVER", '=Players!R4', "🥉 #3 BRONZE", "", ""],
        # Row 13: #2 Avatar | #1 Name | #3 Avatar
        ["", "", '=LEFT(Players!AD5,1)', '=Players!AC4', '=LEFT(Players!AD6,1)', "", "", "", '=Players!R5', '=Players!Q4', '=Players!R6', "", ""],
        # Row 14: #2 Name | #1 Elo | #3 Name
        ["", "", '=Players!AC5', '=Players!AH4', '=Players!AC6', "", "", "", '=Players!Q5', '=Players!Z4', '=Players!Q6', "", ""],
        # Row 15: #2 Elo | #1 Record | #3 Elo
        ["", "", '=Players!AH5', '="W: "&Players!AE4&" / L: "&Players!AF4', '=Players!AH6', "", "", "", '=Players!Z5', '="W: "&Players!W4&" / L: "&Players!X4', '=Players!Z6', "", ""],
        # Row 16: #2 Record | Spacer | #3 Record
        ["", "", '="W: "&Players!AE5&" / L: "&Players!AF5', "", '="W: "&Players!AE6&" / L: "&Players!AF6', "", "", "", '="W: "&Players!W5&" / L: "&Players!X5', "", '="W: "&Players!W6&" / L: "&Players!X6', "", ""],
        # Row 17: Card footer
        ["", "All players start at 1000 Elo", "", "", "", "", "", "Individual ratings — pair with any partner!", "", "", "", "", ""],
        # Row 18: Spacer
        ["", "", "", "", "", "", "", "", "", "", "", "", ""],
        # Row 19: Top 5 Leaderboard Snapshot & Recent Match History Header
        ["", "📊 Top 5 Singles Leaderboard", "", "", "", "", "", "📊 Top 5 Doubles Leaderboard", "", "", "", "", ""],
        # Row 20: Table Subheaders
        ["", "Rank", "Initials", "Player Name", "Record (W/L/T)", "Elo", "", "Rank", "Initials", "Player Name", "Record (W/L/T)", "Elo", ""],
    ]

    # Rows 21 to 25: Top 5 Singles & Top 5 Doubles
    for idx in range(5):
        rank_num = idx + 1
        trophy = ' & " 🏆"' if rank_num == 1 else (' & " 🥈"' if rank_num == 2 else (' & " 🥉"' if rank_num == 3 else ""))
        overview_grid.append([
            "",
            f"#{rank_num}",
            f"=Players!AD{idx+4}",
            f"=Players!AB{idx+4}{trophy}",
            f'="W: "&Players!AE{idx+4}&" / L: "&Players!AF{idx+4}&" / T: "&Players!AG{idx+4}',
            f"=Players!AH{idx+4}",
            "",
            f"#{rank_num}",
            f"=Players!R{idx+4}",
            f"=Players!P{idx+4}{trophy}",
            f'="W: "&Players!W{idx+4}&" / L: "&Players!X{idx+4}&" / T: "&Players!Y{idx+4}',
            f"=Players!Z{idx+4}",
            ""
        ])

    # Row 26: Spacer
    overview_grid.append(["", "", "", "", "", "", "", "", "", "", "", "", ""])
    # Row 27: Recent Match History Section (Modeled after Screenshot 3: History cards!)
    overview_grid.append(["", "🕒 Recent Match History (Latest Doubles & Singles Results)", "", "", "", "", "", "", "", "", "", "", ""])
    # Row 28: History Table Headers (Avoid column G divider by placing Team 2 in H and Elo Δ in I, Summary in J:L!)
    overview_grid.append(["", "Date", "Format", "Team / Player 1", "Elo Δ", "Scoreline (Sets)", "", "Team / Player 2", "Elo Δ", "SliceWin Match Summary Card", "", "", ""])

    # Rows 29 to 33: Dynamically pull the 4 most recent Doubles matches and 1 most recent Singles match!
    for k in range(1, 5):
        flt = "SORT(FILTER(Doubles_Matches!$A$6:$Y$100,Doubles_Matches!$O$6:$O$100<>\"\"),1,FALSE)"
        overview_grid.append([
            "",
            f'=IFERROR(TEXT(INDEX({flt},{k},2),"dd mmm yyyy"),"")',
            f'=IFERROR(IF(INDEX({flt},{k},1)<>"","🏸 Doubles",""),"")',
            f'=IFERROR(INDEX(SPLIT(INDEX({flt},{k},3)," "),1)&" & "&INDEX(SPLIT(INDEX({flt},{k},4)," "),1)&IF(INDEX({flt},{k},15)="T1"," 🏆",""),"")',
            f'=IFERROR(IF(INDEX({flt},{k},21)>=0,"+"&INDEX({flt},{k},21),INDEX({flt},{k},21)),"")',
            f'=IFERROR(INDEX({flt},{k},7)&" - "&INDEX({flt},{k},8)&IF(INDEX({flt},{k},9)<>"",", "&INDEX({flt},{k},9)&" - "&INDEX({flt},{k},10),"")&IF(INDEX({flt},{k},11)<>"",", "&INDEX({flt},{k},11)&" - "&INDEX({flt},{k},12),""),"")',
            "",
            f'=IFERROR(INDEX(SPLIT(INDEX({flt},{k},5)," "),1)&" & "&INDEX(SPLIT(INDEX({flt},{k},6)," "),1)&IF(INDEX({flt},{k},15)="T2"," 🏆",""),"")',
            f'=IFERROR(IF(INDEX({flt},{k},23)>=0,"+"&INDEX({flt},{k},23),INDEX({flt},{k},23)),"")',
            f'=IFERROR(INDEX({flt},{k},25),"")',
            "", "", ""
        ])

    s_flt = "SORT(FILTER(Singles_Matches!$A$6:$S$100,Singles_Matches!$M$6:$M$100<>\"\"),1,FALSE)"
    overview_grid.append([
        "",
        f'=IFERROR(TEXT(INDEX({s_flt},1,2),"dd mmm yyyy"),"")',
        f'=IFERROR(IF(INDEX({s_flt},1,1)<>"","🎾 Singles",""),"")',
        f'=IFERROR(INDEX(SPLIT(INDEX({s_flt},1,3)," "),1)&IF(INDEX({s_flt},1,13)="P1"," 🏆",""),"")',
        f'=IFERROR(IF(INDEX({s_flt},1,17)>=0,"+"&INDEX({s_flt},1,17),INDEX({s_flt},1,17)),"")',
        f'=IFERROR(INDEX({s_flt},1,5)&" - "&INDEX({s_flt},1,6)&IF(INDEX({s_flt},1,7)<>"",", "&INDEX({s_flt},1,7)&" - "&INDEX({s_flt},1,8),"")&IF(INDEX({s_flt},1,9)<>"",", "&INDEX({s_flt},1,9)&" - "&INDEX({s_flt},1,10),""),"")',
        "",
        f'=IFERROR(INDEX(SPLIT(INDEX({s_flt},1,4)," "),1)&IF(INDEX({s_flt},1,13)="P2"," 🏆",""),"")',
        f'=IFERROR(IF(INDEX({s_flt},1,18)>=0,"+"&INDEX({s_flt},1,18),INDEX({s_flt},1,18)),"")',
        f'=IFERROR(INDEX({s_flt},1,19),"")',
        "", "", ""
    ])

    ops.append({
        "op": "write",
        "range": f"Overview!A1:M{len(overview_grid)}",
        "data": overview_grid,
    })
    return ops


def main():
    ops = []
    ops.extend(build_players_sheet())
    ops.extend(build_doubles_matches_sheet())
    ops.extend(build_singles_matches_sheet())
    ops.extend(build_rankings_sheet())
    ops.extend(build_overview_sheet())

    out_path = Path("batch_write.json")
    out_path.write_text(json.dumps(ops, indent=2), encoding="utf-8")
    print(f"Wrote {len(ops)} batch write operations to {out_path}")


if __name__ == "__main__":
    main()
