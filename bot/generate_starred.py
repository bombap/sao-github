#!/usr/bin/env python3
"""GitHub bot: fetch starred repos → classified Vietnamese Markdown (Astro-ready)."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

USERNAME = os.environ.get("GH_USERNAME", "bombap")
OUT_DIR = Path(os.environ.get("STARRED_OUT", "."))

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

ROLE = {
    "video-seedance": "Công cụ / pipeline sản xuất video, short drama hoặc Seedance.",
    "skills-prompt": "Skill hoặc bộ prompt giúp agent làm việc có tay nghề hơn.",
    "image-design": "Công cụ tạo ảnh, design, motion hoặc poster.",
    "cloud-workers": "Hạ tầng edge, Cloudflare Workers hoặc AI gateway.",
    "rag-search": "Tìm kiếm, crawl, RAG hoặc xử lý tài liệu.",
    "agent-llm": "Framework / SDK để dựng agent và ứng dụng LLM.",
    "frontend-ui": "Thư viện giao diện, editor hoặc starter frontend.",
    "selfhost-ops": "Phần mềm tự host, DevOps hoặc nền tảng SaaS.",
    "crypto-web3": "Công cụ crypto, Solana hoặc on-chain.",
    "learning": "Tài liệu học, awesome list hoặc cookbook.",
    "other": "Repo kỹ thuật đã bookmark.",
}


def classify(repo):
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


def fetch_starred():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    repos = []
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
        with urllib.request.urlopen(req, timeout=60) as r:
            batch = json.loads(r.read().decode())
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


def fmt_date(iso):
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return iso[:10]


def render_repo(r, cid):
    desc = (r.get("description") or "").strip()
    role = ROLE[cid]
    about = f"{desc}\n\n*{role}*" if desc else f"*{role}* Chưa có mô tả trên GitHub."
    topics = r.get("topics") or []
    topic_line = ", ".join(f"`{t}`" for t in topics[:8]) if topics else "—"
    archived = " · **đã archive**" if r.get("archived") else ""
    homepage = r.get("homepage") or ""
    home = f"\n- **Website:** {homepage}" if homepage.startswith("http") else ""
    license_ = r.get("license") or ""
    lic = f"\n- **License:** `{license_}`" if license_ and license_ != "NOASSERTION" else ""
    forks = r.get("forks")
    fork_line = f"\n- **Fork:** {forks:,}" if forks else ""
    return f"""### [{r['fullName']}]({r.get('url') or 'https://github.com/' + r['fullName']})

{about}

- **Ngôn ngữ:** `{r.get('language') or '—'}`
- **Stars:** {int(r.get('stars') or 0):,}
- **Cập nhật code:** {fmt_date(r.get('updatedAt') or '')}{archived}{fork_line}{lic}{home}
- **Topics:** {topic_line}
"""


def build_markdown(repos):
    grouped = defaultdict(list)
    for r in repos:
        grouped[classify(r)].append(r)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    used = [c for c in CATEGORIES if grouped.get(c[0])]
    toc = "\n".join(
        f"- [{name}](#{cid}) — {len(grouped[cid])} repo · {blurb}"
        for cid, name, blurb, _ in used
    )
    sections = []
    for cid, name, blurb, _ in used:
        items = sorted(grouped[cid], key=lambda x: int(x.get("stars") or 0), reverse=True)
        body = "\n".join(render_repo(r, cid) for r in items)
        sections.append(f"## {name}\n\n*{blurb}*\n\n{body}")
    return f"""---
title: "Repo đã star của {USERNAME}"
description: "Danh sách GitHub starred, phân loại tiếng Việt, cập nhật bởi GitHub Actions."
publishDate: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}
language: vi
layout: ../../layouts/MarkdownLayout.astro
---

# Repo đã star của `{USERNAME}`

*Cập nhật: {now}*  
*Bot GitHub Actions · {len(repos)} repository · {len(used)} nhóm*

{toc}

---

{chr(10).join(sections)}
"""


def build_category_pages(repos):
    grouped = defaultdict(list)
    for r in repos:
        grouped[classify(r)].append(r)
    pages = {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for cid, name, blurb, _ in CATEGORIES:
        items = grouped.get(cid)
        if not items:
            continue
        items = sorted(items, key=lambda x: int(x.get("stars") or 0), reverse=True)
        body = "\n".join(render_repo(r, cid) for r in items)
        pages[f"src/content/stars/{cid}.md"] = f"""---
title: "{name}"
description: "{blurb}"
publishDate: {now}
draft: false
language: vi
category: "{name}"
count: {len(items)}
---

# {name}

{blurb}

**{len(items)}** repository.

{body}
"""
    return pages


def main():
    repos = fetch_starred()
    if not repos:
        raise SystemExit("No starred repos fetched")
    out = OUT_DIR
    (out / "src/content/stars").mkdir(parents=True, exist_ok=True)
    md = build_markdown(repos)
    (out / "STARRED_REPOS.md").write_text(md, encoding="utf-8")
    for path, content in build_category_pages(repos).items():
        p = out / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    print("wrote", out / "STARRED_REPOS.md", "chars", len(md), "repos", len(repos))


if __name__ == "__main__":
    main()
