# AGENTS.md

Single-utility repo: an FTP server (pyftpdlib) sharing a user-chosen folder on the LAN, for LAN/iPhone access. Source is `server.py`; `build.bat` / `build.ps1` produce a dependency-free single-file `dist\FTPServer.exe` via PyInstaller (end users need only Windows x64 — no Python). Two modes chosen interactively after picking the folder: **1 = read-only** (username `read`, perms `elr`) and **2 = read-write** (username `write`, full perms `elradfmwMT`). There is no `FTP.ps1` anymore — do not recreate it.

## Layout

- `server.py` — the whole application (interactive first run, `--launch` parameter mode, FTP server, firewall, launcher generation).
- `build.ps1` — one-click build (checks/installs pyftpdlib + pyinstaller, runs PyInstaller `--onefile`, cleans `build_tmp`). Only the build machine needs Python.
- `build.bat` — double-click wrapper around `build.ps1` (for users who can't run .ps1 directly).
- `dist\FTPServer.exe` — build artifact, gitignore-style build output; safe to delete and rebuild.

## Gotchas

- **All configuration flows through CLI args** (`--launch --lang --share --mode --user --pass --port --passive-start --passive-end`). The FTP code must not hardcode any of them. Defaults: port 2121, passive 60000–60100, mode read.
- **UI language is bilingual (zh / en)**: without `--lang`, the very first interaction is a language menu (printed bilingually) BEFORE the share prompt; `STRINGS` in `server.py` holds all user-facing text — never print raw strings, always go through `t(key, ...)`. The generated `start.bat` bakes in `--lang <zh|en>` so relaunching keeps the language. Firewall rule names are system-level identifiers and intentionally stay Chinese regardless of UI language (avoiding duplicate rules across languages).
- **Launcher file is `start.bat`** (fixed name, any language) and is generated AFTER a successful server bind, in the exe's own directory (`app_dir()`), with the exact working args baked in. If the exe dir is not writable it falls back to the data dir. Do not write it before binding (a failed run must not persist broken args).
- **Launcher invocation is dual-path**: the bat prefers the machine-local exe ABSOLUTE path (so the bat can be moved anywhere on the same machine and still start), with an `if exist ... else` fallback to `%~dp0` relative path (works when the whole folder — exe + bat — moves together). The args must be fully repeated inside BOTH branches (cmd if/else parenthesization). Paths are always read at runtime from `sys.executable` / `__file__` — never store any machine-specific absolute path in the repo.
- **Launcher generation keeps old configs**: if an existing `start.bat` has identical content, it is left untouched; if the config changed, the old file is first renamed to `start_1.bat`, `start_2.bat`, ... (lowest free index) and only then the new `start.bat` is written — never overwrite.
- **Data directory fallback chain**: `$TEMP` → create if missing → fall back to the program directory if Temp is unusable (write probe). Log (`ftp_server.log`) and password (`ftp_pass.txt`) live there — no share-path config file exists.
- **No share path is ever persisted by the program itself**: no `ftp_share.txt`, no config file with the path. The chosen path lives ONLY inside the generated `start.bat` args (and the Temp log). On interactive first runs the user always drags the folder again — no "last used" prompt.
- **Password is generated once on first run**: random 16 chars (confusable 0/O/1/l/I excluded), plaintext in `ftp_pass.txt` (data dir), reused forever. Deleting the file regenerates it. No hardcoded password anywhere.
- **Read-only vs read-write is enforced by the authorizer perm string**: read-only `perm="elr"` (list + download), read-write `perm="elradfmwMT"` (full). Usernames are tied to the mode (`read` / `write`) — the old `phone` username must not come back. Do not loosen `elr`.
- **Share permissions are probed before starting** (read probe = `os.listdir`; write probe = create+delete a temp file). Read failure always exits; write failure exits only in read-write mode.
- **Command port auto-detection**: if the requested port is busy, a random free port in 10000–65535 (excluding the passive range) is picked; the picked port is what gets baked into the launcher and banner.
- **Firewall auto-config on first run**: rules named `FTP 只读共享` / `FTP 读写共享` (+ ` - 被动端口`) are checked via `netsh` and created if missing — directly when admin, else via a UAC-elevated temp .bat (written in `mbcs` encoding so Chinese rule names survive cmd). Failure degrades to a warning, never blocks startup.
- The exe is a console app (`server.py` has no GUI); all interaction is stdin/stdout. Console output text comes from the `STRINGS` table in Chinese source comments, but displayed text follows the selected language.
- To verify changes: run `build.ps1`, launch `dist\FTPServer.exe` with test args (`--launch --lang en --share ... --mode read|write --user ... --pass ... --port 2199 --passive-start 61000 --passive-end 61100`), confirm the UI prints in the chosen language, confirm via a raw socket login (banner `220 FTP (read-only)` / `(read-write)`) that mode-1 upload gets 550 and mode-2 upload succeeds, and that `dist\start.bat` is generated with those exact args.
