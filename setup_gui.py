"""
setup_gui.py
------------
A graphical screen for connecting to MySQL, instead of typing details into
a plain command-line prompt (where the password shows no feedback at all).

Shown automatically by main.py whenever the app can't connect using the
current config.json (or there isn't one yet). Enter your MySQL details and
click "Connect & Set Up" - it creates the database and tables for you.
"""
import tkinter as tk
from tkinter import ttk

import mysql.connector

import ui
import validators as V
from database import initialize_database, load_config


class SetupPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=ui.BG)
        self.app = app
        cfg = load_config()

        wrap = tk.Frame(self, bg=ui.BG)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        card = tk.Frame(wrap, bg=ui.WHITE, padx=36, pady=28,
                        highlightbackground=ui.BORDER, highlightthickness=1)
        card.pack()

        tk.Label(card, text="Connect to MySQL", font=("Segoe UI", 20, "bold"),
                 bg=ui.WHITE, fg=ui.NAVY).pack()
        tk.Label(card, text="Enter your MySQL details. This runs once -\n"
                            "the database and tables are created automatically.",
                 font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED, justify="center").pack(pady=(4, 16))

        self.host = tk.StringVar(value=cfg["host"])
        self.port = tk.StringVar(value=str(cfg["port"]))
        self.user = tk.StringVar(value=cfg["user"])
        self.password = tk.StringVar(value=cfg["password"])
        self.database = tk.StringVar(value=cfg["database"])

        self.guard = ui.FormGuard()
        row = tk.Frame(card, bg=ui.WHITE)
        row.pack(fill="x")
        self._field(row, "Host", self.host, 0, 0, check=V.host)
        self._field(row, "Port", self.port, 0, 1, width=10, check=V.port)

        self._field(card, "MySQL Username", self.user, check=V.db_user)

        self._label(card, "MySQL Password")
        pw_row = tk.Frame(card, bg=ui.WHITE)
        pw_row.pack(fill="x")
        self.pw_entry = ttk.Entry(pw_row, textvariable=self.password, font=ui.FONT, show="*")
        self.pw_entry.pack(side="left", fill="x", expand=True)
        self.show_pw = tk.BooleanVar(value=False)
        tk.Checkbutton(card, text="Show password", variable=self.show_pw, bg=ui.WHITE, font=ui.FONT_SMALL,
                       activebackground=ui.WHITE,
                       command=lambda: self.pw_entry.config(show="" if self.show_pw.get() else "*")
                       ).pack(anchor="w", pady=(2, 0))

        self._field(card, "Database name", self.database, check=V.db_name)

        self.status = tk.Label(card, text="", font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.RED,
                               wraplength=360, justify="left")
        self.status.pack(fill="x", pady=(10, 0))

        self.connect_btn = ui.button(card, "Connect & Set Up", self.connect)
        self.connect_btn.pack(fill="x", pady=(10, 4))
        self.guard.button = self.connect_btn
        self.guard.refresh()
        ui.button(card, "Quit", self.app.destroy, "grey").pack(fill="x")

        self.pw_entry.bind("<Return>", lambda e: self.connect())

    def _label(self, parent, text):
        tk.Label(parent, text=text, font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED).pack(anchor="w", pady=(8, 2))

    def _field(self, parent, label, var, row=None, col=None, width=None, check=None):
        if row is None:                       # stacked field (full width)
            box = parent
            self._label(box, label)
        else:                                  # side-by-side field (host/port)
            box = tk.Frame(parent, bg=ui.WHITE)
            box.grid(row=row, column=col, sticky="ew", padx=(0, 10) if col == 0 else 0)
            parent.columnconfigure(col, weight=1 if col == 0 else 0)
            tk.Label(box, text=label, font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED).pack(anchor="w", pady=(8, 2))
        entry = ttk.Entry(box, textvariable=var, font=ui.FONT, width=width or 0)
        entry.pack(fill="x")
        if check:                              # instant feedback under the field
            msg = tk.Label(box, text="", font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED,
                           anchor="w", justify="left", wraplength=180 if row is not None else 360)
            msg.pack(fill="x")
            field = self.guard.add(ui.FieldCheck(var.get, check, msg, "", entry))
            var.trace_add("write", lambda *a: self.guard.refresh())
            entry.bind("<FocusOut>", lambda e: (field.touch(), self.guard.refresh()), add="+")

    def connect(self):
        if not self.guard.refresh():
            return
        host = self.host.get().strip() or "localhost"
        user = self.user.get().strip() or "root"
        password = self.password.get()
        database = self.database.get().strip() or "football_league"
        try:
            port = int(self.port.get().strip() or 3306)
        except ValueError:
            self.status.config(text="Port must be a number, e.g. 3306.")
            return

        self.status.config(fg=ui.MUTED, text="Connecting...")
        self.connect_btn.config(state="disabled")
        self.update_idletasks()

        try:
            initialize_database(host, port, user, password, database)
        except mysql.connector.Error as e:
            self.status.config(fg=ui.RED, text=self._friendly_error(e))
            self.connect_btn.config(state="normal")
            return
        except OSError as e:
            self.status.config(fg=ui.RED, text=f"Could not read setup.sql: {e}")
            self.connect_btn.config(state="normal")
            return

        self.status.config(fg=ui.GREEN, text="Connected! Database and tables are ready.")
        self.after(600, self.app.show_login)

    @staticmethod
    def _friendly_error(e):
        text = str(e)
        if "Access denied" in text:
            return "Access denied - check your MySQL username and password."
        if "Can't connect" in text or "getaddrinfo failed" in text:
            return ("Could not reach MySQL at this host/port. Make sure MySQL "
                    "is running and the host/port are correct.")
        return f"Could not connect: {text}"
