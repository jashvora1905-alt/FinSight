from pathlib import Path

import pandas as pd
import pytest

DATA = Path(__file__).resolve().parent.parent / "data"
EDGE = DATA / "edge_cases"


@pytest.fixture(scope="session")
def portfolio():
    return pd.read_csv(DATA / "sample_portfolio.csv")


@pytest.fixture(scope="session")
def transactions():
    return pd.read_csv(DATA / "sample_transactions.csv")


@pytest.fixture
def edge():
    """edge('portfolio_empty') -> DataFrame from data/edge_cases/<name>.csv"""
    return lambda name: pd.read_csv(EDGE / f"{name}.csv")
