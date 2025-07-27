cd path/to/extracted/project
python3 -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
pip install -r rallypoint/requirements.txt
export OPENAI_API_KEY=sk-your-key-here           # Unix/Linux/macOS
# or, on Windows Command Prompt:
set OPENAI_API_KEY=sk-your-key-here
uvicorn rallypoint.main:app --reload

KEY: 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