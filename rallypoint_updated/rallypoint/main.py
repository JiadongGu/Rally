"""
Entry point for the Rallypoint FastAPI application.

This module defines the routes and integrates with the database layer to
handle project submissions, admin management, and public job postings. It
uses FastAPI's templating support via Jinja2 to render HTML pages.

Routes:

* ``GET /`` – Render the client submission form.
* ``POST /`` – Accept submission form data, persist to the database
  and redirect to a success page.
* ``GET /success`` – Display a thank‑you page after a successful
  submission.
* ``GET /admin`` – Show all client projects and provide a form for
  admins to create new freelance job postings.
* ``POST /admin`` – Accept job posting data from the admin form and
  persist it, then reload the admin dashboard.
* ``GET /postings`` – Render a public list of active freelance
  opportunities.

There is deliberately no authentication layer in this MVP. In a
production environment, administrative routes would require
authentication and authorization. Timestamps use the server's local
time via ``datetime.now()``.
"""

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from . import database


app = FastAPI(title="Rallypoint")

# Initialize Jinja2 templates pointing at the templates directory.
templates = Jinja2Templates(directory=str((__file__).rsplit("/", 1)[0] + "/templates"))

# Mount a static directory for CSS or future assets if needed. For now
# it's empty but will keep the structure flexible. Files placed in
# rallypoint/static will be served under /static.
app.mount("/static", StaticFiles(directory=str((__file__).rsplit("/", 1)[0] + "/static")), name="static")


@app.on_event("startup")
def on_startup() -> None:
    """Ensure the SQLite tables exist before handling requests."""
    database.init_db()


@app.get("/")
def read_root(request: Request):
    """Display the client submission form."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/")
async def submit_project(request: Request):
    """Handle submission of a new project from the client form.

    The HTML form posts data as ``application/x-www-form-urlencoded``. To
    avoid requiring the ``python-multipart`` package, the request body is
    decoded and parsed manually using the ``urllib.parse`` module. Only
    standard form fields are accepted.
    """
    from urllib.parse import parse_qs
    body = await request.body()
    # Parse URL‑encoded data
    data = parse_qs(body.decode())
    name = data.get("name", [""])[0]
    email = data.get("email", [""])[0]
    title = data.get("title", [""])[0]
    description = data.get("description", [""])[0]
    if name and email and title and description:
        database.add_project(name=name, email=email, title=title, description=description)
    return RedirectResponse(url="/success", status_code=303)


@app.get("/success")
def submission_success(request: Request):
    """Render a thank‑you page after successful submission."""
    return templates.TemplateResponse("success.html", {"request": request})


@app.get("/admin")
def admin_dashboard(request: Request):
    """Render the admin dashboard with all projects and a posting form."""
    projects = database.get_all_projects()
    return templates.TemplateResponse("admin.html", {"request": request, "projects": projects})


@app.post("/admin")
async def create_posting(request: Request):
    """Handle creation of a new freelance job posting by the admin.

    Data is parsed manually to avoid the ``python-multipart`` dependency.
    """
    from urllib.parse import parse_qs
    body = await request.body()
    data = parse_qs(body.decode())
    title = data.get("title", [""])[0]
    description = data.get("description", [""])[0]
    if title and description:
        database.add_posting(title=title, description=description)
    return RedirectResponse(url="/admin", status_code=303)


@app.get("/postings")
def list_postings(request: Request):
    """Display all active job postings to freelancers."""
    postings = database.get_all_postings()
    return templates.TemplateResponse("postings.html", {"request": request, "postings": postings})