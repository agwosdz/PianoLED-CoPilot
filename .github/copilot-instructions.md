## Copilot instructions for this repository

Be concise. Focus changes on the files listed below and follow the project's run/test/deploy workflows.

- Big picture (two main parts):
  - backend/ — Python Flask + Flask-SocketIO server (eventlet). Key file: `backend/app.py`.
    - Uses eventlet and calls `eventlet.monkey_patch()` before Flask/socket imports. Keep this ordering when editing.
    - Real-time flows use `socketio.emit(...)` and `socketio.start_background_task(...)` (avoid blocking the eventlet loop).
    - Settings persist in SQLite at `backend/settings.db` via `backend/services/settings_service.py`.
    - Hardware integrations (LED, USB MIDI, rtpMIDI) are optional: imports guarded by try/except (e.g. `led_controller`, `USBMIDIInputService`). Maintain that pattern so code runs in CI/headless environments.
  - frontend/ — Svelte (SvelteKit) app. Build output is served from `frontend/build` in production (see `scripts/deploy-to-pi.ps1` nginx config).

- Developer workflows / commands (concrete):
  - Local dev (both): `npm run dev` (root). This runs `dev:backend` (calls `backend/start.py`) and `dev:frontend`.
  - Backend only: `cd backend && python start.py` (or use the dev script). Backend tests: `cd backend && python -m pytest`.
  - Frontend build: `cd frontend && npm run build` (root `package.json` has `build:frontend`).
  - Full install: `npm run install:all` will run `npm install` and `pip install -r backend/requirements.txt`.
  - Deploy to Raspberry Pi: `.
    scripts\deploy-to-pi.ps1 <pi-ip> <backend-port>` (PowerShell). The script clones the repo, sets up a venv, builds frontend and creates a systemd service.

- Project-specific patterns and conventions (important for edits):
  - Non-fatal hardware detection: many modules are optional — preserve try/except import patterns so tests and CI can run without hardware.
  - Settings are canonicalized via `SettingsService` in `backend/services/settings_service.py`. Use `settings_service.set_setting(category, key, value)` to persist and broadcast changes; do not write directly to `settings.db`.
  - Configuration lives in `backend/config.json` and is wrapped by `backend/config.py` functions (validation, backup/restore). Prefer using those helpers for config changes.
  - Socket event names and payload shapes are stable and used by frontend tests: `playback_status`, `live_midi_event`, `led_test_result`, `settings:update`, `settings:bulk_update`, `settings:reset`. Keep payload keys consistent.
  - When adding endpoints, register them as blueprints under `api/` (see `app.register_blueprint(settings_bp, url_prefix='/api/settings')`).

- Integration points / external dependencies to be aware of:
  - eventlet + flask-socketio (async_mode='eventlet') — do not change async_mode without testing full integration.
  - USB MIDI and rtpMIDI services (files: `backend/usb_midi_service.py`, `backend/rtpmidi_service.py`, `backend/midi_input_manager.py`). They expose unified device lists and events consumed by the app.
  - LED hardware code: `backend/led_controller.py`, `backend/led_effects_manager.py`, `backend/simple_led_test.py` — changes here must maintain no-op/headless behavior when hardware is missing.

- Concrete examples to follow when making edits:
  - Persist + notify a setting change:
    - Use SettingsService: `settings_service.set_setting('led', 'led_count', 246)` — this will write to DB and emit `settings:update`.
  - Emit a websocket playback update from PlaybackService:
    - `socketio.emit('playback_status', { 'state': status.state.value, 'current_time': status.current_time, ... })`.
  - Start background LED task without blocking:
    - `socketio.start_background_task(my_task, args...)` or `socketio.sleep()` inside loops instead of time.sleep().

- Tests & safe edits:
  - CI/tests run backend pytest and frontend tests (`npm run test` at root). Many tests rely on default behavior when hardware services are unavailable — do not change fallbacks that return default status objects.

If a section is unclear or you'd like more detail (for example: specific endpoint payload examples, common test failures, or where to run a quick smoke test), tell me which area and I'll expand the instructions. 
