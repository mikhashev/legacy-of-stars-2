# T5 calibration baseline

`baseline_2a4e0ec.json` is the pre-timelines engine's raw run summaries for the five profiles
`scripts/calibrate_timelines.py` shares with the current engine (`balanced`, `aggressive`,
`cautious`, `integration`, `neglect`). It is what `calibrate_timelines.py --baseline` reads to
print the "measured vs baseline" table, in the shape `{profile: [run summary, ...]}`.

- **Commit:** `2a4e0ec` (`feat(engine): T0 - civilization timelines model (no behaviour change)`
  — the pre-T1 engine: T0 lands the timeline model but old saves and the harness's own
  `ContactProgram(seed=..., offline=True)` behave exactly as before it, so it is the correct
  "before" point for the T1+ drift/receipt-frame changes).
- **Seeds:** 500..529 (30 seeds per profile), matching `calibrate_timelines.py`'s default
  `--seed 500 --runs 30`.
- **Max generation:** 60, matching `calibrate_timelines.py`'s default `--max-gen 60`.
- **Date generated:** 2026-09-03.
- **Produced in:** a detached worktree of `2a4e0ec`
  (`git worktree add --detach <tmp-path> 2a4e0ec`), never committed there. The worktree ran a
  throwaway driver script (`run_baseline.py`, not part of this repo) that calls
  `auto_playtest.run_headless(seed, profile, 60, run_id=i+1)` for each seed/profile and dumps the
  returned summaries as JSON.

## Patch applied to the old harness (worktree only, not committed)

The commit's `scripts/auto_playtest.py` predates the T5 calibration instrument and never recorded
when (or whether) a game got its first reply, so metric (e) — "median generation of the first
successful reply" — had nothing to compare against. The engine at that commit already emits a
`response_received` event (see `emit()` / `stats["responses_received"]` in
`src/legacy_of_stars_v3.py`) and already exposes `drain_events()`; the harness just never drained
it. The patch below is the minimal addition needed to record `first_reply_gen`, mirroring the
field the current `scripts/auto_playtest.py` already produces. It touches nothing else — no
existing field, decision, or strategy weight changed.

```diff
--- a/scripts/auto_playtest.py
+++ b/scripts/auto_playtest.py
@@ class AutoPlayer:
         self.program = ContactProgram(seed=seed, offline=True)
         self.logs = []
+        # T5 baseline patch: the generation of the first successful reply, so the calibration
+        # instrument can compare metric (e) against this pre-timelines engine. Detected from the
+        # "response_received" event this commit's engine already emits (see `emit()` /
+        # `stats["responses_received"]` in src/legacy_of_stars_v3.py); nothing else here reads it.
+        self.first_reply_gen = None

     def log(self, msg: str) -> None:
@@ def run(self) -> dict:
             self.resolve_pending_event()
             self.make_decisions()
             p.advance_generation()
+            for event in p.drain_events():
+                if event.kind == "response_received" and self.first_reply_gen is None:
+                    self.first_reply_gen = p.generation
             if p.generation % 20 == 0:
@@ def summary(self) -> dict:
             "passive_detections": p.stats.get("passive_detections", 0),
             "info_attacks": p.stats.get("info_attacks", 0),
+            "first_reply_gen": self.first_reply_gen,
             "exception": None,
         }
```

## Reproducing it

```
git worktree add --detach <tmp-path> 2a4e0ec
# apply the patch above to <tmp-path>/scripts/auto_playtest.py
# then, from <tmp-path>:
python -c "
import json, sys
sys.path.insert(0, 'scripts')
from auto_playtest import run_headless
out = {}
for profile in ('balanced', 'aggressive', 'cautious', 'integration', 'neglect'):
    out[profile] = [run_headless(500 + i, profile, 60, run_id=i + 1) for i in range(30)]
json.dump(out, open('baseline_2a4e0ec.json', 'w', encoding='utf-8'), indent=1)
"
git worktree remove --force <tmp-path>
git worktree prune
```

All 150 runs (5 profiles x 30 seeds) completed with no exceptions.
