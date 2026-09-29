# Validation research (not required to publish)

Scripts here (golden pairs, mutation recall, QE noise, blind judges, lite
builds) calibrate optional quality passes. They are **not** part of
`make wave` or the digest → translate → assemble → verify publish spine.

Publish-adjacent tools stay in the parent package:

- `factcheck.py`, `plainness.py`, `judge.py`
- `qe_config.json` (path used by `tools/pipeline/qe.py`)

Run examples after the move:

```bash
python3 -m tools.validate.research.qe_noise …
python3 tools/validate/research/style_fp_audit.py …
```
