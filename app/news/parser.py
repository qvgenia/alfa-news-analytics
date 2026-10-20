"""Тестовые новости для разработки и проверки ранжирования."""

from app.contracts import NewsItem


def load_sample_news() -> list[NewsItem]:
    """Возвращает тестовый набор новостей без сетевых запросов."""
    return [
        NewsItem(
            news_id="demo-001",
            title="ЦБ сохранил ключевую ставку",
            text=(
                "Банк России сохранил ключевую ставку. "
                "Высокая стоимость заёмного финансирования "
                "может влиять на инвестиционные планы компаний."
            ),
            publisher="Тестовый источник",
            source_url="https://example.com/news/interest-rate",
            topic="финансы",
        ),
        NewsItem(
            news_id="demo-002",
            title="Изменения в логистике и грузоперевозках",
            text=(
                "Компании транспортной отрасли оценивают "
                "изменения стоимости перевозок и цепочек поставок."
            ),
            publisher="Тестовый источник",
            source_url="https://example.com/news/logistics",
            topic="логистика",
        ),
        NewsItem(
            news_id="demo-003",
            title="Новые требования к отчётности компаний",
            text=(
                "Обсуждаются изменения требований к отчётности "
                "и соблюдению нормативных правил для бизнеса."
            ),
            publisher="Тестовый источник",
            source_url="https://example.com/news/reporting",
            topic="регулирование",
        ),
    ]
