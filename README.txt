# Thread-Safe SQLite Save & Persistence Engine

A lightweight, asynchronous, and thread-safe data persistence system for Python applications. This engine automatically handles database state routing, dynamic schema adjustments, and background auto-saving using SQLite3.

## 📊 System Architecture & Data Flow

This engine isolates database I/O from your main application thread by sitting on top of an active in-memory cache, managed safely via thread locks.

┌────────────────────────────────────────────────────────┐
│               Main Application Thread                  │
└───────────────────────────┬────────────────────────────┘
│ (Registers hooks / queries)
▼
┌────────────────────────────────────────────────────────┐
│          Runtime Lifecycle Hooks (syncHook)            │
└───────────────────────────┬────────────────────────────┘
│ (Mutates memory state)
▼
┌────────────────────────────────────────────────────────┐        ┌──────────────────────┐
│           Active Memory Cache (saves registry)         │ ◄────  │  Background Worker   │
└───────────────────────────┬────────────────────────────┘        │    (Daemon Thread)   │
│                                     └──────────┬───────────┘
│ (Thread Lock: db_lock)                         │ (Ticks every 1s)
▼                                                │ (Loads: every 10s)
┌────────────────────────────────────────────────────────┐                   │ (Saves: every 5s)
│                SQLite Engine (database.db)             │ ◄─────────────────┘
└────────────────────────────────────────────────────────┘

### 🔁 Thread Cycle Timeline

The background daemon thread ticks continuously to ensure minimal data loss while preventing write saturation:

| Time Elapsed | Action Block | Process Description |
| :--- | :--- | :--- |
| **Every 1 Second** | `time.sleep(1)` | Sleep interval to prevent CPU spiking. |
| **Every 5 Seconds** | `with db_lock: save()` | Commits active in-memory payloads down to `database.db`. |
| **Every 10 Seconds** | `with db_lock: load()` | Pulls latest database changes into memory cache. |

---

## ✨ Features

- **🔄 Automated Asynchronous Sync:** Runs a background daemon thread that automatically reads updates and commits saves without blocking your main application loop.
- **🧵 Thread-Safe Operations:** Utilises threading locks (`db_lock`) to prevent database collisions and race conditions between automated loops and manual database calls.
- **🏗️ Dynamic Schema Generation (`ensureTable`):** Automatically maps Python data types to SQLite equivalents. If a table or new data column does not exist at runtime, the engine builds or alters the table on the fly.
- **🪝 Runtime Lifecycle Hooks (`syncHook`):** Sync custom callback functions seamlessly. Register your own load and save handlers to automatically format data packets during cycles.
- **🧹 Auto-Clean Sequence:** Complete database management including safe table deletions (`DROP TABLE`) that clear both physical disk footprints and system runtime memory.
- **🪲 Debugger-Ready:** Fully wrapped with telemetry debug decorators to effortlessly trace operations, loads, and errors.

---

## 🛠️ Data Type Mappings

When writing raw rows directly from dictionaries or tracking arrays, Python types are safely transformed to their SQL counterparts:

* `bool` ──► **NUMERIC**
* `int` ──► **INTEGER**
* `float` ──► **REAL**
* `str` / Other ──► **TEXT**