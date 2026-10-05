from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_ROOTS = ("docs", "knowledge/public", "knowledge/local")


def load_documents(project_root: Path = PROJECT_ROOT) -> list[dict]:
    """Read only allowed project text files; never execute document content."""
    root = project_root.resolve()
    documents = []
    for directory in ALLOWED_ROOTS:
        allowed = root / directory
        if not allowed.is_dir() or allowed.resolve() != allowed:
            continue
        for path in sorted(allowed.rglob("*")):
            if path.suffix.lower() not in (".md", ".txt") or not path.is_file():
                continue
            if any(part.startswith(".") for part in path.relative_to(allowed).parts):
                continue
            if path.resolve() != path.absolute():
                continue
            # Do not retrieve evaluation transcripts as evidence for their own tests.
            if directory == "docs" and path.name in ("Day5_Verification.md", "Day1-5_学习总结.md"):
                continue
            documents.append({
                "source": path.relative_to(root).as_posix(),
                "text": path.read_text(encoding="utf-8-sig"),
                "source_type": "local" if directory == "knowledge/local" else "public",
            })
    readme = root / "README.md"
    if readme.is_file() and readme.resolve() == readme.absolute():
        documents.append({"source": "README.md", "text": readme.read_text(encoding="utf-8-sig"), "source_type": "public"})
    return documents
