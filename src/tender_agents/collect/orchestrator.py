import asyncio
import logging
from typing import Optional

from tender_agents.browser.session import HumanSession
from tender_agents.models import CollectPlan, CollectResult, TenderRecord
from tender_agents.platforms.registry import get_adapter

logger = logging.getLogger(__name__)

async def run_collect(
    plan: CollectPlan,
    headed: bool = False,
    result: Optional[CollectResult] = None
) -> CollectResult:
    """
    Оркестратор сбора тендеров: один браузер на все ключевые слова.
    """
    if result is None:
        result = CollectResult()
    adapter = get_adapter(str(plan.platform_url))

    if not adapter:
        logger.error(f"Адаптер для {plan.platform_url} не найден.")
        result.errors_count += 1
        return result

    try:
        async with HumanSession(headed=headed) as session:
            logger.info(f"Начинаю сбор на {plan.platform_url.host}")
            await adapter.open_home(session)

            for keyword in plan.keywords:
                logger.info(f"Ищу: {keyword}")
                result.totals_per_keyword[keyword] = 0

                try:
                    ctx = await adapter.search(session, keyword, plan.filters)

                    count = 0
                    async for item in adapter.iter_listing_pages(session, ctx, max_pages=plan.max_pages):
                        if count >= plan.max_per_keyword:
                            break

                        try:
                            record = await adapter.open_detail(session, item, keyword, plan.filters)
                            if record:
                                result.records.append(record)
                                count += 1
                                result.totals_per_keyword[keyword] = count
                                logger.info(f"Сохранено лотов: {count}")

                            if count >= plan.max_per_keyword:
                                break
                        except Exception as e:
                            logger.error(f"Ошибка при обработке лота {item.url}: {e}")
                            result.errors_count += 1

                except asyncio.CancelledError:
                    logger.warning(f"Сбор прерван пользователем на ключе '{keyword}'")
                    raise
                except Exception as e:
                    logger.error(f"Ошибка при поиске по ключу '{keyword}': {e}")
                    result.errors_count += 1

    except asyncio.CancelledError:
        logger.info("Завершаю работу (прервано)")
    except Exception as e:
        logger.error(f"Критическая ошибка оркестратора: {e}")
        result.errors_count += 1

    return result
