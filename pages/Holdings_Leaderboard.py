# pages/Holdings_Leaderboard.py

import base64
import io
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from scripts.data_processing import load_and_preprocess_data
from scripts.navigation import make_sidebar
from scripts.theme import page_header, section_header, grad_divider
from scripts.utils import render_freshness_badge, render_refresh_status

st.set_page_config(page_title="Holdings Leaderboard", page_icon="🏆", layout="wide")

make_sidebar("Holdings Leaderboard")

page_header("Holdings Leaderboard", icon="🏆",
            subtitle="Top holdings by portfolio value with company logos, market cap, and sector")

render_refresh_status()

st.html(grad_divider())
st.html(section_header("Top Holdings", icon="🏆"))

# ---------- PATHS / CONSTANTS ---------- #

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
LOGO_DIR = PROJECT_ROOT / "downloaded_logos"

TOP_N = 25


# ---------- LOAD DATA ---------- #

data = load_and_preprocess_data()

_stock_info_hl = data.get("stock_info", pd.DataFrame())
if not _stock_info_hl.empty and "last_updated" in _stock_info_hl.columns:
    render_freshness_badge(pd.to_datetime(_stock_info_hl["last_updated"]).max(), label="Fundamentals last updated")

stocks_complete: pd.DataFrame = data.get("stocks_complete")
stocks: pd.DataFrame = data["stocks"]
stock_info: pd.DataFrame = data["stock_info"]

if stocks_complete is None:
    if "stock" in stocks.columns and "stock" in stock_info.columns:
        stocks_complete = pd.merge(stocks, stock_info, how="left", on="stock")
    else:
        stocks_complete = stocks.copy()

df = stocks_complete.copy()

if df.empty:
    st.info("No holdings found. Once you have invested positions, they'll appear here.")
    st.stop()

required_cols = {"stock", "company", "market_value"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"Holdings data is missing required columns: {missing}")
    st.stop()

if "quantity" in df.columns:
    df = df[df["quantity"] > 0].copy()

if df.empty:
    st.info("All positions appear to be sold. No active holdings to display.")
    st.stop()

# ---------- COMPUTE RANKING & FORMATTED FIELDS ---------- #

df = df.sort_values("market_value", ascending=False)
df = df.head(TOP_N).copy()

total_mv = df["market_value"].sum()
df["portfolio_weight"] = (df["market_value"] / total_mv * 100).round(2)

if "market_cap" in df.columns:
    df["market_cap_b"] = df["market_cap"].round(2)
else:
    df["market_cap_b"] = pd.NA

df["market_value_fmt"]    = df["market_value"].apply(lambda x: f"${x:,.0f}")
df["portfolio_weight_fmt"] = df["portfolio_weight"].apply(lambda x: f"{x:.2f}%")
df["market_cap_fmt"]      = df["market_cap_b"].apply(
    lambda x: f"{x:,.2f} B" if pd.notna(x) else "N/A"
)


# ---------- LOGO HANDLING ---------- #

def image_to_base64(img_path: Path, output_size=(64, 64)) -> str:
    if img_path.exists():
        with Image.open(img_path) as img:
            img = img.convert("RGBA")
            img = img.resize(output_size)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    return ""


def resolve_logo_path(ticker: str, company: str):
    candidates: list[Path] = []

    if ticker:
        candidates.append(LOGO_DIR / f"{ticker}.png")
        candidates.append(LOGO_DIR / f"{ticker.upper()}.png")
        candidates.append(LOGO_DIR / f"{ticker.lower()}.png")

    if company:
        safe_name_space      = company.replace("/", "_")
        safe_name_underscore = safe_name_space.replace(" ", "_")
        candidates.append(LOGO_DIR / f"{company}.png")
        candidates.append(LOGO_DIR / f"{safe_name_space}.png")
        candidates.append(LOGO_DIR / f"{safe_name_underscore}.png")

    for p in candidates:
        if p.exists():
            return p
    return None


logo_base64_list: list[str] = []
for _, row in df.iterrows():
    ticker  = str(row.get("stock",   "")).strip()
    company = str(row.get("company", "")).strip()
    logo_path = resolve_logo_path(ticker, company)
    logo_base64_list.append(image_to_base64(logo_path) if logo_path is not None else "")

df["Logo"] = logo_base64_list

# ---------- BUILD DISPLAY TABLE ---------- #
# Holdings Leaderboard keeps st.dataframe with ImageColumn so logos render correctly.

display_df = pd.DataFrame(
    {
        "Logo":              df["Logo"],
        "Ticker":            df["stock"].astype(str),
        "Company":           df["company"].astype(str),
        "Sector":            df["sector"].astype(str) if "sector" in df.columns else "N/A",
        "Portfolio Value":   df["market_value_fmt"],
        "Portfolio Weight":  df["portfolio_weight_fmt"],
        "Market Cap (B USD)": df["market_cap_fmt"],
    }
)

display_df.reset_index(drop=True, inplace=True)
display_df.index = display_df.index + 1

st.dataframe(
    display_df,
    height=800,
    column_config={
        "Logo":              st.column_config.ImageColumn(label=""),
        "Ticker":            st.column_config.TextColumn(label="Ticker"),
        "Company":           st.column_config.TextColumn(label="Company"),
        "Sector":            st.column_config.TextColumn(label="Sector"),
        "Portfolio Value":   st.column_config.TextColumn(label="Portfolio Value 💰"),
        "Portfolio Weight":  st.column_config.TextColumn(label="Portfolio Weight (%)"),
        "Market Cap (B USD)": st.column_config.TextColumn(label="Market Cap (B USD)"),
    },
)

st.html(grad_divider())
st.caption(
    "Logos are loaded from the `downloaded_logos` folder. "
    "Company data comes from your portfolio and stock info files."
)
