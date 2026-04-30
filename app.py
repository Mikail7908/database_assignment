import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

st.set_page_config(
    page_title="Food Delivery Analytics",
    layout="wide"
)

# ── Connection ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    url = st.secrets["database"]["url"]
    return create_engine(url)

@st.cache_data(ttl=300)
def query(sql):
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)

# ── Page header ───────────────────────────────────────────────────────────────
st.title("Food Delivery Platform — Analytics Dashboard")
st.markdown(
    "Live business intelligence dashboard connected to a PostgreSQL database "
    "(Supabase). Data covers orders placed January – April 2026 across "
    "5 restaurants, 5 customers, and 5 delivery drivers."
)
st.divider()

# ── Query 1: Restaurant Revenue ───────────────────────────────────────────────
st.header("1. Restaurant Revenue Ranking")
st.markdown(
    "Joins `restaurant`, `orders`, and `order_item` to rank partner restaurants "
    "by total delivered revenue — supports promotional placement decisions."
)

with st.expander("Show SQL"):
    st.code("""
SELECT
    r.name                                     AS restaurant_name,
    r.cuisine_type,
    COUNT(DISTINCT o.order_id)                 AS completed_orders,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS food_revenue,
    ROUND(SUM(o.delivery_fee), 2)              AS delivery_fees,
    ROUND(SUM(o.total_amount), 2)              AS total_revenue
FROM restaurant r
JOIN orders     o  ON r.restaurant_id = o.restaurant_id
JOIN order_item oi ON o.order_id      = oi.order_id
WHERE o.status = 'delivered'
GROUP BY r.restaurant_id, r.name, r.cuisine_type
ORDER BY total_revenue DESC;
    """, language="sql")

df1 = query("""
    SELECT r.name AS restaurant_name, r.cuisine_type,
           COUNT(DISTINCT o.order_id) AS completed_orders,
           ROUND(SUM(oi.quantity * oi.unit_price), 2) AS food_revenue,
           ROUND(SUM(o.delivery_fee), 2) AS delivery_fees,
           ROUND(SUM(o.total_amount), 2) AS total_revenue
    FROM restaurant r
    JOIN orders     o  ON r.restaurant_id = o.restaurant_id
    JOIN order_item oi ON o.order_id      = oi.order_id
    WHERE o.status = 'delivered'
    GROUP BY r.restaurant_id, r.name, r.cuisine_type
    ORDER BY total_revenue DESC
""")

col1, col2 = st.columns([2, 1])
with col1:
    fig1 = px.bar(
        df1, x="total_revenue", y="restaurant_name", orientation="h",
        color="cuisine_type", text="total_revenue",
        labels={"total_revenue": "Total Revenue (GBP)", "restaurant_name": "",
                "cuisine_type": "Cuisine"},
        title="Total Revenue by Restaurant (Delivered Orders)"
    )
    fig1.update_traces(texttemplate="GBP %{text:.2f}", textposition="outside")
    fig1.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=True)
    st.plotly_chart(fig1, use_container_width=True)
with col2:
    st.dataframe(df1, use_container_width=True, hide_index=True)

st.divider()

# ── Query 2: Top Menu Items ───────────────────────────────────────────────────
st.header("2. Top 10 Most Ordered Menu Items")
st.markdown(
    "Joins `menu_item`, `order_item`, `orders`, and `restaurant` to identify "
    "best-selling dishes — supports stock planning and promotions."
)

with st.expander("Show SQL"):
    st.code("""
SELECT
    mi.name                                    AS item_name,
    r.name                                     AS restaurant_name,
    mi.category,
    SUM(oi.quantity)                           AS total_units_sold,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS item_revenue
FROM menu_item  mi
JOIN order_item oi ON mi.item_id       = oi.item_id
JOIN orders     o  ON oi.order_id      = o.order_id
JOIN restaurant r  ON mi.restaurant_id = r.restaurant_id
WHERE o.status = 'delivered'
GROUP BY mi.item_id, mi.name, r.name, mi.category, mi.price
ORDER BY total_units_sold DESC
LIMIT 10;
    """, language="sql")

df2 = query("""
    SELECT mi.name AS item_name, r.name AS restaurant_name, mi.category,
           SUM(oi.quantity) AS total_units_sold,
           ROUND(SUM(oi.quantity * oi.unit_price), 2) AS item_revenue
    FROM menu_item  mi
    JOIN order_item oi ON mi.item_id       = oi.item_id
    JOIN orders     o  ON oi.order_id      = o.order_id
    JOIN restaurant r  ON mi.restaurant_id = r.restaurant_id
    WHERE o.status = 'delivered'
    GROUP BY mi.item_id, mi.name, r.name, mi.category, mi.price
    ORDER BY total_units_sold DESC
    LIMIT 10
""")

