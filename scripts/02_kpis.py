MAX_PIE_SLICES = 6            
TOP_N_SUBCATEGORIES = 5
MIN_ORDERS_FOR_MARGIN = 10    
ACCENT = "#2F5D8A"

# Category pie: blue + champagne gold, then coordinating colours if more categories appear.
PALETTE = ["#162032", "#E2A678", "#7C543F", "#C28961", "#162032", "#E7CCB2"]
OTHER_COLOR = "#B0B7C3"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def s(v):
    return "" if v is None else str(v).strip()

def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

def pct_change(new, old):
    return round(100.0 * (new - old) / old, 1) if old else None

def money(v):
    return format(v, ",.0f")

def month_label(ym):
    y, m = ym.split("-")
    return MONTHS[int(m) - 1] + " " + y

def days_in_month(y, m):
    if m == 2:
        return 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28
    return 30 if m in (4, 6, 9, 11) else 31

rows = [item["json"] for item in _items]

# ---------- monthly totals ----------
by_month = {}
for r in rows:
    ym = s(r.get("year_month"))
    if not ym:
        continue
    b = by_month.setdefault(ym, {"rev": 0.0, "profit": 0.0, "orders": 0, "returned": 0, "completed": 0, "cancelled": 0, "dates": set()})
    b["rev"] += f(r.get("net_revenue"))
    b["profit"] += f(r.get("net_profit"))
    b["orders"] += 1
    st = s(r.get("order_status"))
    if st == "Returned":
        b["returned"] += 1
    elif st == "Completed":
        b["completed"] += 1
    elif st == "Cancelled":
        b["cancelled"] += 1
    b["dates"].add(s(r.get("order_date")))

months = sorted(by_month)
if not months:
    return [{"json": {"error": "No orders received"}}]
latest = months[-1]
prev = months[-2] if len(months) > 1 else None
L = by_month[latest]
P = by_month[prev] if prev else None
latest_lbl = month_label(latest)
prev_lbl = month_label(prev) if prev else ""

def margin(b):
    return round(100.0 * b["profit"] / b["rev"], 1) if b and b["rev"] else 0.0

def ret_rate(b):
    return round(100.0 * b["returned"] / b["orders"], 1) if b and b["orders"] else 0.0

ly, lm = int(latest[:4]), int(latest[5:7])
partial = len(L["dates"]) < days_in_month(ly, lm)

# ---------- group the latest month by a column ----------
def agg_by(key, month):
    out = {}
    if not month:
        return out
    for r in rows:
        if s(r.get("year_month")) != month:
            continue
        k = s(r.get(key)) or "Unknown"
        a = out.setdefault(k, {"rev": 0.0, "profit": 0.0, "orders": 0})
        a["rev"] += f(r.get("net_revenue"))
        a["profit"] += f(r.get("net_profit"))
        a["orders"] += 1
    return out

def ranked(d):
    return sorted([(k, v) for k, v in d.items() if v["rev"] > 0], key=lambda kv: -kv[1]["rev"])

def thousands(v):
    return round(v / 1000.0, 1)

def title(text):
    # The chart title is drawn in the email itself (see the report node), so it is hidden inside the image.
    return {"display": False, "text": text}

def body(chart, width, height, bg="white"):
    """Complete QuickChart request body - the HTTP node just sends it as-is."""
    return {"version": "2", "backgroundColor": bg, "width": width, "height": height,
            "devicePixelRatio": 2, "format": "png", "chart": chart}

