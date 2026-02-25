"""
scripts/theme.py — Shared UI theme for the Personal Finance app.

Import color constants and call page_header() / apply_base_css() from every
page so the visual language stays consistent without repeating CSS or color
hex codes across files.

Color palette
─────────────
  GREEN        = "#2ecc71"   backward-compat alias (chart lines, Altair)
  RED          = "#e74c3c"   negative values, loss, over-budget, stale data
  BLUE         = "#3498db"   neutral emphasis (savings-rate area, links)
  YELLOW       = "#f39c12"   warnings, moderately stale data

  GREEN_VIVID   = "#00c853"  primary CTA / key numbers
  GREEN_DARK    = "#1b5e20"  table headers, deep accents
  GREEN_MEDIUM  = "#388e3c"  secondary accents
  GREEN_LIGHT   = "#a5d6a7"  muted labels on dark
  GREEN_TEAL    = "#00897b"  teal variant for variety
  GREEN_CARD_BG = "#0d1f12"  stat card background
  GREEN_STRIPE  = "#112218"  alternating table row

  DARK_BG     = "#0b1621"   legacy metric card background
  CARD_BORDER = "#243447"   legacy metric card border
  BANNER_BG   = "#1e2530"   info / freshness banner background

Chart library conventions
─────────────────────────
  Altair  — time-series line and area charts (trends over time)
  Plotly  — categorical charts: bar, pie, treemap, radar; RdYlGn score maps

  GREEN_PIE_PALETTE — 7-color green sequence for Plotly pie / bar charts.
"""

from __future__ import annotations

import streamlit as st

# ── Color palette ──────────────────────────────────────────────────────────────

GREEN  = "#2ecc71"   # backward-compat — keep for Altair chart encoding
RED    = "#e74c3c"
BLUE   = "#3498db"
YELLOW = "#f39c12"

# Extended green palette
GREEN_VIVID   = "#00c853"
GREEN_DARK    = "#1b5e20"
GREEN_MEDIUM  = "#388e3c"
GREEN_LIGHT   = "#a5d6a7"
GREEN_TEAL    = "#00897b"
GREEN_CARD_BG = "#0d1f12"
GREEN_STRIPE  = "#112218"

DARK_BG     = "#0b1621"
CARD_BORDER = "#243447"
BANNER_BG   = "#1e2530"

# 7-color green sequence for Plotly pie / treemap / bar charts
GREEN_PIE_PALETTE = [
    "#00c853", "#2e7d32", "#00897b", "#388e3c",
    "#69f0ae", "#004d40", "#a5d6a7",
]

_HERO_GRADIENT = "linear-gradient(135deg, #1b5e20 0%, #2e7d32 45%, #00695c 100%)"

# ── Shared CSS ─────────────────────────────────────────────────────────────────

