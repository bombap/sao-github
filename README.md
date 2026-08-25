# Sao Github

Bot GitHub Actions tổng hợp repo đã **star** của [bombap](https://github.com/bombap) thành file Markdown tiếng Việt.

## File do bot ghi

| File | Ý nghĩa |
| --- | --- |
| [`STARRED_REPOS.md`](./STARRED_REPOS.md) | Mục lục các nhóm |
| [`src/content/stars/*.md`](./src/content/stars/) | Từng nhóm: bảng Repo · Mô tả · Ngôn ngữ · Stars · Cập nhật |

Trang xem đọc các file này **trực tiếp từ GitHub** (`raw.githubusercontent.com`), không cần tải xuống.

## Bot

- Script: [`bot/generate_starred.py`](./bot/generate_starred.py)
- Workflow: [`.github/workflows/update-starred.yml`](./.github/workflows/update-starred.yml)
- Lịch: `0 19 * * *` (02:00 giờ Việt Nam) + `workflow_dispatch`

Secret tùy chọn: `OPENROUTER_API_KEY` nếu muốn tóm tắt bằng OpenRouter.
