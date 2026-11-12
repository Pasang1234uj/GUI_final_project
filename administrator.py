"""
administrator.py
----------------
Account management for Admins: create, edit and delete
Admin / Viewer accounts.
"""
import tkinter as tk
from tkinter import messagebox

import mysql.connector

import ui
import validators as V
from database import execute, get_setting, hash_password, query, query_one, scalar, set_setting
from login import REFER_CODE_PATTERN, is_valid_student_id

ROLES = ["Admin", "Viewer"]


class UserDialog(ui.Dialog):
    def __init__(self, parent, on_saved, current_user, user=None):
        super().__init__(parent, "Edit User" if user else "Add User")
        self.on_saved = on_saved
        self.current_user = current_user
        self.user = user

        if user:        # the Student ID (username) cannot be changed
            entry = self.add_entry("Student ID", "username", user["username"])
            entry.config(state="disabled")
        else:
            self.add_entry("Student ID (8 digits, starts with 08)", "username", "",
                           check=self.check_username, hint="This will be the username.",
                           ok_text="Student ID is available")
        self.add_entry("Full name", "full_name", user["full_name"] if user else "",
                       check=V.full_name, hint="Letters and spaces only.")
        self.add_combo("Role", "role", ROLES, user["role"] if user else "Viewer",
                       check=self.check_role, hint="", ok_text=lambda v: f"Role: {v}")
        self.add_entry("Password" + (" (leave blank to keep current)" if user else " (min 6 characters)"),
                       "password", show="*", check=self.check_password,
                       hint="Leave blank to keep the current password." if user else "Use at least 6 characters.",
                       ok_text=lambda v: "Password strength: " + V.password_strength(v))
        self.add_entry("Confirm password", "confirm", show="*", check=self.check_confirm,
                       hint="Type the same password again.", ok_text="Passwords match")
        self.vars["password"].trace_add("write", lambda *a: self.guard.refresh())
        self.add_buttons(self.save)
        self.show()

    # ---- live checks ----
    def check_username(self, value):
        error = V.student_id(value)
        if error:
            return error
        taken = self.cached(("user", value), lambda: scalar(
            "SELECT COUNT(*) FROM users WHERE username=%s", (value,)))
        return "That Student ID already has an account." if taken else ""

    def check_role(self, value):
        if not value:
            return "Choose a role."
        if self.user and self.user["role"] == "Admin" and value != "Admin":
            if self.cached("admins", lambda: scalar("SELECT COUNT(*) FROM users WHERE role='Admin'")) <= 1:
                return "There must be at least one Admin."
        return ""

    def check_password(self, value):
        if self.user and value == "":
            return ""                       # editing: blank keeps the current password
        return V.password(value)

    def check_confirm(self, value):
        if self.user and self.vars["password"].get() == "" and value == "":
            return ""
        return V.confirm_password(self.vars["password"].get)(value)

    def save(self):
        username, full_name, role = self.get("username"), self.get("full_name"), self.get("role")
        password = self.vars["password"].get()          # do not strip passwords
        if not self.form_ok():
            return
        if not username or not full_name or not role:
            return self.error("Student ID, full name and role are required.")
        if not self.user and not is_valid_student_id(username):
            return self.error("Student ID must be exactly 8 digits and start with 08.")
        if (not self.user or password) and len(password) < 6:
            return self.error("Password must be at least 6 characters.")

        try:
            if self.user:
                # never let the last Admin lose their role
                if self.user["role"] == "Admin" and role != "Admin":
                    if scalar("SELECT COUNT(*) FROM users WHERE role='Admin'") <= 1:
                        return self.error("There must be at least one Admin.")
                if password:
                    execute("UPDATE users SET full_name=%s, role=%s, password_hash=%s WHERE id=%s",
                            (full_name, role, hash_password(password), self.user["id"]))
                else:
                    execute("UPDATE users SET full_name=%s, role=%s WHERE id=%s",
                            (full_name, role, self.user["id"]))
            else:
                execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (%s,%s,%s,%s)",
                        (username, hash_password(password), full_name, role))
        except mysql.connector.IntegrityError:
            return self.error("That username is already taken.")
        except mysql.connector.Error as e:
            return self.error(str(e))
        self.destroy()
        self.on_saved()


