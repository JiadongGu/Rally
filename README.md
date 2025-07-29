cd path/to/extracted/project
python3 -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
pip install -r rallypoint/requirements.txt
uvicorn rallypoint.main:app --reload

