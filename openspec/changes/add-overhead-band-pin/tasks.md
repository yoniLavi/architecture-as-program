# Tasks

> Backfilled after implementation; every item was completed in `6f37391` and the
> commit that follows it. Recorded so the specs have an account of the change.

## 1. The overhead band

- [x] 1.1 Add `CROSSING_BAND_MIN_MS` / `CROSSING_BAND_MAX_MS` and `check_overhead()`
      to `poc/evaluate.py`, reporting a below-band excursion (the two timed paths
      stopped differing in crossing count) distinctly from an above-band one
- [x] 1.2 Add `measure_within_band()`, retrying a transient excursion so a build is
      not failed by noise
- [x] 1.3 Enforce the band in `main()` rather than `run()`, so a contaminated figure
      cannot reach the artifact while a test that calls `run()` stays load-independent
- [x] 1.4 Set the band's ceiling on a decade boundary and make it half-open there

## 2. The derived magnitude

- [x] 2.1 Add `_magnitude()` and `display.crossing_magnitude` to `serialise()`
- [x] 2.2 Interpolate `#d.crossing_magnitude` in Paper 2 §5 and §7.2
- [x] 2.3 Remove the performance sentence from Paper 2 §1.1's claim block
- [x] 2.4 Cite Paper 2 for the magnitude in Paper 3 §3.1
- [x] 2.5 Record the rule in the Paper 2 source header and in `AGENTS.md`

## 3. The confined tier under load

- [x] 3.1 Add `engine_config()` to `poc/sandbox/host.py` with a 32MiB reservation, a
      64KiB guard, and `memory_may_move`
- [x] 3.2 Build the benchmark's own engine from the same config, so the tier is
      measured as it is run
- [x] 3.3 Distinguish host resource exhaustion from an ungranted capability in the
      instantiation error path
- [x] 3.4 Confirm the crossing measurement is unmoved by the configuration

## 4. Prose

- [x] 4.1 Rewrite Paper 2 §7.2 so the fragility is present-tense, and say what now
      bounds it
- [x] 4.2 Correct §4's method note, which claimed a guard the overhead figure lacked
- [x] 4.3 Trim §3.5 of the projection/tension restatement and the novelty claim,
      keeping both pinned limits and the projection architecture

## 5. Verification

- [x] 5.1 Tests for the band, the retry, the magnitude/band alignment, and `main`'s
      refusal to write a contaminated artifact
- [x] 5.2 Full suite green three consecutive times under a deliberately loaded
      machine (load average 27–63)
- [x] 5.3 `make build`, `check-citations`, `check-freeze`, and pre-commit green
- [x] 5.4 Paper 3's prose counts still agree with `tab:outcomes` (7/5/3/4 = 19)
