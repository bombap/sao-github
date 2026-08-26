#!/usr/bin/env python3
"""Starred repos → catalog.json + Vietnamese Markdown. Optional AI (README → tóm tắt)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

USERNAME = os.environ.get("GH_USERNAME", "bombap")
OUT_DIR = Path(os.environ.get("STARRED_OUT", "."))
RAW_FALLBACK = Path(os.environ.get("STARRED_RAW_FALLBACK", "/workspace/src/data/stars.raw.json"))
SUMMARIES_FILE = Path(os.environ.get("STARRED_SUMMARIES", "/workspace/src/data/summaries.json"))

CATEGORIES = [
    ("video-seedance", "Video / Seedance / Shorts", "Pipeline video, short drama, storyboard, editor.", ["seedance", "short-video", "short video", "shorts", "storyboard", "drama", "tiktok", "toonflow", "moneyprinter", "pixelle", "openmontage", "huobao", "arcreel", "waoowaoo", "printfilm", "tvc-director", "handdrawn", "book-video", "clipsketch", "tooscut", "ai-video", "short-drama", "short drama"]),
    ("skills-prompt", "Agent Skills / Prompt", "Skill, prompt, harness, anti-slop, viết tiếng người.", ["skill", "prompt", "hallmark", "impeccable", "taste-skill", "human-writing", "cangjie", "spec-kit", "system-prompts", "task-master", "rules_template", "mdcvalult"]),
    ("image-design", "Ảnh / Design / Motion", "Tạo ảnh, poster editorial, motion, design system.", ["gpt-image", "image", "poster", "zine", "editorial", "logo", "banana", "draw", "excalidraw", "tldraw", "threeui", "oil-motion", "huashu", "manga", "slides", "ppt"]),
    ("cloud-workers", "Cloudflare / Gateway", "Workers, Hono, AI gateway, serverless.", ["cloudflare", "workers", "hono", "gateway", "ferrogate", "keyaos", "ai-relay", "ai-gateway", "openrouter", "vibesdk"]),
    ("rag-search", "RAG / Search / Data", "RAG, crawl, research, đọc tài liệu.", ["rag", "retrieval", "firecrawl", "crawl", "scraper", "embed", "kotaemon", "dify", "langflow", "marker", "anydoc", "deep-research", "mindsearch", "scira"]),
    ("agent-llm", "Agent / LLM framework", "Orchestration, multi-agent, SDK chat.", ["agent", "llm", "orchestr", "crew", "autogen", "langgraph", "adk", "beeai", "voltagent", "mem0", "copilotkit", "librechat", "chainlit", "openai-agents"]),
    ("frontend-ui", "Frontend / UI kit", "React, Vue, shadcn, editor, canvas.", ["react", "vue", "shadcn", "ui", "css", "tailwind", "storybook", "heroui", "grapesjs", "puck", "json-render", "assistant-ui", "termcn"]),
    ("selfhost-ops", "Self-host / DevOps / SaaS", "PaaS, ERP, CMS, automation, starter kit.", ["coolify", "self-host", "selfhost", "erp", "nocobase", "directus", "appwrite", "chatwoot", "twenty", "saas", "docker", "duplicati"]),
    ("crypto-web3", "Crypto / Solana / Web3", "DEX, protocol, bot, SDK on-chain.", ["solana", "uniswap", "dex", "sandwich", "mev", "jetton", "dn404", "web3", "crypto", "perpetual"]),
    ("learning", "Học tập / Awesome list", "Cookbook, awesome list, handbook.", ["awesome", "cookbook", "handbook", "tutorial", "list of", "cheatsheet"]),
    ("other", "Khác", "Repo không khớp các nhóm trên.", []),
]


def classify(repo: dict) -> str:
    hay = " ".join(
        [
            repo.get("fullName") or repo.get("full_name") or "",
            repo.get("name") or "",
            repo.get("description") or "",
            repo.get("language") or "",
            " ".join(repo.get("topics") or []),
        ]
    ).lower()
    for cid, _n, _b, keys in CATEGORIES:
        if cid == "other":
            continue
        if any(k in hay for k in keys):
            return cid
    return "other"


def http_json(url: str, token: str = "", accept: str = "application/vnd.github+json") -> object:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "sao-github-bot",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read().decode("utf-8", "replace")
        if accept.endswith("+json") or accept.endswith("/json"):
            return json.loads(raw)
        return raw


def fetch_starred() -> list[dict]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    repos: list[dict] = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{USERNAME}/starred?per_page=100&page={page}"
        try:
            batch = http_json(url, token)
        except Exception as exc:
            print("fetch starred failed:", exc)
            break
        if not isinstance(batch, list) or not batch:
            break
        for repo in batch:
            license_obj = repo.get("license") or {}
            repos.append(
                {
                    "id": repo["id"],
                    "fullName": repo["full_name"],
                    "name": repo["name"],
                    "url": repo["html_url"],
                    "description": repo.get("description") or "",
                    "language": repo.get("language") or "",
                    "stars": repo.get("stargazers_count") or 0,
                    "forks": repo.get("forks_count") or 0,
                    "topics": repo.get("topics") or [],
                    "updatedAt": repo.get("updated_at") or "",
                    "archived": bool(repo.get("archived")),
                    "homepage": repo.get("homepage") or "",
                    "license": license_obj.get("spdx_id") if license_obj else "",
                }
            )
        print("page", page, "+", len(batch))
        page += 1
        time.sleep(0.12)
    return repos


def load_repos() -> list[dict]:
    live = fetch_starred()
    if live:
        return live
    if RAW_FALLBACK.exists():
        print("using fallback", RAW_FALLBACK)
        return json.loads(RAW_FALLBACK.read_text(encoding="utf-8"))
    raise SystemExit("No starred repos")


def load_summaries(out: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for path in (SUMMARIES_FILE, out / "summaries.json"):
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, str) and v.strip():
                        found[k] = v.strip()
    catalog_path = out / "catalog.json"
    if catalog_path.exists():
        try:
            cat = json.loads(catalog_path.read_text(encoding="utf-8"))
            for g in cat.get("groups") or cat.get("categories") or []:
                for r in g.get("repos") or []:
                    s = (r.get("summaryVi") or "").strip()
                    if s and r.get("fullName"):
                        found.setdefault(r["fullName"], s)
        except Exception:
            pass
    return found


def llm_config() -> tuple[str, str, str] | None:
    or_key = os.environ.get("OPENROUTER_API_KEY") or ""
    xai = os.environ.get("XAI_API_KEY") or ""
    if or_key:
        model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        return or_key, "https://openrouter.ai/api/v1/chat/completions", model
    if xai:
        return xai, "https://api.x.ai/v1/chat/completions", "grok-4.5"
    return None


def clip_readme(md: str) -> str:
    import re

    text = re.sub(r"<!--[\s\S]*?-->", " ", md or "")
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^#+\s+", "", text, flags=re.M)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1600]


def fetch_readme(full_name: str, token: str) -> str:
    url = f"https://api.github.com/repos/{full_name}/readme"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github.raw+json",
                "User-Agent": "sao-github-bot",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            return clip_readme(r.read().decode("utf-8", "replace"))
    except Exception:
        return ""


def llm_summarize(batch: list[dict], cfg: tuple[str, str, str]) -> dict[str, str]:
    key, endpoint, model = cfg
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Bạn là biên tập viên tiếng Việt. Đọc README (cắt ngắn) và mô tả GitHub, viết 1–2 câu tiếng Việt: repo này làm gì, dùng khi nào. Không dịch máy, không sáo. JSON {items:[{fullName, summaryVi}]}.",
            },
            {"role": "user", "content": json.dumps(batch, ensure_ascii=False)},
        ],
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "sao-github-bot",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = json.loads(r.read().decode("utf-8", "replace"))
        text = (((body.get("choices") or [{}])[0].get("message") or {}).get("content")) or "{}"
        parsed = json.loads(text)
        items = parsed.get("items") or parsed.get("repos") or []
        out = {}
        for it in items:
            name, summary = it.get("fullName"), (it.get("summaryVi") or "").strip()
            if name and summary:
                out[name] = summary
        return out
    except Exception as exc:
        print("llm batch fail:", exc)
        return {}


def maybe_ai_summaries(repos: list[dict], existing: dict[str, str]) -> dict[str, str]:
    cfg = llm_config()
    if not cfg:
        print("no LLM key — keep cached summaries", len(existing))
        return existing
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    pending = [r for r in repos if not existing.get(r["fullName"])]
    print("ai summarize pending", len(pending), "cached", len(existing))
    for i in range(0, len(pending), 6):
        slice_ = pending[i : i + 6]
        payload = []
        for r in slice_:
            payload.append(
                {
                    "fullName": r["fullName"],
                    "description": r.get("description") or "",
                    "language": r.get("language") or "",
                    "readme": fetch_readme(r["fullName"], token),
                }
            )
        existing.update(llm_summarize(payload, cfg))
        print("ai batch", i // 6 + 1, "have", len(existing))
        time.sleep(0.3)
    return existing


def fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return iso[:10]


def md_escape(text: str) -> str:
    return (text or "").replace("\n", " ").strip()


def render_repo_md(r: dict) -> str:
    desc = md_escape(r.get("description") or "")
    summary = md_escape(r.get("summaryVi") or "")
    if not summary:
        summary = desc or "Chưa có tóm tắt tiếng Việt."
    orig = f"\n\n*Mô tả gốc:* {desc}" if desc and desc != summary else ""
    topics = r.get("topics") or []
    topic_line = " ".join(f"`{t}`" for t in topics[:6])
    topic_md = f"\n\n{topic_line}" if topic_line else ""
    archived = " · **đã archive**" if r.get("archived") else ""
    lang = r.get("language") or "—"
    return f"""### [{r['fullName']}]({r.get('url') or 'https://github.com/' + r['fullName']})

