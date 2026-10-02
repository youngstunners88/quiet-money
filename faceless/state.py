"""Job state machine.

A job is one video. It moves forward through STAGES; each stage writes its artifacts
into the job folder and records the transition. Stages are idempotent: re-running a
job resumes from the first stage whose artifacts are missing, so a crash or a CI
timeout never repeats paid work.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from faceless import events
from faceless.config import Paths

STAGES = ["planned", "scripted", "voiced", "visualized", "rendered", "gated", "packaged", "published"]
TERMINAL = {"published", "failed", "held"}


class TransitionError(RuntimeError):
    pass


def slugify(text: str, n: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:n].rstrip("-") or "untitled"


@dataclass
class Job:
    id: str
    pillar: str
    topic: str
    day: str
    slot: int = 0
    status: str = "planned"
    history: list = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)
    cost: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    @property
    def dir(self) -> Path:
        return Paths.output / self.day / self.id

    @property
    def path(self) -> Path:
        return Paths.jobs / f"{self.id}.json"

    def advance(self, to: str, **info) -> None:
        if to not in STAGES and to not in TERMINAL:
            raise TransitionError(f"unknown stage {to}")
        if to in STAGES and self.status in STAGES and STAGES.index(to) < STAGES.index(self.status):
            raise TransitionError(f"{self.id}: cannot go back from {self.status} to {to}")
        self.history.append({"from": self.status, "to": to, "ts": events.now_iso(), **info})
        self.status = to
        events.emit("JOB_TRANSITION", job=self.id, to=to, **info)
        self.save()

    def reached(self, stage: str) -> bool:
        if self.status in ("failed", "held"):
            done = [h["to"] for h in self.history]
            return stage in done
        return self.status in STAGES and STAGES.index(self.status) >= STAGES.index(stage)

    def add_cost(self, key: str, amount: float) -> None:
        self.cost[key] = round(self.cost.get(key, 0) + amount, 6)

    def save(self) -> None:
        Paths.jobs.mkdir(parents=True, exist_ok=True)
        from faceless.config import redact   # job files are committed publicly; error notes can echo request URLs
        self.path.write_text(redact(json.dumps(asdict(self), indent=2, ensure_ascii=False)), encoding="utf-8")


def new_job(pillar: str, topic: str, slot: int = 0, day: str | None = None) -> Job:
    day = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    jid = f"{day}-s{slot}-{pillar}-{slugify(topic, 32)}"
    job = Job(id=jid, pillar=pillar, topic=topic, day=day, slot=slot)
    job.dir.mkdir(parents=True, exist_ok=True)
    job.save()
    events.emit("JOB_CREATED", job=jid, pillar=pillar, topic=topic, slot=slot)
    return job


def load_job(job_id: str) -> Job:
    data = json.loads((Paths.jobs / f"{job_id}.json").read_text(encoding="utf-8"))
    return Job(**data)


def all_jobs() -> list[Job]:
    if not Paths.jobs.exists():
        return []
    return [Job(**json.loads(p.read_text(encoding="utf-8"))) for p in sorted(Paths.jobs.glob("*.json"))]
