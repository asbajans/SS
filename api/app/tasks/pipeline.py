"""Pipeline orchestration: ingest -> ontology -> population -> loop -> report."""
import asyncio
import random
from datetime import UTC, datetime
from types import SimpleNamespace

import structlog
from celery import shared_task
from sqlalchemy import func, select

from app.config import settings
from app.db import AsyncSessionLocal
from app.llm_gateway.factory import build_gateway
from app.models import (
    Agent,
    Document,
    DocumentChunk,
    Ontology,
    Project,
    Run,
    RunEvent,
    TokenUsage,
)
from app.storage import put_bytes
from app.template_service import load_template
from app.webhooks import dispatch_run_event
from engine.actions import parse_agent_action
from engine.insights import build_run_insights, format_insights_markdown
from engine.loop import build_agent_messages
from engine.ontology import build_ontology_prompt, parse_ontology
from engine.population import build_persona_prompt, parse_personas
from engine.report import (
    build_evidence,
    build_outline_messages,
    build_section_messages,
    compose_markdown,
    disclaimer_for,
    fallback_section_body,
    fallback_sections,
    parse_outline,
    render_pdf,
    summarize_events,
)
from engine.scheduler import ScheduleConfig, pick_active_agents

log = structlog.get_logger(__name__)

TERMINAL = {"completed", "failed", "canceled"}
ROUND_HOUR_BASE = 9
PERSONA_BATCH = 5


@shared_task(name="pipeline.run", max_retries=0, soft_time_limit=3 * 3600 - 60)
def run_pipeline(run_id: str) -> dict:
    try:
        return asyncio.run(_run(run_id))
    except Exception as e:  # noqa: BLE001
        log.exception("pipeline_failed", run_id=run_id)
        asyncio.run(_mark_failed(run_id, str(e)))
        return {"status": "failed", "error": str(e)}


async def _mark_failed(run_id: str, error: str) -> None:
    async with AsyncSessionLocal() as s:
        run = await s.get(Run, run_id)
        if run is None:
            return
        run.status = "failed"
        run.error = error[:4000]
        run.finished_at = datetime.now(UTC)
        project = await s.get(Project, run.project_id)
        if project is not None:
            project.status = "failed"
        await s.commit()
    await dispatch_run_event(run_id, "run.failed")


async def _set_status(s, run_id, status: str, **extra) -> Run | None:
    run = await s.get(Run, run_id)
    if run is None:
        return None
    run.status = status
    for key, value in extra.items():
        setattr(run, key, value)
    if status == "running" and run.started_at is None:
        run.started_at = datetime.now(UTC)
    if status in TERMINAL:
        run.finished_at = datetime.now(UTC)
    project = await s.get(Project, run.project_id)
    if project is not None:
        project.status = status
    await s.commit()
    return run


async def _event(
    s,
    run_id,
    round_no: int,
    seq: int,
    event_type: str,
    payload: dict,
    agent_id=None,
    platform: str = "system",
) -> None:
    s.add(
        RunEvent(
            run_id=run_id,
            round=round_no,
            platform=platform,
            seq_in_round=seq,
            agent_id=agent_id,
            event_type=event_type,
            payload=payload,
        )
    )
    await s.commit()


def _scenario_context(project: Project, template) -> str:
    config = project.sim_config or {}
    lines = [
        f"Proje: {project.name}",
        f"Şablon: {template.name} ({template.key})",
    ]
    if config.get("brief"):
        lines.append(f"Araştırma briefi: {str(config['brief'])[:2500]}")
    if config.get("post_text"):
        lines.append(f"Test edilen gönderi:\n{str(config['post_text'])[:2500]}")
    if config.get("audience"):
        lines.append(f"Hedef kitle: {str(config['audience'])[:800]}")
    if config.get("channel"):
        lines.append(f"Kanal: {str(config['channel'])[:200]}")
    return "\n".join(lines)


async def _seed_material(s, project: Project, template) -> str:
    context = _scenario_context(project, template)
    chunks = (
        await s.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.project_id == project.id)
            .order_by(DocumentChunk.chunk_idx)
            .limit(8)
        )
    ).all()
    if chunks:
        docs = "\n\n".join(chunk.content for chunk in chunks)
        return f"{context}\n\nKaynak belgeler:\n{docs}"[:8000]
    return context[:8000]


