"""
team.py
-------
Add / edit / delete football teams (Boys and Girls categories).
"""
import tkinter as tk
from tkinter import messagebox, ttk

import mysql.connector

import ui
import validators as V
from database import execute, get_pools, pool_names, query, query_one


class TeamDialog(ui.Dialog):
    def __init__(self, parent, on_saved, team=None):
        super().__init__(parent, "Edit Team" if team else "Add Team")
        self.on_saved = on_saved
        self.team = team
        self.pool_map = {}

        self.add_entry("Team Name", "name", team["name"] if team else "",
                       check=self.check_name, hint="e.g. IT 'A' IV + IT I")
        cat_cb = self.add_combo("Category", "category", ["Boys", "Girls"],
                                team["category"] if team else "Boys")
        self.pool_cb = self.add_combo("Pool", "pool", [], "", check=self.check_pool,
                                      hint="Choose the pool this team plays in.", ok_text="Pool selected")
        self.add_entry("Coach (optional)", "coach", (team["coach"] or "") if team else "",
                       check=V.coach_name, hint="Leave blank if there is no coach yet.")
        self.vars["category"].trace_add("write", lambda *a: self.guard.refresh())
        if team:                       # category is fixed once a team exists
            cat_cb.config(state="disabled")
        cat_cb.bind("<<ComboboxSelected>>", lambda e: self.load_pools())
        self.load_pools(team["pool_name"] if team else None)
        self.add_buttons(self.save)
        self.show()

    def check_name(self, value):
        error = V.team_name(value)
        if error:
            return error
        category = self.get("category")
        row = self.cached(("team", value.lower(), category), lambda: query_one(
            "SELECT id FROM teams WHERE name=%s AND category=%s", (value, category)))
        if row and (not self.team or row["id"] != self.team["id"]):
            return f"A {category} team called '{value}' already exists."
        return ""

    def check_pool(self, value):
        return "" if value in self.pool_map else "Choose a pool. If none exist, create pools first."

    def load_pools(self, select=None):
        pools = get_pools(self.get("category"))
        self.pool_map = {p["name"]: p["id"] for p in pools}
        names = list(self.pool_map)
        self.pool_cb["values"] = names
        self.vars["pool"].set(select if select in self.pool_map else (names[0] if names else ""))

    def save(self):
        name, category = self.get("name"), self.get("category")
        pool_name, coach = self.get("pool"), self.get("coach")
        if not self.form_ok():
            return
        if not name:
            return self.error("Team name is required.")
        if pool_name not in self.pool_map:
            return self.error("Please choose a pool. If none exist, create pools first (Pools page).")
        try:
            if self.team:
                execute("UPDATE teams SET name=%s, pool_id=%s, coach=%s WHERE id=%s",
                        (name, self.pool_map[pool_name], coach, self.team["id"]))
            else:
                execute("INSERT INTO teams (name, category, pool_id, coach) VALUES (%s,%s,%s,%s)",
                        (name, category, self.pool_map[pool_name], coach))
        except mysql.connector.IntegrityError:
            return self.error("A team with this name already exists in that category.")
        except mysql.connector.Error as e:
            return self.error(str(e))
        self.destroy()
        self.on_saved()


