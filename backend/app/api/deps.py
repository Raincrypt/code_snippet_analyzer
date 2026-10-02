from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db import get_session
from app.services.reviewer import Reviewer

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_reviewer(request: Request) -> Reviewer:
    reviewer: Reviewer = request.app.state.reviewer
    return reviewer


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


ReviewerDep = Annotated[Reviewer, Depends(get_reviewer)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
