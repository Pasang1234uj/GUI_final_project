"""
fixture.py
----------
Modern manual multi-match fixture builder for the Football League Management System.

The administrator selects a category and pool, chooses participating teams,
then creates as many editable match rows as needed. Drafts stay in the page
until the administrator confirms the complete schedule. Confirmed fixtures
are inserted in one MySQL transaction.
"""
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

import mysql.connector

import ui
import validators as V
from database import Transaction, execute, get_fixtures, get_pools, pool_names, query


class MatchRow:
    """One editable match card in the bulk fixture builder."""

    def __init__(self, page, number):
        self.page = page
        self.number = number
        self.frame = tk.Frame(page.rows_inner, bg=ui.WHITE, highlightbackground=ui.BORDER,
                              highlightthickness=1, padx=12, pady=10)
        self.frame.pack(fill="x", pady=(0, 9))
        top = tk.Frame(self.frame, bg=ui.WHITE)
        top.pack(fill="x")
        self.title = tk.Label(top, text=f"MATCH {number:02d}", bg=ui.WHITE,
                              fg=ui.NAVY, font=ui.FONT_B)
        self.title.pack(side="left")
        ui.button(top, "Remove", self.remove, "danger").pack(side="right")

        teams = tk.Frame(self.frame, bg=ui.WHITE)
        teams.pack(fill="x", pady=(9, 8))
        self.home = tk.StringVar()
        self.away = tk.StringVar()
        left = tk.Frame(teams, bg=ui.WHITE)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text="HOME TEAM", bg=ui.WHITE, fg=ui.MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.home_cb = ttk.Combobox(left, textvariable=self.home, state="readonly", font=ui.FONT)
        self.home_cb.pack(fill="x", pady=(3, 0))
        middle = tk.Label(teams, text="VS", bg=ui.WHITE, fg=ui.BLUE,
                          font=("Segoe UI", 12, "bold"), padx=12)
        middle.pack(side="left", pady=(14, 0))
        right = tk.Frame(teams, bg=ui.WHITE)
        right.pack(side="left", fill="x", expand=True)
        tk.Label(right, text="AWAY TEAM", bg=ui.WHITE, fg=ui.MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.away_cb = ttk.Combobox(right, textvariable=self.away, state="readonly", font=ui.FONT)
        self.away_cb.pack(fill="x", pady=(3, 0))

        details = tk.Frame(self.frame, bg=ui.WHITE)
        details.pack(fill="x")
        self.day = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.kickoff = tk.StringVar(value="10:00")
        self.venue = tk.StringVar(value="College Ground")
        self._field(details, "DATE (YYYY-MM-DD)", self.day, 16).pack(side="left", padx=(0, 12))
        self._field(details, "KICK-OFF (HH:MM)", self.kickoff, 12).pack(side="left", padx=(0, 12))
        self._field(details, "VENUE", self.venue, 24).pack(side="left", fill="x", expand=True)

        self.note = tk.Label(self.frame, text="Choose two different teams.",
                             bg=ui.WHITE, fg=ui.MUTED, font=ui.FONT_SMALL)
        self.note.pack(anchor="w", pady=(7, 0))
        self.home_cb.bind("<<ComboboxSelected>>", lambda e: self.validate())
        self.away_cb.bind("<<ComboboxSelected>>", lambda e: self.validate())
        self.refresh_teams(page.team_names)

    def _field(self, parent, label, variable, width):
        box = tk.Frame(parent, bg=ui.WHITE)
        tk.Label(box, text=label, bg=ui.WHITE, fg=ui.MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Entry(box, textvariable=variable, width=width, font=ui.FONT).pack(fill="x", pady=(3, 0))
        return box

    def refresh_teams(self, names):
        old_home, old_away = self.home.get(), self.away.get()
        self.home_cb["values"] = names
        self.away_cb["values"] = names
        self.home.set(old_home if old_home in names else (names[0] if names else ""))
        self.away.set(old_away if old_away in names else (names[1] if len(names) > 1 else ""))
        self.validate()

    def validate(self):
        home, away = self.home.get(), self.away.get()
        if not home or not away:
            msg, colour = "Choose both teams. Select at least two participating teams above.", ui.RED
        elif home == away:
            msg, colour = "Home and away teams must be different.", ui.RED
        else:
            msg, colour = "Match details ready to review.", ui.GREEN
        self.note.config(text=msg, fg=colour)

    def remove(self):
        self.page.remove_match(self)


class FixturePage(tk.Frame):
    def __init__(self, parent, app, category="All"):
        super().__init__(parent, bg=ui.BG)
        self.app = app
        self.category = category if category in ("Boys", "Girls") else "Boys"
        self.pool_map = {}
        self.team_rows = []
        self.team_vars = {}
        self.team_names = []
        self.matches = []
        self.draft_saved = False

        self._build_scrollable_page()
        self._build_builder()
        self._build_published_table()
        self.refresh_pools()
        self.load()

    # ---- scrollable page shell -----------------------------------------
    def _build_scrollable_page(self):
        self.canvas = tk.Canvas(self, bg=ui.BG, highlightthickness=0)
        self.vscroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vscroll.set)
        self.vscroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=ui.BG)
        self.window_id = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window_id, width=e.width))
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        self.canvas.bind("<Destroy>", self._unbind_mousewheel)

    def _bind_mousewheel(self, event=None):
        self.canvas.bind_all("<MouseWheel>", self._mousewheel)

    def _unbind_mousewheel(self, event=None):
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass

    def _mousewheel(self, event):
        if self.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _section(self, parent, title, subtitle=None):
        card = tk.Frame(parent, bg=ui.WHITE, highlightbackground=ui.BORDER, highlightthickness=1)
        card.pack(fill="x", padx=24, pady=(0, 12))
        head = tk.Frame(card, bg=ui.WHITE)
        head.pack(fill="x", padx=16, pady=(13, 5))
        tk.Label(head, text=title, bg=ui.WHITE, fg=ui.NAVY, font=ui.FONT_H2).pack(anchor="w")
        if subtitle:
            tk.Label(head, text=subtitle, bg=ui.WHITE, fg=ui.MUTED, font=ui.FONT_SMALL).pack(anchor="w", pady=(2, 0))
        content = tk.Frame(card, bg=ui.WHITE)
        content.pack(fill="x", padx=16, pady=(7, 15))
        return content

    def _build_builder(self):
        right = ui.page_header(self.body, "Fixture Manager",
                               "Plan a full tournament schedule manually. Nothing is published until you confirm.")
        if not self.app.can_edit:
            tk.Label(right, text="VIEW ONLY", bg=ui.BG, fg=ui.MUTED, font=ui.FONT_B).pack()

        settings = self._section(self.body, "01  Tournament settings",
                                 "Choose the category and pool whose registered teams will take part.")
        self.cat_var = tk.StringVar(value=self.category)
        self.pool_var = tk.StringVar()
        self._labeled_control(settings, "CATEGORY", self.cat_var, ["Boys", "Girls"], self.category,
                              self.category_changed).pack(side="left", padx=(0, 16))
        self.pool_control = self._labeled_control(settings, "POOL", self.pool_var, [], "",
                                                  self.pool_changed)
        self.pool_control.pack(side="left", padx=(0, 16))
        self.team_count = tk.Label(settings, text="0 teams selected", bg=ui.WHITE,
                                   fg=ui.MUTED, font=ui.FONT_B)
        self.team_count.pack(side="right", padx=5)

        teams_card = self._section(self.body, "02  Participating teams",
                                   "Tick the teams you want to use. Match dropdowns below will use this selection.")
        team_top = tk.Frame(teams_card, bg=ui.WHITE)
        team_top.pack(fill="x", pady=(0, 8))
        if self.app.can_edit:
            ui.button(team_top, "Select all", self.select_all, "outline").pack(side="left")
            ui.button(team_top, "Clear selection", self.clear_selection, "grey").pack(side="left", padx=7)
        self.team_list_frame = tk.Frame(teams_card, bg=ui.WHITE)
        self.team_list_frame.pack(fill="x")
        self.no_teams_label = tk.Label(self.team_list_frame, text="No teams found in this pool. Register teams first.",
                                       bg=ui.WHITE, fg=ui.MUTED, font=ui.FONT)
        self.no_teams_label.pack(anchor="w", pady=6)

        match_card = self._section(self.body, "03  Build your match schedule",
                                   "Add match cards, choose each home and away team, then set the date, kick-off and venue.")
        self.match_toolbar = tk.Frame(match_card, bg=ui.WHITE)
        self.match_toolbar.pack(fill="x", pady=(0, 9))
        self.match_count = tk.Label(self.match_toolbar, text="0 matches added", bg=ui.WHITE,
                                    fg=ui.MUTED, font=ui.FONT_B)
        self.match_count.pack(side="left")
        if self.app.can_edit:
            ui.button(self.match_toolbar, "+  Add Match", self.add_match).pack(side="right")
        self.rows_shell = tk.Frame(match_card, bg=ui.WHITE)
        self.rows_shell.pack(fill="x")
        self.rows_canvas = tk.Canvas(self.rows_shell, bg=ui.WHITE, height=300, highlightthickness=0)
        self.rows_scroll = ttk.Scrollbar(self.rows_shell, orient="vertical", command=self.rows_canvas.yview)
        self.rows_canvas.configure(yscrollcommand=self.rows_scroll.set)
        self.rows_canvas.pack(side="left", fill="x", expand=True)
        self.rows_scroll.pack(side="right", fill="y")
        self.rows_inner = tk.Frame(self.rows_canvas, bg=ui.WHITE)
        self.rows_window = self.rows_canvas.create_window((0, 0), window=self.rows_inner, anchor="nw")
        self.rows_inner.bind("<Configure>", lambda e: self.rows_canvas.configure(scrollregion=self.rows_canvas.bbox("all")))
        self.rows_canvas.bind("<Configure>", lambda e: self.rows_canvas.itemconfigure(self.rows_window, width=e.width))
        if not self.app.can_edit:
            tk.Label(match_card, text="Only administrators can create or confirm fixtures.",
                     bg=ui.WHITE, fg=ui.MUTED, font=ui.FONT_SMALL).pack(anchor="w")

        if self.app.can_edit:
            actions = tk.Frame(match_card, bg=ui.WHITE)
            actions.pack(fill="x", pady=(12, 0))
            ui.button(actions, "Save Draft", self.save_draft, "outline").pack(side="left")
            ui.button(actions, "Confirm All Fixtures", self.confirm_all).pack(side="right")
            self.draft_status = tk.Label(actions, text="Draft not saved", bg=ui.WHITE,
                                         fg=ui.MUTED, font=ui.FONT_SMALL)
            self.draft_status.pack(side="right", padx=12)

    def _labeled_control(self, parent, label, variable, values, default, command):
        box = tk.Frame(parent, bg=ui.WHITE)
        tk.Label(box, text=label, bg=ui.WHITE, fg=ui.MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        cb = ttk.Combobox(box, textvariable=variable, values=values, state="readonly",
                          width=17, font=ui.FONT)
        cb.pack(pady=(3, 0))
        cb.bind("<<ComboboxSelected>>", lambda e: command())
        box.combo = cb
        return box

    def _build_published_table(self):
        card = self._section(self.body, "04  Published fixtures",
                             "Confirmed fixtures appear here and are available to the Results and League Table pages.")
        bar = tk.Frame(card, bg=ui.WHITE)
        bar.pack(fill="x", pady=(0, 8))
        self.filter_cat = tk.StringVar(value="All")
        self.filter_pool = tk.StringVar(value="All")
        self.filter_date = tk.StringVar()
        self._labeled_control(bar, "CATEGORY FILTER", self.filter_cat, ["All", "Boys", "Girls"],
                              "All", self.filter_category_changed).pack(side="left", padx=(0, 10))
        self.filter_pool_box = self._labeled_control(bar, "POOL FILTER", self.filter_pool,
                                                     ["All"] + pool_names(), "All", self.load)
        self.filter_pool_box.pack(side="left", padx=(0, 10))
        datebox = tk.Frame(bar, bg=ui.WHITE)
        tk.Label(datebox, text="DATE FILTER (YYYY-MM-DD)", bg=ui.WHITE, fg=ui.MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Entry(datebox, textvariable=self.filter_date, width=16).pack(pady=(3, 0))
        datebox.pack(side="left", padx=(0, 10))
        ui.button(bar, "Filter", self.load, "outline").pack(side="left", pady=(14, 0))
        ui.button(bar, "Reset", self.reset_filter, "grey").pack(side="left", padx=6, pady=(14, 0))

        frame, self.tree = ui.make_table(
            card, ("#", "Date", "Time", "Category", "Pool", "Home Team", "Away Team", "Venue", "Status"),
            (38, 100, 85, 75, 75, 160, 160, 150, 95), left=("Home Team", "Away Team", "Venue"))
        frame.pack(fill="both", expand=True)
        if self.app.can_edit:
            actions = tk.Frame(card, bg=ui.WHITE)
            actions.pack(fill="x", pady=(9, 0))
            ui.button(actions, "Edit Selected", self.edit_fixture, "outline").pack(side="left")
            ui.button(actions, "Delete Selected", self.delete_fixture, "danger").pack(side="left", padx=8)

    # ---- team selection -------------------------------------------------
    def refresh_pools(self):
        pools = get_pools(self.cat_var.get())
        self.pool_map = {p["name"]: p["id"] for p in pools}
        names = list(self.pool_map)
        self.pool_control.combo["values"] = names
        if self.pool_var.get() not in names:
            self.pool_var.set(names[0] if names else "")
        self.refresh_teams()

    def category_changed(self):
        self.refresh_pools()

    def pool_changed(self):
        self.refresh_teams()

    def refresh_teams(self):
        for w in self.team_list_frame.winfo_children():
            w.destroy()
        pool_id = self.pool_map.get(self.pool_var.get())
        rows = query("SELECT id, name FROM teams WHERE pool_id=%s ORDER BY name", (pool_id,)) if pool_id else []
        old_selected = {name for name, var in self.team_vars.items() if var.get()}
        self.team_vars = {}
        self.team_names = [r["name"] for r in rows]
        if not rows:
            tk.Label(self.team_list_frame, text="No teams found in this pool. Register teams first.",
                     bg=ui.WHITE, fg=ui.MUTED, font=ui.FONT).pack(anchor="w", pady=6)
        else:
            for index, row in enumerate(rows):
                var = tk.BooleanVar(value=(row["name"] in old_selected or not old_selected))
                self.team_vars[row["name"]] = var
                cb = tk.Checkbutton(self.team_list_frame, text=row["name"], variable=var,
                                    bg=ui.WHITE, fg=ui.TEXT, activebackground=ui.WHITE,
                                    selectcolor="#E7F0FF", font=ui.FONT, command=self.selection_changed)
                cb.grid(row=index // 3, column=index % 3, sticky="w", padx=(0, 18), pady=4)
        self.selection_changed()

    def selected_teams(self):
        return [name for name, var in self.team_vars.items() if var.get()]

    def selection_changed(self):
        selected = self.selected_teams()
        self.team_count.config(text=f"{len(selected)} team(s) selected")
        for row in self.matches:
            row.refresh_teams(selected)

    def select_all(self):
        for var in self.team_vars.values():
            var.set(True)
        self.selection_changed()

    def clear_selection(self):
        for var in self.team_vars.values():
            var.set(False)
        self.selection_changed()

    # ---- match rows -----------------------------------------------------
    def add_match(self):
        names = self.selected_teams()
        if len(names) < 2:
            return messagebox.showwarning("Select teams", "Please select at least two teams before adding a match.")
        row = MatchRow(self, len(self.matches) + 1)
        self.matches.append(row)
        row.refresh_teams(names)
        self.refresh_match_numbers()
        self.rows_canvas.configure(height=min(440, max(150, len(self.matches) * 145)))
        self.rows_canvas.yview_moveto(1.0)

    def remove_match(self, row):
        if row in self.matches:
            self.matches.remove(row)
            row.frame.destroy()
            self.refresh_match_numbers()

    def refresh_match_numbers(self):
        for i, row in enumerate(self.matches, 1):
            row.number = i
            row.title.config(text=f"MATCH {i:02d}")
        self.match_count.config(text=f"{len(self.matches)} match(es) added")

    def collect_matches(self):
        if not self.matches:
            raise ValueError("Add at least one match to the schedule.")
        selected = set(self.selected_teams())
        results = []
        for i, row in enumerate(self.matches, 1):
            home, away = row.home.get().strip(), row.away.get().strip()
            if home not in selected or away not in selected:
                raise ValueError(f"Match {i}: choose both teams from the selected team list.")
            if home == away:
                raise ValueError(f"Match {i}: home and away teams must be different.")
            try:
                match_date = datetime.strptime(row.day.get().strip(), "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Match {i}: enter a valid date in YYYY-MM-DD format.")
            try:
                match_time = datetime.strptime(row.kickoff.get().strip(), "%H:%M").time()
            except ValueError:
                raise ValueError(f"Match {i}: enter a valid 24-hour time, e.g. 14:30.")
            venue = row.venue.get().strip()
            if not venue:
                raise ValueError(f"Match {i}: venue is required.")
            results.append({
                "category": self.cat_var.get(), "pool_id": self.pool_map[self.pool_var.get()],
                "match_date": match_date, "match_time": match_time,
                "home_team_id": self.team_id(home), "away_team_id": self.team_id(away),
                "home": home, "away": away, "venue": venue
            })
        # A team cannot be scheduled twice at the same date and kick-off.
        occupied = {}
        for i, item in enumerate(results, 1):
            slot = (item["match_date"], item["match_time"])
            for team_id, team_name in ((item["home_team_id"], item["home"]),
                                       (item["away_team_id"], item["away"])):
                key = (slot, team_id)
                if key in occupied:
                    raise ValueError(f"{team_name} is scheduled in both Match {occupied[key]} and Match {i} "
                                     f"at the same date and time.")
                occupied[key] = i
        return results

    def team_id(self, name):
        row = query("SELECT id FROM teams WHERE name=%s AND pool_id=%s",
                    (name, self.pool_map[self.pool_var.get()]))
        if not row:
            raise ValueError(f"Team '{name}' is no longer registered in this pool. Refresh the page.")
        return row[0]["id"]

    def save_draft(self):
        try:
            items = self.collect_matches()
        except (ValueError, KeyError) as e:
            return messagebox.showerror("Check schedule", str(e))
        self.draft_saved = True
        self.draft_status.config(text=f"Draft saved in this session · {len(items)} matches ready", fg=ui.GREEN)
        messagebox.showinfo("Draft saved", "Your schedule is saved as a draft in this page. "
                            "It has not been published to the main Fixtures table.")

    def confirm_all(self):
        try:
            items = self.collect_matches()
        except (ValueError, KeyError) as e:
            return messagebox.showerror("Check schedule", str(e))
        preview = "\n".join(f"{i}. {m['home']} vs {m['away']} — "
                            f"{m['match_date'].strftime('%d %b %Y')} {ui.fmt_time(m['match_time'])}"
                            for i, m in enumerate(items, 1))
        if not messagebox.askyesno("Confirm complete schedule",
                f"Publish all {len(items)} fixtures to the main table?\n\n{preview}\n\n"
                "All fixtures will be saved together."):
            return
        tx = None
        try:
            tx = Transaction()
            sql = ("INSERT INTO fixtures (category,pool_id,match_date,match_time,"
                   "home_team_id,away_team_id,venue) VALUES (%s,%s,%s,%s,%s,%s,%s)")
            for item in items:
                tx.execute(sql, (item["category"], item["pool_id"], item["match_date"],
                                 item["match_time"], item["home_team_id"],
                                 item["away_team_id"], item["venue"]))
            tx.commit()
        except mysql.connector.Error as e:
            if tx:
                tx.rollback()
            return ui.show_db_error(e)
        finally:
            if tx:
                tx.close()
        for row in self.matches:
            row.frame.destroy()
        self.matches.clear()
        self.refresh_match_numbers()
        self.draft_saved = False
        self.draft_status.config(text="Schedule published successfully", fg=ui.GREEN)
        self.load()
        messagebox.showinfo("Fixtures confirmed",
                            f"Successfully published {len(items)} fixtures. They are now visible in the Fixtures table.")

    # ---- published fixture list ---------------------------------------
    def filter_category_changed(self):
        cats = self.filter_cat.get()
        self.filter_pool_box.combo["values"] = ["All"] + pool_names(None if cats == "All" else cats)
        self.filter_pool.set("All")
        self.load()

    def reset_filter(self):
        self.filter_cat.set("All")
        self.filter_pool_box.combo["values"] = ["All"] + pool_names()
        self.filter_pool.set("All")
        self.filter_date.set("")
        self.load()

    def load(self):
        cond, params = [], []
        if self.filter_cat.get() != "All":
            cond.append("f.category=%s")
            params.append(self.filter_cat.get())
        if self.filter_pool.get() != "All":
            cond.append("p.name=%s")
            params.append(self.filter_pool.get())
        if self.filter_date.get().strip():
            try:
                params.append(ui.parse_date(self.filter_date.get()))
                cond.append("f.match_date=%s")
            except ValueError:
                return messagebox.showerror("Invalid date", "Use the format YYYY-MM-DD.")
        try:
            rows = get_fixtures(" AND ".join(cond), params)
        except mysql.connector.Error as e:
            return ui.show_db_error(e)
        ui.fill_table(self.tree,
            [(i + 1, ui.fmt_date(r["match_date"]), ui.fmt_time(r["match_time"]),
              r["category"], r["pool"], r["home"], r["away"], r["venue"], r["status"])
             for i, r in enumerate(rows)],
            [r["id"] for r in rows])

    def edit_fixture(self):
        fixture_id = ui.selected_id(self.tree)
        if fixture_id is None:
            return messagebox.showinfo("Edit fixture", "Select a fixture first.")
        rows = get_fixtures("f.id=%s", (fixture_id,))
        FixtureDialog(self, self.load, fixture=rows[0])

    def delete_fixture(self):
        fixture_id = ui.selected_id(self.tree)
        if fixture_id is None:
            return messagebox.showinfo("Delete fixture", "Select a fixture first.")
        if messagebox.askyesno("Delete fixture", "Delete this fixture (and its result, if any)?"):
            try:
                execute("DELETE FROM fixtures WHERE id=%s", (fixture_id,))
            except mysql.connector.Error as e:
                return ui.show_db_error(e)
            self.load()


class FixtureDialog(ui.Dialog):
    """Small edit dialog for an already-published fixture."""
    def __init__(self, parent, on_saved, fixture=None, category="Boys"):
        super().__init__(parent, "Edit Fixture", width=460)
        self.on_saved = on_saved
        self.fixture = fixture
        self.pool_map, self.team_map = {}, {}
        self.add_entry("Date (YYYY-MM-DD)", "date", fixture["match_date"].strftime("%Y-%m-%d"),
                       check=V.date_text, hint="e.g. 2026-11-21", ok_text="Valid date")
        self.add_entry("Time (HH:MM, 24-hour)", "time", ui.to_hhmm(fixture["match_time"]),
                       check=V.time_text, hint="e.g. 08:45 or 15:30", ok_text="Valid time")
        self.add_entry("Venue", "venue", fixture["venue"], check=V.venue, hint="Where the match is played.")
        self.add_buttons(self.save)
        self.show()

    def save(self):
        if not self.form_ok():
            return
        try:
            execute("UPDATE fixtures SET match_date=%s, match_time=%s, venue=%s WHERE id=%s",
                    (ui.parse_date(self.get("date")), ui.parse_time(self.get("time")),
                     self.get("venue").strip(), self.fixture["id"]))
        except (mysql.connector.Error, ValueError) as e:
            return self.error(str(e))
        self.destroy()
        self.on_saved()
