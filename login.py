"""
login.py
--------
Login screen, sign-up screen and the account rules.

Rules
  * Username = Student ID: exactly 8 digits and it must start with 08.
  * The login page only asks for Student ID and password. The role
    (Admin / Viewer) is read from the account itself, so nobody picks a
    role when logging in.
  * Sign up has no role drop-down either:
      - the FIRST account ever created becomes an Admin and sets a shared
        4-digit refer code;
      - anyone who types the correct refer code becomes an Admin;
      - leaving the refer code blank creates a read-only Viewer.
    An Admin can also add or change accounts from the Administrators page.
  * Every field gives instant feedback while typing (see validators.py) and
    the button stays disabled until the form is valid.
"""
import os
import secrets
import tkinter as tk
from tkinter import messagebox, ttk

import mysql.connector

import ui
import validators as V
from database import execute, get_setting, hash_password, query, scalar, set_setting, verify_password
from validators import REFER_CODE_PATTERN, STUDENT_ID_PATTERN

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROLES = ["Admin", "Viewer"]
MAX_CODE_ATTEMPTS = 5      # different wrong refer codes allowed before sign-up locks


def is_valid_student_id(value):
    return bool(STUDENT_ID_PATTERN.match(value))


class AuthPage(tk.Frame):
    """Shared layout: a photo (with a dark overlay) and college branding on
    the left, a white card on the right."""

    # Photo shown behind the left panel. Put a landscape photo of the
    # college / stadium / a match at this path (any of these extensions).
    BACKGROUND_FILE = os.path.join(BASE_DIR, "login_background.jpg")

    def __init__(self, parent, app):
        super().__init__(parent, bg=ui.NAVY)
        self.app = app
        self.guard = ui.FormGuard()
        self.cached = ui.make_cache()

        left = tk.Frame(self, bg=ui.NAVY)
        left.pack(side="left", fill="both", expand=True)

        self.bg_label = tk.Label(left, bg=ui.NAVY, bd=0)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        left.bind("<Configure>", self._draw_background)

        # The poster/photo already carries the college name and branding,
        # so when one is found it is shown full-bleed with no text on top.
        # If no photo file is present, this fallback panel (logo + name +
        # tagline on plain navy) is shown instead.
        self.fallback = tk.Frame(left, bg=ui.NAVY)
        if app.logo_large:
            tk.Label(self.fallback, image=app.logo_large, bg=ui.NAVY).pack(pady=(0, 16))
        tk.Label(self.fallback, text="SAMTSE COLLEGE OF EDUCATION", font=("Segoe UI", 22, "bold"),
                 fg="white", bg=ui.NAVY).pack()
        tk.Label(self.fallback, text="FOOTBALL LEAGUE MANAGEMENT SYSTEM", font=("Segoe UI", 13, "bold"),
                 fg="#9DC1F5", bg=ui.NAVY).pack(pady=(4, 30))
        tk.Label(self.fallback, text="Play.  Compete.  Grow.", font=("Segoe UI", 26, "italic"),
                 fg="white", bg=ui.NAVY).pack()
        self.fallback.place(relx=0.5, rely=0.5, anchor="center")

        right = tk.Frame(self, bg=ui.BG, width=520)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        self.card = tk.Frame(right, bg=ui.WHITE, padx=34, pady=24,
                             highlightbackground=ui.BORDER, highlightthickness=1)
        self.card.place(relx=0.5, rely=0.5, anchor="center")

    def _draw_background(self, event=None):
        """Fill the left panel with the background photo, re-drawn whenever
        the window is resized. Silently does nothing if no photo is found
        (the plain navy background stays), or if Pillow is not installed."""
        w, h = self.bg_label.winfo_width(), self.bg_label.winfo_height()
        if w < 2 or h < 2:
            return
        photo = None
        for ext in (".jpg", ".jpeg", ".png"):
            path = os.path.splitext(self.BACKGROUND_FILE)[0] + ext
            photo = ui.load_fit_image(path, w, h)    # whole poster stays visible
            if photo:
                break
        if photo:
            self.bg_label.configure(image=photo)
            self.bg_label.image = photo   # keep a reference so it is not garbage-collected
            self.fallback.place_forget()
        else:
            self.bg_label.configure(image="")
            self.fallback.place(relx=0.5, rely=0.5, anchor="center")

    def heading(self, title, subtitle, logo=None):
        if logo:
            tk.Label(self.card, image=logo, bg=ui.WHITE).pack(pady=(0, 6))
        tk.Label(self.card, text=title, font=("Segoe UI", 20, "bold"), bg=ui.WHITE, fg=ui.NAVY).pack()
        tk.Label(self.card, text=subtitle, font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED).pack(pady=(0, 6))

    def live_field(self, parent, label, var, check, hint="", show=None, ok_text="Looks good"):
        """Label + entry + a message that updates on every key press."""
        tk.Label(parent, text=label, font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED
                 ).pack(anchor="w", pady=(6, 1))
        entry = ttk.Entry(parent, textvariable=var, font=ui.FONT, width=34, show=show or "")
        entry.pack(fill="x")
        msg = tk.Label(parent, text=hint, font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED,
                       anchor="w", justify="left", wraplength=350)
        msg.pack(fill="x")
        field = self.guard.add(ui.FieldCheck(var.get, check, msg, hint, entry, ok_text))
        var.trace_add("write", lambda *a: self.guard.refresh())
        entry.bind("<FocusOut>", lambda e: (field.touch(), self.guard.refresh()), add="+")
        return entry, field, msg

    def link(self, text, command):
        lbl = tk.Label(self.card, text=text, font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.BLUE, cursor="hand2")
        lbl.pack()
        lbl.bind("<Button-1>", lambda e: command())
        return lbl


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
class LoginPage(AuthPage):
    def __init__(self, parent, app, student_id=""):
        super().__init__(parent, app)
        card = self.card
        self.heading("LOGIN", "Sign in to access the system", app.logo_medium)

        self.username = tk.StringVar(value=student_id)
        self.password = tk.StringVar()

        _, _, _ = self.live_field(card, "Student ID (e.g. 08201234)", self.username, V.student_id,
                                  hint="Your 8-digit Student ID.", ok_text="Student ID format is correct")
        self.pw_entry, _, _ = self.live_field(card, "Password", self.password,
                                              lambda v: "" if v else "Password is required.",
                                              hint="Enter your password.", show="*", ok_text="Password entered")
        self.show_pw = tk.BooleanVar(value=False)
        tk.Checkbutton(card, text="Show password", variable=self.show_pw, bg=ui.WHITE, font=ui.FONT_SMALL,
                       activebackground=ui.WHITE,
                       command=lambda: self.pw_entry.config(show="" if self.show_pw.get() else "*")
                       ).pack(anchor="w")

        # shown when the Student ID / password pair is wrong
        self.error_lbl = tk.Label(card, text="", font=ui.FONT_B, bg=ui.WHITE, fg=ui.RED,
                                  wraplength=350, justify="left")
        self.error_lbl.pack(fill="x", pady=(8, 0))

        self.login_btn = ui.button(card, "Login", self.login)
        self.login_btn.pack(fill="x", pady=(8, 8))
        self.guard.button = self.login_btn
        self.link("Don't have an account? Sign Up", app.show_signup)

        self.username.trace_add("write", lambda *a: self.error_lbl.config(text=""))
        self.password.trace_add("write", lambda *a: self.error_lbl.config(text=""))
        self.pw_entry.bind("<Return>", lambda e: self.login())
        self.guard.refresh()

    def login(self):
        if not self.guard.refresh():
            return
        username = self.username.get().strip()
        password = self.password.get()
        try:
            rows = query("SELECT * FROM users WHERE username=%s", (username,))
        except Exception as e:
            ui.show_db_error(e)
            return
        if not rows or not verify_password(password, rows[0]["password_hash"]):
            self.password.set("")
            self.error_lbl.config(text="\u2717  Invalid Student ID or password.")
            return
        self.app.login_success(rows[0])   # the role comes from the account


