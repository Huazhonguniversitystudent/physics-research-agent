import json
import re
from pathlib import Path, PureWindowsPath

import pymupdf

from src.rag.documents import PROJECT_ROOT


PDF_ROOTS = ("knowledge/public/papers", "knowledge/local/papers")


def _safe_path(path: str, project_root: Path) -> Path:
    relative = Path(path)
    if relative.is_absolute() or PureWindowsPath(path).is_absolute() or ".." in relative.parts or ".." in PureWindowsPath(path).parts:
        raise ValueError("PDF 只接受允许目录内的相对路径，禁止绝对路径和路径穿越。")
    root = project_root.resolve()
    target = root / relative
    if target.suffix.lower() != ".pdf":
        raise ValueError("只能读取 PDF 文件。")
    for directory in PDF_ROOTS:
        allowed = root / directory
        if allowed.resolve() == allowed and target.parent == allowed and target.resolve() == target:
            return target
    raise ValueError("PDF 最终路径必须位于允许的论文目录，禁止符号链接偏移。")


def list_knowledge_papers(project_root: Path = PROJECT_ROOT, include_local: bool = True) -> list[dict]:
    root = project_root.resolve()
    papers = []
    for directory in PDF_ROOTS:
        if directory == "knowledge/local/papers" and not include_local:
            continue
        allowed = root / directory
        if not allowed.is_dir() or allowed.resolve() != allowed:
            continue
        metadata_path = allowed / "sources.json"
        entries = []
        if metadata_path.is_file() and metadata_path.resolve() == metadata_path:
            entries = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
            if not isinstance(entries, list):
                raise ValueError("sources.json 必须是论文信息数组。")
        known = set()
        for entry in entries:
            filename = entry["local_filename"]
            if Path(filename).name != filename or PureWindowsPath(filename).name != filename:
                raise ValueError("论文 local_filename 只能是文件名。")
            path = _safe_path(f"{directory}/{filename}", root)
            known.add(filename)
            papers.append({"paper_id": entry["paper_id"], "title": entry.get("title", entry["paper_id"]),
                           "authors": entry.get("authors", []), "year": entry.get("year"),
                           "source_url": entry.get("source_url", ""), "license_or_access_note": entry.get("license_or_access_note", "license not verified"),
                           "source": path.relative_to(root).as_posix(), "source_type": "pdf", "local_available": path.is_file()})
        for path in sorted(allowed.iterdir()):
            if path.suffix.lower() != ".pdf" or path.name in known or not path.is_file():
                continue
            try:
                _safe_path(path.relative_to(root).as_posix(), root)
            except ValueError:
                continue
            papers.append({"paper_id": path.stem, "title": path.stem, "authors": [], "year": None,
                           "source_url": "", "license_or_access_note": "user-provided; access authorization required",
                           "source": path.relative_to(root).as_posix(), "source_type": "pdf", "local_available": True})
    ids = [paper["paper_id"] for paper in papers]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[A-Za-z0-9_-]+", identity) for identity in ids):
        raise ValueError("paper_id 必须唯一且仅包含字母、数字、下划线、连字符；可在 sources.json 显式登记。")
    return papers


def load_pdf_document(path: str, *, project_root: Path = PROJECT_ROOT, metadata: dict | None = None) -> list[dict]:
    target = _safe_path(path, project_root)
    info = metadata or {"paper_id": target.stem, "title": target.stem}
    if not re.fullmatch(r"[A-Za-z0-9_-]+", info["paper_id"]):
        raise ValueError("paper_id 格式不合法。")
    pages = []
    try:
        with pymupdf.open(target) as document:
            if document.needs_pass:
                raise ValueError("当前不支持加密 PDF。")
            if not len(document):
                raise ValueError("PDF 没有可读取的页面，请检查下载是否完整。")
            for index, page in enumerate(document):
                # Only trim redundant whitespace. Do not rewrite formulas or numeric text.
                text = "\n".join(re.sub(r"[ \t]+", " ", line).rstrip() for line in page.get_text("text").splitlines()).strip()
                text = re.sub(r"\n{3,}", "\n\n", text)
                pages.append({"source": target.relative_to(project_root.resolve()).as_posix(),
                              "paper_id": info["paper_id"], "title": info["title"], "page_number": index + 1,
                              "text": text, "source_type": "pdf",
                              "text_extraction_status": "extracted" if len(text.strip()) >= 20 else "empty_or_scanned"})
    except (RuntimeError, OSError) as exc:
        raise ValueError("PDF 打开或解析失败，请检查文件是否存在、损坏或加密。") from exc
    return pages


def load_pdf_documents(project_root: Path = PROJECT_ROOT, paper_id: str | None = None, include_local: bool = True) -> list[dict]:
    papers = list_knowledge_papers(project_root, include_local)
    if paper_id is not None:
        papers = [paper for paper in papers if paper["paper_id"] == paper_id]
        if not papers:
            raise ValueError("未找到该 paper_id，请先列出论文。")
    return [page for paper in papers if paper["local_available"]
            for page in load_pdf_document(paper["source"], project_root=project_root, metadata=paper)]


def inspect_paper(paper_id: str, project_root: Path = PROJECT_ROOT, include_local: bool = True) -> dict:
    papers = [paper for paper in list_knowledge_papers(project_root, include_local) if paper["paper_id"] == paper_id]
    if not papers or not papers[0]["local_available"]:
        raise ValueError("未找到可读取的论文，请先列出论文并确认本地文件存在。")
    paper = papers[0]
    pages = load_pdf_document(paper["source"], project_root=project_root, metadata=paper)
    extractable = sum(page["text_extraction_status"] == "extracted" for page in pages)
    return {**paper, "page_count": len(pages), "extractable_pages": extractable,
            "empty_pages": len(pages) - extractable, "total_characters": sum(len(page["text"]) for page in pages),
            "characters_per_page": [len(page["text"]) for page in pages],
            "text_extractable": bool(extractable), "first_excerpt": pages[0]["text"][:250] if pages else "",
            "extraction_note": "v1 只提取文本型 PDF，不做 OCR；empty_or_scanned 也可能是空白页或少量文字页。"}
