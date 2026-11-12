SAMTSE COLLEGE OF EDUCATION - FOOTBALL LEAGUE MANAGEMENT SYSTEM
================================================================

Requirements
------------
- Python 3.9 or newer (Tkinter is included with the standard installer)
- MySQL Server running on your computer
- Python packages:

      pip install mysql-connector-python pillow

  (pillow is optional - it only makes the college logo look smoother)

Files
-----
main.py            Starts the app; header, sidebar and page navigation
ui.py              Colours, fonts, tables, pop-up forms, instant-validation helpers
validators.py      Every input rule (Student ID, password, dates, scores ...)
database.py        MySQL connection and query helpers, password hashing
setup.py           First-time setup (creates database and tables)
setup.sql          Database and table definitions (+ default Pool A / Pool B)
login.py           Login screen and sign-up screen (no role selection)
dashboard.py       Banner, statistics, Admin Section, matches, results, announcement
team.py            Add / edit / delete teams
pool.py            Boys / Girls league overview, add / delete pools
fixture.py         Manual multi-match fixture builder + published fixture table
pooldraw.py        Animated Draw Pools wizard (auto draw or manual drag and drop)
poolplan.py        Pool draw rules (dealing, balance, checks - no GUI)
wizard.py          Shared window for both wizards (steps, saving page, confetti)
roundrobin.py      Animated Auto-Generate Fixtures wizard (setup, preview, save)
scheduler.py       Round-robin calculation and date / kick-off scheduling (no GUI)
result.py          Enter and view match results
league_table.py    Standings calculation (win 3, draw 1, loss 0) and page
announcement.py    Post and read announcements
search.py          Search teams, fixtures, results, announcements
administrator.py   Account management (Admin mode only)
college_logo.png   Official college logo (login, sign-up and the header)
login_background.jpg   Poster shown on the login / sign-up screens
dashboard_banner.jpg   Photo behind the wording on the dashboard banner
boys_league.jpg        Photo on the Boys League banner
girls_league.jpg       Photo on the Girls League banner

How to run
----------
1. Make sure MySQL is running.
2. Put college_logo.png in this folder (optional).
3. Start the program:

       python main.py

   The first time (or whenever it can't connect), a "Connect to MySQL"
   screen appears - enter your Host / Port / Username / Password / Database
   name and click "Connect & Set Up". It creates the database and tables
   for you and saves the details to config.json, so you only do this once.
   (A command-line alternative, python setup.py, still works if you prefer.)

4. Click "Sign Up". The very first account created becomes an Admin and
   sets a shared 4-digit refer code.

Accounts and roles
------------------
There are only two roles: Admin and Viewer.

- Username = Student ID: exactly 8 digits, starting with 08 (e.g. 08201234).
- The LOGIN page asks only for Student ID and password. Nobody chooses a
  role there - it is read from the account.
- The SIGN-UP page asks for Full Name, Student ID, password, confirm
  password and an optional refer code (no role drop-down):
    * first account ever          -> Admin (sets the 4-digit refer code)
    * correct refer code typed    -> Admin
    * refer code left blank       -> Viewer (read-only)
  After 5 different wrong refer codes, sign-up locks until the program is
  restarted.
- An Admin can add, edit or delete accounts and view or change the refer
  code (Dashboard > Admin Section, or the Administrators page).
- Databases from the older version (Super Admin / Co-Admin / Viewer) are
  upgraded automatically the first time the program starts: Super Admins and
  Co-Admins become Admins.

Admin | Viewer switch (top right of every page)
-----------------------------------------------
- Once you are logged in you can switch between Admin and Viewer at any
  time - no extra access is needed.
- Admin mode:  add, update and delete information.
- Viewer mode: view only - every Add / Edit / Delete button is hidden.
- The role stored on the account only decides which mode you start in
  (Admin account -> Admin mode, Viewer account -> Viewer mode).

Dashboard
---------
- Banner with the college photo, then live statistics.
- Admin mode shows an "Admin Section": quick buttons to add a Team, Pool,
  Fixture, Result, Announcement or User, and shortcuts to update Teams,
  Fixtures, Results, Announcements and Users, plus the Refer Code. The
  dashboard refreshes as soon as something is saved.
- Viewer mode shows a "Viewer Section" with read-only shortcuts to Teams,
  Fixtures, Results, League Table and Announcements.

Manual fixture scheduling
-------------------------
1. Open Fixtures while in Admin mode.
2. Choose Boys or Girls and select the required pool.
3. Tick the teams that will participate. Select all or clear the selection
   using the buttons above the team list.
4. Click + Add Match. For every match, choose the home team, away team,
   date (YYYY-MM-DD), kick-off time (HH:MM, 24-hour) and venue.
5. Add as many match cards as required. Remove any unwanted card before
   publishing. The form checks that the same team is not scheduled twice
   at the same date and kick-off time.
6. Save Draft keeps the current schedule on the open Fixtures page only;
   it is not yet written to MySQL or visible to viewers.
7. Confirm All Fixtures displays a review prompt and inserts the complete
   schedule in one database transaction. If an insert fails, the full batch
   is rolled back. Confirmed fixtures appear in the Published Fixtures table
   and are available to Results and League Table.
8. Use Edit Selected to change the date, time or venue of a published match.
   Use Delete Selected to remove a published match and its result.

There is no automatic fixture draw, random shuffle or round-robin generator
in this version. Every home/away pairing and match date is selected manually.

Instant form validation
-----------------------
Every form checks what you type as you type it:
- a message under each field turns red (what is wrong) or green (OK);
- the field border changes colour;
- the Save / Login / Sign Up button stays greyed out until every field is valid;
- checks that need the database also run live (Student ID already registered,
  duplicate team or pool name, refer code correct).
All rules are listed in validators.py.

Forgotten password
-------------------
If you're locked out (forgotten password for the Admin or anyone else),
and you're on the same computer with MySQL already set up, run:

       python reset_password.py

It lists every account and lets you set a new password directly in the
database - no old password needed.

Roles
-----
Admin mode    Add, update and delete teams, pools, fixtures, results,
              announcements and user accounts
Viewer mode   Read-only access to every page

Typical workflow
----------------
1. Sign up first (you become an Admin). Share the refer code with other Admins.
2. Pools page: Pool A and Pool B exist by default for Boys and Girls;
   add or delete pools if needed.
3. Teams page: add teams and assign each to a pool.
4. Fixtures page: schedule matches between teams in the same pool.
5. Results page: enter the score after each match.
6. League Table updates automatically from the results.

Notes
-----
- Deleting a team also deletes its fixtures and results.
- A pool cannot be deleted while it still has teams.
- Connection settings are stored in config.json (created by setup.py).


MANUAL WORKFLOW UPDATE
----------------------
Teams: use "Register Teams (many at once)" to enter multiple teams and
choose the category and pool for each row before saving. The existing
single-team registration remains available.

Fixtures: use the Fixture Manager to select multiple teams and create
many match cards manually. Review the schedule and choose Confirm All Fixtures
to publish the batch to the main Fixtures table. Automatic fixture generation
and pool draw/shuffle screens are not included in this version.


FIXTURE BUILDER UPDATE
----------------------
The Fixtures page now includes a modern, scrollable manual schedule builder.
It supports selecting multiple registered teams, adding many editable match
cards, choosing dates/times/venues for each match, saving an in-page draft,
and confirming the entire batch together. The published fixture table remains
connected to the existing Results and League Table modules.

Database name used by this project: football_league.
Connection details are stored in config.json (created by the setup screen).
