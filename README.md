cd path/to/extracted/project
python3 -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
pip install -r rallypoint/requirements.txt
export OPENAI_API_KEY=         # Unix/Linux/macOS
# or, on Windows Command Prompt:
set OPENAI_API_KEY=
uvicorn rallypoint.main:app --reload

