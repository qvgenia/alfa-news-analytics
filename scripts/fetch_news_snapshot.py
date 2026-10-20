
"""Проверка RSS и сохранение локального снапшота новостей."""

import json
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import certifi


FEEDS = {
    "Банк России — новости": "https://www.cbr.ru/rss/RssNews",
    "Банк России — пресс-релизы": "https://www.cbr.ru/rss/RssPress",
}

OUTPUT = Path("data/news_snapshot.json")
TARGET_COUNT = 40


def tag_name(tag: str) -> str:
    """Возвращает имя XML-тега без пространства имён."""
    return tag.rsplit("}", 1)[-1].lower()


def get_text(element: ET.Element, names: set[str]) -> str:
    """Извлекает текст первого дочернего элемента с подходящим тегом."""
    for child in element:
        if tag_name(child.tag) in names:
            return "".join(child.itertext()).strip()
    return ""


def fetch_feed(name: str, url: str) -> list[dict]:
    """Загружает RSS-ленту и извлекает метаданные новостей."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AlfaNewsAnalytics/0.1"},
    )

    context = ssl.create_default_context(cafile=certifi.where())

    with urllib.request.urlopen(
        request,
        context=context,
        timeout=45,
    ) as response:
        print(f"HTTP {response.status}: {url}")
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    records = []

    for item in root.iter():
        if tag_name(item.tag) not in {"item", "entry"}:
            continue

        title = get_text(item, {"title"})
        link = get_text(item, {"link"})

        # В Atom ссылка может храниться в атрибуте href.
        if not link:
            for child in item:
                if tag_name(child.tag) == "link":
                    rel = child.attrib.get("rel", "alternate")
                    if rel == "alternate":
                        link = child.attrib.get("href", "")
                        if link:
                            break

        description = get_text(
            item,
            {"description", "summary", "content", "encoded"},
        )

        published = get_text(
            item,
            {"pubdate", "published", "updated", "date"},
        )

        if title and link:
            records.append(
                {
                    "title": title,
                    "published_at": published or None,
                    "url": link,
                    "description": description[:500],
                    "publisher": name,
                    "source_feed": url,
                }
            )

    dated = sum(bool(record["published_at"]) for record in records)
    annotated = sum(bool(record["description"]) for record in records)

    print(
        f"{name}: записей={len(records)}, "
        f"с датой={dated}, с аннотацией={annotated}"
    )

    return records


def main() -> None:
    """Загружает обе ленты и сохраняет локальный снапшот."""
    news_by_source = {}

    # Загружаем каждую ленту независимо:
    # сбой одной не помешает попробовать загрузить другую.
    for name, url in FEEDS.items():
        try:
            news_by_source[name] = fetch_feed(name, url)
        except Exception as exc:
            print(f"ОШИБКА: {name}: {type(exc).__name__}: {exc}")
            news_by_source[name] = []

    news_name = "Банк России — новости"
    press_name = "Банк России — пресс-релизы"

    # Сначала стараемся включить записи из обеих лент.
    selected = (
        news_by_source.get(news_name, [])[:28]
        + news_by_source.get(press_name, [])[:12]
    )

    # Удаляем дубликаты по URL, сохраняя порядок.
    unique_records = {}

    for record in selected:
        unique_records.setdefault(record["url"], record)

    # Если после удаления дубликатов записей меньше 40,
    # дополняем снапшот остальными доступными записями.
    for source_records in news_by_source.values():
        for record in source_records:
            unique_records.setdefault(record["url"], record)

    records = list(unique_records.values())[:TARGET_COUNT]

    if len(records) < 30:
        print(
            f"\nПолучено {len(records)} уникальных записей. "
            "Снапшот не сохранён: требуется минимум 30."
        )
        raise SystemExit(1)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "sources": list(FEEDS.values()),
        "items": records,
    }

    OUTPUT.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nСнапшот сохранён локально: {OUTPUT}")
    print(f"Всего уникальных записей: {len(records)}")

    # Показываем распределение по источникам и число аннотаций.
    for name in FEEDS:
        source_records = [
            record
            for record in records
            if record["publisher"] == name
        ]

        annotated = sum(
            bool(record["description"])
            for record in source_records
        )

        print(
            f"{name}: в снапшоте {len(source_records)}, "
            f"с аннотацией {annotated}"
        )


if __name__ == "__main__":
    main()
