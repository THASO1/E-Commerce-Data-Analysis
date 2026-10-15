
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# 1. CONFIGURATION & THEME
# =========================================================

st.set_page_config(
    page_title="E-Commerce Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"

COLORS = {
    "background": "#0B1120",
    "card": "#131D2F",
    "border": "#263449",
    "text": "#E8EEF7",
    "muted": "#94A3B8",
    "cyan": "#22D3EE",
    "teal": "#2DD4BF",
    "blue": "#60A5FA",
    "purple": "#A78BFA",
    "orange": "#FBBF24",
    "red": "#FB7185",
}

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {COLORS["background"]};
        color: {COLORS["text"]};
    }}

    [data-testid="stSidebar"] {{
        background-color: #0F172A;
        border-right: 1px solid {COLORS["border"]};
    }}

    .block-container {{
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1600px;
    }}

    h1, h2, h3 {{
        color: {COLORS["text"]} !important;
        letter-spacing: -0.4px;
    }}

    .dashboard-subtitle {{
        color: {COLORS["muted"]};
        font-size: 0.95rem;
        margin-top: -10px;
        margin-bottom: 24px;
    }}

    .section-label {{
        color: {COLORS["cyan"]};
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 6px;
    }}

    .kpi-card {{
        background: linear-gradient(145deg, #172338, #111827);
        border: 1px solid {COLORS["border"]};
        border-radius: 14px;
        padding: 19px 20px;
        min-height: 132px;
    }}

    .kpi-label {{
        color: {COLORS["muted"]};
        font-size: 0.82rem;
        margin-bottom: 12px;
    }}

    .kpi-value {{
        color: {COLORS["text"]};
        font-size: clamp(1.25rem, 2vw, 1.9rem);
        font-weight: 750;
        line-height: 1.2;
    }}

    .kpi-accent {{
        height: 3px;
        width: 38px;
        border-radius: 5px;
        margin-top: 14px;
    }}

    div[data-testid="stPlotlyChart"] {{
        background-color: transparent;
    }}

    div[data-testid="stDataFrame"] {{
        border: 1px solid {COLORS["border"]};
        border-radius: 10px;
    }}

    div[data-testid="stAlert"] {{
        border-radius: 10px;
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 2. LOAD DATA
# =========================================================

@st.cache_data
def load_data():
    filenames = {
        "orders": "orders.csv",
        "order_items": "order_items.csv",
        "refunds": "order_item_refunds.csv",
        "products": "products.csv",
        "sessions": "website_sessions.csv",
        "pageviews": "website_pageviews.csv",
    }

    result = {}

    for key, filename in filenames.items():
        path = DATA_DIR / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Missing dataset: {path}"
            )

        result[key] = pd.read_csv(path)

    return result


try:
    data = load_data()
except Exception as exc:
    st.error(f"Unable to load the datasets: {exc}")
    st.stop()


# =========================================================
# 3. PREPARE TABLES
# =========================================================

orders = data["orders"].copy()
items = data["order_items"].copy()
refunds = data["refunds"].copy()
products = data["products"].copy()
sessions = data["sessions"].copy()

for frame, column in [
    (orders, "created_at"),
    (items, "created_at"),
    (refunds, "created_at"),
    (sessions, "created_at"),
]:
    frame[column] = pd.to_datetime(
        frame[column], errors="coerce"
    )

for frame, columns in [
    (orders, ["price_usd", "cogs_usd"]),
    (items, ["price_usd", "cogs_usd"]),
    (refunds, ["refund_amount_usd"]),
]:
    for column in columns:
        frame[column] = pd.to_numeric(
            frame[column], errors="coerce"
        )

orders = orders.dropna(
    subset=["created_at", "price_usd", "cogs_usd"]
)

items = items.dropna(
    subset=["created_at", "price_usd", "cogs_usd"]
)

sessions = sessions.dropna(
    subset=["created_at", "website_session_id"]
)

for column in ["utm_source", "utm_campaign", "device_type"]:
    if column in sessions.columns:
        sessions[column] = sessions[column].fillna("Unknown")

products["product_name"] = products["product_name"].fillna(
    products["product_id"].astype(str)
)

items = items.merge(
    products[["product_id", "product_name"]],
    on="product_id",
    how="left",
    validate="many_to_one",
)

items["product_name"] = items["product_name"].fillna(
    items["product_id"].astype(str)
)


# =========================================================
# 4. REUSABLE HELPERS
# =========================================================

def money(value):
    return f"${value:,.2f}"


def section_heading(kicker, title, description=None):
    st.markdown(
        f'<div class="section-label">{kicker}</div>',
        unsafe_allow_html=True,
    )
    st.subheader(title)

    if description:
        st.caption(description)


def kpi_card(label, value, accent):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-accent"
                 style="background:{accent};"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_figure(fig, height=350):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Arial, sans-serif",
            color=COLORS["text"],
            size=12,
        ),
        title=dict(
            font=dict(size=16, color=COLORS["text"]),
            x=0.02,
            xanchor="left",
        ),
        height=height,
        margin=dict(l=24, r=24, t=78, b=42),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11),
            itemwidth=75,
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor=COLORS["border"],
        ),
        yaxis=dict(
            gridcolor="rgba(148,163,184,0.12)",
            zeroline=False,
            linecolor=COLORS["border"],
        ),
        hoverlabel=dict(
            bgcolor="#172338",
            font_color=COLORS["text"],
        ),
    )

    return fig


