# 1. Introduction

## 1.1 Project Structure

- `main.py` - startup entrypoint
- `core/` - shared systems (bot setup, settings, checks, logging, loader, UI, error handling)
- `cogs/admin/` - owner/admin commands
- `cogs/features/` - user-facing features
- `db/` - SQLite files
- `data/` - JSON settings/blacklist/media list
- `logs/` - rotating runtime logs
- `unused_cogs/` - parked features not loaded by default

# 2. Features / Cogs

## 2.1 Quotes

This cog lets users:

- Save memorable messages
- Replay random quotes
- List quotes per person
- See top-used quotes
- Delete quotes via interactive buttons (with permissions)

### 2.1.1 Architecture

Cog destination: `cogs/features/quotes_record/`

```text
quotes_record
├── __init__.py
├── cog.py       -> commands/user flow
├── db.py        -> SQLite data layer
├── helpers.py   -> validation + webhook mimic sending
└── views.py     -> pagination/delete UI
```

### 2.1.2 Commands

- `save` - save a replied message as quote
- `9up` - fetch random quote (optional member/alias target)
- `9uplist` - paginated quote list for a member/alias
- `9uptop` - top used quotes (global or per member/alias)
- `9updel` - interactive quote delete menu

## 2.2 Alias

This cog lets people create short text aliases (like `miko`, `boss`) that resolve to real members.
Those aliases are used by other features like quotes (`9up`, `9uplist`, etc.) via shared converter.

### 2.2.1 Architecture

Cog destination: `cogs/features/alias/`

```text
alias
├── __init__.py
└── cog.py       -> commands/user flow
```

### 2.2.2 Commands

- `alias` - create alias for a member
- `unalias` - remove alias mapping
- `listalias` - list aliases for a member

## 2.3 DLLM

This cog loads a curated list of URLs from `data/dllm_links.json`, then posts one random entry when called.

### 2.3.1 Architecture

Cog destination: `cogs/features/dllm.py`

### 2.3.2 Commands

- `dllm` - send random media link
- `sticker` - alias of `dllm`
- `gif` - alias of `dllm`
- `reload_dllm` *(owner-only, hidden)* - reload media list from disk

## 2.4 Management (Admin)

This cog is the owner control panel for runtime operations.

### 2.4.1 Architecture

Cog destination: `cogs/admin/management.py`

### 2.4.2 Commands *(owner-only, hidden)*

- `reload` - reload extension module
- `load` - load extension module
- `unload` - unload extension module
- `listcogs` - list currently loaded extensions
- `setprefix` - set server command prefix
- `logs` - show recent bot log lines

## 2.5 Blacklist (Admin)

This cog manages per-user command restrictions.

### 2.5.1 Architecture

Cog destination: `cogs/admin/blacklist.py`

### 2.5.2 Commands *(owner-only, hidden)*

- `blacklist` - block user from one command or `all`
- `unblacklist` - remove block entry
- `viewblacklist` - view current server blacklist entries

## 2.6 Health (Admin)

This cog reports runtime/system diagnostics (latency, uptime, RAM, CPU, disk).

### 2.6.1 Architecture

Cog destination: `cogs/admin/health.py`

### 2.6.2 Commands *(owner-only, hidden)*

- `health`

## 2.7 Error Handler (Core Extension)

This extension centralizes command error handling and sends cleaner embeds for common failures.

### 2.7.1 Architecture

Extension destination: `core/error_handler.py`

## 2.8 CCTV (Parked)

This is a parked feature and is not loaded by default.

### 2.8.1 Architecture

Cog destination: `unused_cogs/cctv/`

```text
cctv
├── __init__.py
├── cog.py       -> command flow (`cctv`)
└── capture.py   -> stream search + frame capture
```

### 2.8.2 Commands

- `cctv` *(parked, not active unless re-enabled)*

# 3. Operations

## 3.1 Environment variables

Expected keys in `.env`:

- `BOT_TOKEN`
- `OWNER_ID`
- `ADMIN_ROLE_NAME`

Template is in `.env.example`.

## 3.2 Run locally

From repo root (`ymd-ryo/`):

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt

# Starts the bot
python main.py
```

## 3.3 Run with docker and run locally

From `/Users/neoto/Documents/playground/rmd-ryo`:

```bash
# Build a docker iamge and tag it as local
docker build -t ymd-ryo:local ./ymd-ryo

# Force remove old container if it exists
docker rm -f ymd-ryo-local 2>/dev/null || true

# Start a new container in detached mode
docker run -d \
  --name ymd-ryo-local \
  --restart unless-stopped \
  --env-file "./bot-staging/.env" \
  -v "$(pwd)/bot-staging/db:/app/db" \
  -v "$(pwd)/bot-staging/logs:/app/logs" \
  -v "$(pwd)/bot-staging/data:/app/data" \
  ymd-ryo:local

# Output logs
docker logs -f ymd-ryo-local
```

## 3.4 Data and persistence

- Quotes database: `db/quotes.db`
- Alias database: `db/aliases.db`
- DLLM media links file: `data/dllm_links.json`
- Blacklist file: `data/blacklist.json`
- Server settings file: `data/server_settings.json`
- Logs file: `logs/discord.log`

Back up `db/`, `data/`, and `logs/` before risky changes.

## 3.5 Quick sanity test after boot

1. Run `!health` (owner) to confirm process is healthy.
2. Run `!listcogs` (owner) to verify features are loaded.
3. Save one quote by replying to a message with `!save`.
4. Retrieve with `!9up`.
5. Confirm logs update in `logs/discord.log`.


## 3.6 Notes to future me

- `unused_cogs/cctv` is parked and not part of normal runtime.
- If re-enabling CCTV, check extra dependencies and Docker comments first.

