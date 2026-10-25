
from app.contracts import (
    ClientProfile,
    Insight,
    MatchedFeature,
    NewsItem,
    RankedNewsItem,
    SourceRef,
)
from app.llm.gateway import LLMGateway, GatewayError


class InsightInterpreter:
    """Формирует структурированный Insight для конкретного клиента."""

    def __init__(self, gateway: LLMGateway | None = None) -> None:
        self.gateway = gateway or LLMGateway()

    async def interpret(
        self,
        ranked_news: RankedNewsItem,
        profile: ClientProfile,
        bank_view: str | None = None,
        bank_sources: list[SourceRef] | None = None,
    ) -> Insight:
        news = ranked_news.news
        relevance = ranked_news.relevance

        if news.news_id != relevance.news_id:
            raise ValueError("ID новости не совпадает с результатом ранжирования.")

        if profile.client_id != relevance.client_id:
            raise ValueError("ID клиента не совпадает с профилем.")

        limitations: list[str] = []
        source_refs = list(relevance.source_refs)

        if not source_refs:
            source_refs.append(
                SourceRef(
                    source_id=f"news:{news.news_id}",
                    source_type="news",
                    title=news.title,
                    url=news.source_url,
                )
            )

        if bank_sources:
            source_refs.extend(bank_sources)

        if not bank_view:
            limitations.append(
                "Аналитика банка по этой новости не предоставлена."
            )

        facts = [
            fact.text
            for fact in news.facts
            if fact.text.strip() and fact.confidence is not None
            and fact.confidence >= 0.8
        ]

        if not facts:
            facts = [news.title]
            limitations.append(
                "Нет фактов с достаточной оценкой уверенности; "
                "заголовок приведён как описание новости, а не как "
                "независимо подтверждённый факт."
            )

        matched_features = [
            {
                "feature": feature.feature,
                "profile_field": feature.profile_field,
                "matched": feature.matched,
                "reason": feature.reason,
            }
            for feature in relevance.matched_features
        ]

        system_prompt = (
            "Ты аналитический помощник банка для бизнеса. "
            "Верни только JSON-объект с полями: "
            "what_happened (string), facts (array of strings), "
            "why_it_matters (string), potential_consequences "
            "(array of strings), suggested_actions (array of strings), "
            "ai_inference (string), reasoning_basis (array of strings), "
            "limitations (array of strings). "
            "Используй только предоставленные сведения. "
            "Не придумывай факты, цифры, источники и позицию банка. "
            "Отделяй факты от предположений и рекомендаций. "
            "Если информации недостаточно, прямо укажи это."
        )

        user_payload = {
            "news": {
                "news_id": news.news_id,
                "title": news.title,
                "text": news.text,
                "publisher": news.publisher,
                "published_at": (
                    news.published_at.isoformat()
                    if news.published_at
                    else None
                ),
                "facts": [
                    {
                        "text": fact.text,
                        "confidence": fact.confidence,
                        "source_id": fact.source_id,
                    }
                    for fact in news.facts
                ],
            },
            "client_profile": {
                "industry_code": profile.industry_code,
                "industry_name": profile.industry_name,
                "region": profile.region,
                "city": profile.city,
                "products": profile.products,
            },
            "relevance": {
                "score": relevance.score,
                "rationale": relevance.rationale,
                "matched_features": matched_features,
            },
            "bank_view": bank_view,
        }

        try:
            result = await self.gateway.generate_json(
                system_prompt=system_prompt,
                user_prompt=__import__("json").dumps(
                    user_payload,
                    ensure_ascii=False,
                    default=str,
                ),
            )

            required_strings = ("what_happened", "why_it_matters")
            for field in required_strings:
                if not isinstance(result.get(field), str) or not result[field].strip():
                    raise ValueError(f"Некорректное поле ответа: {field}")

            required_lists = (
                "facts",
                "potential_consequences",
                "suggested_actions",
                "reasoning_basis",
                "limitations",
            )
            for field in required_lists:
                if not isinstance(result.get(field), list) or not all(
                    isinstance(item, str) for item in result[field]
                ):
                    raise ValueError(f"Некорректное поле ответа: {field}")

            ai_inference = result.get("ai_inference")
            if ai_inference is not None and not isinstance(ai_inference, str):
                raise ValueError("Некорректное поле ответа: ai_inference")

            # Факты в Insight берём из источника, а не из генерации AI.
            insight_facts = facts

            return Insight(
                news_id=news.news_id,
                client_id=profile.client_id,
                what_happened=result["what_happened"],
                facts=insight_facts,
                why_it_matters=result["why_it_matters"],
                potential_consequences=result["potential_consequences"],
                suggested_actions=result["suggested_actions"],
                bank_view=bank_view,
                bank_view_available=bool(bank_view),
                ai_inference=ai_inference,
                reasoning_basis=result["reasoning_basis"],
                limitations=limitations + result["limitations"],
                source_refs=source_refs,
            )

        except GatewayError:
            raise
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "Не удалось сформировать корректный Insight."
            ) from exc