# ---------------------------------------------------------------------------
# Sign up
# ---------------------------------------------------------------------------
class SignupPage(AuthPage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.wrong_codes = set()          # distinct wrong codes typed so far
        self.first_user = not self.saved_code()
        subtitle = ("First account: you will become the Admin" if self.first_user
                    else "Create your account")
        self.heading("SIGN UP", subtitle, app.logo_small)

        self.full_name = tk.StringVar()
        self.student_id = tk.StringVar()
        self.refer = tk.StringVar()
        self.password = tk.StringVar()
        self.confirm = tk.StringVar()

        form = tk.Frame(self.card, bg=ui.WHITE)
        form.pack(fill="x")

        self.live_field(form, "Full Name", self.full_name, V.full_name,
                        hint="As it appears on your college ID.")
        self.live_field(form, "Student ID (8 digits, starts with 08)", self.student_id, self.check_student_id,
                        hint="This will be your username.", ok_text="Student ID is available")
        if self.first_user:
            self.refer_entry, _, _ = self.live_field(
                form, "Set a 4-digit refer code (other Admins will need it)", self.refer, V.refer_code_required,
                hint="You choose this code and share it with other Admins.", ok_text="Refer code set")
        else:
            self.refer_entry, _, _ = self.live_field(
                form, "Refer code (optional - Admins only)", self.refer, self.check_refer_code,
                hint="Leave blank to sign up as a Viewer (read-only).", ok_text=self.refer_ok_text)
        self.pw_entry, _, _ = self.live_field(
            form, "Password (min 6 characters)", self.password, V.password, show="*",
            hint="Use at least 6 characters.", ok_text=lambda v: "Password strength: " + V.password_strength(v))
        self.confirm_entry, _, _ = self.live_field(
            form, "Confirm Password", self.confirm, V.confirm_password(self.password.get), show="*",
            hint="Type the same password again.", ok_text="Passwords match")
        self.password.trace_add("write", lambda *a: self.guard.refresh())   # re-check confirm too

        self.show_pw = tk.BooleanVar(value=False)
        tk.Checkbutton(form, text="Show password", variable=self.show_pw, bg=ui.WHITE, font=ui.FONT_SMALL,
                       activebackground=ui.WHITE, command=self.toggle_password).pack(anchor="w")

        self.signup_btn = ui.button(self.card, "Sign Up", self.sign_up)
        self.signup_btn.pack(fill="x", pady=(10, 6))
        self.guard.button = self.signup_btn
        self.link("Already have an account? Login", app.show_login)
        self.confirm_entry.bind("<Return>", lambda e: self.sign_up())
        self.guard.refresh()

    # ---- helpers ----
    def saved_code(self):
        try:
            return get_setting("refer_code") or ""
        except mysql.connector.Error:
            return ""

    def toggle_password(self):
        show = "" if self.show_pw.get() else "*"
        self.pw_entry.config(show=show)
        self.confirm_entry.config(show=show)

    def locked(self):
        return len(self.wrong_codes) > MAX_CODE_ATTEMPTS - 1

    # ---- live checks ----
    def check_student_id(self, v):
        error = V.student_id(v)
        if error:
            return error
        taken = self.cached(("sid", v), lambda: scalar("SELECT COUNT(*) FROM users WHERE username=%s", (v,)))
        return "An account with this Student ID already exists." if taken else ""

    def check_refer_code(self, v):
        if v == "":
            return ""
        error = V.refer_code(v)
        if error:
            return error
        if self.locked():
            return "Too many incorrect codes. Restart the program to try again."
        saved = self.cached("code", self.saved_code)
        if not saved or not secrets.compare_digest(v, saved):
            self.wrong_codes.add(v)
            left = max(MAX_CODE_ATTEMPTS - len(self.wrong_codes), 0)
            return f"Incorrect refer code ({left} tries left). Clear the box to sign up as a Viewer."
        return ""

    def refer_ok_text(self, v):
        return "Correct code - you will join as an Admin"

    # ---- submit ----
    def decide_role(self, code):
        """Returns (role, error). Re-checks everything against the database."""
        saved = self.saved_code()
        if not saved:                                   # very first account
            if not REFER_CODE_PATTERN.match(code):
                return None, "Set a refer code of exactly 4 digits."
            return "Admin", None
        if not code:
            return "Viewer", None
        if self.locked():
            return None, "Too many incorrect codes. Restart the program to try again."
        if not REFER_CODE_PATTERN.match(code) or not secrets.compare_digest(code, saved):
            self.wrong_codes.add(code)
            return None, "Incorrect refer code."
        return "Admin", None

    def sign_up(self):
        if not self.guard.refresh():
            return
        full_name = " ".join(self.full_name.get().split())
        student_id = self.student_id.get().strip()
        code = self.refer.get().strip()
        password = self.password.get()
        try:
            role, error = self.decide_role(code)
            if error:
                return messagebox.showerror("Sign up", error)
            execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (%s,%s,%s,%s)",
                    (student_id, hash_password(password), full_name, role))
            if self.first_user and role == "Admin":
                set_setting("refer_code", code)
        except mysql.connector.IntegrityError:
            return messagebox.showerror("Sign up", "An account with this Student ID already exists.")
        except mysql.connector.Error as e:
            return ui.show_db_error(e)

        messagebox.showinfo("Account created",
                            f"Your account has been created as {role}. You can now log in.")
        self.app.show_login(student_id)
