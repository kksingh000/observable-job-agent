"""Single-port entrypoint for platforms that route one public port per
service (e.g. Render). Locally, `make app` (job_scout.app.main()) runs the
wizard and the Jobvis API as two servers on two ports -- fine when you own
both ports. A PaaS web service only exposes one, so this module mounts BOTH
surfaces onto the same FastAPI app instead. They still share the same
in-process checkpoint and voice bridge that makes them one session (see
job_scout.app.main()'s docstring) -- just reachable over one port instead of
two.

    /            the built Jobvis console (or "API only" if web/out is absent)
    /api/*       the Jobvis API -- voice token, tools, state, SSE, downloads
    /wizard      the Gradio four-step wizard

Run with: uvicorn job_scout.render_entry:app --host 0.0.0.0 --port $PORT

Local development is unaffected -- `make app` still runs job_scout.app.main()
exactly as documented in the README. This module only exists for a
single-port PaaS deploy.
"""

from __future__ import annotations

import gradio as gr
from starlette.routing import Mount

from job_scout.api import create_app
from job_scout.app import build_app

_api_app = create_app()

# create_app() mounts the built console (or nothing, if web/out wasn't built)
# as a catch-all at "/". Starlette checks mounts in the order they were
# added, so a catch-all already sitting at "/" would swallow "/wizard" --
# pull it out, mount the wizard, then put the catch-all back last.
_console_mount = next(
    (route for route in _api_app.router.routes if isinstance(route, Mount) and route.path in ("", "/")),
    None,
)
if _console_mount is not None:
    _api_app.router.routes.remove(_console_mount)

app = gr.mount_gradio_app(_api_app, build_app(), path="/wizard")

if _console_mount is not None:
    app.router.routes.append(_console_mount)
