from src.rag.documents import load_documents
from src.rag.retriever import KnowledgeRetriever


def main() -> None:
    retriever = KnowledgeRetriever(load_documents())
    print(f"RAG v1：{retriever.document_count} documents / {len(retriever.chunks)} chunks；字符级 TF-IDF")
    while True:
        try:
            query = input("请输入检索问题（exit 退出）：").strip()
        except EOFError:
            break
        if query.lower() == "exit":
            break
        if not query:
            continue
        result = retriever.search(query)
        if not result["found"]:
            print(f"{result['message']} top_score={result['top_score']:.4f}")
        for rank, item in enumerate(result["results"], 1):
            print(f"\nRank {rank} score={item['score']:.4f}\n{item['citation']}\nheading={item['heading']}\n{item['text']}\n")


if __name__ == "__main__":
    main()
