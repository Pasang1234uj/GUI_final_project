"""
ui.py
-----
Colours, fonts and small reusable widgets shared by every page so the
whole application has the same look as the prototype.
"""
import math
import os
import time as _time
import tkinter as tk
from datetime import date, datetime, time, timedelta
from tkinter import messagebox, ttk

try:
    from PIL import Image, ImageFilter, ImageTk
    HAS_PIL = True
except ImportError:  # Pillow is optional - logo is just loaded without smoothing
    HAS_PIL = False

# ---- Theme -----------------------------------------------------------------
NAVY = "#0B2A5B"
NAVY_HOVER = "#163C7A"
BLUE = "#1565D8"
BG = "#EEF3FA"
WHITE = "#FFFFFF"
TEXT = "#1F2A44"
MUTED = "#6B7A90"
RED = "#D93025"
GREEN = "#1E8E3E"
BORDER = "#D5DEEA"
CARD_COLORS = ["#1E88E5", "#12A08A", "#F58220", "#7E57C2"]
ORANGE = "#F58220"

FONT = ("Segoe UI", 10)
FONT_B = ("Segoe UI", 10, "bold")
FONT_H1 = ("Segoe UI", 20, "bold")
FONT_H2 = ("Segoe UI", 13, "bold")
FONT_SMALL = ("Segoe UI", 9)


def setup_styles(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Treeview", font=FONT, rowheight=30, background=WHITE,
                    fieldbackground=WHITE, foreground=TEXT, borderwidth=0)
    style.configure("Treeview.Heading", font=FONT_B, background="#E4ECF7",
                    foreground=TEXT, relief="flat", padding=6)
    style.map("Treeview", background=[("selected", "#CFE1FB")],
              foreground=[("selected", TEXT)])
    style.map("Treeview.Heading", background=[("active", "#D6E2F3")])
    style.configure("TCombobox", padding=4)
    style.configure("TEntry", padding=5)
    # entries turn red / green while the user types (instant validation)
    for name, colour in (("Bad", RED), ("Good", GREEN)):
        style.configure(f"{name}.TEntry", padding=5, bordercolor=colour,
                        lightcolor=colour, darkcolor=colour)
        style.map(f"{name}.TEntry", bordercolor=[("focus", colour)],
                  lightcolor=[("focus", colour)], darkcolor=[("focus", colour)])


