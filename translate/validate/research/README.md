# Research / calibration CLIs

Scripts here (golden pairs, mutation recall, lite builds, style FP audit)
calibrate markers and offline metrics. **Not** on the publish conveyor.

Publish path: `translate/steps/*` + `make lt` + `make style` / `make quality` +
`make polish`.

```bash
PYTHONPATH=. python3 -m translate.validate.research.<module> --help
```