_BASE_CSS = f"""
<style>
/* ── Hero header ── */
.hero-container {{
    padding: 1.5rem 1.75rem;
    border-radius: 18px;
    background: {_HERO_GRADIENT};
    color: white;
    margin-bottom: 0.75rem;
}}
.hero-title {{
    font-size: 2.1rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
}}
.hero-subtitle {{
    font-size: 1rem;
    color: {GREEN_LIGHT};
    margin-top: 0.25rem;
}}
.hero-pill {{
    display: inline-block;
    padding: 0.15rem 0.7rem;
    border-radius: 999px;
    background-color: rgba(255,255,255,0.12);
    font-size: 0.8rem;
    margin-bottom: 0.5rem;
}}

/* ── Metric cards (default st.metric) ── */
div[data-testid="metric-container"] {{
    background-color: {DARK_BG};
    padding: 10px 14px;
    border-radius: 14px;
    border: 1px solid {CARD_BORDER};
}}
div[data-testid="metric-container"] > label > div {{
    font-size: 0.75rem;
    font-weight: 500;
}}
div[data-testid="metric-container"] > div {{
    font-size: 0.95rem;
    font-weight: 600;
    overflow-wrap: anywhere;
}}

/* ── Section titles and labels ── */
.section-title {{
    font-size: 1.2rem;
    font-weight: 600;
    color: #2e7d32;
    margin-top: 0.75rem;
    margin-bottom: 0.25rem;
}}
.muted-label {{
    font-size: 0.8rem;
    color: #333;
}}

/* ── Stat cards ── */
.stat-card {{
    background: {GREEN_CARD_BG};
    border: 1px solid {GREEN_DARK};
    border-left: 4px solid {GREEN_VIVID};
    border-radius: 12px;
    padding: 16px 20px;
    box-sizing: border-box;
}}
.stat-card-label {{
    color: {GREEN_LIGHT};
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
.stat-card-value {{
    color: #fff;
    font-size: 1.85rem;
    font-weight: 700;
    margin: 4px 0;
    word-break: break-all;
}}
.stat-card-delta-pos {{ color: {GREEN_VIVID}; font-size: 0.85rem; }}
.stat-card-delta-neg {{ color: #e74c3c;  font-size: 0.85rem; }}
.stat-card-subtitle  {{ color: {GREEN_LIGHT}; font-size: 0.78rem; margin-top: 4px; opacity: 0.8; }}

/* ── Stat card grid ── */
.stat-card-grid {{
    display: grid;
    gap: 12px;
    margin-bottom: 8px;
}}

/* ── HTML fin-tables ── */
.fin-table {{ width: 100%; border-collapse: collapse; border-radius: 10px; overflow: hidden; }}
.fin-table thead tr {{ background: {GREEN_DARK}; }}
.fin-table th {{
    color: {GREEN_LIGHT};
    padding: 10px 14px;
    text-align: left;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
.fin-table tbody tr:nth-child(odd)  {{ background: {GREEN_CARD_BG}; }}
.fin-table tbody tr:nth-child(even) {{ background: {GREEN_STRIPE}; }}
.fin-table td {{ color: #e0e0e0; padding: 9px 14px; font-size: 0.88rem; }}
.fin-table td.positive {{ color: {GREEN_VIVID}; font-weight: 600; }}
.fin-table td.negative {{ color: #e74c3c;  font-weight: 600; }}

/* ── Badges ── */
.badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    margin: 1px;
}}
.badge-green  {{ background: {GREEN_DARK}; color: {GREEN_LIGHT}; }}
.badge-red    {{ background: #7f0000;  color: #ef9a9a; }}
.badge-yellow {{ background: #e65100;  color: #ffe0b2; }}
.badge-teal   {{ background: #004d40;  color: #80cbc4; }}

/* ── Section headers ── */
.sec-header {{
    border-left: 4px solid {GREEN_VIVID};
    padding: 8px 12px;
    margin: 18px 0 10px 0;
    background: rgba(0,200,83,0.08);
    border-radius: 0 6px 6px 0;
}}
.sec-header-title {{ color: #2e7d32; font-size: 1.1rem; font-weight: 700; }}
.sec-header-sub   {{ color: #388e3c; font-size: 0.82rem; margin-top: 2px; }}

/* ── Progress bar ── */
.prog-bg   {{ background: #1b2a1d; border-radius: 999px; height: 8px; }}
.prog-fill {{ height: 8px; border-radius: 999px;
              background: linear-gradient(90deg, {GREEN_DARK}, {GREEN_VIVID}); }}

/* ── Gradient divider ── */
.grad-div {{
    height: 2px;
    margin: 16px 0;
    background: linear-gradient(90deg, {GREEN_VIVID}, {GREEN_TEAL}, transparent);
}}
</style>
"""


def apply_base_css() -> None:
    """Inject shared CSS for the hero header, metric cards, fin-tables, etc.

    Safe to call multiple times per page — Streamlit de-duplicates identical
    HTML injections within a single render.
    """
    st.html(_BASE_CSS)