async def _stage_ontology(s, run, project, template, gateway, seed_text) -> dict:
    messages = build_ontology_prompt(seed_text, template.entity_types)
    result = await gateway.call(
        "ingest_ontology",
        messages,
        user_id=project.user_id,
        project_id=project.id,
        run_id=run.id,
        response_json=True,
    )
    parsed = parse_ontology(result.text, template, seed_text)
    row = (await s.scalars(select(Ontology).where(Ontology.project_id == project.id))).first()
    if row is None:
        row = Ontology(project_id=project.id, entity_types={}, relation_types={})
        s.add(row)
    row.entity_types = {"items": parsed["entity_types"]}
    row.relation_types = {"items": parsed["relation_types"]}
    row.seed_summary = parsed["seed_summary"]
    await s.commit()
    await _event(
        s,
        run.id,
        0,
        0,
        "system",
        {"stage": "ontology", "message": "Ontoloji üretildi", "entities": len(parsed["entity_types"])},
    )
    return parsed


async def _stage_population(
    s, run, project, template, gateway, agents_n: int, seed_text: str
) -> list[Agent]:
    existing = (
        await s.scalars(
            select(Agent).where(Agent.project_id == project.id).order_by(Agent.agent_idx)
        )
    ).all()
    agents = list(existing)
    idx = len(agents)
    while len(agents) < agents_n:
        batch = min(PERSONA_BATCH, agents_n - len(agents))
        messages = build_persona_prompt(
            template,
            project.language or "tr",
            batch,
            idx,
            seed_text if not idx else "",
        )
        result = await gateway.call(
            "persona_synth",
            messages,
            user_id=project.user_id,
            project_id=project.id,
            run_id=run.id,
            response_json=True,
        )
        personas = parse_personas(result.text, template, batch, idx, project.language or "tr")
        for persona in personas:
            agent = Agent(
                project_id=project.id,
                agent_idx=idx,
                name=persona["name"],
                bio=persona["bio"],
                persona=persona["persona"],
                attributes=persona["attributes"],
                platform=persona["platform"],
            )
            s.add(agent)
            agents.append(agent)
            idx += 1
        await s.commit()
    await _event(
        s,
        run.id,
        0,
        0,
        "system",
        {"stage": "population", "message": "Ajan popülasyonu hazır", "agents": len(agents)},
    )
    return agents[:agents_n]


def _snapshot(agent: Agent) -> SimpleNamespace:
    return SimpleNamespace(
        id=agent.id,
        agent_idx=agent.agent_idx,
        name=agent.name,
        bio=agent.bio,
        persona=agent.persona,
        platform=agent.platform,
    )


async def _act_one(
    run,
    project,
    template,
    agent,
    messages,
    round_no,
    seq,
    semaphore,
    redis_client,
) -> tuple[int, float]:
    async with semaphore:
        async with AsyncSessionLocal() as s:
            gateway = build_gateway(s, redis_client, project.user_id, project.id, run.id, agent.id)
            result = await gateway.call(
                "agent_act",
                messages,
                user_id=project.user_id,
                project_id=project.id,
                run_id=run.id,
                agent_id=agent.id,
                response_json=True,
            )
            action = parse_agent_action(result.text, template.action_space)
            payload = {
                "action": action.action,
                "content": action.content,
                "target": action.target,
                "emotion": action.emotion,
                "stance": action.stance,
                "model": result.model,
            }
            s.add(
                RunEvent(
                    run_id=run.id,
                    round=round_no,
                    platform=agent.platform,
                    seq_in_round=seq,
                    agent_id=agent.id,
                    event_type=action.action,
                    payload=payload,
                )
            )
            await s.commit()
            return result.prompt_tokens + result.completion_tokens, result.cost_usd


