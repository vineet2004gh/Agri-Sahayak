
from __future__ import annotations
import os, base64, zlib, json, datetime, warnings
from typing import Optional
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# TradingEconomics data fetching (from notebook)
# ---------------------------------------------------------------------------
COMMODITY_URLS = {
    "wheat":   "https://d3ii0wo49og5mi.cloudfront.net/markets/w%201:com?interval=1d&span=1y&ohlc=0&key=20240229:nazare",
    "rice":    "https://d3ii0wo49og5mi.cloudfront.net/markets/rr1:com?interval=1d&span=1y&ohlc=0&key=20240229:nazare",
    "cotton":  "https://d3ii0wo49og5mi.cloudfront.net/markets/ct1:com?interval=1d&span=1y&ohlc=0&key=20240229:nazare",
    "soybean": "https://d3ii0wo49og5mi.cloudfront.net/markets/s%201:com?interval=1d&span=1y&ohlc=0&key=20240229:nazare",
    "corn":    "https://d3ii0wo49og5mi.cloudfront.net/markets/c%201:com?interval=1d&span=1y&ohlc=0&key=20240229:nazare",
    "maize":   "https://d3ii0wo49og5mi.cloudfront.net/markets/c%201:com?interval=1d&span=1y&ohlc=0&key=20240229:nazare",
    "sugar":   "https://d3ii0wo49og5mi.cloudfront.net/markets/sb1:com?interval=1d&span=1y&ohlc=0&key=20240229:nazare",
    "coffee":  "https://d3ii0wo49og5mi.cloudfront.net/markets/kc1:com?interval=1d&span=1y&ohlc=0&key=20240229:nazare",
    "sunflower": "https://d3ii0wo49og5mi.cloudfront.net/markets/sunf:com?interval=1d&span=1y&ohlc=0&key=20240229:nazare",
    "potato":  "https://d3ii0wo49og5mi.cloudfront.net/markets/fapp:com?interval=1d&span=1y&ohlc=0&key=20240229:nazare",
    "tea":     "https://d3ii0wo49og5mi.cloudfront.net/markets/tea:com?interval=1d&span=1y&ohlc=0&key=20240229:nazare",
}

COMMODITY_CURRENCY = {
    "wheat": "USD", "rice": "USD", "cotton": "USD", "soybean": "USD",
    "corn": "USD", "maize": "USD", "sugar": "USD", "coffee": "USD",
    "sunflower": "INR", "potato": "EUR", "tea": "INR",
}

# Cache for fetched data
_price_cache: dict[str, pd.DataFrame] = {}
_fx_cache: dict[str, float] = {}


def _data_magic(encoded: str, key: str = "tradingeconomics-charts-core-api-key", wbits: int = 16):
    """Decrypt TradingEconomics XOR+zlib encoded data (from notebook)."""
    try:
        a = base64.b64decode(encoded)
        n = bytearray(a)
        s = bytearray(key, "utf-8")
        for i in range(len(n)):
            n[i] ^= s[i % len(s)]
        decoded = zlib.decompress(n, wbits).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        print(f"[PricePred] data_magic error: {e}")
        return None


def _get_fx_to_inr() -> dict[str, float]:
    """Get FX rates to convert to INR."""
    global _fx_cache
    if _fx_cache:
        return _fx_cache
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/INR", timeout=10)
        rates = resp.json().get("rates", {})
        _fx_cache = {
            "USD": 1 / rates.get("USD", 0.012),
            "EUR": 1 / rates.get("EUR", 0.011),
            "INR": 1.0,
        }
    except Exception:
        _fx_cache = {"USD": 83.0, "EUR": 90.0, "INR": 1.0}
    return _fx_cache


