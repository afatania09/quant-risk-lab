"""Optional real-market-data loader."""

from __future__ import annotations

import pandas as pd


DEFAULT_TICKERS = ["AAPL", "MSFT", "JPM", "XOM", "JNJ", "WMT"]


def download_returns(
    tickers: list[str] | None = None,
    start: str = "2018-01-01",
    end: str | None = None,
) -> pd.DataFrame:
    """Download adjusted prices from Yahoo Finance and return daily log returns."""
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError("Install market data support: pip install -e '.[market-data]'") from exc
    symbols = tickers or DEFAULT_TICKERS
    prices = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(symbols[0])
    returns = prices.pct_change(fill_method=None).dropna(how="any")
    if returns.empty:
        raise RuntimeError("No usable price history was returned")
    return returns
