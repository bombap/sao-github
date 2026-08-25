#!/usr/bin/env python3
"""GitHub bot: starred repos → Vietnamese Markdown files (index + per-category)."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

USERNAME = os.environ.get("GH_USERNAME", "bombap")
OUT_DIR = Path(os.environ.get("STARRED_OUT", "."))
RAW_FALLBACK = Path(os.environ.get("STARRED_RAW_FALLBACK", "/workspace/src/data/stars.raw.json"))

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


def fetch_starred() -> list[dict]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    repos: list[dict] = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{USERNAME}/starred?per_page=100&page={page}"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "sao-github-bot",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                batch = json.loads(r.read().decode())
        except Exception as exc:
            print("fetch failed:", exc)
            break
        if not batch:
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
        time.sleep(0.15)
    return repos


def load_repos() -> list[dict]:
    live = fetch_starred()
    if live:
        return live
    if RAW_FALLBACK.exists():
        print("using fallback", RAW_FALLBACK)
        return json.loads(RAW_FALLBACK.read_text(encoding="utf-8"))
    raise SystemExit("No starred repos")


def fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return iso[:10]


def cell(text: str, limit: int = 160) -> str:
    s = (text or "").replace("\r", "").replace("\n", " ").replace("|", "\\|")
    s = s.replace("<", "<").replace(">", ">").strip()
    if not s:
        return "—"
    if len(s) <= limit:
        return s
    clipped = s[: limit - 1]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped + "…"


def repo_row(r: dict) -> str:
    url = r.get("url") or f"https://github.com/{r['fullName']}"
    name = cell(r["fullName"], 80)
    archived = " · archive" if r.get("archived") else ""
    desc = cell(r.get("description") or "")
    topics = r.get("topics") or []
    if topics and desc != "—":
        tags = " ".join(f"`{t}`" for t in topics[:4])
        desc = f"{desc} {tags}"
    elif topics:
        desc = " ".join(f"`{t}`" for t in topics[:6])
    lang = cell(r.get("language") or "—", 24)
    stars = f"{int(r.get('stars') or 0):,}"
    updated = fmt_date(r.get("updatedAt") or "")
    return f"| [{name}]({url}){archived} | {desc} | {lang} | {stars} | {updated} |"


def table(repos: list[dict]) -> str:
    header = "| Repo | Mô tả | Ngôn ngữ | Stars | Cập nhật |\n| --- | --- | --- | ---: | --- |"
    rows = "\n".join(repo_row(r) for r in repos)
    return f"{header}\n{rows}"


def group_repos(repos: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in repos:
        grouped[classify(r)].append(r)
    for cid, items in grouped.items():
        items.sort(key=lambda x: int(x.get("stars") or 0), reverse=True)
    return grouped


def build_index(repos: list[dict], grouped: dict[str, list[dict]]) -> str:
    now = datetime.now(timezone.utc)
    used = [c for c in CATEGORIES if grouped.get(c[0])]
    rows = []
    for cid, name, blurb, _ in used:
        n = len(grouped[cid])
        rows.append(
            f"| {name} | [{cid}.md](./src/content/stars/{cid}.md) | {n} | {blurb} |"
        )
    body = "\n".join(rows)
    return f"""---
title: "Repo đã star của {USERNAME}"
description: "Mục lục Markdown do GitHub bot tổng hợp từ starred repos."
publishDate: {now.strftime("%Y-%m-%d")}
language: vi
---

# Repo đã star của `{USERNAME}`

Tổng hợp **tự động** bởi GitHub Actions (02:00 giờ Việt Nam mỗi ngày, hoặc chạy tay `workflow_dispatch`).

Mỗi nhóm là **một file Markdown** trong [`src/content/stars/`](https://github.com/{USERNAME}/sao-github/tree/main/src/content/stars). Trang xem đọc các file đó trực tiếp từ GitHub.

*Cập nhật: {now.strftime("%Y-%m-%d %H:%M UTC")}*  
*{len(repos)} repository · {len(used)} nhóm · bot `generate_starred.py`*

| Nhóm | File Markdown | Số repo | Nội dung |
| --- | --- | ---: | --- |
{body}
"""


def build_category_page(cid: str, name: str, blurb: str, items: list[dict], now: datetime) -> str:
    return f"""---
title: "{name}"
description: "{blurb}"
publishDate: {now.strftime("%Y-%m-%d")}
draft: false
language: vi
category: "{name}"
count: {len(items)}
---

← [Mục lục · STARRED_REPOS.md](../../STARRED_REPOS.md)

# {name}

{blurb}

**{len(items)}** repository · sắp xếp theo số star · nguồn GitHub starred của `{USERNAME}`.

{table(items)}
"""


def main() -> None:
    repos = load_repos()
    grouped = group_repos(repos)
    now = datetime.now(timezone.utc)
    out = OUT_DIR
    stars_dir = out / "src" / "content" / "stars"
    stars_dir.mkdir(parents=True, exist_ok=True)

    index = build_index(repos, grouped)
    (out / "STARRED_REPOS.md").write_text(index, encoding="utf-8")

    written = 1
    for cid, name, blurb, _ in CATEGORIES:
        items = grouped.get(cid)
        if not items:
            continue
        path = stars_dir / f"{cid}.md"
        path.write_text(build_category_page(cid, name, blurb, items, now), encoding="utf-8")
        written += 1
        print("wrote", path, "repos", len(items), "chars", path.stat().st_size)

    print("wrote", out / "STARRED_REPOS.md", "chars", len(index), "files", written, "repos", len(repos))


if __name__ == "__main__":
    main()