def fetch_commodity_prices(crop: str) -> Optional[pd.DataFrame]:
    """Fetch 1-year daily prices for a commodity from TradingEconomics."""
    crop_lower = crop.strip().lower()
    if crop_lower in _price_cache:
        return _price_cache[crop_lower]

    url = COMMODITY_URLS.get(crop_lower)
    if not url:
        print(f"[PricePred] No URL for crop: {crop_lower}")
        return None

    try:
        resp = requests.get(url, verify=False, timeout=15)
        json_data = resp.json()
        data = _data_magic(json_data)
        if not data or "series" not in data:
            return None

        df = pd.DataFrame(data["series"][0]["data"])
        df.columns = ["date", "price", "pct_change", "change"][:len(df.columns)]
        df["date"] = df["date"].apply(
            lambda x: datetime.datetime.fromtimestamp(x, datetime.timezone.utc)
        )
        df = df[["date", "price"]].dropna()
        df = df.sort_values("date").reset_index(drop=True)

        # Convert to INR
        fx = _get_fx_to_inr()
        currency = COMMODITY_CURRENCY.get(crop_lower, "USD")
        df["price_inr"] = df["price"] * fx.get(currency, 1.0)

        df.set_index("date", inplace=True)
        _price_cache[crop_lower] = df
        print(f"[PricePred] Fetched {len(df)} days of {crop_lower} prices")
        return df

    except Exception as e:
        print(f"[PricePred] Fetch failed for {crop_lower}: {e}")
        return None


def _generate_synthetic_prices(crop: str, days: int = 365) -> pd.DataFrame:
    """Fallback: generate realistic synthetic daily prices."""
    base_prices = {
        "wheat": 2500, "rice": 3000, "cotton": 6000, "maize": 2200,
        "soybean": 4500, "mustard": 5000, "onion": 1500, "potato": 1200,
        "tomato": 2000, "sugarcane": 3500, "sugar": 3200, "corn": 2200,
        "coffee": 8000, "tea": 5000, "sunflower": 4000,
        "millet": 2200, "ragi": 2800, "barley": 1800, "chickpea": 5500,
    }
    base = base_prices.get(crop.lower(), 3000)
    np.random.seed(hash(crop) % 2**31)
    dates = pd.date_range(end=datetime.datetime.now(), periods=days, freq="D")
    trend = np.linspace(0, base * 0.05, days)
    seasonal = base * 0.08 * np.sin(np.linspace(0, 2 * np.pi, days))
    noise = np.random.normal(0, base * 0.015, days).cumsum()
    prices = base + trend + seasonal + noise
    prices = np.maximum(prices, base * 0.5)
    df = pd.DataFrame({"price_inr": prices}, index=dates)
    df.index.name = "date"
    return df


# ---------------------------------------------------------------------------
# Model fitting functions
# ---------------------------------------------------------------------------

def _compute_returns(prices: pd.Series) -> pd.Series:
    """Compute log returns."""
    return np.log(prices / prices.shift(1)).dropna()


def fit_arima(prices: pd.Series, forecast_days: int = 7) -> dict:
    """Fit ARIMA model using auto_arima."""
    from pmdarima import auto_arima
    from statsmodels.tsa.arima.model import ARIMA

    try:
        auto_result = auto_arima(prices, seasonal=False, stepwise=True,
                                  suppress_warnings=True, max_p=3, max_q=3, max_d=2)
        order = auto_result.order
        model = ARIMA(prices, order=order).fit()
        forecast = model.forecast(steps=forecast_days)
        aic = model.aic
        residuals = model.resid
        return {
            "name": "ARIMA", "order": str(order), "forecast": forecast.values.tolist(),
            "aic": aic, "residuals": residuals, "fitted": model.fittedvalues,
        }
    except Exception as e:
        print(f"[PricePred] ARIMA error: {e}")
        return {"name": "ARIMA", "error": str(e)}


def fit_garch(returns: pd.Series, forecast_days: int = 7) -> dict:
    """Fit standard GARCH(1,1)."""
    from arch import arch_model
    try:
        scaled = returns * 100
        model = arch_model(scaled, mean="AR", lags=1, vol="Garch", p=1, q=1)
        fitted = model.fit(disp="off")
        fcast = fitted.forecast(horizon=forecast_days)
        mean_f = (fcast.mean.iloc[-1].values / 100).tolist()
        var_f = (fcast.variance.iloc[-1].values / 10000).tolist()
        return {
            "name": "GARCH(1,1)", "forecast_returns": mean_f, "forecast_variance": var_f,
            "aic": fitted.aic, "bic": fitted.bic, "fitted": fitted,
        }
    except Exception as e:
        print(f"[PricePred] GARCH error: {e}")
        return {"name": "GARCH(1,1)", "error": str(e)}