# ---------- JS chart serializer (no imports, n8n Python compatible) ----------
# QuickChart needs a string chart config if it contains JavaScript functions.
def to_js(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return ('"' + value
                .replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t")
                .replace("\b", "\\b")
                .replace("\f", "\\f")
                .replace("\u2028", "\\u2028")
                .replace("\u2029", "\\u2029") + '"')
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(to_js(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(to_js(str(k)) + ":" + to_js(v) for k, v in value.items()) + "}"
    raise ValueError("Unsupported chart configuration value: " + str(type(value)))

# ---------- chart 1: net revenue by month ----------
# The vertical gradient is evaluated by QuickChart, NOT by this Python node.
chart_monthly = {
    "type": "line",
    "data": {
        "labels": [month_label(m) for m in months],
        "datasets": [{
            "label": "Net revenue (thousands)",
            "data": [thousands(by_month[m]["rev"]) for m in months],
            "borderColor": "#7C543F",
            "borderWidth": 3,
            "backgroundColor": "__GRADIENT__",
            "pointBorderColor": "#7C543F",
            "pointBackgroundColor": "#FFFFFF",
            "pointBorderWidth": 2,
            "pointRadius": 3,
            "pointHoverRadius": 5,
            "fill": True,
            "lineTension": 0.25,
        }],
    },
    "options": {
        "title": title("Net Revenue by Month"),
        "legend": {"display": False},
        "scales": {
            "yAxes": [{
                "ticks": {"beginAtZero": True},
                "scaleLabel": {"display": True, "labelString": "Net revenue (thousands)"},
            }],
        },
        "plugins": {"datalabels": {"display": False}},
    },
}

# Render the chart configuration as a JS string, and insert the gradient function.
# NO `import json` or other imports; n8n's restricted Python environment allows none.
chart_monthly_js = to_js(chart_monthly).replace(
    '"__GRADIENT__"',
    "getGradientFillHelper('vertical', ["
    "'rgba(124,84,63,0.40)',"
    "'rgba(194,137,97,0.22)',"
    "'rgba(226,166,120,0.08)',"
    "'rgba(255,255,255,0)'"
    "])"
)

# ---------- chart 2: category pie (latest month) ----------
cats = ranked(agg_by("category", latest))
if len(cats) > MAX_PIE_SLICES:
    head = cats[:MAX_PIE_SLICES - 1]
    other = sum(v["rev"] for _, v in cats[MAX_PIE_SLICES - 1:])
    cats = head + [("Other", {"rev": other})]
cat_total = sum(v["rev"] for _, v in cats)
pie_labels = [k + " (" + str(round(100.0 * v["rev"] / cat_total, 1)) + "%)" for k, v in cats] if cat_total else []
pie_colors = [OTHER_COLOR if k == "Other" else PALETTE[i % len(PALETTE)] for i, (k, v) in enumerate(cats)]
chart_category = {
    "type": "pie",
    "data": {"labels": pie_labels,
             "datasets": [{"data": [round(v["rev"], 0) for _, v in cats], "backgroundColor": pie_colors}]},
    "options": {"title": title("Net Revenue by Category - " + latest_lbl),
                "legend": {"display": True, "position": "right"},
                "plugins": {"datalabels": {"display": False}}},
}

# ---------- horizontal bar helper (values shown in thousands) ----------
def hbar(names, values, text):
    return {
        "type": "horizontalBar",
        "data": {"labels": names,
                 "datasets": [{"label": "Net revenue (thousands)", "data": [thousands(v) for v in values],
                               "backgroundColor": ACCENT}]},
        "options": {"title": title(text), "legend": {"display": False},
                    "layout": {"padding": {"right": 40}},
                    "scales": {"xAxes": [{"ticks": {"beginAtZero": True},
                                          "scaleLabel": {"display": True, "labelString": "Net revenue (thousands)"}}]},
                    "plugins": {"datalabels": {"display": True, "anchor": "end", "align": "end",
                                               "color": "#222", "font": {"size": 11, "weight": "bold"}}}},
    }

# ---------- rank-based solid bar colours: dark navy -> light yellow ----------
# Each entire bar uses ONE solid colour. Lower-ranked bars become progressively lighter.
# Colour stops are shared by the subcategory and store charts.
RANK_BAR_PALETTE = [
    "#162032",  # Dark navy
    "#354A68",  # Muted navy blue
    "#718090",  # Slate blue
    "#B8ABA0",  # Warm taupe
    "#F1D88A",  # Champagne yellow
]

def ranked_bar_colors(count):
    """Return one rank-based solid colour per bar, even when there are >5 stores."""
    if count <= 0:
        return []
    if count == 1:
        return [RANK_BAR_PALETTE[0]]
    n_intervals = len(RANK_BAR_PALETTE) - 1
    out = []
    for i in range(count):
        pos = i * n_intervals / (count - 1)
        lo = min(int(pos), n_intervals - 1)
        t = pos - lo
        ca, cb = RANK_BAR_PALETTE[lo], RANK_BAR_PALETTE[lo + 1]
        rgb = []
        for k in (1, 3, 5):
            a = int(ca[k:k+2], 16)
            b = int(cb[k:k+2], 16)
            rgb.append(format(round(a + (b - a) * t), "02X"))
        out.append("#" + "".join(rgb))
    return out

# ---------- chart 3: top 5 subcategories ----------
subs = ranked(agg_by("subcategory", latest))[:TOP_N_SUBCATEGORIES]
chart_subcategory = hbar([k for k, _ in subs], [v["rev"] for _, v in subs],
                         "Top " + str(TOP_N_SUBCATEGORIES) + " Subcategories - " + latest_lbl)
chart_subcategory["data"]["datasets"][0]["backgroundColor"] = ranked_bar_colors(len(subs))
chart_subcategory["data"]["datasets"][0]["borderWidth"] = 0

# ---------- chart 4: stores (same rank-based solid colours) ----------
stores = agg_by("store_id", latest)
prev_stores = agg_by("store_id", prev)
st_ranked = ranked(stores)
chart_store = hbar(["Store " + k for k, _ in st_ranked], [v["rev"] for _, v in st_ranked],
                   "Net Revenue by Store - " + latest_lbl)
chart_store["data"]["datasets"][0]["backgroundColor"] = ranked_bar_colors(len(st_ranked))
chart_store["data"]["datasets"][0]["borderWidth"] = 0

# ---------- store facts for the LLM (all numbers pre-computed here) ----------
facts = []
total_store_rev = sum(v["rev"] for _, v in st_ranked)
if st_ranked and total_store_rev:
    k0, v0 = st_ranked[0]
    chg0 = pct_change(v0["rev"], prev_stores.get(k0, {}).get("rev", 0.0))
    facts.append("Top store: Store " + k0 + " with " + money(v0["rev"]) + " net revenue ("
                 + str(round(100.0 * v0["rev"] / total_store_rev, 1)) + "% of the month)"
                 + (", " + ("+" if chg0 > 0 else "") + str(chg0) + "% vs " + prev_lbl if chg0 is not None else "") + ".")
    top3 = st_ranked[:3]
    facts.append("Top 3 stores (" + ", ".join(k for k, _ in top3) + ") account for "
                 + str(round(100.0 * sum(v["rev"] for _, v in top3) / total_store_rev, 1)) + "% of net revenue.")
if prev_stores:
    keys = set(stores) | set(prev_stores)
    change = {k: stores.get(k, {"rev": 0.0})["rev"] - prev_stores.get(k, {"rev": 0.0})["rev"] for k in keys}
    avg_prev = sum(v["rev"] for v in prev_stores.values()) / len(prev_stores)
    def describe(k):
        pr = prev_stores.get(k, {"rev": 0.0})["rev"]
        pc = pct_change(stores.get(k, {"rev": 0.0})["rev"], pr)
        note = " (from a low base)" if pr < 0.25 * avg_prev else ""
        return "Store " + k + " (" + ("+" if change[k] > 0 else "") + money(change[k]) + ", " + (str(pc) + "%" if pc is not None else "n/a") + note + ")"
    gain = max(change, key=lambda k: change[k])
    drop = min(change, key=lambda k: change[k])
    facts.append("Biggest increase vs " + prev_lbl + ": " + describe(gain) + ". Biggest decrease: " + describe(drop) + ".")
    declined = sum(1 for k in keys if change[k] < 0)
    facts.append(str(declined) + " of " + str(len(keys)) + " stores had lower net revenue than in " + prev_lbl + ".")
elig = [(k, 100.0 * v["profit"] / v["rev"], v["orders"]) for k, v in stores.items()
        if v["orders"] >= MIN_ORDERS_FOR_MARGIN and v["rev"] > 0]
if elig:
    lo = min(elig, key=lambda t: t[1])
    hi = max(elig, key=lambda t: t[1])
    facts.append("Gross margin among stores with " + str(MIN_ORDERS_FOR_MARGIN) + "+ orders: lowest Store " + lo[0]
                 + " at " + str(round(lo[1], 1)) + "%, highest Store " + hi[0] + " at " + str(round(hi[1], 1)) + "%.")

# =====================================================================
# FACTS FOR THE LLM - one block per report section. All numbers are calculated here,
# so the model only has to put them into words.
# =====================================================================
def sgn(v, d=1):
    return ("+" if v > 0 else "") + str(round(v, d))

def vs(cur, old, unit="%", pts=False):
    """'X (+Y% vs Nov 2024)' style fragment."""
    if old is None:
        return ""
    ch = round(cur - old, 1) if pts else pct_change(cur, old)
    if ch is None:
        return ""
    return " (" + sgn(ch) + (" pts" if pts else "%") + " vs " + prev_lbl + ")"

def aov(b):
    return b["rev"] / b["completed"] if b and b["completed"] else 0.0

# ---- KPI facts (cards) ----
kf = []
kf.append("Net revenue: " + money(L["rev"]) + vs(L["rev"], P["rev"] if P else None) + ".")
kf.append("Orders placed: " + money(L["orders"]) + vs(L["orders"], P["orders"] if P else None)
          + "; completed orders: " + money(L["completed"]) + (" vs " + money(P["completed"]) if P else "") + ".")
kf.append("Average value of a completed order: " + money(aov(L)) + vs(aov(L), aov(P) if P else None) + ".")
kf.append("Gross margin: " + str(margin(L)) + "%" + vs(margin(L), margin(P) if P else None, pts=True)
          + "; net profit " + money(L["profit"]) + (" vs " + money(P["profit"]) if P else "") + ".")
kf.append("Return rate: " + str(ret_rate(L)) + "%" + vs(ret_rate(L), ret_rate(P) if P else None, pts=True)
          + "; returned orders " + str(L["returned"]) + (" vs " + str(P["returned"]) if P else "")
          + "; cancelled orders " + str(L["cancelled"]) + (" vs " + str(P["cancelled"]) if P else "") + ".")

# ---- trend facts (chart 1: net revenue by month) ----
tf = []
revs = [(m, by_month[m]["rev"]) for m in months]
if len(revs) >= 2:
    hi_m = max(revs, key=lambda t: t[1]); lo_m = min(revs, key=lambda t: t[1])
    avg_all = sum(v for _, v in revs) / len(revs)
    rank = sorted([v for _, v in revs], reverse=True).index(L["rev"]) + 1
    tf.append("The chart covers " + str(len(revs)) + " months (" + month_label(months[0]) + " to " + latest_lbl + ").")
    tf.append(latest_lbl + " net revenue is " + money(L["rev"]) + ", rank " + str(rank) + " of " + str(len(revs)) + " months; "
              + sgn(pct_change(L["rev"], avg_all)) + "% versus the " + str(len(revs)) + "-month average of " + money(avg_all) + ".")
    tf.append("Highest month: " + month_label(hi_m[0]) + " (" + money(hi_m[1]) + "). Lowest month: " + month_label(lo_m[0]) + " (" + money(lo_m[1]) + ").")
    ups = sum(1 for i in range(1, len(revs)) if revs[i][1] > revs[i - 1][1])
    tf.append("Month-on-month, revenue rose in " + str(ups) + " of " + str(len(revs) - 1) + " months. Monthly revenue is volatile, so single-month moves can be large.")
else:
    tf.append("Only one month of data is available, so no trend can be described.")

# ---- category facts (chart 2: pie) ----
cf = []
cat_now, cat_prev = agg_by("category", latest), agg_by("category", prev)
cn = ranked(cat_now); cn_total = sum(v["rev"] for _, v in cn)
if cn and cn_total:
    k0, v0 = cn[0]
    sh0 = 100.0 * v0["rev"] / cn_total
    sh0p = None
    if cat_prev and sum(v["rev"] for v in cat_prev.values()):
        sh0p = 100.0 * cat_prev.get(k0, {"rev": 0.0})["rev"] / sum(v["rev"] for v in cat_prev.values())
    cf.append("Largest category: " + k0 + " with " + money(v0["rev"]) + " (" + str(round(sh0, 1)) + "% of net revenue)"
              + (", share " + sgn(sh0 - sh0p) + " pts vs " + prev_lbl if sh0p is not None else "") + ".")
    cf.append("Categories ranked: " + "; ".join(k + " " + str(round(100.0 * v["rev"] / cn_total, 1)) + "%" for k, v in cn) + ".")
    if cat_prev:
        chg = {k: cat_now.get(k, {"rev": 0.0})["rev"] - cat_prev.get(k, {"rev": 0.0})["rev"] for k in set(cat_now) | set(cat_prev)}
        g, d = max(chg, key=lambda k: chg[k]), min(chg, key=lambda k: chg[k])
        cf.append("Biggest revenue gain vs " + prev_lbl + ": " + g + " (" + ("+" if chg[g] > 0 else "") + money(chg[g]) + "). Biggest drop: " + d + " (" + ("+" if chg[d] > 0 else "") + money(chg[d]) + ").")

# ---- sub-category facts (chart 3) ----
sf = []
sub_now, sub_prev = agg_by("subcategory", latest), agg_by("subcategory", prev)
sn = ranked(sub_now); sn_total = sum(v["rev"] for _, v in sn)
if sn and sn_total:
    top = sn[:TOP_N_SUBCATEGORIES]
    sf.append("Top " + str(len(top)) + " subcategories: " + "; ".join(
        k + " " + money(v["rev"]) + " (" + str(round(100.0 * v["rev"] / sn_total, 1)) + "%"
        + ((", " + sgn(pct_change(v["rev"], sub_prev[k]["rev"])) + "% vs " + prev_lbl)
           if sub_prev.get(k, {"rev": 0.0})["rev"] and pct_change(v["rev"], sub_prev[k]["rev"]) is not None else "") + ")"
        for k, v in top) + ".")
    sf.append("Together the top " + str(len(top)) + " make up " + str(round(100.0 * sum(v["rev"] for _, v in top) / sn_total, 1)) + "% of net revenue.")
    if len(top) > 1:
        sf.append("Gap between #1 (" + top[0][0] + ") and #2 (" + top[1][0] + "): " + money(top[0][1]["rev"] - top[1][1]["rev"]) + ".")

# ---------- best product (by net revenue, latest month) ----------
def prod_agg(month):
    out = {}
    if not month:
        return out
    for r in rows:
        if s(r.get("year_month")) != month:
            continue
        pid = s(r.get("product_id"))
        if not pid or pid.upper() == "UNKNOWN":
            continue
        a = out.setdefault(pid, {"rev": 0.0, "orders": 0, "name": s(r.get("product_name")),
                                 "cat": s(r.get("category")), "sub": s(r.get("subcategory"))})
        a["rev"] += f(r.get("net_revenue"))
        if r.get("is_completed") in (True, "true", "True", 1):
            a["orders"] += 1
    return out

prod_now, prod_prev = prod_agg(latest), prod_agg(prev)
best_product = {}
if prod_now:
    pid, a = max(prod_now.items(), key=lambda kv: kv[1]["rev"])
    if a["rev"] > 0:
        pr = prod_prev.get(pid, {}).get("rev", 0.0)
        best_product = {
            "best_product_id": pid,
            "best_product_name": a["name"] if a["name"] and a["name"] != "Unknown" else pid,
            "best_product_category": a["cat"],
            "best_product_subcategory": a["sub"],
            "best_product_orders": a["orders"],                       # completed orders containing this product
            "best_product_revenue": round(a["rev"], 2),
            "best_product_share_pct": round(100.0 * a["rev"] / L["rev"], 1) if L["rev"] else None,
            "best_product_mom_pct": pct_change(a["rev"], pr) if pr else None,
        }

# ---------- best store ----------
best_store = {}
if st_ranked:
    k0, v0 = st_ranked[0]
    pr = prev_stores.get(k0, {}).get("rev", 0.0)
    best_store = {
        "best_store_id": k0,
        "best_store_revenue": round(v0["rev"], 2),
        "best_store_orders": v0["orders"],
        "best_store_share_pct": round(100.0 * v0["rev"] / total_store_rev, 1) if total_store_rev else None,
        "best_store_mom_pct": pct_change(v0["rev"], pr) if pr else None,
    }

result = {
    "report_month": latest,
    "report_month_label": latest_lbl,
    "prev_month_label": prev_lbl,
    "first_month_label": month_label(months[0]),
    "latest_month_partial": partial,
    "latest_month_days": len(L["dates"]),

    "net_revenue": round(L["rev"], 2),
    "net_revenue_prev": round(P["rev"], 2) if P else None,
    "net_revenue_mom_pct": pct_change(L["rev"], P["rev"]) if P else None,

    "gross_margin_pct": margin(L),
    "gross_margin_prev_pct": margin(P) if P else None,
    "gross_margin_change_pts": round(margin(L) - margin(P), 1) if P else None,

    "orders": L["orders"],
    "orders_prev": P["orders"] if P else None,
    "orders_mom_pct": pct_change(L["orders"], P["orders"]) if P else None,

    "return_rate_pct": ret_rate(L),
    "return_rate_prev_pct": ret_rate(P) if P else None,
    "return_rate_change_pts": round(ret_rate(L) - ret_rate(P), 1) if P else None,

    "kpi_facts": "\n".join("- " + x for x in kf),
    "trend_facts": "\n".join("- " + x for x in tf),
    "category_facts": "\n".join("- " + x for x in cf),
    "subcategory_facts": "\n".join("- " + x for x in sf),
    "store_facts": "\n".join("- " + x for x in facts),

    # 4 chart request bodies, in the order they appear in the Merge node / email
    "chart_monthly": body(chart_monthly_js, 600, 340),
    "chart_category": body(chart_category, 600, 340),
    "chart_subcategory": body(chart_subcategory, 600, 300),
    "chart_store": body(chart_store, 600, 460),
}
result.update(best_product)
result.update(best_store)
return [{"json": result}]
