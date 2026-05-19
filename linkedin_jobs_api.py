from pathlib import Path
import runpy
import sys

script = Path(__file__).resolve().parent / "scrapers" / "linkedin_jobs_api.py"
sys.path.insert(0, str(script.parent))
runpy.run_path(str(script), run_name="__main__")