col1, col2 = st.columns([2, 1])
with col1:
    fig2 = px.bar(
        df2, x="total_units_sold", y="item_name", orientation="h",
        color="category", text="total_units_sold",
        labels={"total_units_sold": "Total Units Sold", "item_name": "",
                "category": "Category"},
        title="Top 10 Most Ordered Menu Items"
    )
    fig2.update_traces(textposition="outside")
    fig2.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig2, use_container_width=True)
with col2:
    st.dataframe(df2, use_container_width=True, hide_index=True)

st.divider()

# ── Query 3: Driver Performance ───────────────────────────────────────────────
st.header("3. Driver Performance")
st.markdown(
    "Joins `driver`, `orders`, and `review` to compare average delivery time "
    "and customer rating per driver — informs performance management."
)

with st.expander("Show SQL"):
    st.code("""
SELECT
    d.first_name || ' ' || d.last_name       AS driver_name,
    d.vehicle_type,
    COUNT(o.order_id)                         AS total_deliveries,
    ROUND(
        AVG(EXTRACT(EPOCH FROM (o.delivered_at - o.placed_at)) / 60)::NUMERIC
    , 1)                                      AS avg_delivery_minutes,
    ROUND(AVG(rv.driver_rating), 2)           AS avg_driver_rating
FROM driver d
JOIN orders      o  ON d.driver_id = o.driver_id
LEFT JOIN review rv ON o.order_id  = rv.order_id
WHERE o.status = 'delivered'
GROUP BY d.driver_id, d.first_name, d.last_name, d.vehicle_type
ORDER BY avg_driver_rating DESC;
    """, language="sql")

df3 = query("""
    SELECT d.first_name || ' ' || d.last_name AS driver_name,
           d.vehicle_type,
           COUNT(o.order_id) AS total_deliveries,
           ROUND(
               AVG(EXTRACT(EPOCH FROM (o.delivered_at - o.placed_at)) / 60)::NUMERIC
           , 1) AS avg_delivery_minutes,
           ROUND(AVG(rv.driver_rating), 2) AS avg_driver_rating
    FROM driver d
    JOIN orders      o  ON d.driver_id = o.driver_id
    LEFT JOIN review rv ON o.order_id  = rv.order_id
    WHERE o.status = 'delivered'
    GROUP BY d.driver_id, d.first_name, d.last_name, d.vehicle_type
    ORDER BY avg_driver_rating DESC
""")
df3["avg_delivery_minutes"] = df3["avg_delivery_minutes"].astype(float)
df3["avg_driver_rating"]    = df3["avg_driver_rating"].astype(float)

col1, col2 = st.columns(2)
with col1:
    fig3a = px.bar(
        df3, x="driver_name", y="avg_delivery_minutes", color="vehicle_type",
        text="avg_delivery_minutes",
        labels={"avg_delivery_minutes": "Avg Delivery Time (min)", "driver_name": "",
                "vehicle_type": "Vehicle"},
        title="Average Delivery Time per Driver"
    )
    fig3a.update_traces(texttemplate="%{text} min", textposition="outside")
    st.plotly_chart(fig3a, use_container_width=True)
with col2:
    fig3b = px.bar(
        df3, x="driver_name", y="avg_driver_rating", color="vehicle_type",
        text="avg_driver_rating",
        labels={"avg_driver_rating": "Avg Rating (out of 5)", "driver_name": "",
                "vehicle_type": "Vehicle"},
        title="Average Customer Rating per Driver"
    )
    fig3b.update_traces(textposition="outside")
    fig3b.update_layout(yaxis_range=[0, 6])
    st.plotly_chart(fig3b, use_container_width=True)

st.dataframe(df3, use_container_width=True, hide_index=True)
st.divider()

# ── Query 4: Monthly Trend ────────────────────────────────────────────────────
st.header("4. Monthly Order Volume and Revenue Trend")
st.markdown(
    "Aggregates `orders` by month — reveals platform growth trends "
    "to support business planning and forecasting."
)

with st.expander("Show SQL"):
    st.code("""
SELECT
    TO_CHAR(o.placed_at, 'YYYY-MM')                               AS month,
    COUNT(o.order_id)                                              AS total_orders,
    COUNT(o.order_id) FILTER (WHERE o.status = 'delivered')       AS delivered_orders,
    COUNT(o.order_id) FILTER (WHERE o.status = 'cancelled')       AS cancelled_orders,
    ROUND(
        SUM(o.total_amount) FILTER (WHERE o.status = 'delivered'), 2
    )                                                              AS monthly_revenue
FROM orders o
GROUP BY TO_CHAR(o.placed_at, 'YYYY-MM')
ORDER BY month;
    """, language="sql")