class ReferCodeDialog(ui.Dialog):
    """View / change the 4-digit code new Admins need when they sign up."""

    def __init__(self, parent):
        super().__init__(parent, "Admin Refer Code")
        tk.Label(self.body, text="Anyone who enters this 4-digit code when signing up becomes an Admin.",
                 font=ui.FONT_SMALL, bg=ui.WHITE, fg=ui.MUTED, wraplength=340, justify="left").pack(anchor="w")
        self.add_entry("Refer code", "code", get_setting("refer_code", ""),
                       check=V.refer_code_required, hint="Exactly 4 digits.", ok_text="Valid refer code")
        self.add_buttons(self.save)
        self.show()

    def save(self):
        code = self.get("code")
        if not self.form_ok():
            return
        if not REFER_CODE_PATTERN.match(code):
            return self.error("The refer code must be exactly 4 digits.")
        try:
            set_setting("refer_code", code)
        except mysql.connector.Error as e:
            return self.error(str(e))
        self.destroy()
        messagebox.showinfo("Refer code", "Refer code updated.")


class AdministratorPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=ui.BG)
        self.app = app
        if not app.can_edit:                 # safety net - the menu item is hidden anyway
            tk.Label(self, text="Only an Admin can manage accounts.", font=ui.FONT_H2,
                     bg=ui.BG, fg=ui.RED).pack(pady=60)
            return

        right = ui.page_header(self, "Administrators", "Manage Admin and Viewer accounts")
        ui.button(right, "Refer Code", lambda: ReferCodeDialog(self), "outline").pack(side="left", padx=4)
        ui.button(right, "+  Add User", self.add_user).pack(side="left")

        frame, self.tree = ui.make_table(
            self, ("#", "Student ID", "Full Name", "Role", "Created"), (50, 160, 240, 120, 130),
            left=("Student ID", "Full Name"))
        frame.pack(fill="both", expand=True, padx=24)

        actions = tk.Frame(self, bg=ui.BG)
        actions.pack(fill="x", padx=24, pady=10)
        ui.button(actions, "Edit Selected", self.edit_user, "outline").pack(side="left")
        ui.button(actions, "Delete Selected", self.delete_user, "danger").pack(side="left", padx=8)
        self.load()

    def load(self):
        try:
            rows = query("SELECT id, username, full_name, role, created_at FROM users ORDER BY role, username")
        except mysql.connector.Error as e:
            return ui.show_db_error(e)
        ui.fill_table(self.tree,
                      [(i + 1, r["username"], r["full_name"], r["role"], ui.fmt_date(r["created_at"]))
                       for i, r in enumerate(rows)],
                      [r["id"] for r in rows])

    def add_user(self):
        UserDialog(self, self.load, self.app.user)

    def edit_user(self):
        user_id = ui.selected_id(self.tree)
        if user_id is None:
            return messagebox.showinfo("Edit user", "Select a user first.")
        UserDialog(self, self.load, self.app.user, query_one("SELECT * FROM users WHERE id=%s", (user_id,)))

    def delete_user(self):
        user_id = ui.selected_id(self.tree)
        if user_id is None:
            return messagebox.showinfo("Delete user", "Select a user first.")
        if user_id == self.app.user["id"]:
            return messagebox.showerror("Delete user", "You cannot delete your own account.")
        if messagebox.askyesno("Delete user", "Delete this account?"):
            try:
                execute("DELETE FROM users WHERE id=%s", (user_id,))
            except mysql.connector.Error as e:
                return ui.show_db_error(e)
            self.load()
