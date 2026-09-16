| Component | Description | Recommended Testing Stage |
|---|---|---|
| `scrape_headlines.py` | Scrapes headlines from multiple news sources using HTTP requests, parses HTML anchors, deduplicates and outputs JSON. | **Integration** – requires network access and HTML parsing; unit tests for `HeadlineParser` can be added, but primary verification is integration.
| `seed_headlines.py` | Retrieves RSS/Atom feeds, extracts article URLs, ensures kanban structure, appends new URLs to `kanban.md`. | **Integration** – involves network fetching and file I/O; unit tests for parsing logic are possible.
| `duplicate_detection.py` | Computes SHA‑256 hash of article text, checks against stored hashes to avoid duplicates. | **Unit** – pure function logic; can be fully tested without external dependencies.
| `validate_unsplash_images.py` | Checks image URLs via `curl` for `Content‑Length`, replaces oversized images with a placeholder. | **Unit/Integration** – core logic is unit‑testable, but actual header retrieval is integration with external service.
| `alert_pipeline_errors.py` | Monitors `pipeline_errors.log`, sends new JSON entries as Telegram messages. | **Integration** – requires environment variables and network (Telegram API). Unit‑level parsing can be mocked.
| `three-layer-architecture.md` | Documentation describing Hermes three‑layer system architecture. | **No testing required** – documentation artifact.
| `config.example.yaml` | Example configuration file for the project. | **No testing required** – static config.
| `requirements.txt` | Lists Python dependencies for the project. | **No testing required** – dependency list.
| `Dockerfile` | Container definition for the project (if used). | **Integration** – can be built and run to verify container setup.
| `site/` HTML files | Static website pages generated from articles. | **End‑to‑End** – render the site and verify navigation/content.
| `pipeline_errors.log` | Log file for pipeline errors. | **No testing required** – runtime artifact.
| `alert_script.log` (created by `alert_pipeline_errors.py`) | Log file for alert script activity. | **No testing required** – runtime artifact.
