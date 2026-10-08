MOVIE BOOKING SYSTEM — DJANGO VERSION
====================================
Your original design, movie posters, seat layout, ticket printing, booking
search, CSV download, movie editor and price editor are preserved.
Accounts and bookings now live in Django's database, not localStorage.

FIRST RUN — WINDOWS / VS CODE
----------------------------
1. Extract this ZIP (do not run it inside the ZIP).
2. In VS Code, choose File > Open Folder. Open movie-booking-django.
   You must see manage.py and requirements.txt directly in this folder.
3. Open Terminal > New Terminal and run these commands ONE AT A TIME:

   py -m venv venv
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   .\venv\Scripts\python.exe manage.py migrate
   .\venv\Scripts\python.exe manage.py seed_movies
   .\venv\Scripts\python.exe manage.py createsuperuser
   .\venv\Scripts\python.exe manage.py runserver

4. createsuperuser asks for a username, optional email and password.
   Choose your own administrator username and password. Password characters
   do not appear while typing; this is normal. No default admin password exists.
5. Keep the terminal running. Open Chrome at:
   http://127.0.0.1:8000/
6. Click Create an account to register a customer with a 10-digit phone number.
   Use a password of at least 8 characters that is not common or entirely numeric.

Activation is not required: the commands above use the virtual environment
Python directly, avoiding PowerShell activation-policy and PATH problems.
Do NOT run startproject again. This ZIP already contains the Django project.
Do NOT use Live Server or double-click templates/index.html.

NEXT TIME
---------
Open the same folder and run:
   .\venv\Scripts\python.exe manage.py runserver
Stop the server with Ctrl+C. Restarting does not erase your database.

ADMIN: WHERE TO SEE REGISTERED USERS
----------------------------------
Open http://127.0.0.1:8000/admin/ and sign in with the superuser you created.
Click Users under Authentication and Authorization. Customer usernames are
phone numbers; First name contains the full name entered at registration.
The last-login field records the most recent login, not who is currently online.
Passwords are securely hashed and cannot be viewed as plain text.

To use the original movie-management interface, log in on the HOME PAGE with
that same superuser username (in the phone/username field) and password.
Click Admin to manage movies, prices, bookings, CSV exports and your password.
The Registered users link opens Django's user administration page.
Only superusers can access the custom administration API.
The built-in Django admin also lets you inspect bookings and change prices.
Use the home-page Admin > Movies form to add movies and upload posters.
Removing a movie archives it so booking history remains available.
Cancelling a booking deletes that booking and makes its seats available again.

DATABASE
--------
SQLite is the default and needs no separate installation or XAMPP.
The db.sqlite3 file is created by migrate. Back it up together with media/.
Keep .secret_key private; Django generates it once on first run.
Old browser-only accounts and bookings are NOT imported. Register again.
The original five movies are added by seed_movies, which can be run again
without resetting existing prices or duplicating unchanged sample movies.

OPTIONAL MYSQL
--------------
The SQLite version is tested. MySQL support is configured but was not tested
against a running MySQL server in this environment. Use a Django-supported
MySQL/MariaDB release; older XAMPP distributions may need an upgrade.
Changing database does NOT transfer SQLite data.

1. Start your MySQL service and create the database in your SQL client:
   CREATE DATABASE movie_booking CHARACTER SET utf8mb4;
2. Install the driver into this project's environment:
   .\venv\Scripts\python.exe -m pip install mysqlclient
3. In the same PowerShell terminal, set your actual connection details:
   $env:DB_ENGINE="mysql"
   $env:DB_NAME="movie_booking"
   $env:DB_USER="root"
   $env:DB_PASSWORD="YOUR_MYSQL_PASSWORD"
   $env:DB_HOST="127.0.0.1"
   $env:DB_PORT="3306"
4. Run migrate, seed_movies, createsuperuser and runserver as above.
   Set these variables again whenever opening a new terminal.
5. To return to SQLite in that terminal:
   Remove-Item Env:DB_ENGINE
If mysqlclient fails to install, use the default SQLite setup first.

PROJECT FILES
-------------
manage.py                 Django command entry point
config/settings.py        Database, templates, static files and timezone
config/urls.py            Home page, /api/ endpoints and /admin/
booking/models.py         Movies, ticket classes, bookings, seat reservations
booking/views.py          Registration, sessions, validation and booking API
booking/admin.py          Django administration configuration
booking/migrations/       Database schema migration (included)
booking/tests.py          Automated security and booking tests
templates/index.html      Your original page adapted as a Django template
static/app.js             Your original UI connected to the Django API
static/style.css          Original styling
static/images/            Original five movie posters
media/posters/            New poster uploads (created when used)

TESTING
-------
   .\venv\Scripts\python.exe manage.py test booking
Tests cover registration, hashed passwords, login/logout, CSRF protection,
permissions, booking ownership, server-calculated totals, invalid requests,
duplicate-seat rollback, cancellation, admin edits and idempotent seeding.
Database uniqueness prevents two bookings from reserving the same seat for
the same movie/date/time. A multi-seat reservation succeeds or rolls back whole.
Each movie/date/time is treated as a separate screen; there is no theatre model.
Up to 10 seats can be booked at once. Prices are whole rupees.
There is no payment gateway; booking amounts do not represent collected payments.

TROUBLESHOOTING
---------------
"can't open manage.py": run dir. Open the folder containing manage.py.
"No module named django": run the requirements installation command above.
"no such table": stop server, run migrate, then seed_movies, then restart.
Port 8000 already in use: run manage.py runserver 8001 and open port 8001.
Forgot admin password: run manage.py changepassword YOUR_ADMIN_USERNAME.
Session security error: refresh the page and retry; enable browser cookies.

This is a local learning project. For public hosting, use a production server,
DEBUG=0, a secret environment key, HTTPS with secure cookies, login rate limits,
proper static/media hosting and backups. Do not expose runserver publicly.
Django compatibility reference: https://docs.djangoproject.com/en/5.2/releases/5.2/
