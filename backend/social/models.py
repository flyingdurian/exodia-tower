"""Platform-neutral, offline editorial models. No external posting here."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

class Stage(str, Enum):
    IDEA='idea'
    RESEARCH='research'
    SCRIPT='script'
    ASSETS='assets'
    EDIT='edit'
    REVIEW='review'
    APPROVED='approved'
    SCHEDULED='scheduled'
    PUBLISHED='published'
    MONITORED='monitored'

class Platform(str, Enum):
    YOUTUBE='youtube'
    TIKTOK='tiktok'
    INSTAGRAM='instagram'

@dataclass
class ContentJob:
    title: str
    platforms: set[Platform]
    id: str = field(default_factory=lambda: str(uuid4()))
    stage: Stage = Stage.IDEA
    source_urls: list[str] = field(default_factory=list)
    notes: str = ''
    approval_record: dict | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def advance(self, target: Stage) -> None:
        order=list(Stage)
        current=order.index(self.stage)
        if target != order[current+1] if current < len(order)-1 else True:
            raise ValueError('Stage transitions must advance by one step')
        if target in (Stage.APPROVED, Stage.SCHEDULED, Stage.PUBLISHED) and not self.approval_record:
            raise PermissionError('Operator approval is required')
        if target == Stage.PUBLISHED:
            raise PermissionError('Publishing requires an authenticated provider adapter')
        self.stage=target
        self.updated_at=datetime.now(timezone.utc)