df4 = query("""
    SELECT TO_CHAR(o.placed_at, 'YYYY-MM') AS month,
           COUNT(o.order_id) AS total_orders,
           COUNT(o.order_id) FILTER (WHERE o.status = 'delivered') AS delivered_orders,
           COUNT(o.order_id) FILTER (WHERE o.status = 'cancelled') AS cancelled_orders,
           ROUND(SUM(o.total_amount) FILTER (WHERE o.status = 'delivered'), 2) AS monthly_revenue
    FROM orders o
    GROUP BY TO_CHAR(o.placed_at, 'YYYY-MM')
    ORDER BY month
""")
df4["monthly_revenue"] = df4["monthly_revenue"].astype(float)

fig4 = go.Figure()
fig4.add_trace(go.Scatter(
    x=df4["month"], y=df4["monthly_revenue"],
    mode="lines+markers+text", name="Revenue (GBP)",
    text=df4["monthly_revenue"].apply(lambda v: f"GBP {v:.2f}"),
    textposition="top center",
    line=dict(color="#4C72B0", width=3),
    fill="tozeroy", fillcolor="rgba(76,114,176,0.1)"
))
fig4.add_trace(go.Bar(
    x=df4["month"], y=df4["total_orders"],
    name="Total Orders", yaxis="y2",
    marker_color="rgba(221,132,82,0.5)"
))
fig4.update_layout(
    title="Monthly Order Volume and Revenue Trend (Jan-Apr 2026)",
    xaxis_title="Month",
    yaxis=dict(title="Revenue (GBP)", titlefont=dict(color="#4C72B0")),
    yaxis2=dict(title="Number of Orders", titlefont=dict(color="#DD8452"),
                overlaying="y", side="right"),
    legend=dict(x=0.01, y=0.99)
)
st.plotly_chart(fig4, use_container_width=True)
st.dataframe(df4, use_container_width=True, hide_index=True)
st.divider()

# ── Query 5: Customer LTV ─────────────────────────────────────────────────────
st.header("5. Customer Lifetime Value")
st.markdown(
    "Joins `customer` and `orders` to identify high-value customers for "
    "loyalty programmes and those at risk of churn."
)

with st.expander("Show SQL"):
    st.code("""
SELECT
    c.first_name || ' ' || c.last_name                            AS customer_name,
    COUNT(o.order_id)                                              AS total_orders,
    COUNT(o.order_id) FILTER (WHERE o.status = 'delivered')       AS completed_orders,
    ROUND(
        SUM(o.total_amount) FILTER (WHERE o.status = 'delivered'), 2
    )                                                              AS lifetime_value,
    ROUND(
        AVG(o.total_amount) FILTER (WHERE o.status = 'delivered'), 2
    )                                                              AS avg_order_value
FROM customer c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name
ORDER BY lifetime_value DESC;
    """, language="sql")

df5 = query("""
    SELECT c.first_name || ' ' || c.last_name AS customer_name,
           COUNT(o.order_id) AS total_orders,
           COUNT(o.order_id) FILTER (WHERE o.status = 'delivered') AS completed_orders,
           ROUND(SUM(o.total_amount) FILTER (WHERE o.status = 'delivered'), 2) AS lifetime_value,
           ROUND(AVG(o.total_amount) FILTER (WHERE o.status = 'delivered'), 2) AS avg_order_value
    FROM customer c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.first_name, c.last_name
    ORDER BY lifetime_value DESC
""")
df5["lifetime_value"]  = df5["lifetime_value"].astype(float)
df5["avg_order_value"] = df5["avg_order_value"].astype(float)

col1, col2 = st.columns([2, 1])
with col1:
    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        name="Lifetime Value", x=df5["customer_name"], y=df5["lifetime_value"],
        text=df5["lifetime_value"].apply(lambda v: f"GBP {v:.0f}"),
        textposition="outside", marker_color="#4C72B0"
    ))
    fig5.add_trace(go.Bar(
        name="Avg Order Value", x=df5["customer_name"], y=df5["avg_order_value"],
        marker_color="#55A868"
    ))
    fig5.update_layout(
        barmode="group",
        title="Customer Lifetime Value vs Average Order Value",
        yaxis_title="Value (GBP)",
        xaxis_title=""
    )
    st.plotly_chart(fig5, use_container_width=True)
with col2:
    st.dataframe(df5, use_container_width=True, hide_index=True)
