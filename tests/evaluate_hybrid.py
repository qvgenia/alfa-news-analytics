import json
import time
from pathlib import Path

from app.rag.pdf_loader import load_pdf
from app.rag.chunker import chunk_pages
from app.rag.retriever import search_chunks
from app.rag.semantic_retriever import SemanticRetriever
from app.rag.hybrid_retriever import HybridRetriever

questions = json.loads(
    Path("tests/rag_eval_questions.json").read_text(encoding="utf-8")
)

chunks = []
for pdf in sorted(Path("data/reports").glob("*.pdf")):
    chunks.extend(chunk_pages(load_pdf(pdf)))

print(f"Загружено чанков: {len(chunks)}")

start = time.perf_counter()
semantic = SemanticRetriever(chunks)
print(f"Подготовка семантического индекса: {time.perf_counter() - start:.2f} сек.")

hybrid = HybridRetriever(chunks, semantic_retriever=semantic)


def unique_pages(results, limit=5):
    pages = []
    seen = set()
    for result in results:
        key = (result.get("document"), result.get("page"))
        if key not in seen:
            seen.add(key)
            pages.append(key)
        if len(pages) >= limit:
            break
    return pages


methods = {
    "TF-IDF": lambda q: search_chunks(q, chunks, top_k=20),
    "Semantic": lambda q: semantic.search(q, top_k=20),
    "Hybrid": lambda q: hybrid.search(q, top_k=5),
}

metrics = {
    name: {"recall": [], "mrr": [], "latency": []}
    for name in methods
}

for item in questions:
    relevant = {
        (source["document"], source["page"])
        for source in item["relevant_sources"]
    }
    print(f"\nВопрос: {item['query']}")

    for name, search in methods.items():
        start = time.perf_counter()
        results = search(item["query"])
        elapsed = time.perf_counter() - start
        found = unique_pages(results)

        hits = len(set(found) & relevant)
        recall = hits / len(relevant) if relevant else 0.0
        rr = next(
            (1 / rank for rank, page in enumerate(found, 1) if page in relevant),
            0.0,
        )

        metrics[name]["recall"].append(recall)
        metrics[name]["mrr"].append(rr)
        metrics[name]["latency"].append(elapsed)

        print(
            f"  {name:8} Recall@5={recall:.3f} "
            f"MRR@5={rr:.3f} latency={elapsed * 1000:.1f} ms"
        )
        print("    Топ:", ", ".join(
            f"{doc} стр. {page}" for doc, page in found
        ))

print("\n=== СРЕДНИЕ МЕТРИКИ ===")
for name, values in metrics.items():
    print(
        f"{name:8} "
        f"Recall@5={sum(values['recall']) / len(values['recall']):.3f} | "
        f"MRR@5={sum(values['mrr']) / len(values['mrr']):.3f} | "
        f"latency={sum(values['latency']) / len(values['latency']) * 1000:.1f} ms"
    )