# ---- Images ----------------------------------------------------------------
def load_image(path, size):
    """Load an image scaled to fit inside size x size. Returns None if missing."""
    if not os.path.exists(path):
        return None
    try:
        if HAS_PIL:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((size, size), Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        img = tk.PhotoImage(file=path)
        factor = max(1, img.width() // size)
        return img.subsample(factor, factor) if factor > 1 else img
    except Exception:
        return None


def load_cover_image(path, width, height, focus=(0.5, 0.5), zoom=1.0):
    """Load a photo cropped/scaled to fill a width x height box exactly
    (like CSS `object-fit: cover`).
      focus = (x, y) between 0 and 1: which part of the photo to keep when
              cropping ((0.5, 0.0) keeps the top, (0.5, 1.0) the bottom);
      zoom  = 1.0 shows as much of the photo as fits, 1.5 zooms in.
    Returns None if the file is missing or Pillow is not installed, so
    callers can fall back to a plain colour."""
    if not (HAS_PIL and os.path.exists(path)):
        return None
    try:
        img = Image.open(path).convert("RGB")
        dst_ratio = width / height
        if img.width / img.height > dst_ratio:     # photo is wider than the box
            box_w, box_h = img.height * dst_ratio, img.height
        else:                                       # photo is taller than the box
            box_w, box_h = img.width, img.width / dst_ratio
        crop_w, crop_h = int(box_w / zoom), int(box_h / zoom)
        x0 = int((img.width - crop_w) * focus[0])
        y0 = int((img.height - crop_h) * focus[1])
        img = img.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize((width, height), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def load_fit_image(path, width, height):
    """Show the WHOLE photo (nothing cropped) centred in a width x height
    box. The empty sides are filled with a blurred, darkened copy of the
    same photo so it never looks like plain bars. Used for the login poster."""
    if not (HAS_PIL and os.path.exists(path)):
        return None
    try:
        img = Image.open(path).convert("RGB")
        scale = min(width / img.width, height / img.height)
        fg = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
        fill = max(width / img.width, height / img.height)
        bg = img.resize((int(img.width * fill) + 1, int(img.height * fill) + 1), Image.BILINEAR)
        x0, y0 = (bg.width - width) // 2, (bg.height - height) // 2
        bg = bg.crop((x0, y0, x0 + width, y0 + height)).filter(ImageFilter.GaussianBlur(18))
        bg = Image.blend(bg, Image.new("RGB", bg.size, (6, 20, 48)), 0.55)
        bg.paste(fg, ((width - fg.width) // 2, (height - fg.height) // 2))
        return ImageTk.PhotoImage(bg)
    except Exception:
        return None


def photo_banner(parent, photo_path, colour, height=220, focus=(0.5, 0.5), zoom=1.0,
                 lines=(), chip=None):
    """Banner where the photo fills the WHOLE space and the wording sits on
    top of it. A soft gradient in the banner colour fades in from the left
    so the white text stays readable while the faces on the right stay
    clear. The picture is re-fitted whenever the window is resized.

      lines = [(text, font, fill), ...]  drawn top to bottom at the left
      chip  = (text, background, foreground) small label under the lines
    Returns the Canvas (pack it yourself)."""
    import tkinter.font as tkfont

    canvas = tk.Canvas(parent, height=height, bg=colour, highlightthickness=0, bd=0)
    state = {"width": 0}

    def draw(event=None):
        width = canvas.winfo_width()
        if width < 50 or width == state["width"]:
            return
        state["width"] = width
        canvas.delete("all")
        photo = _banner_photo(photo_path, width, height, colour, focus, zoom)
        if photo:
            canvas.image = photo                      # keep a reference
            canvas.create_image(0, 0, image=photo, anchor="nw")
        # wording: vertically centred block, with a soft shadow for contrast
        sizes = [tkfont.Font(font=f).metrics("linespace") for _, f, _ in lines]
        total = sum(sizes) + (34 if chip else 0)
        y = max((height - total) // 2, 8)
        for (text, font, fill), size in zip(lines, sizes):
            canvas.create_text(29, y + 1, text=text, font=font, fill="#000000", anchor="nw")
            canvas.create_text(28, y, text=text, font=font, fill=fill, anchor="nw")
            y += size
        if chip:
            text, bg, fg = chip
            item = canvas.create_text(40, y + 22, text=text, font=FONT_B, fill=fg, anchor="w")
            x1, y1, x2, y2 = canvas.bbox(item)
            box = canvas.create_rectangle(28, y1 - 4, x2 + 12, y2 + 4, fill=bg, outline="")
            canvas.tag_lower(box, item)

    canvas.bind("<Configure>", draw)
    return canvas


def _banner_photo(path, width, height, colour, focus, zoom):
    """Photo cropped to width x height with a gradient of `colour` on the left."""
    if not (HAS_PIL and os.path.exists(path)):
        return None
    try:
        img = Image.open(path).convert("RGB")
        dst_ratio = width / height
        if img.width / img.height > dst_ratio:
            box_w, box_h = img.height * dst_ratio, img.height
        else:
            box_w, box_h = img.width, img.width / dst_ratio
        crop_w, crop_h = int(box_w / zoom), int(box_h / zoom)
        x0 = int((img.width - crop_w) * focus[0])
        y0 = int((img.height - crop_h) * focus[1])
        img = img.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize((width, height), Image.LANCZOS)
        # gradient: strong on the far left (behind the text), gone by ~48% width
        fade_end = int(width * 0.48)
        ramp = Image.new("L", (width, 1))
        ramp.putdata([int(235 * max(0.0, 1 - x / fade_end) ** 1.3) if x < fade_end else 0
                      for x in range(width)])
        ramp = ramp.resize((width, height))
        rgb = tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))
        img.paste(Image.new("RGB", (width, height), rgb), (0, 0), ramp)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


# ---- Formatting ------------------------------------------------------------
def fmt_date(d):
    if isinstance(d, (date, datetime)):
        return d.strftime("%d %b %Y")
    return str(d)


def _to_hm(t):
    if isinstance(t, timedelta):          # MySQL TIME comes back as timedelta
        total = int(t.total_seconds())
        return total // 3600, (total % 3600) // 60
    if isinstance(t, time):
        return t.hour, t.minute
    h, m = str(t).split(":")[:2]
    return int(h), int(m)


def fmt_time(t):
    h, m = _to_hm(t)
    return datetime(2000, 1, 1, h, m).strftime("%I:%M %p")


def to_hhmm(t):
    h, m = _to_hm(t)
    return f"{h:02d}:{m:02d}"


def parse_date(text):
    return datetime.strptime(text.strip(), "%Y-%m-%d").date()


def parse_time(text):
    return datetime.strptime(text.strip(), "%H:%M").time()


def show_db_error(err):
    messagebox.showerror("Database error", f"Something went wrong with the database:\n\n{err}")


# ---- Widgets ---------------------------------------------------------------
def button(parent, text, command, kind="primary"):
    styles = {
        "primary": dict(bg=BLUE, fg=WHITE, activebackground="#0F4FB0",
                        activeforeground=WHITE, highlightbackground=BLUE),
        "outline": dict(bg=WHITE, fg=BLUE, activebackground="#E6F0FF",
                        activeforeground=BLUE, highlightbackground=BLUE),
        "danger": dict(bg=WHITE, fg=RED, activebackground="#FDECEA",
                       activeforeground=RED, highlightbackground=RED),
        "grey": dict(bg="#E5EAF2", fg=TEXT, activebackground="#D4DBE7",
                     activeforeground=TEXT, highlightbackground="#E5EAF2"),
    }
    btn = tk.Button(parent, text=text, command=command, font=FONT_B, relief="flat",
                    bd=0, cursor="hand2", padx=14, pady=6, highlightthickness=1,
                    **styles[kind])
    btn._on = dict(bg=styles[kind]["bg"], fg=styles[kind]["fg"],
                   highlightbackground=styles[kind]["highlightbackground"])
    return btn


def set_enabled(btn, enabled):
    """Grey a button out (or bring it back) - used by the form validation."""
    if enabled:
        btn.config(state="normal", cursor="hand2", **btn._on)
    else:
        btn.config(state="disabled", cursor="arrow", bg="#D5DCE8", fg="#8A97AD",
                   disabledforeground="#8A97AD", highlightbackground="#D5DCE8")


def page_header(parent, title, subtitle=""):
    """Title on the left. Returns a frame on the right for action buttons."""
    bar = tk.Frame(parent, bg=BG)
    bar.pack(fill="x", padx=24, pady=(18, 10))
    left = tk.Frame(bar, bg=BG)
    left.pack(side="left")
    tk.Label(left, text=title, font=FONT_H1, bg=BG, fg=NAVY).pack(anchor="w")
    if subtitle:
        tk.Label(left, text=subtitle, font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w")
    right = tk.Frame(bar, bg=BG)
    right.pack(side="right")
    return right


def labeled_combo(parent, label, values, default=None, width=14, command=None):
    """Small label above a read-only drop-down. Returns (frame, StringVar, combobox)."""
    box = tk.Frame(parent, bg=BG)
    tk.Label(box, text=label, font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w")
    var = tk.StringVar(value=default if default is not None else values[0])
    cb = ttk.Combobox(box, textvariable=var, values=values, state="readonly",
                      width=width, font=FONT)
    cb.pack()
    if command:
        cb.bind("<<ComboboxSelected>>", lambda e: command())
    return box, var, cb


def make_table(parent, columns, widths=None, height=12, left=()):
    """Treeview with a scrollbar. Returns (frame, tree)."""
    frame = tk.Frame(parent, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height,
                        selectmode="browse")
    for i, col in enumerate(columns):
        tree.heading(col, text=col)
        tree.column(col, width=widths[i] if widths else 100,
                    anchor="w" if col in left else "center")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    tree.tag_configure("odd", background="#F5F8FD")
    tree.tag_configure("even", background=WHITE)
    tree.tag_configure("Completed", foreground=GREEN)
    tree.tag_configure("top", font=FONT_B, foreground=NAVY)
    return frame, tree


def fill_table(tree, rows, ids=None, extra_tags=None):
    for item in tree.get_children():
        tree.delete(item)
    for i, row in enumerate(rows):
        tags = ["odd" if i % 2 else "even"]
        if extra_tags and extra_tags[i]:
            tags.append(extra_tags[i])
        tree.insert("", "end", iid=str(ids[i]) if ids else None, values=row, tags=tags)


def selected_id(tree):
    sel = tree.selection()
    return int(sel[0]) if sel else None


# ---- Instant form validation ----------------------------------------------
def make_cache():
    """Tiny memo for database look-ups made while typing, so MySQL is asked
    once per value instead of once per key press."""
    store = {}

    def cached(key, fn):
        if key not in store:
            store[key] = fn()
        return store[key]
    return cached


class FieldCheck:
    """Watches one input and shows a message under it as the user types.

    check(value) returns "" when valid, otherwise the error text.
    Empty untouched fields show a grey hint instead of an error, so a blank
    form does not start out shouting at the user.
    """

    def __init__(self, get_value, check, msg_label, hint="", entry=None, ok_text="Looks good"):
        self.get_value, self.check = get_value, check
        self.msg, self.hint, self.entry, self.ok_text = msg_label, hint, entry, ok_text
        self.touched = False

    def touch(self):
        self.touched = True

    def _style(self, name):
        if self.entry is not None and isinstance(self.entry, ttk.Entry):
            self.entry.configure(style=name)

    def update(self):
        value = self.get_value()
        try:
            error = self.check(value)
        except Exception:          # a failed look-up must never break typing
            error = ""
        if error and (self.touched or value != ""):
            self.msg.config(text="\u2717  " + error, fg=RED)
            self._style("Bad.TEntry")
        elif not error and value != "":
            text = self.ok_text(value) if callable(self.ok_text) else self.ok_text
            self.msg.config(text="\u2713  " + text, fg=GREEN)
            self._style("Good.TEntry")
        else:
            self.msg.config(text=self.hint, fg=MUTED)
            self._style("TEntry")
        return not error


class FormGuard:
    """Keeps the Save / Login button disabled until every field is valid."""

    def __init__(self, button=None):
        self.items, self.button = [], button

    def add(self, item):
        self.items.append(item)
        return item

    def refresh(self):
        results = [item.update() for item in self.items]
        ok = all(results)
        if self.button is not None:
            set_enabled(self.button, ok)
        return ok

    def valid(self):
        return all(not item.check(item.get_value()) for item in self.items)


# ---- Pop-up form -----------------------------------------------------------
class Dialog(tk.Toplevel):
    """Small modal form window. Add fields, then add_buttons(), then show().

    Fields accept an optional check= function (see validators.py). When a
    field has one, a message appears under it and updates on every key
    press; the Save button stays disabled until every field is valid.
    """

    def __init__(self, parent, title, width=420):
        super().__init__(parent.winfo_toplevel())
        self.title(title)
        self.configure(bg=WHITE)
        self.resizable(False, False)
        self.width = width
        self.vars = {}
        self.texts = {}
        self.labels = {}
        self.guard = FormGuard()
        self.save_btn = None
        self.cached = make_cache()
        self.body = tk.Frame(self, bg=WHITE, padx=26, pady=22)
        self.body.pack(fill="both", expand=True)
        tk.Label(self.body, text=title, font=FONT_H2, bg=WHITE, fg=NAVY).pack(anchor="w", pady=(0, 10))

    def _label(self, text, key=None):
        lbl = tk.Label(self.body, text=text, font=FONT_SMALL, bg=WHITE, fg=MUTED)
        lbl.pack(anchor="w", pady=(8, 2))
        if key:
            self.labels[key] = lbl
        return lbl

    def _watch(self, key, widget, check, hint, ok_text, raw=False):
        """Add the live message under a field and wire it to the form guard."""
        msg = tk.Label(self.body, text=hint, font=FONT_SMALL, bg=WHITE, fg=MUTED,
                       anchor="w", justify="left", wraplength=self.width - 60)
        msg.pack(fill="x")
        getter = (lambda: self.vars[key].get()) if raw else (lambda: self.get(key))
        field = self.guard.add(FieldCheck(getter, check, msg, hint, widget, ok_text))
        if key in self.vars:
            self.vars[key].trace_add("write", lambda *a: self.guard.refresh())
        else:                                   # Text widget has no variable
            widget.bind("<KeyRelease>", lambda e: self.guard.refresh())
        widget.bind("<FocusOut>", lambda e: (field.touch(), self.guard.refresh()), add="+")
        return field

    def add_entry(self, label, key, value="", show=None, check=None, hint="",
                  ok_text="Looks good"):
        self._label(label, key)
        var = tk.StringVar(value=value)
        self.vars[key] = var
        entry = ttk.Entry(self.body, textvariable=var, font=FONT, show=show or "")
        entry.pack(fill="x")
        if check:
            self._watch(key, entry, check, hint, ok_text, raw=show is not None)
        return entry

    def add_combo(self, label, key, values, value="", check=None, hint="",
                  ok_text="Looks good"):
        self._label(label, key)
        var = tk.StringVar(value=value if value in values else "")
        self.vars[key] = var
        cb = ttk.Combobox(self.body, textvariable=var, values=values, state="readonly", font=FONT)
        cb.pack(fill="x")
        if check:
            self._watch(key, cb, check, hint, ok_text)
        return cb

    def add_text(self, label, key, value="", height=6, check=None, hint="",
                 ok_text="Looks good"):
        self._label(label, key)
        box = tk.Text(self.body, height=height, width=40, font=FONT, wrap="word",
                      relief="solid", bd=1)
        box.insert("1.0", value)
        box.pack(fill="x")
        self.texts[key] = box
        if check:
            self._watch(key, box, check, hint, ok_text)
        return box

    def add_buttons(self, on_save, save_text="Save"):
        row = tk.Frame(self.body, bg=WHITE)
        row.pack(fill="x", pady=(18, 0))
        self.save_btn = button(row, save_text, on_save)
        self.save_btn.pack(side="right")
        button(row, "Cancel", self.destroy, "grey").pack(side="right", padx=8)
        self.guard.button = self.save_btn
        self.guard.refresh()

    def get(self, key):
        if key in self.texts:
            return self.texts[key].get("1.0", "end").strip()
        return self.vars[key].get().strip()

    def form_ok(self):
        """Final gate used by save(): runs every check once more."""
        return self.guard.refresh()

    def error(self, message):
        messagebox.showerror("Error", message, parent=self)

    def show(self):
        self.update_idletasks()
        parent = self.master
        w = max(self.width, self.winfo_reqwidth())
        h = self.winfo_reqheight()
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
        self.transient(parent)
        self.wait_visibility()
        self.grab_set()


# ---- Scrollable page -------------------------------------------------------
class ScrollFrame(tk.Frame):
    """A frame that scrolls vertically when its content is taller than the
    window. Put widgets in .inner"""

    def __init__(self, parent, bg=BG):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(window, width=e.width))
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)
        self.canvas.bind("<Destroy>", self._unbind_wheel)

    def _bind_wheel(self, _e=None):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", self._on_wheel)
        self.canvas.bind_all("<Button-5>", self._on_wheel)

    def _unbind_wheel(self, _e=None):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            try:
                self.canvas.unbind_all(seq)
            except tk.TclError:
                pass

    def _on_wheel(self, e):
        if not self.canvas.winfo_exists():
            return
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            return                                  # nothing to scroll
        step = -1 if (e.num == 4 or e.delta > 0) else 1
        self.canvas.yview_scroll(step, "units")


# ---- Animation toolkit -------------------------------------------------------
# Tkinter has no built-in animation, so everything below is the same trick:
# change a property a little, wait ~15 ms with widget.after(), repeat.
def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    """Colour between two '#rrggbb' colours (t = 0 gives c1, t = 1 gives c2)."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(round(lerp(x, y, t))) for x, y in zip(a, b))


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    return 3 * t * t - 2 * t * t * t


def ease_out_back(t):
    """Slight overshoot, then settle - gives a springy feel."""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def _alive(widget):
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        return False


def tween(widget, duration_ms, update, on_done=None, ease=ease_out, delay=0):
    """Call update(progress) about 60 times a second while progress goes
    from 0 to 1 (shaped by `ease`). Stops quietly if the widget is destroyed."""
    def run():
        start = _time.time()

        def step():
            if not _alive(widget):
                return
            t = min((_time.time() - start) * 1000.0 / max(duration_ms, 1), 1.0)
            update(ease(t))
            if t < 1.0:
                widget.after(15, step)
            elif on_done:
                on_done()
        step()

    if delay:
        widget.after(delay, lambda: run() if _alive(widget) else None)
    else:
        run()


def count_up(label, target, duration_ms=700, delay=0, start=0, fmt="{}"):
    """Numbers that roll up (or down) to their value."""
    tween(label, duration_ms,
          lambda p: label.config(text=fmt.format(int(round(lerp(start, target, p))))), delay=delay)


def fade_in(window, duration_ms=260):
    """Fade a pop-up window in (silently skipped where unsupported)."""
    try:
        window.attributes("-alpha", 0.0)
    except tk.TclError:
        return

    def update(p):
        try:
            window.attributes("-alpha", p)
        except tk.TclError:
            pass
    tween(window, duration_ms, update)


def hover_fade(widget, normal, hover, ms=140):
    """Background colour fades smoothly when the mouse enters or leaves."""
    state = {"cur": normal}

    def go(target):
        try:
            if str(widget.cget("state")) == "disabled":
                return
        except tk.TclError:
            return
        begin = state["cur"]

        def update(p):
            state["cur"] = lerp_color(begin, target, p)
            widget.config(bg=state["cur"])
        tween(widget, ms, update)
    widget.bind("<Enter>", lambda e: go(hover), add="+")
    widget.bind("<Leave>", lambda e: go(normal), add="+")


def pulse(widget, base, bright, times=2, ms_each=520, delay=0):
    """Draw attention: the background breathes between two colours."""
    def update(p):
        t = (math.sin(p * math.pi * 2 * times - math.pi / 2) + 1) / 2
        widget.config(bg=lerp_color(base, bright, t))
    tween(widget, ms_each * times, update, on_done=lambda: widget.config(bg=base),
          ease=lambda t: t, delay=delay)


def round_rect_points(x1, y1, x2, y2, r=10):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


def round_rect(canvas, x1, y1, x2, y2, r=10, **kw):
    """Rounded rectangle on a Canvas (returns the item id)."""
    return canvas.create_polygon(round_rect_points(x1, y1, x2, y2, r), smooth=True, **kw)


def bind_mousewheel(canvas):
    """Scroll a Canvas with the mouse wheel while the pointer is over it."""
    def on_wheel(e):
        if not _alive(canvas):
            return
        step = -1 if (getattr(e, "num", 0) == 4 or e.delta > 0) else 1
        canvas.yview_scroll(step * 2, "units")

    def enter(_e=None):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            canvas.bind_all(seq, on_wheel)

    def leave(_e=None):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            try:
                canvas.unbind_all(seq)
            except tk.TclError:
                pass
    canvas.bind("<Enter>", enter, add="+")
    canvas.bind("<Leave>", leave, add="+")
    canvas.bind("<Destroy>", leave, add="+")


class Segmented(tk.Canvas):
    """Pill-shaped switch with a highlight that slides to the chosen option."""

    def __init__(self, parent, options, value, command=None, seg_width=96, height=34,
                 accent=BLUE, bg=WHITE, track="#E4ECF7"):
        super().__init__(parent, width=seg_width * len(options), height=height, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.options, self.command = list(options), command
        self.seg_w = seg_width
        self.value = value if value in self.options else self.options[0]
        round_rect(self, 0, 0, seg_width * len(options), height, height // 2, fill=track, outline="")
        self._pill_x = self.options.index(self.value) * seg_width + 3
        self.pill = round_rect(self, self._pill_x, 3, self._pill_x + seg_width - 6, height - 3,
                               (height - 6) // 2, fill=accent, outline="")
        self.texts = [self.create_text(i * seg_width + seg_width / 2, height / 2, text=o, font=FONT_B,
                                       fill=WHITE if o == self.value else MUTED)
                      for i, o in enumerate(self.options)]
        self.bind("<Button-1>", self._click)

    def get(self):
        return self.value

    def _click(self, event):
        i = max(0, min(int(event.x // self.seg_w), len(self.options) - 1))
        if self.options[i] != self.value:
            self.set(self.options[i])
            if self.command:
                self.command()

    def set(self, value, animate=True):
        target = self.options.index(value) * self.seg_w + 3
        start, self.value = self._pill_x, value
        for item, option in zip(self.texts, self.options):
            self.itemconfig(item, fill=WHITE if option == value else MUTED)

        def update(p):
            x = lerp(start, target, p)
            self.move(self.pill, x - self._pill_x, 0)
            self._pill_x = x
        if animate:
            tween(self, 260, update, ease=ease_out_back)
        else:
            update(1.0)


class Chip(tk.Label):
    """Toggle button (used for the weekday picker); the colour fades on click."""

    def __init__(self, parent, text, selected=False, command=None, on=BLUE, off="#E4ECF7", bg=WHITE):
        self.on, self.off, self.command = on, off, command
        self.selected = selected
        super().__init__(parent, text=text, font=FONT_B, padx=11, pady=6, cursor="hand2",
                         bg=on if selected else off, fg=WHITE if selected else TEXT)
        self._color = on if selected else off
        self.bind("<Button-1>", lambda e: self.toggle())

    def toggle(self):
        self.set(not self.selected)
        if self.command:
            self.command()

    def set(self, selected, animate=True):
        self.selected = selected
        target = self.on if selected else self.off
        start = self._color
        self.config(fg=WHITE if selected else TEXT)

        def update(p):
            self._color = lerp_color(start, target, p)
            self.config(bg=self._color)
        if animate:
            tween(self, 170, update)
        else:
            update(1.0)
