"""
Main entry point for the Rallypoint FastAPI application.

This module sets up the FastAPI app, mounts the static file directory, configures
Jinja2 templating, defines the database models and CRUD operations, and
implements the HTTP endpoints required for the MVP. It also exposes a simple
``generate_recommendations`` function that returns staffing suggestions for
job postings based on their description.

The app includes the following routes:

* ``GET /``: Display the service request submission form.
* ``POST /submit_request``: Handle service request submissions.
* ``GET /success``: Show a thank-you page after submission.
* ``GET /admin``: Admin dashboard listing service requests and job postings, with a form to create new postings.
* ``POST /admin/post_job``: Handle creation of new job postings.
* ``GET /postings``: Public job board displaying all current postings along with AI-generated recommendations.

To run the application locally use:

    uvicorn rallypoint.main:app --reload

"""

from datetime import datetime
from typing import Dict, List, Any
import os
import json

# Attempt to import the optional OpenAI client. If unavailable the application
# will fall back to a simple heuristic for generating recommendations.
try:
    from openai import OpenAI
    
    client = OpenAI(api_key=api_key)  # type: ignore
except ImportError:
    openai = None  # type: ignore

# Determine whether the OpenAI API is both configured and reachable. We do a
# small connectivity test on module import: if the `OPENAI_API_KEY` is set and
# the `openai` library is available, attempt a trivial call to the Chat
# Completions API. A global flag is set to indicate availability. This avoids
# silently falling back to heuristics when the API is unreachable but a key
# is present, and provides informative logging in the server console.
OPENAI_AVAILABLE = False
if openai and os.getenv("OPENAI_API_KEY"):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        # Decide which API to use based on the version installed. In OpenAI
        # Python client >=1.0.0 the ChatCompletion API has moved to
        # client.chat.completions.create; earlier versions expose ChatCompletion
        # directly. We attempt to detect the attribute to select the correct
        # invocation. This test call uses minimal tokens to validate both the
        # API key and network connectivity.
        if hasattr(openai, "ChatCompletion"):
              # old-style configuration
            _ = client.chat.completions.create(model="gpt-4-turbo",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            temperature=0.0)
        else:
            # Newer SDK: instantiate a client and call the chat API.
            client = openai.OpenAI(api_key=api_key)
            _ = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                temperature=0.0,
            )
        OPENAI_AVAILABLE = True
        print("[AI] OpenAI connectivity test succeeded.")
    except Exception as e:
        OPENAI_AVAILABLE = False
        print("[AI] OpenAI connectivity test failed:", e)

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .database import init_db, reset_data, get_db


# Initialize the database once on application startup.
init_db()
# Clear all existing data on each server start. This ensures the service
# requests and job postings tables begin empty every time the application
# process is started. Remove this call to persist data between runs.
reset_data()

app = FastAPI(title="Rallypoint", description="Service request and job posting platform", version="0.1.0")

# Configure Jinja2 templates directory. The directory is relative to this file.
templates = Jinja2Templates(directory="rallypoint/templates")

# Mount the ``static`` directory for serving CSS/JS assets (currently empty but ready for future use).
app.mount("/static", StaticFiles(directory="rallypoint/static"), name="static")


