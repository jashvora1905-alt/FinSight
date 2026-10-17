# Tests (owner: Atharva, Data/Testing/Integration)

    pip install pytest pandas numpy fastapi httpx python-multipart
    python data/generate_sample_data.py        # regenerate all CSVs (shared schema)
    pytest -rsx                                # whole suite; -rs shows why anything is skipped
    FINSIGHT_SKIP_API=1 pytest -rsx            # knowingly skip API tests if the backend isn't checked out
    python -m unittest discover -s behavior/tests    # Prisha's own unittest suite (run in CI too)

* `contract.py` + `adapters.py`: the only place tests touch module internals. Only modules in
  `NOT_DELIVERED` (health score) may skip; anything else missing is a FAILURE.
* `oracle.py`: independent reference calculations. `validators.py`: strict reference validators.
* Files ending `_reference` avoid name clashes with the module owners' own tests.
* Expected non-green: `test_upload_includes_health_score` (xfail, Health Score not in backend yet),
  `portfolio_blank_symbol` (xfail strict, BUG B013).
