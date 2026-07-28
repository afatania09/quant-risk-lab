"""Run a reproducible risk report for a diversified $10m US equity portfolio."""

from quant_risk.data import DEFAULT_TICKERS, download_returns
from quant_risk.market import historical_var_es, monte_carlo_var_es, parametric_var_es
from quant_risk.stress import historical_stress


def main() -> None:
    returns = download_returns(start="2018-01-01")
    positions = [2_000_000, 2_000_000, 1_500_000, 1_500_000, 1_500_000, 1_500_000]
    methods = {
        "Historical": historical_var_es(returns, positions),
        "Parametric": parametric_var_es(returns, positions),
        "Monte Carlo": monte_carlo_var_es(returns, positions),
    }
    print(f"Portfolio: {dict(zip(DEFAULT_TICKERS, positions))}")
    for method, (var, es) in methods.items():
        print(f"{method:12s} 99% VaR: ${var:,.0f} | ES: ${es:,.0f}")
    print("\nWorst observed days:")
    print(historical_stress(returns, positions).to_string())


if __name__ == "__main__":
    main()