{summary}{orig}

`{lang}` · **{int(r.get('stars') or 0):,}** stars · {fmt_date(r.get('updatedAt') or '')}{archived}{topic_md}
"""


def build_catalog(repos: list[dict], summaries: dict[str, str], grouped: dict[str, list[dict]]) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    groups = []
    for cid, name, blurb, _ in CATEGORIES:
        items = grouped.get(cid) or []
        if not items:
            continue
        rows = []
        for r in items:
            rows.append(
                {
                    "id": r.get("id") or 0,
                    "fullName": r["fullName"],
                    "name": r.get("name") or r["fullName"].split("/")[-1],
                    "url": r.get("url") or f"https://github.com/{r['fullName']}",
                    "description": r.get("description") or "",
                    "summaryVi": summaries.get(r["fullName"]) or "",
                    "language": r.get("language") or "",
                    "stars": int(r.get("stars") or 0),
                    "topics": r.get("topics") or [],
                    "updatedAt": r.get("updatedAt") or "",
                    "archived": bool(r.get("archived")),
                    "category": cid,
                }
            )
        groups.append(
            {
                "id": cid,
                "name": name,
                "blurb": blurb,
                "count": len(rows),
                "repos": rows,
            }
        )
    return {
        "updatedAt": now,
        "username": USERNAME,
        "total": len(repos),
        "summarized": sum(1 for r in repos if summaries.get(r["fullName"])),
        "groups": groups,
    }


def build_index_md(catalog: dict) -> str:
    now = catalog["updatedAt"]
    rows = []
    for g in catalog["groups"]:
        rows.append(
            f"| {g['name']} | [{g['id']}.md](./src/content/stars/{g['id']}.md) | {g['count']} | {g['blurb']} |"
        )
    body = "\n".join(rows)
    return f"""---
