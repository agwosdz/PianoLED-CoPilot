Project: Piano LED Visualizer — guidance for AI coding agents

Be brief and actionable. Focus changes to the Python backend unless the change explicitly touches the frontend.

Architecture (big picture)
- Backend: `backend/app.py` is the Flask + SocketIO entrypoint. It initializes the `SettingsService`, `LEDController`, `LEDEffectsManager`, MIDI services and exposes REST and WebSocket endpoints.
- Settings: `backend/services/settings_service.py` stores settings in SQLite (`settings.db`) and is the canonical source of truth. Use its API to read/update configuration (category/key).
- Hardware: `backend/led_controller.py` wraps rpi_ws281x and runs in simulation mode when hardware libs are missing. Respect `led.enabled` and `led_count` from settings.
- MIDI: `backend/midi_input_manager.py` unifies USB and rtpMIDI inputs. USB and rtp services live alongside but are optional (import guarded).

Key integration points and patterns
- Web API <> services: `app.py` registers blueprints under `/api/*`. For settings use `/api/settings` which delegates to `SettingsService` (see `backend/api/settings.py`).
- WebSockets: `socketio.emit` is the standard method for broadcasting events. Many services accept a `websocket_callback` param (pass `socketio.emit`).
- Hardware-optional imports: many modules import hardware drivers inside try/except and fall back to simulation. When adding features, follow this pattern so code runs on dev machines.
- Config vs Settings: `backend/config.py` provides file-based validation & helpers. `SettingsService` is the runtime DB-backed settings store. Prefer `SettingsService` for runtime changes; use `config.py` helpers for validation and generation utilities.

Developer workflows & commands
- Run backend locally (dev mode): set FLASK_DEBUG=true then run `python -m backend.app` (or run `backend/app.py` directly). The app uses eventlet — don't switch async modes without testing WebSocket behavior.
- Tests: backend tests under `backend/tests` and `tests/` (unit + integration). Run usual pytest in repo root. Many tests assume hardware libs missing — CI/simulated environment is used.
- Deploy to Pi: see `scripts/deploy-to-pi.ps1` / `.sh`. The stack expects Python packages from `backend/requirements.txt` — install those on the target.

Project-specific conventions
- Settings schema: settings are grouped by category (e.g., `led`, `piano`, `gpio`). Use `SettingsService.get_setting(category, key)` and `set_setting(category, key, value)`; `get_all_settings()` returns merged defaults.
- Brightness scale: settings and APIs accept 0.0–1.0 internally; some API endpoints accept 0–100 legacy values — normalize in endpoints (see `backend/api/settings.py` `_normalize_settings_payload`).
- LED indexing: logical indices are 0-based. `LEDController` maps to physical indices based on `led_orientation` (normal/reversed) via `_map_led_index`.
- Error handling: endpoints return JSON errors; logs use module-level loggers. Avoid raising raw exceptions from API handlers — return JSON with status codes instead.

Concrete examples to follow
- To broadcast playback status from a service: call `socketio.emit('playback_status', data)` or pass `websocket_callback=socketio.emit` to service constructors (see `app.py` initialization of `SettingsService` and `USBMIDIInputService`).
- To add a new settings key: update `_get_default_settings_schema` in `backend/services/settings_service.py`, then use `settings_service.set_setting('category','key', value)`. Tests rely on defaults being seeded on service init.
- To add a new API route that triggers LED action: call `led_controller.turn_on_led(index, (r,g,b), auto_show=True)` and use `socketio.start_background_task` for long-running effects.

Testing & quality gates
- Many CI tests run without real hardware. Follow the simulation patterns (guard hardware imports). Verify changes by running unit tests (`pytest`) and running `backend/app.py` locally.

Files to inspect when changing behavior
- `backend/app.py` — routes, service wiring, and WebSocket events
- `backend/services/settings_service.py` — settings schema, DB, broadcasting
- `backend/led_controller.py` — hardware integration and simulation
- `backend/midi_input_manager.py` — unified MIDI event flow and duplicate filtering
- `backend/config.py` — validation helpers, mapping generation, export/import

If something is unclear
- Ask for which environment to target (Raspberry Pi with rpi_ws281x or local dev). Note whether changes should run without hardware.

End of instructions.
