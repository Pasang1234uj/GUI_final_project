"""
main.py
-------
Starts the application, owns the main window (header + sidebar) and
switches between pages.

Run:  python main.py      (run setup.py once before the first start)
"""
import os
import tkinter as tk
import traceback
from tkinter import messagebox

import database
import ui
from administrator import AdministratorPage
from announcement import AnnouncementPage
from dashboard import DashboardPage
from fixture import FixturePage
from league_table import LeagueTablePage
from login import LoginPage, SignupPage
from pool import PoolPage
from result import ResultPage
from search import SearchPage
from setup_gui import SetupPage
from team import TeamPage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_FILE = os.path.join(BASE_DIR, "college_logo.png")

PAGES = {
    "Dashboard": DashboardPage,
    "Teams": TeamPage,
    "Pools": PoolPage,
    "Fixtures": FixturePage,
    "Results": ResultPage,
    "League Table": LeagueTablePage,
    "Announcements": AnnouncementPage,
    "Search": SearchPage,
    "Administrators": AdministratorPage,
}

NAV_ICONS = {
    "Dashboard": "⌂", "Teams": "☻", "Pools": "▦", "Fixtures": "▤", "Results": "✎",
    "League Table": "☰", "Announcements": "✉", "Search": "◉",
    "Administrators": "⚙", "Logout": "➜",
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Samtse College of Education - Football League Management System")
        self.geometry("1280x760")
        self.minsize(1100, 660)
        self.configure(bg=ui.BG)
        ui.setup_styles(self)

        self.user = None
        self.mode = "Viewer"          # "Admin" or "Viewer" - the switch at the top right
        self.current = ("Dashboard", {})
        self.logo_small = ui.load_image(LOGO_FILE, 44)
        self.logo_medium = ui.load_image(LOGO_FILE, 76)
        self.logo_large = ui.load_image(LOGO_FILE, 110)
        self.nav_buttons = {}
        self.content = None
        self.start()

    def start(self):
        """Show the connection screen if MySQL isn't reachable yet, otherwise
        go straight to the login page."""
        try:
            database.get_connection().close()
            database.migrate_roles()          # upgrades old Super Admin / Co-Admin accounts
            self.show_login()
        except Exception:
            self.show_setup()

    def show_setup(self):
        self.clear()
        self.user = None
        SetupPage(self, self).pack(fill="both", expand=True)

    # ---- permissions ----
    @property
    def can_edit(self):
        """Add / update / delete is available in Admin mode. In Viewer mode
        everything is read-only. Anyone who has logged in can switch freely."""
        return bool(self.user) and self.mode == "Admin"

    def set_mode(self, mode):
        """Switch between Admin and Viewer mode from the top-right switch."""
        if mode == self.mode:
            return
        self.mode = mode
        name, kwargs = self.current
        if name == "Administrators" and mode == "Viewer":
            name, kwargs = "Dashboard", {}
        self.build_shell()
        self.navigate(name, **kwargs)

    # ---- screens ----
    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def show_login(self, student_id=""):
        self.clear()
        self.user = None
        LoginPage(self, self, student_id).pack(fill="both", expand=True)

    def show_signup(self):
        self.clear()
        self.user = None
        SignupPage(self, self).pack(fill="both", expand=True)

    def login_success(self, user):
        self.user = user
        self.mode = "Admin" if user["role"] == "Admin" else "Viewer"
        self.build_shell()
        self.navigate("Dashboard")

    def logout(self):
        if messagebox.askyesno("Logout", "Do you want to log out?"):
            self.show_login()

    def build_shell(self):
        self.clear()
        self.nav_buttons = {}

        # header
        header = tk.Frame(self, bg="#DCE9F8", height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        if self.logo_small:
            tk.Label(header, image=self.logo_small, bg="#DCE9F8").pack(side="left", padx=(16, 10))
        titles = tk.Frame(header, bg="#DCE9F8")
        titles.pack(side="left")
        tk.Label(titles, text="SAMTSE COLLEGE OF EDUCATION", font=("Segoe UI", 12, "bold"),
                 bg="#DCE9F8", fg=ui.NAVY).pack(anchor="w")
        tk.Label(titles, text="FOOTBALL LEAGUE MANAGEMENT SYSTEM", font=ui.FONT_SMALL,
                 bg="#DCE9F8", fg=ui.NAVY).pack(anchor="w")
        who = tk.Frame(header, bg="#DCE9F8")
        who.pack(side="right", padx=20)
        tk.Label(who, text=self.user["full_name"], font=ui.FONT_B, bg="#DCE9F8", fg=ui.NAVY).pack(anchor="e")
        tk.Label(who, text=f"Student ID {self.user['username']}", font=ui.FONT_SMALL, bg="#DCE9F8",
                 fg=ui.MUTED).pack(anchor="e")
        self.mode_switch(header)

        # body = sidebar + content
        body = tk.Frame(self, bg=ui.BG)
        body.pack(fill="both", expand=True)
        sidebar = tk.Frame(body, bg=ui.NAVY, width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Frame(sidebar, bg=ui.NAVY, height=12).pack()

        items = ["Dashboard", "Teams", "Pools", "Fixtures", "Results",
                 "League Table", "Announcements", "Search"]
        if self.can_edit:
            items.append("Administrators")
        items.append("Logout")
        for name in items:
            self._nav_item(sidebar, name)

        self.content = tk.Frame(body, bg=ui.BG)
        self.content.pack(side="left", fill="both", expand=True)

    def mode_switch(self, header):
        """Admin | Viewer switch at the top right of every page.
        Admin mode: add and update information. Viewer mode: view only."""
        box = tk.Frame(header, bg="#DCE9F8")
        box.pack(side="right", padx=(0, 10))
        tk.Label(box, text="MODE", font=("Segoe UI", 8, "bold"), bg="#DCE9F8", fg=ui.MUTED).pack(anchor="w")
        row = tk.Frame(box, bg=ui.BLUE, padx=1, pady=1)
        row.pack()
        for name in ("Admin", "Viewer"):
            active = self.mode == name
            text = f"\u2713 {name}" if active else name
            lbl = tk.Label(row, text=text, font=ui.FONT_B, padx=16, pady=4, cursor="hand2",
                           bg=ui.BLUE if active else ui.WHITE,
                           fg="white" if active else ui.BLUE)
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, n=name: self.set_mode(n))

    def _nav_item(self, sidebar, name):
        lbl = tk.Label(sidebar, text=f"  {NAV_ICONS[name]}   {name}", font=ui.FONT_B, anchor="w",
                       bg=ui.NAVY, fg="white", padx=12, pady=11, cursor="hand2")
        lbl.pack(fill="x", padx=8, pady=2)
        lbl.bind("<Button-1>", lambda e: self.navigate(name))
        lbl.bind("<Enter>", lambda e: lbl.config(bg=ui.NAVY_HOVER) if lbl.cget("bg") != ui.BLUE else None)
        lbl.bind("<Leave>", lambda e: lbl.config(bg=ui.NAVY) if lbl.cget("bg") != ui.BLUE else None)
        self.nav_buttons[name] = lbl

    def navigate(self, name, **kwargs):
        """Show a page. Extra keyword arguments are passed to the page
        (e.g. navigate('Fixtures', category='Girls'))."""
        if name == "Logout":
            self.logout()
            return
        self.current = (name, kwargs)
        for w in self.content.winfo_children():
            w.destroy()
        for key, lbl in self.nav_buttons.items():
            lbl.config(bg=ui.BLUE if key == name else ui.NAVY)
        try:
            PAGES[name](self.content, self, **kwargs).pack(fill="both", expand=True)
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", f"Could not open {name}:\n\n{e}")


if __name__ == "__main__":
    App().mainloop()
