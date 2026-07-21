# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`coopprodsystem` is a **production-system simulation library** (published to PyPI as `coopprodsystem`). It models factory-style production: resource-consuming/producing `Station`s wired into a `ProductionLine` graph, with expertise-based production-speed scaling and an internal event bus. It is a standalone package — nothing in this repo depends on any specific game or app; `coopgame`'s `examples/voroni_world` is one prospective consumer (see its `specs/open/resource-system.md`).

## Architecture

- **`Station`** (`coopprodsystem/factory/station.py`) — the core unit. Has `input_reqs`/`output` (each a `StationResourceDefinition`: a `ContainerContent` + storage capacity), consumes inputs and produces outputs on a timer (`production_timer_sec_callback`), and speeds up over time via an `ExpertiseSchedule` (from `cooptools.expertise.expertiseSchedules` — `ByRunsExpertiseSchedule`/`ByTimeExpertiseSchedule`).
- **Input/output storage**: each `Station` builds one `coopstorage.storage.loc_load.storage.Storage` for input and one for output. Internally, each `StationResourceDefinition` gets its own dedicated `Location` (capacity 1) holding exactly one pre-placed `Container`, whose `uom_capacities` encodes that slot's capacity and whose `resource_qualifier` restricts it to that one resource. `Station` mutates content via the direct `Storage.add_content_to_container_at_location`/`remove_content_from_container_at_location` calls — **not** the `TransferRequestCriteria`/reservation pipeline `coopstorage` is otherwise built around. That pipeline is for multi-actor contention over shared storage; a `Station`'s own input/output slots have exactly one actor (the station itself), so the direct calls are sufficient and much less ceremony. Revisit this choice only if something *other* than the owning `Station` needs to reach into its storage.
- **`ProductionLine`** (`coopprodsystem/factory/productionLine.py`) — a graph (via `coopgraph.graphs.Graph`) of `Station`s with directed relationships. Automatically creates `StationTransfer`s to move content from a feeder station's output to a downstream station's input once capacity allows.
- **`StationTransfer`** (`stationTransfer.py`) — an in-flight content transfer between two stations, gated by a `TimedDecay` timer.
- **Events** (`coopprodsystem/events/`) — internal event dispatch (`eventDefinition.py`, via `pubsub`) for station-added, production-started/finished, transfer-started/completed.
- **Driving model**: `Station`/`ProductionLine` drive themselves via **wall-clock `time.perf_counter()`**, either through their own background thread (`start_async()` → `cooptools.coopthreading.AsyncWorker`) or by repeatedly calling `.update(time_perf)` manually. There is **no delta_ms/game-tick integration** — a consumer with its own tick loop (e.g. a game) must call `.update()` every frame and pass real wall time, not scaled/game time.
- **Resource/UoM identity**: `Resource`/`UnitOfMeasure` (from `coopstorage.storage.loc_load.dcs`) are `BaseIdentifiedDataClass`es — equality and hashing are by an auto-generated `id`, **not** by field values. Two separately-constructed `Resource(name='wood')` calls are *not* equal. Always define each `Resource`/`UnitOfMeasure` **once** as a shared instance (see `tests/sku_manifest.py`/`uom_manifest.py`) and pass that same object everywhere — never reconstruct one from a name string expecting it to compare equal to an existing one.

## Migrated to `coopstorage`'s `storage/loc_load` architecture (2026-07-21)

This package previously depended on `coopstorage.my_dataclasses`/`coopstorage.storage` (the flat `Content`/`ResourceUoM`/`StorageState` model from `coopstorage` 0.1–0.4). `coopstorage` has since done a full rewrite — `Location`s now hold `Container`s (channel-slotted), a `Container` holds `ContainerContent(resource, uom, qty)` and owns its own capacity, `ResourceUoM` as a combined type is gone (inventory keys are now bare `Tuple[Resource, UnitOfMeasure]`), and the primary API is a `TransferRequestCriteria`/reservation pipeline built for multi-actor/distributed storage (mongo/postgres/sqlite-backed data stores, pluggable reservation providers). The old `my_dataclasses`/`storage`(flat)/`storage2` modules are gone entirely from current `coopstorage` — there was no way to keep using them.

Everything in `coopprodsystem/factory/` (`station.py`, `stationResourceDefinition.py`, `stationTransfer.py`, `productionLine.py`) and the test fixtures (`tests/*_manifest.py`) were rewritten against the new API, using the direct-manipulation calls rather than the full transfer-request/reservation machinery (see Architecture above for why). `requirements.txt`/`setup.py` were also cleaned up — `coopgraph`/`coopstorage`/`cooptools`/`Pypubsub` are the *only* things this package's own code actually imports; the old pinned `matplotlib==3.4.3`/`pandas`/`numpy`/`Pillow`/etc. were never referenced anywhere in `coopprodsystem` itself (confirmed by grepping every import in the package) and were dropped — they were almost certainly copy-pasted into this `requirements.txt` from elsewhere. `coopstorage`/`cooptools` are now pinned as lower bounds (`>=`), not exact pins — exact pins are what caused this drift to go unnoticed for so long.

**If you're touching `station.py`'s storage code**, know that `coopstorage.storage.loc_load.data/__init__.py` unconditionally imports its `postgres` submodule (pulling in `sqlalchemy`, `pydantic`) even though `Station` only ever uses the default in-memory `StorageDataStore()`. This means `import coopprodsystem` transitively requires `sqlalchemy` + `pydantic` to be installed even though nothing in this package touches a real database — that's an eager-import cost in `coopstorage`, not something fixable here.

## Tests

`tests/` has `unittest`-style tests (`test_station.py`, `test_prodline.py`) plus fixture manifests (`station_manifest.py`, `sku_manifest.py`, `uom_manifest.py`). Run from the repo root (not from inside `tests/`, since `station_manifest.py` imports `tests.sku_manifest` as an absolute package import):

```bash
python -m unittest discover -s tests
```

As of 2026-07-21: all 3 pass. Also verified with a standalone functional smoke test (production run to capacity → expertise scaling → `FULL` status → `remove_output` draining storage) outside the test suite.

## Dependencies worth knowing

`coopgraph`, `coopstorage>=1.24`, `cooptools>=1.69`, `Pypubsub` (companion packages, source in sibling `PycharmProjects/` dirs, same author) — these are the actual, verified direct dependencies; see the migration note above for why the old `requirements.txt` had much more than this.
