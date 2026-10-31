# FITNESS ZONE

> Step-by-step VS Code and hosting instructions are in **SETUP.md**.

Intelligent fitness, workout and sports-gear platform built with **Django**, HTML, CSS and vanilla JavaScript.

## Quick start

```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations accounts shop workouts
python manage.py migrate
python manage.py seed_demo          # demo categories, products and the exercise library
python manage.py createsuperuser    # for /admin/
python manage.py runserver
```

Open http://127.0.0.1:8000/ and the admin panel at http://127.0.0.1:8000/admin/.

Settings come from environment variables (see `.env.example`). Defaults work out of the box:
SQLite database and a console email backend, so **verification and welcome emails print in your terminal**.
To configure email locally, copy `.env.example` to `.env`, switch the backend to SMTP, and fill in the Gmail settings;
settings in `.env` are loaded automatically.

## What is included

| Requirement | Where |
|---|---|
| Template setup, responsive design | `templates/base.html`, `static/css/style.css` (mobile menu, fluid grids, keyboard focus, reduced motion) |
| Register, login, logout, welcome email | `accounts/` (login accepts username **or** email; email sent from `accounts/emails.py`, templates in `templates/emails/`) |
| Product details | `/product/<slug>/` |
| Category-wise product view | `/shop/category/<slug>/` |
| Dedicated shop page: search, filters, sorting, pagination | `/shop/` (search, category, brand, price range, in-stock, on-sale, 4 sort orders, 12 per page) |
| Favourites and cart | `shop/` (heart toggles without a page reload; cart with quantity update, stock checks, free delivery over ₹999) |
| Checkout and orders | Cash on delivery for now, stock reduced atomically, order history page |
| AI-assisted workout recommendations | `workouts/recommender.py` |
| Dashboard, history, progress | `/workouts/dashboard/`, `/workouts/history/` (weekly stats, streak, 7-day bars, weight trend chart) |
| Admin panel | Products (inline price, stock, active, featured), categories, orders (status actions, cancel and restock), exercises, plans, logs |

## Project layout

```
fitforge/    settings, root urls, wsgi/asgi
accounts/    Profile model, register/login/logout, welcome email, email-or-username backend
shop/        Category, Product, Favourite, Cart, Order models; shop views; seed_demo command
workouts/    Exercise, WorkoutPlan, PlanDay, WorkoutLog, BodyMetric; recommender; dashboard
templates/   base layout, partials, page templates, email templates
static/      css/style.css, js/main.js
```

## About the "AI" recommender

The engine is rule-based today: it reads goal, experience, equipment and days per week, chooses a training split
(full body, upper/lower, push/pull/legs), picks matching exercises from the library and sets sets/reps/rest per goal.
It also suggests shop products for the goal. `generate_plan()` is the single entry point, so an LLM-backed
generator can replace or refine it later without changing views or templates. Plans are general guidance, not medical advice.

## Real email (Gmail example)

Set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`,
`EMAIL_USE_TLS=1`, `EMAIL_USE_SSL=0`, and `EMAIL_HOST_USER` to your Gmail address. Email connections time out
after 10 seconds by default (`EMAIL_TIMEOUT`). Create a Google App Password
(requires 2-Step Verification) and set it as `EMAIL_HOST_PASSWORD`; do not use your regular Gmail password.
Set `DEFAULT_FROM_EMAIL` to the same Gmail address. Locally, put these settings in `.env`; on a host, configure
them as environment variables. Restart the app after changing settings.

## PostgreSQL

`pip install psycopg2-binary`, then set `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`.

## Aiven MySQL on Render

The app can use Aiven MySQL when `MYSQL_HOST` is set. Create a MySQL service and database in Aiven, then add these
environment variables to the Render web service:

| Variable | Value |
|---|---|
| `MYSQL_HOST` | Aiven service hostname |
| `MYSQL_PORT` | Port shown in Aiven's service details |
| `MYSQL_DATABASE` | Aiven database name |
| `MYSQL_USER` | Aiven database username |
| `MYSQL_PASSWORD` | Aiven database password |
| `MYSQL_SSL_CA` | Absolute path to the Aiven CA certificate |

Download the CA certificate from Aiven and upload it in Render under **Secret Files**; set `MYSQL_SSL_CA` to its
mounted path (for example, `/etc/secrets/ca.pem`). Keep the password and certificate private. `MYSQL_HOST` takes
precedence over `DATABASE_URL`, so remove the old PostgreSQL variable only after confirming the Aiven connection.
The deployment build runs migrations automatically. Back up or export existing data before switching databases;
data is not copied automatically. Product images are files, not database records, and need separate persistent or
cloud storage.

## Deploying

Set `DJANGO_DEBUG=0`, a long random `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and `SITE_URL`;
run `python manage.py collectstatic`; serve with `gunicorn fitforge.wsgi`. WhiteNoise serves static files. Uploaded
product images and profile photos are stored in the configured Django database, so they persist across web-service
redeploys. This increases database storage and backup usage. Existing images still present on the server are imported
to the database the first time they are requested; images already lost from temporary storage must be uploaded again.

## Git and GitHub

```bash
git init && git add . && git commit -m "Initial FITNESS ZONE platform"
git branch -M main
git remote add origin https://github.com/<you>/fitness-zone.git
git push -u origin main
```

## Roadmap (from the business plan)

Online payments (Razorpay/UPI), order tracking, product reviews, premium subscriptions (`Profile.is_premium` is
already in place), advanced AI coaching, trainer booking and gym partnerships.

## Changing the website name

Edit `SITE_NAME` in `fitforge/settings.py` (or set the `SITE_NAME` environment variable). It updates the logo, titles, footer, emails and admin panel.

## Frontend upgrade

Premium dark redesign with an opening animation, workout library, AI Coach (rule-based, labelled as such), dashboard,
Mindset & Momentum articles and password reset. Models are unchanged. Details: BANGLA_GUIDE.md section 16.
