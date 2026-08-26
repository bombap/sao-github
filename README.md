# Sao Github

Bot GitHub Actions lấy repo đã **star** của [bombap](https://github.com/bombap), đọc README, tóm tắt tiếng Việt (OpenRouter hoặc xAI nếu có secret), rồi ghi:

| File | Ý nghĩa |
| --- | --- |
| [`catalog.json`](./catalog.json) | Dữ liệu trang xem (nhóm, tóm tắt, stars) |
| [`STARRED_REPOS.md`](./STARRED_REPOS.md) | Mục lục Markdown |
| [`src/content/stars/*.md`](./src/content/stars/) | Từng nhóm |

## Bot

- Script: [`bot/generate_starred.py`](./bot/generate_starred.py)
- Workflow: [`.github/workflows/update-starred.yml`](./.github/workflows/update-starred.yml)
- Lịch: `0 19 * * *` (02:00 giờ Việt Nam) + `workflow_dispatch`

Secret tùy chọn: `OPENROUTER_API_KEY` — nếu có, bot đọc README và tóm tắt repo mới. Tóm tắt cũ giữ nguyên trong `catalog.json`.
