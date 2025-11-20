# views/Holdings_Leaderboard.py

import base64
import io
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from scripts.data_processing import load_and_preprocess_data

st.title("🏆 Holdings Leaderboard")

st.write(
    """
    See your top holdings by portfolio value with company logos, market cap, and sector.
    This gives you a quick, visual sense of what actually drives your portfolio.
    """
)

st.divider()

# ---------- PATHS / CONSTANTS ---------- #

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
LOGO_DIR = PROJECT_ROOT / "downloaded_logos"

TOP_N = 25  # how many holdings to show


# ---------- LOAD DATA ---------- #

data = load_and_preprocess_data()

# Prefer the enriched stocks_complete if available, otherwise fall back.
stocks_complete: pd.DataFrame = data.get("stocks_complete")
stocks: pd.DataFrame = data["stocks"]
stock_info: pd.DataFrame = data["stock_info"]

if stocks_complete is None:
    # Minimal fallback merge: you already have this in preprocess, but just in case.
    if "stock" in stocks.columns and "stock" in stock_info.columns:
        stocks_complete = pd.merge(stocks, stock_info, how="left", on="stock")
    else:
        stocks_complete = stocks.copy()

df = stocks_complete.copy()

if df.empty:
    st.info("No holdings found. Once you have invested positions, they’ll appear here.")
    st.stop()

# Ensure required columns exist
required_cols = {"stock", "company", "market_value"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"Holdings data is missing required columns: {missing}")
    st.stop()

# Filter to current holdings (quantity > 0 if present)
if "quantity" in df.columns:
    df = df[df["quantity"] > 0].copy()

if df.empty:
    st.info("All positions appear to be sold. No active holdings to display.")
    st.stop()

# ---------- COMPUTE RANKING & FORMATTED FIELDS ---------- #

# Sort by portfolio value (descending)
df = df.sort_values("market_value", ascending=False)

# Limit to top N
df = df.head(TOP_N).copy()

# Portfolio weight
total_mv = df["market_value"].sum()
df["portfolio_weight"] = (df["market_value"] / total_mv * 100).round(2)

# Market cap (billions) from stock_info if available
if "market_cap" in df.columns:
    df["market_cap_b"] = df["market_cap"].round(2)
else:
    df["market_cap_b"] = pd.NA

# Nice numeric formatting
df["market_value_fmt"] = df["market_value"].apply(lambda x: f"${x:,.0f}")
df["portfolio_weight_fmt"] = df["portfolio_weight"].apply(lambda x: f"{x:.2f}%")
df["market_cap_fmt"] = df["market_cap_b"].apply(
    lambda x: f"{x:,.2f} B" if pd.notna(x) else "N/A"
)


# ---------- LOGO HANDLING ---------- #

def image_to_base64(img_path: Path, output_size=(64, 64)) -> str:
    """
    Convert image at img_path to Base64 PNG, resized to output_size.
    Returns empty string if file not found.
    """
    if img_path.exists():
        with Image.open(img_path) as img:
            img = img.convert("RGBA")
            img = img.resize(output_size)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    return ""

def resolve_logo_path(ticker: str, company: str):
    """
    Try to find a logo file for the given ticker/company in LOGO_DIR.

    Priority:
    1. {TICKER}.png
    2. {ticker.lower()}.png
    3. {Company}.png
    4. {Company with spaces replaced by _}.png
    """
    candidates: list[Path] = []

    # By ticker
    if ticker:
        candidates.append(LOGO_DIR / f"{ticker}.png")
        candidates.append(LOGO_DIR / f"{ticker.upper()}.png")
        candidates.append(LOGO_DIR / f"{ticker.lower()}.png")

    # By company name
    if company:
        safe_name_space = company.replace("/", "_")
        safe_name_underscore = safe_name_space.replace(" ", "_")
        candidates.append(LOGO_DIR / f"{company}.png")
        candidates.append(LOGO_DIR / f"{safe_name_space}.png")
        candidates.append(LOGO_DIR / f"{safe_name_underscore}.png")

    for p in candidates:
        if p.exists():
            return p

    return None


# Create Logo column as Base64
logo_base64_list: list[str] = []
for _, row in df.iterrows():
    ticker = str(row.get("stock", "")).strip()
    company = str(row.get("company", "")).strip()

    logo_path = resolve_logo_path(ticker, company)
    if logo_path is not None:
        logo_base64_list.append(image_to_base64(logo_path))
    else:
        logo_base64_list.append("")

df["Logo"] = logo_base64_list

# ---------- BUILD DISPLAY TABLE ---------- #

display_df = pd.DataFrame(
    {
        "Logo": df["Logo"],
        "Ticker": df["stock"].astype(str),
        "Company": df["company"].astype(str),
        "Sector": df["sector"].astype(str) if "sector" in df.columns else "N/A",
        "Portfolio Value": df["market_value_fmt"],
        "Portfolio Weight": df["portfolio_weight_fmt"],
        "Market Cap (B USD)": df["market_cap_fmt"],
    }
)

# Reset index to start from 1
display_df.reset_index(drop=True, inplace=True)
display_df.index = display_df.index + 1

# Column configs
image_column = st.column_config.ImageColumn(label="")
ticker_column = st.column_config.TextColumn(label="Ticker")
company_column = st.column_config.TextColumn(label="Company")
sector_column = st.column_config.TextColumn(label="Sector")
value_column = st.column_config.TextColumn(label="Portfolio Value 💰")
weight_column = st.column_config.TextColumn(label="Portfolio Weight (%)")
mcap_column = st.column_config.TextColumn(label="Market Cap (B USD)")

st.dataframe(
    display_df,
    height=800,
    column_config={
        "Logo": image_column,
        "Ticker": ticker_column,
        "Company": company_column,
        "Sector": sector_column,
        "Portfolio Value": value_column,
        "Portfolio Weight": weight_column,
        "Market Cap (B USD)": mcap_column,
    },
)

st.caption(
    "Logos are loaded from the `downloaded_logos` folder. "
    "Company data comes from your portfolio and stock info files."
)
