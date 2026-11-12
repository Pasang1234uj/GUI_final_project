"""
league_table.py
---------------
Calculates standings from completed fixtures (win = 3, draw = 1, loss = 0)
and shows them on the League Table page.
"""
import tkinter as tk
from tkinter import messagebox

import mysql.connector

import ui
from database import get_fixtures, pool_names, query


def compute_standings(category, pool_name=None):
    """Return a sorted list of dicts: Team, Pool, P, W, D, L, GF, GA, GD, Pts."""
    sql = ("SELECT t.id, t.name, p.name AS pool FROM teams t "
           "JOIN pools p ON p.id = t.pool_id WHERE t.category=%s")
    params = [category]
    if pool_name and pool_name != "All":
        sql += " AND p.name=%s"
        params.append(pool_name)

    table = {r["id"]: {"Team": r["name"], "Pool": r["pool"], "P": 0, "W": 0, "D": 0,
                       "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0}
             for r in query(sql, params)}

    for f in get_fixtures("f.status='Completed' AND f.category=%s", (category,)):
        hs, aws = f["home_score"], f["away_score"]
        for team_id, gf, ga in ((f["home_team_id"], hs, aws), (f["away_team_id"], aws, hs)):
            row = table.get(team_id)
            if row is None:
                continue
            row["P"] += 1
            row["GF"] += gf
            row["GA"] += ga
            if gf > ga:
                row["W"] += 1
                row["Pts"] += 3
            elif gf == ga:
                row["D"] += 1
                row["Pts"] += 1
            else:
                row["L"] += 1

    rows = list(table.values())
    for row in rows:
        row["GD"] = row["GF"] - row["GA"]
    rows.sort(key=lambda r: (-r["Pts"], -r["GD"], -r["GF"], r["Team"].lower()))
    return rows


class LeagueTablePage(tk.Frame):
    COLUMNS = ("Pos", "Team", "Pool", "P", "W", "D", "L", "GF", "GA", "GD", "Pts")

    def __init__(self, parent, app, category="Boys"):
        super().__init__(parent, bg=ui.BG)
        self.app = app
        ui.page_header(self, "League Table", "Ranked by points, then goal difference, then goals scored")

        bar = tk.Frame(self, bg=ui.BG)
        bar.pack(fill="x", padx=24, pady=(0, 10))
        box, self.cat, _ = ui.labeled_combo(bar, "Category", ["Boys", "Girls"], category,
                                            command=self.category_changed)
        box.pack(side="left", padx=(0, 14))
        box, self.pool, self.pool_cb = ui.labeled_combo(bar, "Pool", ["All"] + pool_names(category),
                                                        "All", command=self.load)
        box.pack(side="left")

        frame, self.tree = ui.make_table(
            self, self.COLUMNS, (60, 240, 90, 60, 60, 60, 60, 70, 70, 70, 70), left=("Team",))
        frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.load()

    def category_changed(self):
        self.pool_cb["values"] = ["All"] + pool_names(self.cat.get())
        self.pool.set("All")
        self.load()

    def load(self):
        try:
            rows = compute_standings(self.cat.get(), self.pool.get())
        except mysql.connector.Error as e:
            ui.show_db_error(e)
            return
        data = [(i + 1, r["Team"], r["Pool"], r["P"], r["W"], r["D"], r["L"], r["GF"], r["GA"],
                 f"{r['GD']:+d}", r["Pts"]) for i, r in enumerate(rows)]
        tags = ["top" if i == 0 and rows[0]["P"] > 0 else "" for i in range(len(rows))]
        ui.fill_table(self.tree, data, extra_tags=tags)