def generate_recommendations(description: str) -> Dict[str, object]:
    """Generate a naive staffing recommendation for a job description.

    Given a textual description of work to be performed, this function heuristically
    infers which specialties may be required, how many people should be allocated,
    and an estimated hourly rate for the project. It is deliberately simple and
    intended as a placeholder until a more sophisticated AI model can be
    integrated (e.g. via an external LLM service).

    Parameters
    ----------
    description: str
        Free-text description of the work to be performed.

    Returns
    -------
    Dict[str, object]
        A dictionary with the following keys:

        * ``specialties`` (List[str]): list of specialties inferred from the description.
        * ``num_people`` (int): recommended number of workers.
        * ``estimated_rate`` (float): suggested hourly rate per worker in GBP.
    """
    # Normalise the description for keyword matching.
    desc = description.lower()

    # Guard against harmful or prohibited tasks. If the description contains
    # keywords associated with weapons or other illegal activities, we return a
    # sentinel value indicating that no recommendations will be provided.
    prohibited_keywords = [
        "bomb",
        "weapon",
        "nuclear",
        "gun",
        "firearm",
        "explosive",
        "drugs",
    ]
    if any(word in desc for word in prohibited_keywords):
        return {
            "prohibited": True,
            "message": "Content violates our guidelines and cannot be fulfilled.",
        }

    # If the OpenAI API passed our connectivity test, delegate recommendation
    # generation to the external model. This covers arbitrary tasks beyond the
    # simple keyword heuristics below.
    if OPENAI_AVAILABLE:
        try:
            # Debug log to indicate that the OpenAI integration is being used
            print("[AI] Calling OpenAI for recommendations…")
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert project planner. Given a free‑text description of work, "
                        "infer the most appropriate and specific specialties (trades) required to complete the job. "
                        "Avoid generic labels like 'generalist contractor'—if something isn't obvious, pick the closest relevant trade based on the description. "
                        "Return a JSON object with exactly these keys: \n"
                        "- 'specialties': a list of strings naming the required specialties;\n"
                        "- 'num_people': an integer representing the total recommended team size;\n"
                        "- 'estimated_rate': a float representing the hourly rate per person in pounds;\n"
                        "- 'components': a list of high‑level components of the project;\n"
                        "- 'estimated_time': an integer representing the number of weeks it will take to hire the necessary personnel;\n"
                        "- 'tasks': a list of task objects. Each task object must have: 'description' (string describing the task), "
                        "'specialties' (list of strings naming the specialties for that task), 'num_people' (int number of people required for the task), "
                        "and 'estimated_time' (int weeks to hire for that task).\n"
                        "Do not include any additional keys or any explanatory text outside of the JSON."
                    ),
                },
                {"role": "user", "content": description},
            ]
            # Use the appropriate API based on the installed OpenAI SDK. In
            # openai-python >= 1.0.0 there is no ChatCompletion class; instead
            # we instantiate a client and call client.chat.completions.create.
            if hasattr(openai, "ChatCompletion"):
                response = client.chat.completions.create(model="gpt-4-turbo",
                messages=messages,
                max_tokens=200,
                temperature=0.2)
            else:
                client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=messages,
                    max_tokens=200,
                    temperature=0.2,
                )
            content = response.choices[0].message.content
            data = json.loads(content)
            # Validate the structure and provide defaults.
            return {
                "specialties": data.get("specialties", []),
                "num_people": int(data.get("num_people", 1)),
                "estimated_rate": float(data.get("estimated_rate", 50.0)),
                "components": data.get("components", []),
                "estimated_time": data.get("estimated_time", 0),
                "tasks": data.get("tasks", []),
            }
        except Exception as e:
            # If the API call fails or returns invalid data, fall back to heuristics.
            # Log the error so users can troubleshoot API issues.
            print("[AI] Error calling OpenAI:", e)
            pass
    # Mapping of specialty to associated keywords.
    specialty_keywords = {
        # Mechanical work on vehicles, bikes, machinery.
        "mechanical engineer": ["mechanical", "engine", "bike", "bicycle", "repair", "machine"],
        # Software and web projects.
        "software developer": ["app", "software", "website", "backend", "frontend", "fastapi"],
        # Visual and brand design work.
        "graphic designer": ["design", "logo", "branding", "graphic"],
        # Electrical and electronics.
        "electrical engineer": ["electrical", "circuit", "wiring", "electronics"],
        # Marketing and promotion.
        "marketing specialist": ["marketing", "advertising", "promotion", "social media"],
        # Carpentry and woodworking – removed generic "build" to avoid spurious matches.
        "carpenter": ["wood", "carpentry", "furniture", "cabinet"],
        # Aerospace and aircraft construction/maintenance.
        "aerospace engineer": ["aircraft", "plane", "airplane", "jet", "cessna", "aeronautical"],
        # Sculptors and artists for statues, sculptures, etc.
        "sculptor": ["sculpture", "statue", "sculpt", "carve", "model", "art"],
        # Logistics/transport coordination for delivery and shipping tasks.
        "logistics coordinator": ["ship", "delivery", "send", "transport", "logistics"],
        # Pool construction and installation specialists.
        "pool builder": ["swimming pool", "pool", "pool construction", "water feature", "spa"],
        # Tiling specialists for flooring and surfaces.
        "tiler": ["tile", "tiling", "ceramic", "mosaic", "grout"]
        ,# Railway and locomotive engineering.
        "railway engineer": ["train", "locomotive", "rail", "railway"]
    }
    matched_specialties: List[str] = []
    # Identify specialties by looking for keyword hits.
    for specialty, keywords in specialty_keywords.items():
        if any(keyword in desc for keyword in keywords):
            matched_specialties.append(specialty)

    # If no specialty matches, fall back to a generalist recommendation.
    if not matched_specialties:
        matched_specialties.append("generalist contractor")

    # Determine the number of people based on the number of specialties and description length.
    base_people = max(1, len(matched_specialties))
    # Longer descriptions likely require more effort.
    extra_people = len(desc.split()) // 50  # add one extra person for every 50 words
    num_people = base_people + extra_people
    # Certain complex specialties require a minimum team size. For example,
    # building or servicing an aircraft should involve a larger team.
    if "aerospace engineer" in matched_specialties:
        num_people = max(num_people, 3)

    # Estimate a rate. Each specialty has a typical base rate, otherwise use a default.
    base_rates = {
        "mechanical engineer": 60.0,
        "software developer": 70.0,
        "graphic designer": 50.0,
        "electrical engineer": 65.0,
        "marketing specialist": 55.0,
        "carpenter": 45.0,
        "aerospace engineer": 90.0,
        "sculptor": 55.0,
        "logistics coordinator": 50.0,
        "pool builder": 60.0,
        "tiler": 50.0,
        "railway engineer": 75.0,
        "generalist contractor": 40.0,
    }
    # Use the average of specialty rates as the base hourly rate.
    rates = [base_rates.get(spec, 50.0) for spec in matched_specialties]
    estimated_rate = sum(rates) / len(rates)

    # Determine components for each specialty. These human‑readable labels describe
    # the major workstreams that the project will require. Default to a
    # generic description if a specialty isn't listed.
    component_labels = {
        "mechanical engineer": "Mechanical engineering tasks",
        "software developer": "Software development",
        "graphic designer": "Design tasks",
        "electrical engineer": "Electrical engineering tasks",
        "marketing specialist": "Marketing and promotion",
        "carpenter": "Carpentry work",
        "aerospace engineer": "Aerospace engineering tasks",
        "sculptor": "Sculpture work",
        "logistics coordinator": "Logistics and delivery",
        "pool builder": "Pool construction",
        "tiler": "Tiling work",
        "railway engineer": "Railway engineering tasks",
        "generalist contractor": "General contracting tasks",
    }
    components = [component_labels.get(spec, f"{spec} tasks") for spec in matched_specialties]

    # Estimate the time to fill the contract in weeks. Each specialty has a base
    # time; the overall estimate is the maximum of these. These numbers are
    # heuristic and can be refined with real data.
    time_estimates = {
        "mechanical engineer": 4,
        "software developer": 3,
        "graphic designer": 2,
        "electrical engineer": 4,
        "marketing specialist": 2,
        "carpenter": 3,
        "aerospace engineer": 8,
        "sculptor": 5,
        "logistics coordinator": 1,
        "pool builder": 6,
        "tiler": 4,
        "railway engineer": 6,
        "generalist contractor": 2,
    }
    estimated_time = 0
    for spec in matched_specialties:
        estimated_time = max(estimated_time, time_estimates.get(spec, 2))

    # Build a list of tasks based on the specialties. Each task corresponds to a
    # major workstream and allocates one person. The estimated time is the
    # same per-specialty time used above. In a more sophisticated system this
    # could be derived from further analysis of the description.
    tasks: List[Dict[str, Any]] = []
    for spec in matched_specialties:
        task_desc = component_labels.get(spec, f"{spec} tasks")
        tasks.append(
            {
                "description": task_desc,
                "specialties": [spec],
                "num_people": 1,
                "estimated_time": time_estimates.get(spec, 2),
            }
        )

    return {
        "specialties": matched_specialties,
        "num_people": num_people,
        "estimated_rate": round(estimated_rate, 2),
        "components": components,
        "estimated_time": estimated_time,
        "tasks": tasks,
    }


