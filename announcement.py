"""
announcement.py
---------------
Post, read and delete announcements. Admins can post; everyone can read.
"""
import tkinter as tk
from tkinter import messagebox

import mysql.connector

import ui
import validators as V
from database import execute, query, query_one


class AnnouncementDialog(ui.Dialog):
    def __init__(self, parent, on_saved, posted_by):
        super().__init__(parent, "Add Announcement", width=480)
        self.on_saved = on_saved
        self.posted_by = posted_by
        self.add_entry("Title", "title", check=V.announcement_title,
                       hint="A short headline (3-150 characters).")
        self.add_text("Message", "message", height=7, check=V.announcement_message,
                      hint="Write the notice (5-1000 characters).",
                      ok_text=lambda v: f"{len(v)}/{V.MAX_MESSAGE} characters")
        self.add_buttons(self.save, "Post")
        self.show()

    def save(self):
        title, message = self.get("title"), self.get("message")
        if not self.form_ok():
            return
        if not title or not message:
            return self.error("Both title and message are required.")
        try:
            execute("INSERT INTO announcements (title, message, posted_by) VALUES (%s,%s,%s)",
                    (title, message, self.posted_by))
        except mysql.connector.Error as e:
            return self.error(str(e))
        self.destroy()
        self.on_saved()


class AnnouncementPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=ui.BG)
        self.app = app
        right = ui.page_header(self, "Announcements")
        if app.can_edit:
            ui.button(right, "+  Add Announcement",
                      lambda: AnnouncementDialog(self, self.load, app.user["full_name"])).pack()

        frame, self.tree = ui.make_table(
            self, ("#", "Date", "Title", "Posted By"), (50, 120, 480, 140), left=("Title",))
        frame.pack(fill="both", expand=True, padx=24)
        self.tree.bind("<Double-1>", lambda e: self.view())

        actions = tk.Frame(self, bg=ui.BG)
        actions.pack(fill="x", padx=24, pady=10)
        ui.button(actions, "View Selected", self.view, "outline").pack(side="left")
        if app.can_edit:
            ui.button(actions, "Delete Selected", self.delete, "danger").pack(side="left", padx=8)
        self.load()

    def load(self):
        try:
            rows = query("SELECT id, title, posted_by, created_at FROM announcements "
                         "ORDER BY created_at DESC, id DESC")
        except mysql.connector.Error as e:
            return ui.show_db_error(e)
        ui.fill_table(self.tree,
                      [(i + 1, ui.fmt_date(r["created_at"]), r["title"], r["posted_by"])
                       for i, r in enumerate(rows)],
                      [r["id"] for r in rows])

    def view(self):
        ann_id = ui.selected_id(self.tree)
        if ann_id is None:
            return messagebox.showinfo("Announcement", "Select an announcement first.")
        a = query_one("SELECT * FROM announcements WHERE id=%s", (ann_id,))
        messagebox.showinfo(a["title"], f"{a['message']}\n\nPosted by {a['posted_by']} on {ui.fmt_date(a['created_at'])}")

    def delete(self):
        ann_id = ui.selected_id(self.tree)
        if ann_id is None:
            return messagebox.showinfo("Delete", "Select an announcement first.")
        if messagebox.askyesno("Delete announcement", "Delete this announcement?"):
            try:
                execute("DELETE FROM announcements WHERE id=%s", (ann_id,))
            except mysql.connector.Error as e:
                return ui.show_db_error(e)
            self.load()
