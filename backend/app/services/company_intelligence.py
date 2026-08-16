from __future__ import annotations

import logging
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.company_intelligence.extractor import CompanyIntelligenceExtractor, CompanyWebsiteFetcher
from app.company_intelligence.summarizer import CompanyIntelligenceSummarizer
from app.core.config import get_settings
from app.models.company_intelligence import CompanyIntelligence, IntelligenceStatus
from app.repositories.company_intelligence import CompanyIntelligenceRepository
from app.schemas.company_intelligence import (
    CompanyIntelligenceListResponse,
    CompanyIntelligenceRead,
    CompanyIntelligenceRequest,
    CompanyIntelligenceResponse,
)
from app.workers.queue import enqueue_task

logger = logging.getLogger(__name__)


class CompanyIntelligenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = CompanyIntelligenceRepository(session)

    async def analyze(self, payload: CompanyIntelligenceRequest) -> CompanyIntelligenceResponse:
        if payload.run_in_background:
            settings = get_settings()
            task = await enqueue_task(
                settings.agent_worker_task_name,
                {
                    "agent_name": "company_intelligence",
                    "payload": payload.model_dump(mode="json", exclude={"run_in_background"}),
                },
            )
            return CompanyIntelligenceResponse(status="queued", task_id=task.id)

        intelligence = await self.analyze_now(payload)
        return CompanyIntelligenceResponse(
            status="completed",
            data=CompanyIntelligenceRead.model_validate(intelligence),
        )

    async def analyze_now(self, payload: CompanyIntelligenceRequest) -> CompanyIntelligence:
        url_str = str(payload.website_url)
        company_name = payload.company_name or ""

        # Step 1: Initial upsert in PENDING / RUNNING status
        record = await self.repository.upsert(
            website_url=url_str,
            company_name=company_name or url_str,
            company_id=payload.company_id,
            status=IntelligenceStatus.RUNNING,
        )

        try:
            import httpx
            from urllib.parse import urlparse
            fetcher = CompanyWebsiteFetcher()
            extractor = CompanyIntelligenceExtractor()
            summarizer = CompanyIntelligenceSummarizer()

            # Step 2: Fetch homepage
            try:
                html, headers = await fetcher.fetch_page(url_str)
            except httpx.HTTPStatusError as e:
                logger.warning(f"Failed to fetch {url_str} due to {e.response.status_code}, attempting fallback", extra={"url": url_str, "status_code": e.response.status_code})
                parsed = urlparse(url_str)
                root_url = f"{parsed.scheme}://{parsed.netloc}/"
                if url_str != root_url:
                    try:
                        html, headers = await fetcher.fetch_page(root_url)
                        logger.info(f"Fallback to root domain {root_url} succeeded", extra={"url": root_url})
                    except Exception as fallback_exc:
                        logger.error(f"Fallback to root domain {root_url} also failed: {fallback_exc}", extra={"url": root_url, "error": str(fallback_exc)})
                        raise e
                else:
                    raise e

            # Discover About / Careers subpages
            about_url, careers_url = extractor._discover_subpage_urls(
                BeautifulSoup(html, "html.parser"), url_str
            )
            about_html: str | None = None
            careers_html: str | None = None

            if about_url:
                try:
                    about_html, _ = await fetcher.fetch_page(about_url)
                except httpx.HTTPStatusError as sub_exc:
                    logger.debug("Failed to fetch discovered about page", extra={"url": about_url, "status_code": sub_exc.response.status_code})
                except Exception as sub_exc:
                    logger.debug("Failed to fetch discovered about page", extra={"url": about_url, "error": str(sub_exc)})

            if careers_url:
                try:
                    careers_html, _ = await fetcher.fetch_page(careers_url)
                except httpx.HTTPStatusError as sub_exc:
                    logger.debug("Failed to fetch discovered careers page", extra={"url": careers_url, "status_code": sub_exc.response.status_code})
                except Exception as sub_exc:
                    logger.debug("Failed to fetch discovered careers page", extra={"url": careers_url, "error": str(sub_exc)})

            # Step 3: Extract raw content
            raw_content = extractor.extract(
                html=html,
                base_url=url_str,
                headers=headers,
                about_html=about_html,
                careers_html=careers_html,
            )
            logger.info("Pages analyzed", extra={"action": "pages_analyzed", "url": url_str, "about_found": bool(about_html), "careers_found": bool(careers_html)})

            derived_company_name = company_name or raw_content.get("domain_name") or "Company"

            # Step 4: AI Summarization (with rule-based fallback)
            summary_data = await summarizer.summarize(raw_content)
            logger.info("Enrichment completed", extra={"action": "enrichment_completed", "url": url_str})

            # Step 5: Save completed analysis in DB via Repository Upsert
            completed_record = await self.repository.upsert(
                website_url=url_str,
                company_name=derived_company_name,
                company_id=payload.company_id,
                overview=summary_data.get("overview"),
                products_services=summary_data.get("products_services", []),
                tech_stack=raw_content.get("tech_stack", []),
                careers_url=raw_content.get("careers_url"),
                about_url=raw_content.get("about_url"),
                contact_info=raw_content.get("contact_info", {}),
                raw_content=raw_content,
                raw_summary=summary_data.get("summary"),
                status=IntelligenceStatus.COMPLETED,
            )
            logger.info("Persistence completed", extra={"action": "persistence_completed", "company_id": str(payload.company_id), "url": url_str})
            return completed_record

        except Exception as exc:
            logger.exception("Company intelligence analysis failed", extra={"url": url_str})
            failed_record = await self.repository.upsert(
                website_url=url_str,
                company_name=company_name or url_str,
                company_id=payload.company_id,
                status=IntelligenceStatus.FAILED,
                error=str(exc),
            )
            return failed_record

    async def get(self, intelligence_id: UUID) -> CompanyIntelligence:
        record = await self.repository.get_by_id(intelligence_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company intelligence record not found",
            )
        return record

    async def get_by_company_id(self, company_id: UUID) -> CompanyIntelligence:
        record = await self.repository.get_by_company_id(company_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No company intelligence found for company_id",
            )
        return record

    async def refresh(self, intelligence_id: UUID) -> CompanyIntelligenceResponse:
        record = await self.get(intelligence_id)
        payload = CompanyIntelligenceRequest(
            website_url=record.website_url,
            company_name=record.company_name,
            company_id=record.company_id,
            run_in_background=False,
        )
        updated = await self.analyze_now(payload)
        return CompanyIntelligenceResponse(
            status="completed",
            data=CompanyIntelligenceRead.model_validate(updated),
        )

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> CompanyIntelligenceListResponse:
        items, total = await self.repository.list(page=page, page_size=page_size, search=search)
        return CompanyIntelligenceListResponse(
            items=[CompanyIntelligenceRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )


from bs4 import BeautifulSoup  # Imported for discovery helper in analyze_now
