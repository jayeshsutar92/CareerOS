import logging
import os
import re
import uuid
from typing import Sequence

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import Template
from app.repositories.template import TemplateRepository
from app.schemas.template import TemplateCreate

logger = logging.getLogger(__name__)


class TemplateService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TemplateRepository(session)

    async def get_template(self, template_id: uuid.UUID) -> Template:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template

    async def list_templates(self) -> Sequence[Template]:
        return await self.repo.list_all()

    async def seed_templates(self) -> list[Template]:
        """Parse templates.txt and seed them if they don't exist."""
        # templates.txt is at the project root, one level up from backend
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        templates_path = os.path.join(project_root, "templates.txt")

        if not os.path.exists(templates_path):
            logger.warning(f"templates.txt not found at {templates_path}. Skipping seed.")
            return []

        with open(templates_path, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = re.split(r'\n---\n', content)
        seeded_templates = []

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            # Parse Name
            # e.g. "**1. The Builder (proof-over-promises)**" -> "1. The Builder (proof-over-promises)"
            name_match = re.search(r'\*\*(.*?)\*\*', chunk)
            if not name_match:
                continue
            name = name_match.group(1).strip()

            # Parse Subject
            subject_match = re.search(r'Subject:\s*(.*)', chunk)
            if not subject_match:
                continue
            subject = subject_match.group(1).strip()

            # Parse Body
            # Everything after the subject line
            body_parts = chunk.split(subject_match.group(0))
            if len(body_parts) < 2:
                continue
            body = body_parts[1].strip()

            # Check if exists
            existing = await self.repo.get_by_name(name)
            if not existing:
                template_in = TemplateCreate(name=name, subject=subject, body=body)
                db_obj = await self.repo.create(template_in)
                seeded_templates.append(db_obj)
                logger.info(f"Seeded template: {name}")

        return seeded_templates