async def _stage_running(s, run, project, template, redis_client, agents: list[Agent]) -> str:
    config = run.sim_config or {}
    defaults = template.sim_defaults or {}
    rounds = int(config.get("rounds") or defaults.get("rounds", 20))
    rounds = max(1, min(rounds, settings.engine_max_rounds))
    platforms = int(config.get("platforms") or 1)
    schedule = ScheduleConfig(
        agents_n=len(agents),
        rounds=rounds,
        platforms=platforms,
        activity_level=0.6,
    )
    rng = random.Random(hash(str(run.id)) & 0xFFFF)
    snapshots = [_snapshot(agent) for agent in agents]
    by_idx = {snap.agent_idx: snap for snap in snapshots}
    recent: list[dict] = []
    semaphore = asyncio.Semaphore(max(1, settings.engine_default_concurrency))
    user_id = project.user_id
    project_id = project.id
    run_id = run.id
    language = project.language or "tr"
    scenario = _scenario_context(project, template)

    for round_no in range(1, rounds + 1):
        current = await s.get(Run, run_id)
        if current is None or current.status == "canceled":
            return "canceled"
        if current.token_budget and current.tokens_used >= current.token_budget:
            await _event(
                s,
                run_id,
                round_no,
                0,
                "system",
                {"stage": "running", "message": "Token bütçesi doldu, turlar durduruldu"},
            )
            break
        hour = (ROUND_HOUR_BASE + round_no) % 24
        active_idx = pick_active_agents(schedule, [snap.agent_idx for snap in snapshots], hour, rng)
        active = [by_idx[i] for i in active_idx if i in by_idx]
        if not active:
            active = rng.sample(snapshots, k=min(len(snapshots), max(1, len(snapshots) // 10)))
        tasks = []
        for seq, snap in enumerate(active, start=1):
            messages = build_agent_messages(
                snap, template, round_no, hour, recent, language, scenario
            )
            tasks.append(
                _act_one(
                    SimpleNamespace(id=run_id, token_budget=current.token_budget),
                    SimpleNamespace(id=project_id, user_id=user_id),
                    template,
                    snap,
                    messages,
                    round_no,
                    seq,
                    semaphore,
                    redis_client,
                )
            )
        results = await asyncio.gather(*tasks)
        tokens = sum(r[0] for r in results)
        cost = sum(r[1] for r in results)
        current = await s.get(Run, run_id)
        if current is None:
            return "canceled"
        if current.status == "canceled":
            return "canceled"
        current.current_round = round_no
        current.tokens_used = (current.tokens_used or 0) + tokens
        current.cost_usd = float(current.cost_usd or 0) + cost
        await s.commit()
        events = (
            await s.scalars(
                select(RunEvent)
                .where(RunEvent.run_id == run_id, RunEvent.round == round_no)
                .order_by(RunEvent.seq_in_round)
                .limit(80)
            )
        ).all()
        names = {snap.id: snap.name for snap in snapshots}
        for ev in events:
            recent.append(
                {
                    "agent_name": names.get(ev.agent_id),
                    "event_type": ev.event_type,
                    "content": (ev.payload or {}).get("content"),
                }
            )
        recent = recent[-60:]
        await _event(
            s,
            run_id,
            round_no,
            0,
            "system",
            {"stage": "running", "message": f"Tur {round_no}/{rounds} tamamlandı"},
        )
    return "done"


async def _stage_report(s, run, project, template, gateway) -> dict:
    language = project.language or "tr"
    config = run.sim_config or {}
    platforms = int(config.get("platforms") or 1)
    rounds = run.current_round
    events = (
        await s.scalars(
            select(RunEvent)
            .where(RunEvent.run_id == run.id, RunEvent.event_type != "system")
            .order_by(RunEvent.round, RunEvent.seq_in_round)
        )
    ).all()
    agents = (await s.scalars(select(Agent).where(Agent.project_id == project.id))).all()
    docs = (await s.scalars(select(Document).where(Document.project_id == project.id))).all()
    ontology = (
        await s.scalars(select(Ontology).where(Ontology.project_id == project.id))
    ).first()
    names = {agent.id: agent.name for agent in agents}
    source_files = [doc.filename for doc in docs]
    seed_summary = (ontology.seed_summary if ontology else "") or ""
    stats_text = summarize_events(events, len(agents), rounds, platforms)
    insights = build_run_insights(events, names, language, rounds)
    evidence, bibliography = build_evidence(events, names, source_files)
    fallback = fallback_sections(language)
    try:
        outline_res = await gateway.call(
            "report_outline",
            build_outline_messages(
                project_name=project.name,
                template_name=template.name,
                language=language,
                seed_summary=seed_summary,
                stats_text=stats_text,
                source_files=source_files,
            ),
            user_id=project.user_id,
            project_id=project.id,
            run_id=run.id,
            response_json=True,
        )
        titles = parse_outline(outline_res.text, fallback)
    except Exception as exc:  # noqa: BLE001
        log.warning("report_outline_failed", run_id=str(run.id), err=str(exc))
        titles = fallback
    sections: list[dict] = [
        {
            "title": "Summary metrics" if language == "en" else "Özet metrikler",
            "body": format_insights_markdown(insights, language),
        }
    ]
    for idx, title in enumerate(titles, start=1):
        await _event(
            s,
            run.id,
            0,
            0,
            "system",
            {"stage": "report", "message": f"Rapor bölümü {idx}/{len(titles)}: {title}"},
        )
        await s.commit()
        try:
            res = await gateway.call(
                "report_section",
                build_section_messages(
                    title=title,
                    project_name=project.name,
                    language=language,
                    evidence=evidence,
                    previous_titles=[section["title"] for section in sections],
                ),
                user_id=project.user_id,
                project_id=project.id,
                run_id=run.id,
            )
            body = res.text.strip()
            if res.model == "mock":
                body = fallback_section_body(title, stats_text, evidence, language)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "report_section_failed", run_id=str(run.id), section=title, err=str(exc)
            )
            body = fallback_section_body(title, stats_text, evidence, language)
        sections.append({"title": title, "body": body})
    disclaimer = disclaimer_for(language)
    if language == "en":
        report_title = f"{project.name} — Simulation Report"
        meta_lines = [
            f"Project: {project.name}",
            f"Template: {template.name}",
            f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            f"Agents: {len(agents)} · Rounds: {rounds} · Platforms: {platforms}",
        ]
    else:
        report_title = f"{project.name} — Simülasyon Raporu"
        meta_lines = [
            f"Proje: {project.name}",
            f"Şablon: {template.name}",
            f"Üretim: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            f"Ajan: {len(agents)} · Tur: {rounds} · Platform: {platforms}",
        ]
    markdown = compose_markdown(
        title=report_title,
        meta_lines=meta_lines,
        sections=sections,
        bibliography=bibliography,
        disclaimer=disclaimer,
    )
    pdf_bytes = render_pdf(markdown, report_title, f"{project.name} · Social Simulation")
    base_key = f"projects/{project.id}/runs/{run.id}"
    md_key = f"{base_key}/report.md"
    pdf_key = f"{base_key}/report.pdf"
    await put_bytes(md_key, markdown.encode("utf-8"), "text/markdown; charset=utf-8")
    await put_bytes(pdf_key, pdf_bytes, "application/pdf")
    run.report_object_key = pdf_key
    run.report_meta = {
        "pdf_key": pdf_key,
        "md_key": md_key,
        "sections": [section["title"] for section in sections],
        "sources": len(source_files),
        "events": len(events),
        "generated_at": datetime.now(UTC).isoformat(),
        "insights": {
            "summary": insights["summary"],
            "actions": insights["actions"][:6],
            "participants": insights["participants"],
        },
    }
    await s.commit()
    await _event(
        s, run.id, 0, 0, "system", {"stage": "report", "message": "Rapor hazır (PDF + Markdown)"}
    )
    await s.commit()
    return {"pdf_key": pdf_key, "md_key": md_key, "sections": len(sections)}


async def _apply_usage_totals(s, run: Run) -> None:
    row = (
        await s.execute(
            select(
                func.coalesce(func.sum(TokenUsage.prompt_tokens), 0)
                + func.coalesce(func.sum(TokenUsage.completion_tokens), 0),
                func.coalesce(func.sum(TokenUsage.cost_usd), 0),
            ).where(TokenUsage.run_id == run.id, TokenUsage.status == "ok")
        )
    ).one()
    run.tokens_used = int(row[0] or 0)
    run.cost_usd = float(row[1] or 0)
    await s.commit()


async def _run(run_id: str) -> dict:
    import redis.asyncio as aioredis

    redis_client = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        async with AsyncSessionLocal() as s:
            run = await s.get(Run, run_id)
            if run is None:
                return {"status": "missing"}
            project = await s.get(Project, run.project_id)
            if project is None:
                await _set_status(s, run_id, "failed", error="project missing")
                return {"status": "failed"}
            template = await load_template(s, project.template_key)
            config = run.sim_config or {}
            defaults = template.sim_defaults or {}
            agents_n = int(config.get("agents_n") or defaults.get("agents_n", 60))
            agents_n = max(1, min(agents_n, settings.engine_max_agents))
            await _set_status(s, run_id, "ingesting")
            await _event(
                s, run_id, 0, 0, "system", {"stage": "ingesting", "message": "Kaynaklar hazırlanıyor"}
            )
            seed_text = await _seed_material(s, project, template)
            await _set_status(s, run_id, "ontology")
            await _event(
                s, run_id, 0, 0, "system", {"stage": "ontology", "message": "Ontoloji çıkarılıyor"}
            )
            gateway = build_gateway(s, redis_client, project.user_id, project.id, run.id)
            await _stage_ontology(s, run, project, template, gateway, seed_text)
            await _set_status(s, run_id, "population")
            await _event(
                s,
                run_id,
                0,
                0,
                "system",
                {"stage": "population", "message": "Persona popülasyonu üretiliyor"},
            )
            agents = await _stage_population(
                s, run, project, template, gateway, agents_n, seed_text
            )
            await _set_status(s, run_id, "running")
            await _event(
                s, run_id, 0, 0, "system", {"stage": "running", "message": "Simülasyon başladı"}
            )
            outcome = await _stage_running(s, run, project, template, redis_client, agents)
            if outcome == "canceled":
                return {"status": "canceled"}
            await _set_status(s, run_id, "report")
            await _event(
                s,
                run_id,
                0,
                0,
                "system",
                {"stage": "report", "message": "Rapor üretiliyor"},
            )
            await s.commit()
            await _stage_report(s, run, project, template, gateway)
            await _apply_usage_totals(s, run)
            await _set_status(s, run_id, "completed")
            await _event(
                s,
                run_id,
                0,
                0,
                "system",
                {"stage": "completed", "message": "Simülasyon tamamlandı"},
            )
            await dispatch_run_event(run_id, "run.completed")
            return {"status": "completed"}
    finally:
        await redis_client.aclose()
