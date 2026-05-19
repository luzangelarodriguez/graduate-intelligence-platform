from pathlib import Path
import runpy
import sys

script = Path(__file__).resolve().parent / "scrapers" / "scraper.py"
sys.path.insert(0, str(script.parent))
runpy.run_path(str(script), run_name="__main__")