@app.get("/")
async def index(request: Request):
    """Render the homepage with a service request form."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/submit_request")
async def submit_request(request: Request):
    """Handle submission of a service request from the homepage form.

    The form data is extracted from ``request.form()`` to avoid requiring the
    ``python-multipart`` dependency at import time. This also keeps the
    endpoint signature simple.
    """
    form = await request.form()
    name = form.get("name")
    email = form.get("email")
    description = form.get("description")
    created_at = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO service_requests (name, email, description, created_at) VALUES (?, ?, ?, ?)",
            (name, email, description, created_at),
        )
        conn.commit()
    # Redirect to a thank-you page
    return RedirectResponse(url="/success", status_code=303)


@app.get("/success")
async def success(request: Request):
    """Display a simple thank-you page after a successful submission."""
    return templates.TemplateResponse("success.html", {"request": request})


@app.get("/admin")
async def admin_dashboard(request: Request):
    """Render the admin dashboard showing all service requests and job postings."""
    # Fetch service requests and job postings from the database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, description, created_at FROM service_requests ORDER BY created_at DESC")
        requests = cursor.fetchall()
        cursor.execute("SELECT id, title, description, created_at FROM job_postings ORDER BY created_at DESC")
        postings = cursor.fetchall()
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "service_requests": requests,
            "job_postings": postings,
        },
    )


@app.post("/admin/post_job")
async def post_job(request: Request):
    """Handle creation of a new job posting from the admin dashboard.

    As with the service request endpoint, we extract form data from the request
    to avoid requiring ``python-multipart``.
    """
    form = await request.form()
    title = form.get("title")
    description = form.get("description")
    created_at = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO job_postings (title, description, created_at) VALUES (?, ?, ?)",
            (title, description, created_at),
        )
        conn.commit()
    # Redirect back to the admin dashboard
    return RedirectResponse(url="/admin", status_code=303)


@app.get("/postings")
async def postings(request: Request):
    """Render the public job board with AI recommendations for each posting."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description, created_at FROM job_postings ORDER BY created_at DESC")
        rows = cursor.fetchall()
    # Enrich each posting with AI recommendations
    enriched_postings: List[Dict[str, object]] = []
    for row in rows:
        job_id, title, description, created_at = row
        rec = generate_recommendations(description)
        enriched_postings.append(
            {
                "id": job_id,
                "title": title,
                "description": description,
                "created_at": created_at,
                "recommendations": rec,
            }
        )
    return templates.TemplateResponse(
        "postings.html",
        {
            "request": request,
            "postings": enriched_postings,
        },
    )