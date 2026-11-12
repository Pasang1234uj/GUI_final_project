"""
validators.py
-------------
Every input rule of the system in one place.

Each validator takes the text typed so far and returns:
    ""          -> the value is valid
    "message"   -> what is wrong (shown instantly under the field)

They contain no GUI or database code, so they are easy to read, reuse and
test. Rules that need the database (for example "this Student ID is already
registered") are added next to the form that needs them.
"""
import re
from datetime import date, datetime

STUDENT_ID_PATTERN = re.compile(r"^08\d{6}$")
REFER_CODE_PATTERN = re.compile(r"^\d{4}$")

MAX_SCORE = 99
MAX_MESSAGE = 1000


# ---- accounts --------------------------------------------------------------
def student_id(v):
    if not v:
        return "Student ID is required."
    if not v.isdigit():
        return "Digits only - no letters, spaces or symbols."
    if len(v) >= 2 and not v.startswith("08"):
        return "Student ID must start with 08."
    if len(v) == 1 and v != "0":
        return "Student ID must start with 08."
    if len(v) < 8:
        return f"{len(v)}/8 digits - keep typing."
    if len(v) > 8:
        return "Too long - a Student ID has exactly 8 digits."
    return ""


def full_name(v):
    if not v:
        return "Full name is required."
    if len(v) < 3:
        return "Enter your full name (at least 3 characters)."
    if len(v) > 100:
        return "Name is too long (100 characters maximum)."
    if not all(c.isalpha() or c in " .'-" for c in v):
        return "Letters only (spaces, . ' - are allowed)."
    if not v[0].isalpha():
        return "Name must start with a letter."
    return ""


def password(v):
    if not v:
        return "Password is required."
    if len(v) < 6:
        return f"At least 6 characters ({len(v)}/6)."
    if len(v) > 64:
        return "Password is too long (64 characters maximum)."
    return ""


def password_strength(v):
    """Returns 'Weak', 'Fair' or 'Strong' for a password that is already valid."""
    score = 0
    score += len(v) >= 8
    score += len(v) >= 12
    score += any(c.islower() for c in v) and any(c.isupper() for c in v)
    score += any(c.isdigit() for c in v)
    score += any(not c.isalnum() for c in v)
    return "Weak" if score <= 1 else "Fair" if score <= 3 else "Strong"


def confirm_password(get_password):
    """Returns a validator that compares the field with the password field."""
    def check(v):
        if not v:
            return "Re-enter the password to confirm it."
        if v != get_password():
            return "Passwords do not match."
        return ""
    return check


def refer_code(v):
    """Optional 4-digit code (blank is allowed)."""
    if v == "":
        return ""
    if not v.isdigit():
        return "Digits only."
    if len(v) != 4:
        return f"{len(v)}/4 digits - the refer code has exactly 4 digits."
    return ""


def refer_code_required(v):
    if v == "":
        return "A 4-digit refer code is required."
    return refer_code(v)


# ---- league data -----------------------------------------------------------
def team_name(v):
    if not v:
        return "Team name is required."
    if len(v) < 2:
        return "Team name needs at least 2 characters."
    if len(v) > 80:
        return "Team name is too long (80 characters maximum)."
    if not any(c.isalnum() for c in v):
        return "Team name must contain a letter or a number."
    return ""


def coach_name(v):
    """Optional."""
    if v == "":
        return ""
    if len(v) < 2:
        return "Coach name needs at least 2 characters."
    if len(v) > 80:
        return "Coach name is too long (80 characters maximum)."
    if not all(c.isalpha() or c in " .'-" for c in v):
        return "Letters only (spaces, . ' - are allowed)."
    return ""


def pool_name(v):
    if not v:
        return "Pool name is required."
    if len(v) > 30:
        return f"Pool name is too long ({len(v)}/30)."
    if not any(c.isalnum() for c in v):
        return "Pool name must contain a letter or a number."
    return ""


def venue(v):
    if not v:
        return "Venue is required."
    if len(v) < 3:
        return "Venue needs at least 3 characters."
    if len(v) > 100:
        return f"Venue is too long ({len(v)}/100)."
    return ""


def date_text(v):
    if not v:
        return "Date is required (YYYY-MM-DD)."
    try:
        d = datetime.strptime(v, "%Y-%m-%d")
    except ValueError:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            return "That date does not exist."
        return "Use the format YYYY-MM-DD, e.g. 2026-11-21."
    if not 2000 <= d.year <= 2100:
        return "Year must be between 2000 and 2100."
    return ""


def time_text(v):
    if not v:
        return "Time is required (HH:MM)."
    try:
        datetime.strptime(v, "%H:%M")
    except ValueError:
        return "Use 24-hour HH:MM, e.g. 08:45 or 15:30."
    return ""


def score(v):
    if v == "":
        return "Enter a score (0 or more)."
    if not v.isdigit():
        return "Whole numbers only (0 or more)."
    if int(v) > MAX_SCORE:
        return f"Score looks too high (maximum {MAX_SCORE})."
    return ""


def start_date(v):
    """Date for the first generated match day: a real date, today or later."""
    error = date_text(v)
    if error:
        return error
    if datetime.strptime(v, "%Y-%m-%d").date() < date.today():
        return "Pick today or a later date."
    return ""


def matches_per_day(v):
    if v == "":
        return "Enter how many matches are played per day."
    if not v.isdigit():
        return "Whole numbers only."
    if not 1 <= int(v) <= 12:
        return "Choose between 1 and 12 matches per day."
    return ""


def interval_minutes(v):
    if v == "":
        return "Enter the minutes between kick-offs."
    if not v.isdigit():
        return "Whole numbers only."
    if not 30 <= int(v) <= 240:
        return "Choose between 30 and 240 minutes."
    return ""


def announcement_title(v):
    if not v:
        return "Title is required."
    if len(v) < 3:
        return "Title needs at least 3 characters."
    if len(v) > 150:
        return f"Title is too long ({len(v)}/150)."
    return ""


def announcement_message(v):
    if not v:
        return "Message is required."
    if len(v) < 5:
        return "Message needs at least 5 characters."
    if len(v) > MAX_MESSAGE:
        return f"Message is too long ({len(v)}/{MAX_MESSAGE})."
    return ""


# ---- MySQL connection screen ----------------------------------------------
def host(v):
    if not v:
        return "Host is required (usually localhost)."
    if " " in v:
        return "Host cannot contain spaces."
    return ""


def port(v):
    if not v:
        return "Port is required (usually 3306)."
    if not v.isdigit():
        return "Port must be a number."
    if not 1 <= int(v) <= 65535:
        return "Port must be between 1 and 65535."
    return ""


def db_user(v):
    return "" if v else "MySQL username is required (usually root)."


def db_name(v):
    if not v:
        return "Database name is required."
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", v):
        return "Letters, numbers and _ only; must not start with a number."
    return ""