def fit_egarch(returns: pd.Series, forecast_days: int = 7) -> dict:
    """Fit EGARCH(1,1,1) — asymmetric, log-variance.
    Uses simulation-based forecasting since analytic forecasts are not
    available for EGARCH with horizon > 1.
    """
    from arch import arch_model
    try:
        scaled = returns * 100
        model = arch_model(scaled, mean="AR", lags=1, vol="EGARCH", p=1, q=1, o=1)
        fitted = model.fit(disp="off")
        # EGARCH requires simulation-based forecasting for multi-step
        fcast = fitted.forecast(horizon=forecast_days, method="simulation", simulations=1000)
        mean_f = (fcast.mean.iloc[-1].values / 100).tolist()
        var_f = (fcast.variance.iloc[-1].values / 10000).tolist()
        return {
            "name": "EGARCH(1,1,1)", "forecast_returns": mean_f, "forecast_variance": var_f,
            "aic": fitted.aic, "bic": fitted.bic, "fitted": fitted,
        }
    except Exception as e:
        print(f"[PricePred] EGARCH error: {e}")
        return {"name": "EGARCH(1,1,1)", "error": str(e)}

def fit_arima_garch(prices: pd.Series, forecast_days: int = 7) -> dict:
    """Hybrid ARIMA-GARCH: ARIMA for mean, GARCH on residuals."""
    from statsmodels.tsa.arima.model import ARIMA
    from arch import arch_model
    from pmdarima import auto_arima
    try:
        auto_res = auto_arima(prices, seasonal=False, stepwise=True,
                               suppress_warnings=True, max_p=3, max_q=3)
        order = auto_res.order
        arima_model = ARIMA(prices, order=order).fit()
        arima_forecast = arima_model.forecast(steps=forecast_days).values
        residuals = arima_model.resid.dropna()
        scaled_resid = residuals * 100
        garch_model = arch_model(scaled_resid, mean="Zero", vol="Garch", p=1, q=1)
        garch_fitted = garch_model.fit(disp="off")
        garch_fcast = garch_fitted.forecast(horizon=forecast_days)
        variance = garch_fcast.variance.iloc[-1].values / 10000
        sigma = np.sqrt(variance)
        upper = arima_forecast + 1.96 * sigma
        lower = arima_forecast - 1.96 * sigma
        return {
            "name": "ARIMA-GARCH", "arima_order": str(order),
            "forecast": arima_forecast.tolist(),
            "upper_ci": upper.tolist(), "lower_ci": lower.tolist(),
            "volatility": sigma.tolist(),
            "aic": arima_model.aic + garch_fitted.aic,
        }
    except Exception as e:
        print(f"[PricePred] ARIMA-GARCH error: {e}")
        return {"name": "ARIMA-GARCH", "error": str(e)}


# ---------------------------------------------------------------------------
# Model comparison & price conversion
# ---------------------------------------------------------------------------

def _returns_to_prices(current_price: float, forecast_returns: list) -> list:
    """Convert forecasted log returns to price levels."""
    prices = []
    p = current_price
    for r in forecast_returns:
        p = p * np.exp(r)
        prices.append(round(p, 2))
    return prices


def _price_range(current_price: float, pred_return: float, sigma: float):
    """Compute expected price and confidence range (from notebook)."""
    expected = current_price * np.exp(pred_return)
    lower = current_price * np.exp(pred_return - 1.96 * sigma)
    upper = current_price * np.exp(pred_return + 1.96 * sigma)
    return round(expected, 2), round(lower, 2), round(upper, 2)


