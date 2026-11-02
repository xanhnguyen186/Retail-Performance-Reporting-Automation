MISSING_EMPLOYEE = "UNASSIGNED"
HIGH_VALUE_THRESHOLD = 50000          

def s(v):
    return "" if v is None else str(v).strip()

def to_num(v):
    t = s(v).replace(",", "").replace("$", "").replace("EGP", "").strip()
    try:
        return float(t)
    except ValueError:
        return None

# ---------- date helpers (no datetime available) ----------
def days_from_civil(y, m, d):
    y -= 1 if m <= 2 else 0
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468

def civil_from_days(z):
    z += 719468
    era = z // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + 3 if mp < 10 else mp - 9
    return (y + (1 if m <= 2 else 0), m, d)

def valid_ymd(y, m, d):
    return 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31

def parse_date(v):
    """-> (y, m, d) or None. Handles 2024-01-31, 2024-01-31T00:00:00Z, 31/01/2024, Excel serial numbers."""
    raw = s(v)
    if not raw:
        return None
    t = raw.replace("T", " ").split(" ")[0]
    for sep in ("-", "/"):
        p = t.split(sep)
        if len(p) == 3 and all(x.isdigit() for x in p):
            if len(p[0]) == 4 and valid_ymd(int(p[0]), int(p[1]), int(p[2])):
                return int(p[0]), int(p[1]), int(p[2])
            if len(p[2]) == 4 and valid_ymd(int(p[2]), int(p[1]), int(p[0])):   
                return int(p[2]), int(p[1]), int(p[0])
    if raw.replace(".", "", 1).isdigit() and 20000 < float(raw) < 60000:       
        ymd = civil_from_days(int(float(raw)) - 25569)
        if valid_ymd(*ymd):
            return ymd
    return None

def fmt(y, m, d):
    return str(y) + "-" + str(m).zfill(2) + "-" + str(d).zfill(2)

STATUS_MAP = {"completed": "Completed", "complete": "Completed",
              "returned": "Returned", "return": "Returned",
              "cancelled": "Cancelled", "canceled": "Cancelled", "cancel": "Cancelled"}

seen = set()
output = []

for item in _items:
    r = item["json"]

    # 1. De-duplicate on order_id (keep first)
    oid = s(r.get("order_id")).upper()
    if not oid or oid in seen:
        continue
    seen.add(oid)

    # 2. Dates: normalise order_date, rebuild date_id, add week/month keys
    ymd = parse_date(r.get("order_date"))
    if not ymd:
        continue                                   # an order with no usable date can't be tracked
    y, m, d = ymd
    z = days_from_civil(y, m, d)
    wy, wm, wd = civil_from_days(z - (z + 3) % 7)  # Monday of that week

    # 3. Amounts: must be numeric
    rev = to_num(r.get("total_revenue"))
    cost = to_num(r.get("total_cost"))
    if rev is None or cost is None:
        continue                                   # drop rows with unusable amounts (none in current file)
    rev, cost = round(rev, 2), round(cost, 2)

    # 4. Text columns
    status = STATUS_MAP.get(s(r.get("order_status")).lower(), s(r.get("order_status")).title())
    payment = s(r.get("payment_method"))           # fixes '  Cash  ' -> 'Cash'
    employee = s(r.get("employee_id")).upper()
    emp_missing = employee == ""
    if emp_missing:
        employee = MISSING_EMPLOYEE                # keep the order; revenue still counts

    # 4b. Product columns (from the Google Sheets lookup join). Blank -> "Unknown" so charts never break.
    product_id = s(r.get("product_id")).upper()
    product_name = s(r.get("product_name"))
    category = s(r.get("category")).title() or "Unknown"
    subcategory = s(r.get("subcategory")).title() or "Unknown"

    # 5. Performance fields. Only Completed orders count toward revenue/profit.
    completed = status == "Completed"
    profit = round(rev - cost, 2)

    output.append({"json": {
        "order_id": oid,
        "order_date": fmt(y, m, d),
        "date_id": int(str(y) + str(m).zfill(2) + str(d).zfill(2)),
        "year_month": str(y) + "-" + str(m).zfill(2),
        "week_start": fmt(wy, wm, wd),
        "customer_id": s(r.get("customer_id")).upper(),
        "store_id": int(s(r.get("store_id"))) if s(r.get("store_id")).isdigit() else s(r.get("store_id")),
        "employee_id": employee,
        "payment_method": payment,
        "order_status": status,
        "product_id": product_id or "UNKNOWN",
        "product_name": product_name or "Unknown",
        "category": category,
        "subcategory": subcategory,
        "total_revenue": rev,
        "total_cost": cost,
        "gross_profit": profit,
        "margin_pct": round(100.0 * profit / rev, 1) if rev else 0.0,
        "is_completed": completed,
        "net_revenue": rev if completed else 0.0,
        "net_cost": cost if completed else 0.0,
        "net_profit": profit if completed else 0.0,
        "is_negative_margin": profit < 0,
        "is_high_value": rev >= HIGH_VALUE_THRESHOLD,
        "employee_missing": emp_missing,
    }})

return output
