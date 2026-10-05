from src.rag.pdf_documents import list_knowledge_papers
from src.rag.retriever import KnowledgeRetriever, load_knowledge_documents


def main() -> None:
    for paper in list_knowledge_papers():
        print(f"{paper['paper_id']}: {paper['title']} | 本地可用={paper['local_available']}")
    retriever = KnowledgeRetriever(load_knowledge_documents("papers"))
    print("仅做 PDF 检索，不调用 DeepSeek；输入 exit 退出。英文论文建议英文关键词。")
    while True:
        query = input("请输入论文检索问题：").strip()
        if query.lower() in ("exit", "quit"):
            break
        if not query:
            continue
        result = retriever.search(query)
        print(f"coverage={result['query_coverage']:.3f} | {result['message']}")
        for rank, item in enumerate(result["results"], 1):
            print(f"Rank {rank} | paper={item['paper_id']} | page={item['page_number']} | score={item['score']:.4f}")
            print(item["citation"], item["heading"])
            print(item["text"][:400])


if __name__ == "__main__":
    main()
