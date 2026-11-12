"""
dashboard.py
------------
Home screen: statistics cards, upcoming matches, latest results and the
latest announcement.
"""
import os
import tkinter as tk

import ui
from administrator import ReferCodeDialog, UserDialog
from announcement import AnnouncementDialog
from database import get_fixtures, query_one, scalar
from fixture import FixtureDialog
from pool import PoolDialog
from result import ResultDialog
from team import TeamDialog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BANNER_FILE = os.path.join(BASE_DIR, "dashboard_banner.jpg")


class DashboardPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=ui.BG)
        self.app = app
        # the page scrolls if the window is too small to show everything
        scroller = ui.ScrollFrame(self)
        scroller.pack(fill="both", expand=True)
        self.body = scroller.inner

        right = ui.page_header(self.body, "Dashboard", f"Welcome, {app.user['full_name']}")
        ui.button(right, "Boys League", lambda: app.navigate("Pools", category="Boys"), "outline").pack(side="left", padx=3)
        ui.button(right, "Girls League", lambda: app.navigate("Pools", category="Girls"), "outline").pack(side="left", padx=3)

        self.hero_banner()
        self.stat_cards()
        self.admin_section()
        self.match_panels()
        self.announcement_banner()

    def refresh(self, *_):
        """Rebuild the dashboard so new data shows immediately."""
        self.app.navigate("Dashboard")

    # ---- banner photo ----
    def hero_banner(self):
        """The photo fills the whole banner; the wording sits on a navy
        fade on the left so it stays readable."""
        app = self.app
        banner = ui.photo_banner(
            self.body, BANNER_FILE, ui.NAVY, height=220, focus=(0.5, 0.0),
            lines=[("SAMTSE COLLEGE OF EDUCATION", ("Segoe UI", 9, "bold"), "#BBD4F8"),
                   ("Football League", ("Segoe UI", 26, "bold"), "white"),
                   (f"Welcome, {app.user['full_name']}", ui.FONT, "white")],
            chip=(f"{app.mode} mode", ui.BLUE if app.can_edit else "#F5B301",
                  "white" if app.can_edit else "#1F2A44"))
        banner.pack(fill="x", padx=24, pady=(0, 14))

    # ---- admin section ----
    def admin_section(self):
        """Admin mode: add and update information straight from the dashboard.
        Viewer mode: view-only shortcuts to the latest information."""
        app = self.app
        card = tk.Frame(self.body, bg=ui.WHITE, highlightbackground=ui.BORDER, highlightthickness=1)
        card.pack(fill="x", padx=24, pady=(0, 14))

        head = tk.Frame(card, bg=ui.WHITE)
        head.pack(fill="x", padx=14, pady=(12, 2))
        tk.Label(head, text="Admin Section" if app.can_edit else "Viewer Section",
                 font=ui.FONT_H2, bg=ui.WHITE, fg=ui.NAVY).pack(side="left")

        if app.can_edit:
            self.button_row(card, "Add information  (pools first, then fixtures)", [
                ("Register Teams", lambda: app.navigate("Teams"), "primary"),
                ("+  Pool", lambda: PoolDialog(self, self.refresh, "Boys"), "primary"),
                ("Manual Fixture", lambda: app.navigate("Fixtures"), "primary"),
            ])
            self.button_row(card, "", [
                ("+  Result", lambda: ResultDialog(self, self.refresh), "primary"),
                ("+  Announcement",
                 lambda: AnnouncementDialog(self, self.refresh, app.user["full_name"]), "primary"),
                ("+  User", lambda: UserDialog(self, self.refresh, app.user), "primary"),
            ])
            self.button_row(card, "Update information  (opens the page, then Edit / Delete)", [
                ("Teams", lambda: app.navigate("Teams"), "outline"),
                ("Fixtures", lambda: app.navigate("Fixtures"), "outline"),
                ("Results", lambda: app.navigate("Results"), "outline"),
                ("Announcements", lambda: app.navigate("Announcements"), "outline"),
                ("Users", lambda: app.navigate("Administrators"), "outline"),
                ("Refer Code", lambda: ReferCodeDialog(self), "outline"),
            ], last=True)
        else:
            note = "You are in Viewer mode (read-only). Switch to Admin at the top right to add or update information."
            tk.Label(card, text=note, font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED
                     ).pack(anchor="w", padx=14, pady=(0, 2))
            self.button_row(card, "View the latest information", [
                ("Teams", lambda: app.navigate("Teams"), "outline"),
                ("Fixtures", lambda: app.navigate("Fixtures"), "outline"),
                ("Results", lambda: app.navigate("Results"), "outline"),
                ("League Table", lambda: app.navigate("League Table"), "outline"),
                ("Announcements", lambda: app.navigate("Announcements"), "outline"),
            ], last=True)

    def button_row(self, card, label, buttons, last=False):
        if label:
            tk.Label(card, text=label, font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED
                     ).pack(anchor="w", padx=14, pady=(8, 3))
        row = tk.Frame(card, bg=ui.WHITE)
        row.pack(fill="x", padx=14, pady=(0, 12 if last else 2))
        for i, (text, command, kind) in enumerate(buttons):
            row.columnconfigure(i, weight=1, uniform=f"btn_{id(row)}")
            ui.button(row, text, command, kind).grid(row=0, column=i, sticky="ew",
                                                     padx=(0 if i == 0 else 6, 0))

    # ---- statistics ----
    def stat_cards(self):
        row = tk.Frame(self.body, bg=ui.BG)
        row.pack(fill="x", padx=24, pady=(0, 14))
        stats = [
            ("Total Teams", "SELECT COUNT(*) FROM teams"),
            ("Total Pools", "SELECT COUNT(*) FROM pools"),
            ("Total Fixtures", "SELECT COUNT(*) FROM fixtures"),
            ("Results Entered", "SELECT COUNT(*) FROM fixtures WHERE status='Completed'"),
        ]
        for i, (label, sql) in enumerate(stats):
            colour = ui.CARD_COLORS[i]
            row.columnconfigure(i, weight=1, uniform="cards")
            card = tk.Frame(row, bg=colour, padx=18, pady=14)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0))
            tk.Label(card, text=str(scalar(sql)), font=("Segoe UI", 28, "bold"), bg=colour, fg="white").pack(anchor="w")
            tk.Label(card, text=label, font=ui.FONT_B, bg=colour, fg="white").pack(anchor="w")

    # ---- upcoming matches / latest results ----
    def panel(self, parent, title, target):
        card = tk.Frame(parent, bg=ui.WHITE, highlightbackground=ui.BORDER, highlightthickness=1)
        head = tk.Frame(card, bg=ui.WHITE)
        head.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(head, text=title, font=ui.FONT_H2, bg=ui.WHITE, fg=ui.NAVY).pack(side="left")
        link = tk.Label(head, text="View All", font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.BLUE, cursor="hand2")
        link.pack(side="right")
        link.bind("<Button-1>", lambda e: self.app.navigate(target))
        return card

    def match_panels(self):
        wrap = tk.Frame(self.body, bg=ui.BG)
        wrap.pack(fill="x", padx=24)
        wrap.columnconfigure(0, weight=1, uniform="panels")
        wrap.columnconfigure(1, weight=1, uniform="panels")

        upcoming = self.panel(wrap, "Upcoming Matches", "Fixtures")
        upcoming.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        rows = get_fixtures("f.status='Scheduled'", limit=3)
        if not rows:
            tk.Label(upcoming, text="No upcoming matches.", bg=ui.WHITE, fg=ui.MUTED, font=ui.FONT).pack(pady=24)
        for f in rows:
            item = tk.Frame(upcoming, bg=ui.WHITE)
            item.pack(fill="x", padx=14, pady=6)
            box = tk.Frame(item, bg="#E8F0FE", padx=10, pady=4)
            box.pack(side="left")
            tk.Label(box, text=f["match_date"].strftime("%d"), font=("Segoe UI", 15, "bold"), bg="#E8F0FE", fg=ui.NAVY).pack()
            tk.Label(box, text=f["match_date"].strftime("%b"), font=ui.FONT_SMALL, bg="#E8F0FE", fg=ui.NAVY).pack()
            info = tk.Frame(item, bg=ui.WHITE)
            info.pack(side="left", padx=12)
            tk.Label(info, text=f"{f['category']} - {f['pool']}", font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.BLUE).pack(anchor="w")
            tk.Label(info, text=f"{f['home']}   vs   {f['away']}", font=ui.FONT_B, bg=ui.WHITE, fg=ui.TEXT).pack(anchor="w")
            tk.Label(info, text=f"{ui.fmt_time(f['match_time'])}  ·  {f['venue']}", font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED).pack(anchor="w")

        latest = self.panel(wrap, "Latest Results", "Results")
        latest.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        rows = get_fixtures("f.status='Completed'", order="f.match_date DESC, f.match_time DESC", limit=3)
        if not rows:
            tk.Label(latest, text="No results entered yet.", bg=ui.WHITE, fg=ui.MUTED, font=ui.FONT).pack(pady=24)
        for f in rows:
            item = tk.Frame(latest, bg=ui.WHITE)
            item.pack(fill="x", padx=14, pady=6)
            tk.Label(item, text=f"{f['category']} - {f['pool']}", font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.BLUE).pack(anchor="w")
            line = tk.Frame(item, bg=ui.WHITE)
            line.pack(fill="x")
            tk.Label(line, text=f["home"], font=ui.FONT, bg=ui.WHITE, fg=ui.TEXT, width=16, anchor="w").pack(side="left")
            tk.Label(line, text=f"{f['home_score']} - {f['away_score']}", font=("Segoe UI", 12, "bold"),
                     bg=ui.WHITE, fg=ui.RED, width=7).pack(side="left")
            tk.Label(line, text=f["away"], font=ui.FONT, bg=ui.WHITE, fg=ui.TEXT, anchor="w").pack(side="left")
            tk.Label(item, text=ui.fmt_date(f["match_date"]), font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED).pack(anchor="w")

    # ---- latest announcement ----
    def announcement_banner(self):
        a = query_one("SELECT * FROM announcements ORDER BY created_at DESC, id DESC LIMIT 1")
        banner = tk.Frame(self.body, bg="#FFF6DB", highlightbackground="#F3DC96", highlightthickness=1, padx=16, pady=10)
        banner.pack(fill="x", padx=24, pady=14)
        if not a:
            tk.Label(banner, text="No announcements yet.", bg="#FFF6DB", fg=ui.MUTED, font=ui.FONT).pack(anchor="w")
            return
        head = tk.Frame(banner, bg="#FFF6DB")
        head.pack(fill="x")
        tk.Label(head, text="Latest Announcement:  " + a["title"], font=ui.FONT_B, bg="#FFF6DB", fg=ui.TEXT).pack(side="left")
        tk.Label(head, text=ui.fmt_date(a["created_at"]), font=ui.FONT_SMALL, bg="#FFF6DB", fg=ui.MUTED).pack(side="right")
        msg = a["message"] if len(a["message"]) < 160 else a["message"][:157] + "..."
        tk.Label(banner, text=msg, font=ui.FONT_SMALL, bg="#FFF6DB", fg=ui.MUTED, wraplength=900, justify="left").pack(anchor="w")
