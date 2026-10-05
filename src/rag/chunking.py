import re

from src.rag.citations import make_citation


def chunk_document(document: dict, max_chars: int = 900, overlap_chars: int = 150) -> list[dict]:
    if max_chars <= 0 or not 0 <= overlap_chars < max_chars:
        raise ValueError("chunk 大小必须为正，overlap 必须小于 chunk 大小。")
    if document["source_type"] == "pdf":
        if document.get("text_extraction_status") == "empty_or_scanned":
            return []
        # Reuse line aggregation within ONE page; never manufacture stable PDF line citations.
        chunks = chunk_document({**document, "source_type": "public"}, max_chars, overlap_chars)
        for chunk in chunks:
            chunk["chunk_id"] = f"paper:{document['paper_id']}:p{document['page_number']}:{chunk['start_line']}-{chunk['end_line']}"
            chunk.pop("start_line")
            chunk.pop("end_line")
            chunk.update({key: document[key] for key in ("source_type", "paper_id", "title", "page_number")})
            chunk["heading"] = document["title"]
            chunk["citation"] = f"[paper:{document['paper_id']}:p{document['page_number']}]"
        return chunks
    lines = document["text"].splitlines()
    if not lines or not document["text"].strip():
        return []
    sections = []
    start, heading = 0, ""
    headings = []
    in_code = False
    for index, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code = not in_code
        match = re.match(r"^(#{1,6})\s+(.+)", line) if not in_code else None
        if match:
            if index > start:
                sections.append((start, index, heading))
            level = len(match.group(1))
            headings = [(depth, title) for depth, title in headings if depth < level]
            headings.append((level, match.group(2)))
            start, heading = index, " / ".join(title for _, title in headings)
    sections.append((start, len(lines), heading))
    chunks = []
    for section_start, section_end, heading in sections:
        start = section_start
        while start < section_end:
            end, size = start, 0
            while end < section_end:
                width = len(lines[end]) + 1
                if end > start and size + width > max_chars:
                    break
                size += width
                end += 1
            text = "\n".join(lines[start:end])
            if text.strip():
                chunks.append({
                    "chunk_id": f"{document['source']}:L{start + 1}-L{end}",
                    "source": document["source"], "source_type": document["source_type"],
                    "heading": heading, "text": text,
                    "start_line": start + 1, "end_line": end,
                    "citation": make_citation(document["source"], start + 1, end),
                })
            if end == section_end:
                break
            next_start, overlap = end, 0
            while next_start > start + 1 and overlap < overlap_chars:
                next_start -= 1
                overlap += len(lines[next_start]) + 1
            start = next_start
    return chunks
