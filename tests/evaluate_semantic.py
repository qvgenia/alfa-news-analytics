import json
import time
from pathlib import Path

from app.rag.pdf_loader import load_pdf
from app.rag.chunker import chunk_pages
from app.rag.retriever import search_chunks
from app.rag.semantic_retriever import SemanticRetriever


questions = json.loads(
    Path("tests/rag_eval_questions.json").read_text(encoding="utf-8")
)

chunks = []
for pdf in sorted(Path("data/reports").glob("*.pdf")):
    chunks.extend(chunk_pages(load_pdf(pdf)))

print(f"Загружено чанков: {len(chunks)}")

# Время инициализации семантического поиска включает кодирование всех чанков.
start = time.perf_counter()
semantic = SemanticRetriever(chunks)
semantic_init_time = time.perf_counter() - start
print(f"Подготовка семантического поиска: {semantic_init_time:.2f} сек.")

metrics = {
    "TF-IDF": {"recall": [], "mrr": [], "latency": []},
    "Semantic": {"recall": [], "mrr": [], "latency": []},
}


def unique_pages(results, limit=5):
    pages = []
    seen = set()
    for result in results:
        key = (result.get("document"), result.get("page"))
        if key not in seen:
            seen.add(key)
            pages.append(key)
        if len(pages) == limit:
            break
    return pages


for item in questions:
    relevant = {
        (source["document"], source["page"])
        for source in item["relevant_sources"]
    }

    methods = {
        "TF-IDF": lambda: search_chunks(item["query"], chunks, top_k=20),
        "Semantic": lambda: semantic.search(item["query"], top_k=20),
    }

    print(f"\n{item['id']}: {item['query']}")

    for name, search in methods.items():
        start = time.perf_counter()
        results = search()
        elapsed = time.perf_counter() - start

        found = unique_pages(results)
        hits = len(set(found) & relevant)
        recall = hits / len(relevant) if relevant else 0.0
        rr = next(
            (
                1 / rank
                for rank, page in enumerate(found, start=1)
                if page in relevant
            ),
            0.0,
        )

        metrics[name]["recall"].append(recall)
        metrics[name]["mrr"].append(rr)
        metrics[name]["latency"].append(elapsed)

        print(
            f"  {name}: Recall@5={recall:.2f}, "
            f"MRR@5={rr:.2f}, latency={elapsed * 1000:.1f} ms"
        )
        for document, page in found:
            print(f"    {document}, стр. {page}")

print("\n=== СРЕДНИЕ РЕЗУЛЬТАТЫ ===")
for name, values in metrics.items():
    count = len(questions)
    print(
        f"{name}: "
        f"Recall@5={sum(values['recall']) / count:.3f}, "
        f"MRR@5={sum(values['mrr']) / count:.3f}, "
        f"среднее время запроса="
        f"{sum(values['latency']) / count * 1000:.1f} ms"
    )
print(f"Подготовка семантического поиска: {semantic_init_time:.2f} сек.")