def filter_by_date(frame, start, end):
    return frame.loc[
        (frame["created_at"] >= pd.Timestamp(start))
        & (
            frame["created_at"]
            < pd.Timestamp(end) + pd.Timedelta(days=1)
        )
    ].copy()


# =========================================================
# 5. HEADER
# =========================================================

st.markdown(
    '<div class="section-label">BUSINESS INTELLIGENCE</div>',
    unsafe_allow_html=True,
)

st.title("E-Commerce Intelligence")

st.markdown(
    """
    <div class="dashboard-subtitle">
        Maven Fuzzy Factory · Sales, Marketing & Customer Analytics
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 6. SIDEBAR FILTERS
# =========================================================

st.sidebar.markdown("## Dashboard Controls")
st.sidebar.caption("Filter the analysis")

min_date = orders["created_at"].min().date()
max_date = orders["created_at"].max().date()

date_range = st.sidebar.date_input(
    "Order date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Select both a start date and an end date.")
    st.stop()

start_date, end_date = date_range

if start_date > end_date:
    st.sidebar.error("Start date must not exceed end date.")
    st.stop()

all_products = sorted(
    products["product_name"].dropna().unique().tolist()
)

selected_products = st.sidebar.multiselect(
    "Products",
    options=all_products,
    default=all_products,
)

all_sources = sorted(
    sessions["utm_source"].dropna().unique().tolist()
)

selected_sources = st.sidebar.multiselect(
    "Marketing sources",
    options=all_sources,
    default=all_sources,
)

st.sidebar.divider()
st.sidebar.caption("Maven Fuzzy Factory dataset")


# =========================================================
# 7. APPLY FILTERS
# =========================================================

filtered_orders = filter_by_date(
    orders, start_date, end_date
)

filtered_items = filter_by_date(
    items, start_date, end_date
)

filtered_refunds = refunds.copy()

filtered_sessions = filter_by_date(
    sessions, start_date, end_date
)

filtered_orders = filtered_orders.merge(
    products[["product_id", "product_name"]],
    left_on="primary_product_id",
    right_on="product_id",
    how="left",
    validate="many_to_one",
)

filtered_orders["product_name"] = (
    filtered_orders["product_name"].fillna("Unknown")
)

filtered_orders = filtered_orders.loc[
    filtered_orders["product_name"].isin(selected_products)
].copy()

filtered_items = filtered_items.loc[
    filtered_items["product_name"].isin(selected_products)
].copy()

filtered_sessions = filtered_sessions.loc[
    filtered_sessions["utm_source"].isin(selected_sources)
].copy()

# Keep only orders originating from the filtered sessions.
# This is appropriate for the marketing-source selection.
allowed_session_ids = set(
    filtered_sessions["website_session_id"]
)

marketing_orders = filtered_orders.loc[
    filtered_orders["website_session_id"].isin(
        allowed_session_ids
    )
].copy()


# =========================================================
# 8. EXECUTIVE KPIs
# =========================================================

section_heading(
    "01 / OVERVIEW",
    "Executive Overview",
    f"Order dates: {start_date:%d %b %Y} — {end_date:%d %b %Y}",
)

revenue = filtered_orders["price_usd"].sum()
cogs = filtered_orders["cogs_usd"].sum()
profit = revenue - cogs
order_count = filtered_orders["order_id"].nunique()

aov = revenue / order_count if order_count else 0
margin = profit / revenue * 100 if revenue else 0

k1, k2, k3, k4 = st.columns(4)

with k1:
    kpi_card("TOTAL REVENUE", money(revenue), COLORS["cyan"])

with k2:
    kpi_card("TOTAL PROFIT", money(profit), COLORS["teal"])

with k3:
    kpi_card("TOTAL ORDERS", f"{order_count:,}", COLORS["blue"])

with k4:
    kpi_card("AVERAGE ORDER VALUE", money(aov), COLORS["purple"])

st.write("")

k5, k6, k7, k8 = st.columns(4)

with k5:
    kpi_card("COST OF GOODS SOLD", money(cogs), COLORS["orange"])

with k6:
    kpi_card("PROFIT MARGIN", f"{margin:.2f}%", COLORS["teal"])

with k7:
    kpi_card(
        "PRODUCTS SOLD",
        f"{filtered_items['order_item_id'].nunique():,}",
        COLORS["blue"],
    )

with k8:
    kpi_card(
        "WEBSITE SESSIONS",
        f"{len(filtered_sessions):,}",
        COLORS["purple"],
    )


# =========================================================
# 9. SALES TRENDS
# =========================================================

st.divider()

section_heading(
    "02 / SALES",
    "Sales Performance",
    "Track revenue, profit, and order volume over time.",
)

if filtered_orders.empty:
    st.warning("No orders match the selected filters.")
else:
    monthly = filtered_orders.copy()

    monthly["month"] = (
        monthly["created_at"].dt.to_period("M").dt.to_timestamp()
    )

    monthly = (
        monthly.groupby("month", as_index=False)
        .agg(
            revenue=("price_usd", "sum"),
            cogs=("cogs_usd", "sum"),
            orders=("order_id", "nunique"),
        )
        .sort_values("month")
    )

    monthly["profit"] = monthly["revenue"] - monthly["cogs"]

    left, right = st.columns([1.7, 1])

    with left:
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=monthly["month"],
                y=monthly["revenue"],
                name="Revenue",
                mode="lines+markers",
                line=dict(color=COLORS["cyan"], width=3),
                fill="tozeroy",
                fillcolor="rgba(34,211,238,0.08)",
                hovertemplate="$%{y:,.2f}<extra>Revenue</extra>",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=monthly["month"],
                y=monthly["profit"],
                name="Profit",
                mode="lines",
                line=dict(color=COLORS["teal"], width=2),
                hovertemplate="$%{y:,.2f}<extra>Profit</extra>",
            )
        )

        fig.update_layout(
            title="Monthly Revenue & Profit",
            hovermode="x unified",
            margin=dict(l=58, r=24, t=88, b=58),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                font=dict(size=11),
                itemwidth=90,
                traceorder="normal",
            ),
            xaxis=dict(
                title="",
                tickformat="%b %Y",
                tickangle=0,
                ticklabelmode="period",
                nticks=7,
                automargin=True,
                showgrid=False,
                zeroline=False,
                linecolor=COLORS["border"],
            ),
            yaxis=dict(
                title="",
                tickprefix="$",
                tickformat=",.0f",
                automargin=True,
                gridcolor="rgba(148,163,184,0.12)",
                zeroline=False,
                linecolor=COLORS["border"],
            ),
        )

        st.plotly_chart(
            style_figure(fig, 390),
            use_container_width=True,
            config={"responsive": True, "displayModeBar": False},
        )

    with right:
        fig = px.bar(
            monthly,
            x="month",
            y="orders",
            title="Orders by Month",
            color_discrete_sequence=[COLORS["purple"]],
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Orders",
        )

        st.plotly_chart(
            style_figure(fig, 380),
            use_container_width=True,
        )


# =========================================================
# 10. PRODUCT PERFORMANCE
# =========================================================

st.divider()

section_heading(
    "03 / PRODUCTS",
    "Product Performance",
    "Compare product revenue, profit, and sales volume.",
)

if filtered_items.empty:
    st.info("No product sales match the current filters.")
else:
    product_summary = (
        filtered_items.groupby(
            ["product_id", "product_name"],
            as_index=False,
        )
        .agg(
            revenue=("price_usd", "sum"),
            cogs=("cogs_usd", "sum"),
            units=("order_item_id", "nunique"),
        )
    )

    product_summary["profit"] = (
        product_summary["revenue"] - product_summary["cogs"]
    )

    product_summary["profit_margin"] = np.where(
        product_summary["revenue"] > 0,
        product_summary["profit"]
        / product_summary["revenue"] * 100,
        0,
    )

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            product_summary.sort_values("revenue"),
            x="revenue",
            y="product_name",
            orientation="h",
            title="Revenue by Product",
            color="revenue",
            color_continuous_scale=["#164E63", COLORS["cyan"]],
            hover_data=["units", "profit"],
        )

        fig.update_layout(
            xaxis_title="Revenue (USD)",
            yaxis_title="",
            xaxis_tickprefix="$",
            coloraxis_showscale=False,
        )

        st.plotly_chart(
            style_figure(fig, 330),
            use_container_width=True,
        )

    with right:
        fig = px.bar(
            product_summary.sort_values("profit"),
            x="profit",
            y="product_name",
            orientation="h",
            title="Profit by Product",
            color_discrete_sequence=[COLORS["teal"]],
            hover_data=["units", "profit_margin"],
        )

        fig.update_layout(
            xaxis_title="Profit (USD)",
            yaxis_title="",
            xaxis_tickprefix="$",
        )

        st.plotly_chart(
            style_figure(fig, 330),
            use_container_width=True,
        )

    display = product_summary.rename(
        columns={
            "product_name": "Product",
            "units": "Units Sold",
            "revenue": "Revenue",
            "cogs": "COGS",
            "profit": "Profit",
            "profit_margin": "Profit Margin (%)",
        }
    )

    st.dataframe(
        display[
            [
                "Product",
                "Units Sold",
                "Revenue",
                "COGS",
                "Profit",
                "Profit Margin (%)",
            ]
        ].style.format(
            {
                "Revenue": "${:,.2f}",
                "COGS": "${:,.2f}",
                "Profit": "${:,.2f}",
                "Profit Margin (%)": "{:.2f}%",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# 11. MARKETING PERFORMANCE
# =========================================================

st.divider()

section_heading(
    "04 / MARKETING",
    "Marketing Performance",
    "Compare acquisition sources by sessions, orders, and revenue.",
)

if filtered_sessions.empty:
    st.info("No sessions match the selected marketing filters.")
else:
    session_orders = (
        marketing_orders.dropna(subset=["website_session_id"])
        .groupby("website_session_id", as_index=False)
        .agg(
            order_count=("order_id", "nunique"),
            revenue=("price_usd", "sum"),
        )
    )

    session_stats = filtered_sessions[
        ["website_session_id", "utm_source", "utm_campaign"]
    ].merge(
        session_orders,
        on="website_session_id",
        how="left",
        validate="one_to_one",
    )

    session_stats["order_count"] = (
        session_stats["order_count"].fillna(0)
    )

    session_stats["revenue"] = (
        session_stats["revenue"].fillna(0)
    )

    source_summary = (
        session_stats.groupby("utm_source", as_index=False)
        .agg(
            sessions=("website_session_id", "nunique"),
            orders=("order_count", "sum"),
            revenue=("revenue", "sum"),
        )
    )

    source_summary["conversion_rate"] = np.where(
        source_summary["sessions"] > 0,
        source_summary["orders"]
        / source_summary["sessions"] * 100,
        0,
    )

    unknown_source = source_summary.loc[
        source_summary["utm_source"].eq("Unknown")
    ]
    if not unknown_source.empty:
        unknown_revenue = unknown_source["revenue"].sum()
        unknown_sessions = unknown_source["sessions"].sum()
        total_source_revenue = source_summary["revenue"].sum()
        unknown_share = (
            unknown_revenue / total_source_revenue * 100
            if total_source_revenue > 0
            else 0
        )
        st.info(
            f"**Tracking insight — Unknown source:** "
            f"{unknown_sessions:,.0f} sessions and "
            f"{money(unknown_revenue)} in attributed revenue "
            f"({unknown_share:.1f}% of the revenue shown here) have no "
            f"recorded marketing source. This may reflect missing or "
            f"unavailable attribution data; review UTM tagging and session "
            f"tracking before assigning a cause."
        )

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            source_summary.sort_values("revenue"),
            x="revenue",
            y="utm_source",
            orientation="h",
            title="Revenue by Source",
            color_discrete_sequence=[COLORS["cyan"]],
        )

        fig.update_layout(
            xaxis_title="Revenue (USD)",
            yaxis_title="",
            xaxis_tickprefix="$",
        )

        st.plotly_chart(
            style_figure(fig, 330),
            use_container_width=True,
        )

    with right:
        fig = px.bar(
            source_summary.sort_values("conversion_rate"),
            x="conversion_rate",
            y="utm_source",
            orientation="h",
            title="Conversion Rate by Source",
            color_discrete_sequence=[COLORS["purple"]],
        )

        fig.update_layout(
            xaxis_title="Conversion Rate (%)",
            yaxis_title="",
            xaxis_ticksuffix="%",
        )

        st.plotly_chart(
            style_figure(fig, 330),
            use_container_width=True,
        )

    st.subheader("Campaign Breakdown")

    campaign_summary = (
        session_stats.groupby(
            ["utm_source", "utm_campaign"],
            as_index=False,
        )
        .agg(
            sessions=("website_session_id", "nunique"),
            orders=("order_count", "sum"),
            revenue=("revenue", "sum"),
        )
    )

    campaign_summary["conversion_rate"] = np.where(
        campaign_summary["sessions"] > 0,
        campaign_summary["orders"]
        / campaign_summary["sessions"] * 100,
        0,
    )

    st.dataframe(
        campaign_summary.rename(
            columns={
                "utm_source": "Source",
                "utm_campaign": "Campaign",
                "sessions": "Sessions",
                "orders": "Orders",
                "revenue": "Revenue",
                "conversion_rate": "Conversion Rate (%)",
            }
        ).style.format(
            {
                "Revenue": "${:,.2f}",
                "Conversion Rate (%)": "{:.2f}%",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# 12. CUSTOMER ANALYTICS
# =========================================================

st.divider()

section_heading(
    "05 / CUSTOMERS",
    "Customer Analytics",
    "Understand purchase frequency and customer value.",
)

if filtered_orders.empty:
    st.info("No customer purchase data in this date range.")
else:
    customer_summary = (
        filtered_orders.groupby("user_id", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            revenue=("price_usd", "sum"),
        )
    )

    customer_summary["segment"] = np.select(
        [
            customer_summary["orders"] == 1,
            customer_summary["orders"] == 2,
            customer_summary["orders"] >= 3,
        ],
        [
            "One-Time",
            "Repeat (2 Orders)",
            "High-Frequency (3+ Orders)",
        ],
        default="Other",
    )

    segment_summary = (
        customer_summary.groupby("segment", as_index=False)
        .agg(
            customers=("user_id", "nunique"),
            revenue=("revenue", "sum"),
            avg_revenue_per_customer=("revenue", "mean"),
        )
    )

    left, right = st.columns(2)

    with left:
        fig = px.pie(
            segment_summary,
            names="segment",
            values="customers",
            hole=0.62,
            title="Customer Distribution",
            color_discrete_sequence=[
                COLORS["cyan"],
                COLORS["purple"],
                COLORS["teal"],
            ],
        )

        fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
        )

        st.plotly_chart(
            style_figure(fig, 350),
            use_container_width=True,
        )

    with right:
        fig = px.bar(
            segment_summary,
            x="segment",
            y="avg_revenue_per_customer",
            title="Average Revenue per Customer",
            color_discrete_sequence=[COLORS["teal"]],
        )

        fig.update_layout(
            xaxis_title="Customer Segment",
            yaxis_title="Average Revenue (USD)",
            yaxis_tickprefix="$",
            xaxis_tickangle=-15,
        )

        st.plotly_chart(
            style_figure(fig, 350),
            use_container_width=True,
        )

    st.dataframe(
        segment_summary.rename(
            columns={
                "segment": "Segment",
                "customers": "Customers",
                "revenue": "Revenue",
                "avg_revenue_per_customer": "Average Revenue per Customer",
            }
        ).style.format(
            {
                "Revenue": "${:,.2f}",
                "Average Revenue per Customer": "${:,.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# 13. REFUND ANALYSIS
# =========================================================

st.divider()

section_heading(
    "06 / REFUNDS",
    "Refund Analysis",
    "Review refunded amounts and refunded items by product.",
)

if filtered_refunds.empty:
    st.info("No refunds match the selected refund date range.")
else:
    refund_items = filtered_refunds.dropna(
        subset=["order_item_id", "refund_amount_usd"]
    ).copy()

    # Map refunds to products using all order items. Refund dates can fall
    # outside the selected order-date range, so filtered_items may omit them.
    item_product_lookup = items[
        ["order_item_id", "product_id", "product_name"]
    ].drop_duplicates(subset=["order_item_id"])

    refund_items = refund_items.merge(
        item_product_lookup,
        on="order_item_id",
        how="left",
        validate="many_to_one",
    )
    refund_items["product_name"] = refund_items["product_name"].fillna(
        "Unknown product"
    )

    refund_amount = refund_items["refund_amount_usd"].sum()
    refunded_count = refund_items["order_item_id"].nunique()
    sold_count = filtered_items["order_item_id"].nunique()

    refund_rate = (
        refunded_count / sold_count * 100
        if sold_count
        else 0
    )

    r1, r2, r3 = st.columns(3)

    with r1:
        kpi_card("REFUNDED AMOUNT", money(refund_amount), COLORS["red"])

    with r2:
        kpi_card("REFUNDED ITEMS", f"{refunded_count:,}", COLORS["orange"])

    with r3:
        kpi_card("REFUNDED ITEM RATE", f"{refund_rate:.2f}%", COLORS["purple"])

    refund_product_summary = (
        refund_items.groupby(
            ["product_id", "product_name"],
            as_index=False,
        )
        .agg(
            refunded_amount=("refund_amount_usd", "sum"),
            refunded_items=("order_item_id", "nunique"),
        )
    )

    units_by_product = (
        filtered_items.groupby(
            ["product_id", "product_name"],
            as_index=False,
        )
        .agg(
            units_sold=("order_item_id", "nunique")
        )
    )

    refund_product_summary = refund_product_summary.merge(
        units_by_product,
        on=["product_id", "product_name"],
        how="left",
        validate="one_to_one",
    )

    refund_product_summary["refund_rate"] = np.where(
        refund_product_summary["units_sold"] > 0,
        refund_product_summary["refunded_items"]
        / refund_product_summary["units_sold"] * 100,
        0,
    )

    fig = px.bar(
        refund_product_summary.sort_values("refund_rate"),
        x="refund_rate",
        y="product_name",
        orientation="h",
        title="Refunded Item Rate by Product",
        color_discrete_sequence=[COLORS["red"]],
        hover_data=["refunded_items", "refunded_amount"],
    )

    fig.update_layout(
        xaxis_title="Refunded Item Rate (%)",
        yaxis_title="",
        xaxis_ticksuffix="%",
    )

    st.plotly_chart(
        style_figure(fig, 350),
        use_container_width=True,
    )


# =========================================================
# 14. FOOTER
# =========================================================

st.divider()

st.caption(
    "Built with Python · Streamlit · Pandas · NumPy · Plotly"
)

st.caption(
    "Maven Fuzzy Factory E-Commerce Analysis | Portfolio Project"
)
