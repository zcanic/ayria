# Eval Results

This directory is the intended storage target for saved eval run artifacts.

Recommended naming:

- `results/<scenario_id>/<timestamp>__<short_commit>.json`

Do not commit large volumes of generated result files by default.

Keep committed examples small and intentional:

- one baseline result per meaningful milestone
- one failure example if it teaches something important

For normal daily runs, treat this directory as an artifact output target rather
than as a source directory.
