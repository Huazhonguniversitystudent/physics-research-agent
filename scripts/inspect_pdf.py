import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.pdf_documents import inspect_paper


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("用法：python scripts/inspect_pdf.py <paper_id>")
    print(json.dumps(inspect_paper(sys.argv[1]), ensure_ascii=False, indent=2))
