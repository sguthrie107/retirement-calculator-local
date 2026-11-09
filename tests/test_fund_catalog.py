from lib.constants import DATA_FILES
from lib.data_loader import get_fund_by_ticker
from app.services.benchmark import TICKER_PROXY_MAP


def test_401k_fund_catalog_has_verified_index_details():
    expected_benchmarks = {
        "VFIAX": "S&P 500 Index",
        "VTMGX": "FTSE Developed All Cap ex US Index",
        "VIMAX": "Morningstar U.S. Mid Cap Index",
        "VSMAX": "Morningstar U.S. Small Cap Index",
        "FXAIX": "S&P 500 Index",
        "FSGGX": "MSCI ACWI ex USA Index (Net)",
        "FSMDX": "Russell MidCap Index",
        "FSSNX": "Russell 2000 Index",
    }

    for ticker, benchmark in expected_benchmarks.items():
        fund = get_fund_by_ticker(DATA_FILES["STOCKS"], ticker)
        assert fund["benchmark"] == benchmark
        assert fund["source_url"].startswith("https://")

    vtmgx = get_fund_by_ticker(DATA_FILES["STOCKS"], "VTMGX")
    fsggx = get_fund_by_ticker(DATA_FILES["STOCKS"], "FSGGX")
    assert vtmgx["expense_ratio"] == 0.05
    assert fsggx["expense_ratio"] == 0.055
    assert fsggx["name"] == "Fidelity Global ex U.S. Index Fund"


def test_401k_fund_benchmark_proxies_match_the_fund_indexes():
    assert TICKER_PROXY_MAP["VTMGX"] == "VEA"
    assert TICKER_PROXY_MAP["VIMAX"] == "VO"
    assert TICKER_PROXY_MAP["VSMAX"] == "VB"
    assert TICKER_PROXY_MAP["FSGGX"] == "ACWX"
    assert TICKER_PROXY_MAP["FSMDX"] == "IWR"
    assert TICKER_PROXY_MAP["FSSNX"] == "IWM"