def compare_models(prices_series: pd.Series, forecast_days: int = 7) -> dict:
    """Run all models, compare on test set, return rankings + forecasts."""
    n = len(prices_series)
    train_size = int(n * 0.8)
    train = prices_series.iloc[:train_size]
    test = prices_series.iloc[train_size:]
    returns = _compute_returns(prices_series)
    train_returns = returns.iloc[:train_size - 1]
    test_returns = returns.iloc[train_size - 1:]
    current_price = float(prices_series.iloc[-1])

    results = []

    # 1. ARIMA (on price levels)
    arima_res = fit_arima(train, forecast_days)
    if "error" not in arima_res:
        test_fc = fit_arima(train, len(test))
        if "error" not in test_fc:
            from sklearn.metrics import mean_squared_error, mean_absolute_error
            pred_len = min(len(test), len(test_fc["forecast"]))
            rmse = np.sqrt(mean_squared_error(test.values[:pred_len], test_fc["forecast"][:pred_len]))
            mae = mean_absolute_error(test.values[:pred_len], test_fc["forecast"][:pred_len])
            arima_res["rmse"] = round(rmse, 4)
            arima_res["mae"] = round(mae, 4)
        # Get actual forecast
        full_arima = fit_arima(prices_series, forecast_days)
        if "error" not in full_arima:
            arima_res["forecast"] = full_arima["forecast"]
            arima_res["aic"] = full_arima.get("aic")
        results.append(arima_res)

    # 2-4. GARCH variants (on returns)
    garch_fitters = [
        ("GARCH(1,1)", fit_garch),
        ("EGARCH(1,1,1)", fit_egarch),
        ("GJR-GARCH(1,1,1)", fit_gjr_garch),
    ]
    for name, fitter in garch_fitters:
        res = fitter(returns, forecast_days)
        if "error" not in res and "forecast_returns" in res:
            res["forecast_prices"] = _returns_to_prices(current_price, res["forecast_returns"])
            # Confidence intervals from variance
            if "forecast_variance" in res:
                sigmas = [np.sqrt(v) for v in res["forecast_variance"]]
                uppers, lowers = [], []
                p = current_price
                for r, s in zip(res["forecast_returns"], sigmas):
                    exp, lo, hi = _price_range(p, r, s)
                    uppers.append(hi)
                    lowers.append(lo)
                    p = exp
                res["upper_ci"] = uppers
                res["lower_ci"] = lowers
            results.append(res)

    # 5. EMD+ARIMA
    emd_res = fit_emd_arima(prices_series, forecast_days)
    if "error" not in emd_res:
        results.append(emd_res)

    # 6. ARIMA-GARCH hybrid
    ag_res = fit_arima_garch(prices_series, forecast_days)
    if "error" not in ag_res:
        results.append(ag_res)

    # Rank by AIC (lower is better)
    for r in results:
        if "aic" not in r or r.get("aic") is None:
            r["aic"] = float("inf")

    results.sort(key=lambda x: x.get("aic", float("inf")))
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return {
        "models": results,
        "best_model": results[0]["name"] if results else "none",
        "current_price": current_price,
        "data_points": n,
        "forecast_days": forecast_days,
    }


# ---------------------------------------------------------------------------
# Main prediction function (with Gemini interpretation)
# ---------------------------------------------------------------------------

