# Changelog

All notable LoopEngineer product changes are recorded by product version.

## 0.4.0 - 2026-06-16

### Added

- Lazy shared channel policy for disabled, declared-forbidden-scope, and active-locking modes.
- Watcher inbox schema, examples, validation, digest support, and summary-first design guidance.
- Watcher automation mode and rotation policy using inbox/digest-first reads and context budget thresholds.
- Coordination cost model and `coordination_tax.py` advisory routing script.
- Loop audit skill and `loop_audit.py` for deterministic checks of common orchestration drift.

### Changed

- Scheduler watcher skill metadata now references the local watcher inbox and rotation policy.
- Script, schema, and skill indexes now include the M5 audit, cost, and watcher policy surface.

### Deprecated

- None.

### Removed

- None.

### Compatibility

- pluginApiVersion: 1
- protocolVersion: 1
- schemaMajorVersion: 1
- skillContractVersion: 1
- adapterContractVersion: 0

## 0.1.0 - 2026-06-15

### Added

- Initial product version file.
- Initial repository metadata file.
- Versioning policy for product, plugin API, protocol, schema, skill contract, and adapter contract boundaries.

### Changed

- None.

### Deprecated

- None.

### Removed

- None.

### Compatibility

- pluginApiVersion: 1
- protocolVersion: 1
- schemaMajorVersion: 1
- skillContractVersion: 1
- adapterContractVersion: 0