class BulkTeamDialog(tk.Toplevel):
    """Scrollable multi-team registration; each row has its own pool assignment."""
    def __init__(self, parent, on_saved):
        super().__init__(parent.winfo_toplevel())
        self.on_saved = on_saved
        self.title("Register Multiple Teams")
        self.configure(bg=ui.BG)
        self.geometry("900x620")
        self.minsize(760, 500)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        tk.Label(self, text="Register Multiple Teams", font=ui.FONT_H2,
                 bg=ui.BG, fg=ui.NAVY).pack(anchor="w", padx=22, pady=(18, 4))
        tk.Label(self, text="Enter each team and assign its category and pool before saving.",
                 font=ui.FONT, bg=ui.BG, fg=ui.MUTED).pack(anchor="w", padx=22, pady=(0, 12))
        head=tk.Frame(self,bg=ui.BG); head.pack(fill="x",padx=22)
        for title,width in [("Team name",28),("Category",12),("Pool",18),("Coach (optional)",22)]:
            tk.Label(head,text=title,width=width,anchor="w",bg=ui.BG,fg=ui.MUTED,font=ui.FONT_SMALL).pack(side="left",padx=4)
        outer=tk.Frame(self,bg=ui.WHITE,highlightbackground=ui.BORDER,highlightthickness=1)
        outer.pack(fill="both",expand=True,padx=22,pady=6)
        self.canvas=tk.Canvas(outer,bg=ui.WHITE,highlightthickness=0)
        sb=ttk.Scrollbar(outer,orient="vertical",command=self.canvas.yview)
        self.rows_frame=tk.Frame(self.canvas,bg=ui.WHITE)
        self.rows_frame.bind("<Configure>",lambda e:self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0,0),window=self.rows_frame,anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        self.rows=[]
        controls=tk.Frame(self,bg=ui.BG); controls.pack(fill="x",padx=22,pady=8)
        ui.button(controls,"+ Add Another Team",self.add_row,"outline").pack(side="left")
        ui.button(controls,"Save All Teams",self.save).pack(side="right")
        ui.button(controls,"Cancel",self.destroy,"grey").pack(side="right",padx=8)
        for _ in range(5): self.add_row()
        self.update_idletasks()

    def add_row(self):
        row=tk.Frame(self.rows_frame,bg=ui.WHITE); row.pack(fill="x",padx=8,pady=5)
        name=tk.StringVar(); cat=tk.StringVar(value="Boys"); pool=tk.StringVar(); coach=tk.StringVar()
        e=ttk.Entry(row,textvariable=name,width=28); e.pack(side="left",padx=4)
        cb=ttk.Combobox(row,textvariable=cat,values=["Boys","Girls"],state="readonly",width=10); cb.pack(side="left",padx=4)
        pc=ttk.Combobox(row,textvariable=pool,state="readonly",width=17); pc.pack(side="left",padx=4)
        ttk.Entry(row,textvariable=coach,width=22).pack(side="left",padx=4)
        def load(*_):
            pools=get_pools(cat.get())
            pc["values"]=[x["name"] for x in pools]
            pool.set(pools[0]["name"] if pools else "")
        cb.bind("<<ComboboxSelected>>",load); load()
        ui.button(row,"Remove",lambda:self.remove_row(row),"danger").pack(side="left",padx=5)
        self.rows.append((row,name,cat,pool,coach))

    def remove_row(self,row):
        self.rows=[r for r in self.rows if r[0] is not row]
        row.destroy()

    def save(self):
        records=[]
        for _,name,cat,pool,coach in self.rows:
            n=name.get().strip()
            if not n: continue
            if not pool.get():
                messagebox.showerror("Pool required",f"Create/select a pool for {cat.get()} before registering {n}.",parent=self); return
            records.append((n,cat.get(),pool.get(),coach.get().strip()))
        if not records:
            messagebox.showinfo("No teams","Enter at least one team name.",parent=self); return
        seen=set()
        for n,c,_,_ in records:
            key=(n.casefold(),c)
            if key in seen:
                messagebox.showerror("Duplicate team",f"{n} appears more than once.",parent=self); return
            seen.add(key)
            if query_one("SELECT id FROM teams WHERE LOWER(name)=LOWER(%s) AND category=%s",(n,c)):
                messagebox.showerror("Duplicate team",f"A {c} team named {n} already exists.",parent=self); return
        try:
            from database import Transaction
            tx = Transaction()
            try:
                for n,c,pool_name,coach_name in records:
                    pool=query_one("SELECT id FROM pools WHERE category=%s AND name=%s",(c,pool_name))
                    if not pool: raise ValueError(f"Pool {pool_name} no longer exists for {c}.")
                    tx.execute("INSERT INTO teams (name,category,pool_id,coach) VALUES (%s,%s,%s,%s)",
                               (n,c,pool["id"],coach_name))
                tx.commit()
            except Exception:
                tx.rollback()
                raise
            finally:
                tx.close()
        except Exception as exc:
            messagebox.showerror("Registration failed",str(exc),parent=self); return
        messagebox.showinfo("Success",f"{len(records)} teams registered successfully.",parent=self)
        self.destroy(); self.on_saved()



class TeamPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=ui.BG)
        self.app = app
        right = ui.page_header(self, "Teams Management")
        if app.can_edit:
            ui.button(right, "Register Teams (many at once)", self.bulk_register).pack(side="left", padx=(0, 8))
            ui.button(right, "+  Add One Team", self.add_team, "outline").pack(side="left")

        bar = tk.Frame(self, bg=ui.BG)
        bar.pack(fill="x", padx=24, pady=(0, 10))
        box, self.cat, _ = ui.labeled_combo(bar, "Category", ["All", "Boys", "Girls"], "All",
                                            command=self.category_changed)
        box.pack(side="left", padx=(0, 14))
        box, self.pool, self.pool_cb = ui.labeled_combo(bar, "Pool", ["All"] + pool_names(), "All",
                                                        command=self.load)
        box.pack(side="left", padx=(0, 14))
        sbox = tk.Frame(bar, bg=ui.BG)
        sbox.pack(side="left", fill="x", expand=True)
        tk.Label(sbox, text="Search teams", font=ui.FONT_SMALL, bg=ui.BG, fg=ui.MUTED).pack(anchor="w")
        self.search = tk.StringVar()
        entry = ttk.Entry(sbox, textvariable=self.search, font=ui.FONT)
        entry.pack(fill="x")
        entry.bind("<KeyRelease>", lambda e: self.load())

        frame, self.tree = ui.make_table(
            self, ("#", "Team Name", "Category", "Pool", "Coach"), (50, 240, 100, 100, 240),
            left=("Team Name", "Coach"))
        frame.pack(fill="both", expand=True, padx=24)

        if app.can_edit:
            actions = tk.Frame(self, bg=ui.BG)
            actions.pack(fill="x", padx=24, pady=10)
            ui.button(actions, "Edit Selected", self.edit_team, "outline").pack(side="left")
            ui.button(actions, "Delete Selected", self.delete_team, "danger").pack(side="left", padx=8)
        self.load()

    def category_changed(self):
        cat = self.cat.get()
        self.pool_cb["values"] = ["All"] + pool_names(None if cat == "All" else cat)
        self.pool.set("All")
        self.load()

    def load(self):
        sql = ("SELECT t.id, t.name, t.category, p.name AS pool, t.coach "
               "FROM teams t JOIN pools p ON p.id = t.pool_id")
        cond, params = [], []
        if self.cat.get() != "All":
            cond.append("t.category=%s")
            params.append(self.cat.get())
        if self.pool.get() != "All":
            cond.append("p.name=%s")
            params.append(self.pool.get())
        term = self.search.get().strip()
        if term:
            cond.append("(t.name LIKE %s OR t.coach LIKE %s)")
            params += [f"%{term}%", f"%{term}%"]
        if cond:
            sql += " WHERE " + " AND ".join(cond)
        sql += " ORDER BY t.category, p.name, t.name"
        try:
            rows = query(sql, params)
        except mysql.connector.Error as e:
            ui.show_db_error(e)
            return
        ui.fill_table(self.tree,
                      [(i + 1, r["name"], r["category"], r["pool"], r["coach"] or "")
                       for i, r in enumerate(rows)],
                      [r["id"] for r in rows])

    def bulk_register(self):
        BulkTeamDialog(self, self.load)

    def add_team(self):
        TeamDialog(self, self.load)

    def edit_team(self):
        team_id = ui.selected_id(self.tree)
        if team_id is None:
            return messagebox.showinfo("Edit team", "Select a team first.")
        team = query_one("SELECT t.*, p.name AS pool_name FROM teams t "
                         "JOIN pools p ON p.id = t.pool_id WHERE t.id=%s", (team_id,))
        TeamDialog(self, self.load, team)

    def delete_team(self):
        team_id = ui.selected_id(self.tree)
        if team_id is None:
            return messagebox.showinfo("Delete team", "Select a team first.")
        if messagebox.askyesno("Delete team",
                               "Delete this team?\nAll fixtures and results involving it will also be deleted."):
            try:
                execute("DELETE FROM teams WHERE id=%s", (team_id,))
            except mysql.connector.Error as e:
                return ui.show_db_error(e)
            self.load()