def page_header(
    title: str,
    icon: str = "",
    subtitle: str = "",
    pills: list | None = None,
) -> None:
    """Render the gradient hero header used on every page.

    Automatically injects the shared base CSS so callers don't need a
    separate apply_base_css() call.

    Args:
        title:    Page title text (without icon).
        icon:     Optional emoji prefix shown before the title (e.g. "📈").
        subtitle: Optional second line of smaller descriptive text.
        pills:    Optional list of short strings rendered as pill badges above
                  the title — useful for status labels on the home dashboard.
    """
    apply_base_css()

    title_text = f"{icon}&nbsp;{title}" if icon else title

    pills_html = ""
    if pills:
        pills_html = (
            "<div style='margin-bottom:0.4rem;'>"
            + "".join(f"<span class='hero-pill'>{p}</span>&nbsp;" for p in pills)
            + "</div>"
        )

    subtitle_html = (
        f"<div class='hero-subtitle'>{subtitle}</div>" if subtitle else ""
    )

    st.html(
        f"""
        <div class='hero-container'>
            {pills_html}
            <div class='hero-title'>{title_text}</div>
            {subtitle_html}
        </div>
        """
    )


# ── Component functions ────────────────────────────────────────────────────────

def stat_card(
    label: str,
    value: str,
    delta: str | None = None,
    positive: bool = True,
    icon: str = "",
    subtitle: str | None = None,
) -> str:
    """Return HTML string for a rich green stat card.

    Callers render via ``st.html(stat_card(...))``.
    """
    icon_html = (
        f"<span style='font-size:1.1rem;margin-right:6px;'>{icon}</span>"
        if icon else ""
    )
    delta_class = "stat-card-delta-pos" if positive else "stat-card-delta-neg"
    arrow = "▲" if positive else "▼"
    delta_html = (
        f"<div class='{delta_class}'>{arrow} {delta}</div>" if delta else ""
    )
    subtitle_html = (
        f"<div class='stat-card-subtitle'>{subtitle}</div>" if subtitle else ""
    )
    return f"""
<div class='stat-card'>
  <div class='stat-card-label'>{icon_html}{label}</div>
  <div class='stat-card-value'>{value}</div>
  {delta_html}
  {subtitle_html}
</div>
"""


def stat_card_grid(cards: list[dict], cols: int = 4) -> str:
    """Return HTML for a CSS grid of stat cards.

    Each dict in *cards* may contain: label, value, delta, positive, icon,
    subtitle (all optional except label and value).
    """
    card_html = "".join(
        stat_card(
            label=c.get("label", ""),
            value=c.get("value", ""),
            delta=c.get("delta"),
            positive=c.get("positive", True),
            icon=c.get("icon", ""),
            subtitle=c.get("subtitle"),
        )
        for c in cards
    )
    return f"""
<div class='stat-card-grid' style='grid-template-columns:repeat({cols},1fr);'>
  {card_html}
</div>
"""


def badge(text: str, color: str = "green") -> str:
    """Return HTML for a colored pill badge.

    *color* must be one of: ``"green"``, ``"red"``, ``"yellow"``, ``"teal"``.
    """
    return f"<span class='badge badge-{color}'>{text}</span>"


def score_badge(score: float) -> str:
    """Return a colored badge for a 0–100 buy score.

    ≥ 70 → green, 40–69 → yellow, < 40 → red.
    """
    try:
        s = float(score)
    except (TypeError, ValueError):
        return f"<span class='badge badge-teal'>{score}</span>"

    if s >= 70:
        color = "green"
    elif s >= 40:
        color = "yellow"
    else:
        color = "red"
    return badge(f"{s:.0f}", color)


def section_header(title: str, subtitle: str = "", icon: str = "") -> str:
    """Return HTML for a green left-border section header.

    Callers render via ``st.html(section_header(...))``.
    """
    prefix = f"{icon} " if icon else ""
    sub_html = (
        f"<div class='sec-header-sub'>{subtitle}</div>" if subtitle else ""
    )
    return f"""
<div class='sec-header'>
  <div class='sec-header-title'>{prefix}{title}</div>
  {sub_html}
</div>
"""


