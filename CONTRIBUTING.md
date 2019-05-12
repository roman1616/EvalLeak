# Contributing to EvalLeak

Thanks for looking at EvalLeak. This is a small, focused tool: detect
contamination between dataset splits. Contributions that keep it small and
focused are welcome.

## Development setup

```bash
git clone https://github.com/roman1616/EvalLeak.git
cd EvalLeak
pip install -e .
python -m pytest tests
```

Python 3.11+ is recommended. There are no runtime dependencies; tests run
offline in about a second.

## Ground rules

- **Deterministic output.** Two runs on the same manifests must produce
  byte-identical reports. Do not introduce randomness, timestamps, or
  iteration-order dependence into the scan path.
- **Standard library only.** Runtime dependencies stay at zero. Test-time
  dependencies stay at pytest.
- **Conservative flags.** A false positive in a leakage report costs someone
  a day of dataset rework. Prefer precision over recall; document the
  threshold you chose and why.
- **Tests for every behaviour change.** The shingle, overlap, and report
  modules are the core; changes there need coverage on both the happy path
  and the threshold boundary.

## Commit style

Short imperative subjects (`fix: ...`, `feat: ...`, `docs: ...`), body only
when the "why" is not obvious from the diff.

## Reporting issues

Include the manifest formats involved, the configured thresholds, and the
exact containment number you expected versus got. Reproduction manifests
with synthetic records are preferred over real data.