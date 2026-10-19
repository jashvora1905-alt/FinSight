# Tests (owner: Atharva, Data/Testing/Integration)

From the repository root, in a clean virtual environment:

    pip install -r requirements.txt            # pins pandas 2.3.3
    python data/generate_sample_data.py        # regenerate all CSVs (shared schema); only if you edit the generator
    python -m pytest -rsx                      # whole suite (pytest.ini: testpaths = tests); -rs shows any skip reason
    python -m pytest -q                        # expected after all branches are merged: 0 failed, 0 skipped

* `contract.py` + `adapters.py`: the only place tests touch module internals. A missing module or
  backend is a FAILURE. Only modules listed in `NOT_DELIVERED` (currently none) may skip.
* `oracle.py`: independent reference calculations. `validators.py`: strict reference validators.
* Files ending `_reference` avoid name clashes with the module owners' own tests (Aditya, Soumil, Prisha, Jash).
* API tests use a temporary SQLite database (`backend.config.DB_PATH`), never `backend/finsight.db`.
* Prisha's unittest-style tests also run under pytest from `tests/`.
* `BUG_LOG.md` = findings and decisions; `REVIEW_NOTES.md` = data-layer and health-score sign-off notes for Jash.
* Set `FINSIGHT_SKIP_API=1` only to knowingly skip API tests in a checkout without the backend.
