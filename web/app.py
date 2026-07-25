"""FastAPI surface for the web generator.

Same rule as everywhere else: this file imports cff.core and adapts it to
HTTP. No framework logic lives here. The front end is a static page in
web/static that calls two endpoints:

    POST /api/generate   answers in  -> findings + base64 zip out
    POST /api/subscribe  email in    -> sample chapter send (via ESP)

Run locally:  uvicorn web.app:app --reload
"""

from __future__ import annotations

import base64
import io
import os
import re
import zipfile
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cff.core.generate import MANIFEST_PATH, generate
from cff.core.schema import load_spec
from cff.core.validate import validate

STATIC = Path(__file__).parent / "static"
ESP_ENDPOINT = os.environ.get("ESP_ENDPOINT", "")
ESP_KEY = os.environ.get("ESP_KEY", "")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

app = FastAPI(title="cff-web", docs_url=None, redoc_url=None)


class GenerateRequest(BaseModel):
    answers: dict[str, Any]


class SubscribeRequest(BaseModel):
    email: str


@app.get("/api/spec")
def spec() -> JSONResponse:
    """The seven questions, so the page renders from the same source of truth."""
    s = load_spec()
    return JSONResponse(
        {
            "layers": [
                {
                    "id": l.id,
                    "order": l.order,
                    "name": l.name,
                    "prompt": l.prompt,
                    "good_example": l.good_example,
                    "hint": l.hint,
                    "fields": [
                        {"id": f.id, "label": f.label, "required": f.required}
                        for f in l.fields
                    ],
                }
                for l in s.layers
            ]
        }
    )


@app.post("/api/generate")
def api_generate(req: GenerateRequest) -> JSONResponse:
    if not any(
        str(v).strip()
        for bucket in req.answers.values()
        if isinstance(bucket, dict)
        for v in bucket.values()
    ) and not any(isinstance(v, str) and v.strip() for v in req.answers.values()):
        return JSONResponse(
            {"error": "Fill in at least the first question and try again."},
            status_code=422,
        )

    files = generate(req.answers)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)

    findings = validate(files)
    solid = [
        l.name
        for l in load_spec().layers
        if not any(f.layer == l.id for f in findings)
    ]
    return JSONResponse(
        {
            "files": sorted(n for n in files if n != MANIFEST_PATH),
            "solid": solid,
            "findings": [f.as_dict() for f in findings],
            "zip_b64": base64.b64encode(buffer.getvalue()).decode(),
        }
    )


@app.post("/api/subscribe")
def api_subscribe(req: SubscribeRequest) -> JSONResponse:
    email = req.email.strip()
    if not EMAIL_RE.match(email):
        return JSONResponse(
            {"error": "That doesn't look like an email address."}, status_code=422
        )
    if not (ESP_ENDPOINT and ESP_KEY):
        print(f"[no ESP configured] would subscribe: {email}")
        return JSONResponse({"ok": True})
    try:
        requests.post(
            ESP_ENDPOINT,
            json={"email": email, "tags": ["web-generator"]},
            headers={"Authorization": f"Bearer {ESP_KEY}"},
            timeout=10,
        ).raise_for_status()
    except Exception:
        return JSONResponse(
            {"error": "Something went wrong on our end. Try again in a minute."},
            status_code=502,
        )
    return JSONResponse({"ok": True})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/", StaticFiles(directory=STATIC), name="static")
