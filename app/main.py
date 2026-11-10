import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(os.getenv("PROJECTS_DIR", "/data/projects")).resolve()
AUTOMATION_ROOT = Path(os.getenv("AUTOMATION_DIR", "/data/automation")).resolve()
API_KEY = os.getenv("APP_API_KEY", "")

app = FastAPI(title="EasyEDA Pro Python Workbench", version="0.2.0")


class OpenProjectRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=500)


class InvokeScriptRequest(BaseModel):
    session: str = Field(..., min_length=1, max_length=128)
    script: str = Field(..., min_length=1, max_length=120)


def require_key(value: Optional[str]) -> None:
    if not API_KEY:
        raise HTTPException(status_code=503, detail="APP_API_KEY is not configured")
    if value is None or value != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def resolve_inside(root: Path, raw: str, *, must_exist: bool = True) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if resolved != root and root not in resolved.parents:
        raise HTTPException(status_code=400, detail=f"Path must stay inside {root}")
    if must_exist and not resolved.exists():
        raise HTTPException(status_code=404, detail="Path does not exist")
    return resolved


def cli_binary() -> Optional[str]:
    return shutil.which("easyeda-pro") or shutil.which("lceda-pro")


def run_cli(args: list[str], timeout: int = 30) -> dict:
    binary = cli_binary()
    if not binary:
        raise HTTPException(status_code=503, detail="EasyEDA Pro CLI executable not found")
    try:
        proc = subprocess.run(
            [binary, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "DISPLAY": os.getenv("DISPLAY", ":1")},
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="EasyEDA CLI timed out")
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-16000:],
        "stderr": proc.stderr[-16000:],
    }


@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>EasyEDA Pro Workbench</title>
<style>
body{font:16px system-ui;background:#101827;color:#e5edf7;margin:3rem}
a{color:#75c7ff}.card{padding:1rem;background:#1d2a3d;border-radius:12px;margin:1rem 0}
</style></head><body>
<h1>EasyEDA Pro Python Workbench</h1>
<div class="card">Python API and remote desktop gateway are running.</div>
<p><a href="/vnc/vnc.html?autoconnect=true&resize=remote&path=websockify">Open noVNC desktop</a></p>
<p><a href="/healthz">Health check</a></p>
</body></html>"""


@app.get("/healthz")
def health():
    binary = cli_binary()
    return {
        "status": "ok",
        "api": "up",
        "easyeda_binary_found": bool(binary),
        "easyeda_binary": binary,
        "projects_dir_exists": PROJECT_ROOT.exists(),
        "projects_dir_writable": os.access(PROJECT_ROOT, os.W_OK),
        "automation_dir_exists": AUTOMATION_ROOT.exists(),
        "note": "Liveness only; this does not prove editor GUI, activation, or CLI bridge readiness.",
    }


@app.get("/api/status")
def status(x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)
    return {"installed": bool(cli_binary()), "binary": cli_binary()}


@app.get("/api/cli-help")
def cli_help(x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)
    return run_cli(["--help"])


@app.get("/api/doctor")
def doctor(x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)
    return run_cli(["doctor"])


@app.get("/api/sessions")
def sessions(x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)
    return run_cli(["session", "list"])


@app.post("/api/open-project")
def open_project(body: OpenProjectRequest, x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)
    project = resolve_inside(PROJECT_ROOT, body.path)
    if not project.is_dir():
        raise HTTPException(status_code=400, detail="Project path must be an .eprj3 project directory")
    if project.suffix.lower() not in {".eprj3", ".eprj2", ".eprj"}:
        raise HTTPException(status_code=400, detail="Expected an EasyEDA project directory (.eprj3/.eprj2/.eprj)")
    return {"project": str(project), **run_cli(["open", "--path", str(project)], timeout=90)}


@app.post("/api/invoke-script")
def invoke_script(body: InvokeScriptRequest, x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.js", body.script):
        raise HTTPException(status_code=400, detail="script must be a simple .js filename")
    script_path = resolve_inside(AUTOMATION_ROOT, body.script)
    if not script_path.is_file():
        raise HTTPException(status_code=404, detail="Automation script not found")
    if script_path.stat().st_size > 64 * 1024:
        raise HTTPException(status_code=413, detail="Automation script exceeds 64 KiB")
    code = script_path.read_text(encoding="utf-8")
    # Script content is passed as a single argv item; it is never interpreted by a shell.
    return run_cli(
        ["invoke", "--session", body.session, "--ext-uuid", "eda", "--code", code],
        timeout=120,
    )