def progress_bar(value: float, max_val: float = 100) -> str:
    """Return HTML for a gradient green progress bar (0 → max_val)."""
    pct = min(100.0, max(0.0, (value / max_val * 100) if max_val else 0))
    return f"""
<div class='prog-bg'>
  <div class='prog-fill' style='width:{pct:.1f}%;'></div>
</div>
"""


def grad_divider() -> str:
    """Return HTML for a green → teal gradient rule."""
    return "<div class='grad-div'></div>"


def html_table(
    df,
    col_labels: dict,
    formatters: dict | None = None,
    pos_cols: tuple | list = (),
    neg_cols: tuple | list = (),
    ticker_col: str | None = None,
) -> str:
    """Return a styled HTML fin-table.

    Args:
        df:         DataFrame to render.
        col_labels: ``{original_col: display_header}`` mapping.  Only columns
                    present in *df* are included.
        formatters: ``{display_header: fmt}`` where *fmt* is either a Python
                    format string (e.g. ``"${:,.2f}"``) or a callable that
                    accepts a cell value and returns an HTML string.
        pos_cols:   Original column names whose cells get the ``.positive``
                    CSS class (vivid green text).
        neg_cols:   Original column names whose cells get the ``.negative``
                    CSS class (red text).
        ticker_col: Original column name whose values are wrapped as teal
                    badge pills.

    Returns:
        HTML string — render with ``st.html(html_table(...))``.
    """
    if formatters is None:
        formatters = {}

    # Only keep columns that actually exist
    valid = {k: v for k, v in col_labels.items() if k in df.columns}
    if not valid:
        return "<p style='color:#333;'>No data to display.</p>"

    subset = df[list(valid.keys())].copy()
    subset = subset.rename(columns=valid)
    display_labels = list(valid.values())

    # Pre-compute sets of display labels for coloring
    pos_display = {valid[c] for c in pos_cols if c in valid}
    neg_display = {valid[c] for c in neg_cols if c in valid}
    ticker_display = valid.get(ticker_col) if ticker_col else None

    # Header
    ths = "".join(f"<th>{lbl}</th>" for lbl in display_labels)
    header = f"<thead><tr>{ths}</tr></thead>"

    # Rows
    rows = []
    for _, row in subset.iterrows():
        cells = []
        for lbl in display_labels:
            raw = row[lbl]
            # Format
            if lbl in formatters:
                fmt = formatters[lbl]
                if callable(fmt):
                    cell_str = fmt(raw)
                else:
                    try:
                        cell_str = fmt.format(raw)
                    except (ValueError, TypeError):
                        cell_str = "N/A" if _is_na(raw) else str(raw)
            else:
                cell_str = "N/A" if _is_na(raw) else str(raw)

            # Ticker badge
            if lbl == ticker_display:
                cell_str = f"<span class='badge badge-teal'>{cell_str}</span>"

            # CSS class
            if lbl in pos_display:
                td = f"<td class='positive'>{cell_str}</td>"
            elif lbl in neg_display:
                td = f"<td class='negative'>{cell_str}</td>"
            else:
                td = f"<td>{cell_str}</td>"
            cells.append(td)
        rows.append(f"<tr>{''.join(cells)}</tr>")

    body = f"<tbody>{''.join(rows)}</tbody>"
    return (
        f"<div style='overflow-x:auto;'>"
        f"<table class='fin-table'>{header}{body}</table>"
        f"</div>"
    )


def _is_na(val) -> bool:
    """Return True if *val* is None, NaN, or pandas NA."""
    if val is None:
        return True
    try:
        import math
        if isinstance(val, float) and math.isnan(val):
            return True
    except (TypeError, ValueError):
        pass
    try:
        import pandas as pd
        if pd.isna(val):
            return True
    except Exception:
        pass
    return False
