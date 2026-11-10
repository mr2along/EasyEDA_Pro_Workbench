---
title: EasyEDA Pro Python Workbench
emoji: 🛠️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# EasyEDA Pro Python Workbench

A Hugging Face Docker Space for running the **EasyEDA Pro Linux desktop** with XFCE/Xvfb, VNC/noVNC, Nginx, and a Python FastAPI automation gateway.

## Important compatibility and licensing notes

- EasyEDA Pro is proprietary. This repository does not include or redistribute its installer.
- Obtain the Linux x64 desktop installer from the official [EasyEDA download page](https://easyeda.com/page/download), and review its license.
- The current official CLI guide says the CLI is built into the EasyEDA Pro **desktop** client (documented from v4.1.60+); confirm the actual installed build with `easyeda-pro --help` and `easyeda-pro doctor`. The browser editor does not provide the desktop session/bridge CLI.
- Linux package format and download hosting may change. Do not assume every release is a ZIP. This container supports a mounted/extracted install under `/opt/easyeda-pro`; see installation options below.
- Interactive first-run sign-in/activation may be required. This project does not bypass licensing.
- Use a **private Space** unless you intentionally want to expose the desktop. Configure all secrets before starting.

## Deploy to Hugging Face

1. Create a **Docker Space** or connect this repository as a Docker Space.
2. Ensure the Space README metadata contains `sdk: docker` and `app_port: 7860` (already configured above).
3. Set these Space **Secrets**:
   - `WEB_PASSWORD`: password protecting the noVNC page.
   - `VNC_PASSWORD`: VNC password (at least 6 characters).
   - `APP_API_KEY`: long random token protecting automation APIs.
4. Optional: set `EASYEDA_INSTALLER_URL` to a direct official HTTPS Linux x64 installer URL. The installer is downloaded at container startup; only official EasyEDA domains are accepted. If the official download uses an unsupported package format, install it into `/opt/easyeda-pro` using a compatible build process instead.
5. Attach persistent storage at `/data` if projects and scripts must survive restarts.
6. Start the Space. Open the app home page, then choose **Open noVNC desktop**. Complete EasyEDA activation interactively.

### Local Docker run

```bash
docker build -t easyeda-pro-workbench .
docker run --rm -p 7860:7860 \
  -e WEB_PASSWORD='change-this' \
  -e VNC_PASSWORD='change-this-too' \
  -e APP_API_KEY='replace-with-a-long-random-token' \
  -v easyeda-data:/data easyeda-pro-workbench
```

If using `EASYEDA_INSTALLER_URL`, pass it as an additional environment variable. Never commit secrets to Git.

## Runtime layout

```text
Browser -> HTTPS :7860 (Hugging Face)
  -> Nginx
     -> /             FastAPI :8000
     -> /vnc/         noVNC static files (Basic Auth)
     -> /websockify   WebSocket proxy (Basic Auth)
         -> websockify :6080 -> x11vnc :5900 -> Xvfb :1 + XFCE
                                                    -> EasyEDA Pro
```

## Python API

All `/api/*` endpoints require `X-API-Key: <APP_API_KEY>`.

- `GET /healthz` — liveness and dependency status; does not claim the EDA editor is ready.
- `GET /api/status` — executable discovery.
- `GET /api/cli-help` — EasyEDA CLI help.
- `GET /api/doctor` — local editor bridge status.
- `GET /api/sessions` — list editor sessions.
- `POST /api/open-project` — open a project path under `/data/projects`.
- `POST /api/invoke-script` — run a reviewed JavaScript file from `/data/automation` in a selected editor session.

The invoke endpoint intentionally accepts only a script filename, not arbitrary shell commands or inline code. Scripts execute with EasyEDA editor permissions; only place trusted, reviewed scripts in `/data/automation`. Keep the Space private.

Example:

```bash
curl -H "X-API-Key: $APP_API_KEY" https://YOUR-SPACE.hf.space/api/status
```

## Project storage

- Projects: `/data/projects`
- Reviewed automation scripts: `/data/automation`
- EasyEDA installation: `/opt/easyeda-pro`

Use persistent storage mounted at `/data`. Without it, project data can be lost when the Space restarts or is rebuilt.

## Verification

Run locally:

```bash
python -m compileall -q app scripts
python -m unittest discover -s tests -v
```

GitHub Actions validates Python syntax and unit tests. Docker image build validates container packaging, but does **not** certify the proprietary EasyEDA binary, licensing, GUI rendering, local bridge, design generation, ERC/DRC, or electrical correctness. Those require a real EasyEDA Pro desktop runtime and interactive validation.

## Security

- Prefer a private Hugging Face Space.
- Never commit credentials, installer tokens, customer designs, or private libraries.
- Keep `/data/automation` limited to reviewed JavaScript. EasyEDA's `eda` extension context can have broad editor permissions.
- No arbitrary shell endpoint is exposed.
- VNC is bound to localhost inside the container and is reached through authenticated noVNC.


## Hugging Face source synchronization

The GitHub Actions workflow `.github/workflows/sync-to-hf.yml` mirrors every push to `main` into `Mrlongpro/EasyEDA_Pro_Workbench` using the official `huggingface/hub-sync` action.

Before enabling it:

1. Create a Hugging Face **write** access token with permission to create and write the target Space repository.
2. Add it in GitHub: **Settings → Secrets and variables → Actions → New repository secret**, name it exactly `HF_TOKEN`. Never paste the token into a commit or chat.
3. Add a GitHub Actions repository variable named `HF_SYNC_ENABLED` with value `true` to enable automatic sync. It is intentionally disabled until credentials and Space entitlement are ready.
4. Ensure the Hugging Face account is eligible to create/run a Docker Space. Hugging Face currently documents Docker Spaces as requiring a paid personal plan or an eligible Team/Enterprise account.
5. Run the workflow manually once, or push to `main`; inspect the `Sync to Hugging Face Space` workflow result.

The Space itself must also receive runtime secrets in its **Settings → Variables and secrets**:

- `WEB_PASSWORD`
- `VNC_PASSWORD`
- `APP_API_KEY`
- Optional `EASYEDA_INSTALLER_URL` (HTTPS official EasyEDA download URL)

The GitHub `HF_TOKEN` is only for source synchronization. Do not reuse it as any runtime application password. For project persistence, configure persistent storage mounted at `/data` if available for the selected Space plan/hardware.

A Space repository can be created by the sync action, but this does not grant compute entitlement or guarantee a successful Docker runtime. Validate the Space build and runtime separately after the first sync.