def run_price_prediction(
    crop: str,
    google_api_key: str,
    forecast_days: int = 7,
    district: str = "",
    state: str = "",
) -> dict:
    """Full pipeline: fetch data → fit models → compare → forecast → Gemini interpret."""
    # 1. Fetch real data (fallback to synthetic)
    df = fetch_commodity_prices(crop)
    if df is None or len(df) < 30:
        print(f"[PricePred] Using synthetic data for {crop}")
        df = _generate_synthetic_prices(crop)
        data_source = "synthetic"
    else:
        data_source = "tradingeconomics"

    prices = df["price_inr"].dropna()
    if len(prices) < 30:
        return {"error": f"Insufficient price data for {crop} ({len(prices)} points)"}

    # 2. Compare models
    print(f"[PricePred] Comparing models for {crop} ({len(prices)} data points)...")
    comparison = compare_models(prices, forecast_days)

    # 3. Get best model's forecast
    best = comparison["models"][0] if comparison["models"] else {}
    best_name = best.get("name", "unknown")
    forecast_prices = best.get("forecast_prices") or best.get("forecast")
    upper_ci = best.get("upper_ci")
    lower_ci = best.get("lower_ci")

    # 4. Gemini interpretation
    response_text = _gemini_interpret_price(
        crop, best_name, comparison, forecast_prices,
        upper_ci, lower_ci, google_api_key, district, state, data_source,
    )

    # Clean results for JSON serialization
    clean_models = []
    for m in comparison["models"]:
        clean = {k: v for k, v in m.items()
                 if k not in ("fitted", "residuals", "forecast_variance", "forecast_returns")}
        if clean.get("aic") == float("inf"):
            clean["aic"] = None
        clean_models.append(clean)

    return {
        "response": response_text,
        "crop": crop,
        "current_price": comparison["current_price"],
        "forecast_days": forecast_days,
        "forecast_prices": forecast_prices,
        "upper_ci": upper_ci,
        "lower_ci": lower_ci,
        "best_model": best_name,
        "model_comparison": clean_models,
        "data_source": data_source,
        "data_points": comparison["data_points"],
    }


def _gemini_interpret_price(
    crop, best_model, comparison, forecast, upper_ci, lower_ci,
    api_key, district, state, data_source,
) -> str:
    """Send price forecast to Gemini for farmer-friendly interpretation."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-flash-latest")

        current = comparison["current_price"]
        location = f"{district}, {state}" if district else (state or "India")

        model_summary = "\n".join(
            f"  {m['rank']}. {m['name']} — AIC: {m.get('aic', 'N/A')}, "
            f"RMSE: {m.get('rmse', 'N/A')}, MAE: {m.get('mae', 'N/A')}"
            for m in comparison["models"][:6]
        )

        fc_str = ""
        if forecast:
            fc_str = ", ".join(f"Day {i+1}: ₹{p:,.2f}" for i, p in enumerate(forecast[:7]))

        prompt = (
            "You are an agricultural market analyst. A suite of time-series models "
            "(ARIMA, GARCH, EGARCH, GJR-GARCH, EMD+ARIMA, ARIMA-GARCH hybrid) "
            "have been used to forecast agricultural commodity prices.\n\n"
            f"Crop: {crop.title()}\n"
            f"Location: {location}\n"
            f"Current Price: ₹{current:,.2f}/quintal\n"
            f"Data Source: {data_source} ({comparison['data_points']} days)\n"
            f"Best Model: {best_model}\n\n"
            f"Model Rankings:\n{model_summary}\n\n"
            f"Price Forecast (next {comparison['forecast_days']} days):\n{fc_str}\n\n"
            "Provide a farmer-friendly analysis:\n"
            "1. **Price Trend**: Is the price going up, down, or stable?\n"
            "2. **Best Selling Window**: When should the farmer sell?\n"
            "3. **Risk Assessment**: How volatile is the market?\n"
            "4. **Recommendation**: Hold or sell? With reasoning.\n"
            "5. **Confidence**: How reliable is this forecast?\n\n"
            "Use simple language. Include ₹ prices."
        )

        resp = model.generate_content(prompt)
        answer = resp.text if resp and resp.text else ""

        header = (
            f"📈 **Market Price Prediction for {crop.title()}**\n"
            f"📍 {location} | 🏆 Best Model: {best_model}\n"
            f"💰 Current: ₹{current:,.2f}/quintal\n\n---\n\n"
        )
        return header + answer

    except Exception as e:
        print(f"[PricePred] Gemini error: {e}")
        fc_str = ""
        if forecast:
            fc_str = "\n".join(f"  Day {i+1}: ₹{p:,.2f}" for i, p in enumerate(forecast[:7]))
        return (
            f"📈 **Price Prediction for {crop.title()}**\n"
            f"Best Model: {best_model}\n"
            f"Current: ₹{comparison['current_price']:,.2f}\n"
            f"Forecast:\n{fc_str}\n\n"
            "Detailed analysis temporarily unavailable."
        )