title: "Repo đã star của {USERNAME}"
description: "Danh sách GitHub starred, tóm tắt tiếng Việt từ README."
publishDate: {now[:10]}
language: vi
---

# Repo đã star của `{USERNAME}`

Tổng hợp tự động bởi GitHub Actions. Tóm tắt tiếng Việt do AI đọc README của từng repo.

*Cập nhật: {now}*  
*{catalog['total']} repository · {len(catalog['groups'])} nhóm · {catalog['summarized']} đã có tóm tắt AI*

| Nhóm | File Markdown | Số repo | Nội dung |
| --- | --- | ---: | --- |
{body}
"""


def build_category_md(g: dict, now: str) -> str:
    body = "\n".join(render_repo_md(r) for r in g["repos"])
    return f"""---
title: "{g['name']}"
description: "{g['blurb']}"
publishDate: {now[:10]}
language: vi
category: "{g['name']}"
count: {g['count']}
---

← [Mục lục · STARRED_REPOS.md](../../STARRED_REPOS.md)

# {g['name']}

{g['blurb']}

**{g['count']}** repository · tóm tắt tiếng Việt từ README.

{body}
"""


def main() -> None:
    out = OUT_DIR
    repos = load_repos()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in repos:
        grouped[classify(r)].append(r)
    for cid, items in grouped.items():
        items.sort(key=lambda x: int(x.get("stars") or 0), reverse=True)

    summaries = load_summaries(out)
    summaries = maybe_ai_summaries(repos, summaries)
    for r in repos:
        r["summaryVi"] = summaries.get(r["fullName"]) or ""

    catalog = build_catalog(repos, summaries, grouped)
    stars_dir = out / "src" / "content" / "stars"
    stars_dir.mkdir(parents=True, exist_ok=True)
    (out / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "STARRED_REPOS.md").write_text(build_index_md(catalog), encoding="utf-8")
    for g in catalog["groups"]:
        (stars_dir / f"{g['id']}.md").write_text(build_category_md(g, catalog["updatedAt"]), encoding="utf-8")
    print("wrote catalog", catalog["total"], "summarized", catalog["summarized"])


if __name__ == "__main__":
    main()
