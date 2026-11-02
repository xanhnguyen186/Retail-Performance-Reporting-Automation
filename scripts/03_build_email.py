# ======================= SETTINGS - edit these =======================
REPORT_TITLE = "Monthly Performance Report"     # email subject
HERO_LABEL = "BUSINESS PERFORMANCE"
HERO_TITLE = "Monthly Report"
BRAND_NAME = "Lotus Group"                        
BRAND_LOGO_URL = ""                            
HERO_DESCRIPTION = "A snapshot of your store performance, insights and key trends."
KPI_SUMMARY_PREFIX = "This month,"                 
CURRENCY = "$"                                   

HERO_IMAGE_URL = "https://res.cloudinary.com/q8q8gpln/image/upload/v1793524353/Luxury_Winter_Boutique_Electronics_Display.png"  # REPLACE with direct URL of email_hero_kpi_extended.png
PRODUCT_IMAGE_URL = "https://res.cloudinary.com/q8q8gpln/image/upload/v1793525494/lotus_product_feature_background.png"  # REPLACE with email_product_blended.png URL
STORE_IMAGE_URL = "https://res.cloudinary.com/q8q8gpln/image/upload/v1793597075/lotus_store_feature_background.jpg"  # REPLACE with email_store_blended.png URL
# =====================================================================

NAVY, MUTED, INK = "#10214B", "#5B6B8C", "#0B1220"
GOOD, BAD, FLAT = "#16A34A", "#DC2626", "#64748B"
LINE = "#DCE6F5"
FONT = "Inter,Arial,Helvetica,sans-serif"

CHART_TAGS = ["TREND", "CATEGORY", "SUBCATEGORY", "STORE"]      

# ---------------------------- helpers ----------------------------
def esc(v):
    return (str(v).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))

def strip_tags(t):
    out, depth = [], 0
    for ch in str(t):
        if ch == "<":
            depth += 1
        elif ch == ">" and depth:
            depth -= 1
        elif not depth:
            out.append(ch)
    return "".join(out)

def clean_line(t):
    return strip_tags(t).replace("__", "").replace("`", "").strip()

def rich(text, strong_style="font-weight:700;"):
    """Escape the text, then turn **bold** markers into <strong>. Unbalanced markers are dropped."""
    parts = esc(text).split("**")
    if len(parts) % 2 == 0:
        parts = ["".join(parts)]
    parts = [p.replace("*", "") for p in parts]
    return "".join(p if i % 2 == 0 else '<strong style="' + strong_style + '">' + p + "</strong>"
                   for i, p in enumerate(parts))

def fnum(v, decimals=0):
    if v is None or v == "":
        return "-"
    return format(float(v), ",." + str(decimals) + "f")

def url_ok(u):
    return str(u).strip().startswith("http")

def lucide_icon(name, size=24):
    url = ICON_URLS.get(name, "")

    if not url_ok(url):
        return ""

    return (
        '<img src="' + esc(url) + '" '
        'width="' + str(size) + '" '
        'height="' + str(size) + '" '
        'alt="" '
        'style="display:inline-block;'
        'width:' + str(size) + 'px;'
        'height:' + str(size) + 'px;'
        'vertical-align:middle;border:0;">'
    )

def brand_logo(size=24):
    """Email-safe, optional Lotus Group logo. Empty URL means no icon."""
    if not url_ok(BRAND_LOGO_URL):
        return ""
    return (
        '<img src="' + esc(BRAND_LOGO_URL) + '" width="' + str(size) + '" '
        'height="' + str(size) + '" alt="" '
        'style="display:block;width:' + str(size) + 'px;height:' + str(size) + 'px;'
        'border:0;object-fit:contain;">'
    )

def css_url(u):
    return str(u).strip().replace("'", "%27").replace('"', "%22").replace("&", "&amp;")

def direct_url(u):
    """Convert common Google Drive *preview* links to image endpoints.
    Drive still sometimes blocks hotlinking: a public CDN URL is recommended.
    """
    u = str(u or "").strip()
    if "drive.google.com/file/d/" in u:
        fid = u.split("/file/d/", 1)[1].split("/", 1)[0].split("?", 1)[0]
        if fid:
            return "https://drive.google.com/uc?export=view&id=" + fid
    return u

HERO_IMAGE_URL = direct_url(HERO_IMAGE_URL)
PRODUCT_IMAGE_URL = direct_url(PRODUCT_IMAGE_URL)
STORE_IMAGE_URL = direct_url(STORE_IMAGE_URL)

ICON_URLS = {
    "revenue": "https://res.cloudinary.com/q8q8gpln/image/upload/v1793424147/wallet-3.png",
    "margin": "https://res.cloudinary.com/q8q8gpln/image/upload/v1793424563/percent.png",
    "orders": "https://res.cloudinary.com/q8q8gpln/image/upload/v1793424559/shopping-bag.png",
    "returns": "https://res.cloudinary.com/q8q8gpln/image/upload/v1793424556/rotate-ccw.png",
    "product": "https://res.cloudinary.com/q8q8gpln/image/upload/v1793424583/crown.png",
    "store": "https://res.cloudinary.com/q8q8gpln/image/upload/v1793424579/store.png",
}

# ---------------------------- 1. inputs ----------------------------
kpi, llm_text, charts = {}, "", []
for item in _items:
    j = item["json"]
    if "report_month" in j:
        kpi = j
    elif j.get("text") or j.get("output"):
        llm_text = str(j.get("text") or j.get("output"))
    elif j.get("url"):
        charts.append(direct_url(j["url"]))

month = kpi.get("report_month_label", "")
prev_label = kpi.get("prev_month_label", "")
first_label = kpi.get("first_month_label", "")

# ---------------------------- 2. parse the LLM's tagged sections ----------------------------
sections, order, current = {}, [], None
for raw in llm_text.replace("\r", "").split("\n"):
    line = raw.strip().strip("*#` ").strip()
    if line.startswith("[") and line.endswith("]") and 1 < len(line) < 30:
        current = line[1:-1].strip().upper().replace(" ", "_")
        sections[current] = []
        order.append(current)
    elif current is not None and not raw.strip().startswith("```"):
        sections[current].append(raw)

def paragraph(tag):
    return " ".join(clean_line(x) for x in sections.get(tag, []) if clean_line(x))

def bullets(tag):
    items = []
    for x in sections.get(tag, []):
        t = clean_line(x)
        if not t:
            continue
        if t[0] in "-*•":
            t = t[1:].strip()
        elif t[0].isdigit() and "." in t[:3]:
            t = t[t.index(".") + 1:].strip()
        elif items:
            items[-1] += " " + t
            continue
        items.append(t)
    return items

parsed_ok = any(t in sections for t in ["KPI"] + CHART_TAGS + ["ACTIONS"])

# ---------------------------- 3. building blocks ----------------------------
def spacer(h=16):
    return '<tr><td height="' + str(h) + '" style="font-size:0;line-height:0;">&nbsp;</td></tr>'

def plain_heading(title, meta="", title_color=None):
    """Two-column section title without an icon or icon placeholder."""
    title_color = title_color or NAVY
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        '<tr><td valign="middle" style="font-family:' + FONT + ';font-size:18px;'
        'font-weight:800;color:' + title_color + ';">' + esc(title) + '</td>'
        '<td align="right" valign="middle" style="font-family:' + FONT + ';'
        'font-size:12px;color:' + MUTED + ';">' + esc(meta) + '</td>'
        '</tr></table>'
    )


def plain_kpi_summary(text):
    """Plain KPI insight, with a configurable natural-language opening."""
    if not text:
        return ""
    content = str(text).strip()
    prefix = KPI_SUMMARY_PREFIX.strip()
    if prefix and not content.lower().startswith(prefix.rstrip(',').lower()):
        content = prefix + " " + content
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="margin-top:12px;"><tr><td '
        'style="padding:8px 6px 4px;font-family:' + FONT + ';font-size:14px;'
        'line-height:1.65;color:' + NAVY + ';">'
        + rich(content, "font-weight:750;color:#10214B;") + '</td></tr></table>'
    )


def strip_box(text):
    """Dark chart-insight strip without a lightbulb/icon."""
    if not text:
        return ""
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="margin-top:12px;"><tr><td bgcolor="' + INK + '" '
        'style="background:' + INK + ';border-radius:14px;padding:14px 18px;'
        'font-family:' + FONT + ';font-size:14px;line-height:22px;color:#DCE5F5;">'
        + rich(text, "font-weight:700;color:#FFFFFF;") + '</td></tr></table>'
    )

def trend(change, unit, lower_is_better=False):
    """Return arrow, change figure, plain comparison label, and semantic colour."""
    if change in (None, ""):
        return "", "", "no previous month", FLAT
    v = float(change)
    if v == 0:
        return "&#9654;", "0.0" + unit, "vs " + prev_label, FLAT
    good = (v < 0) if lower_is_better else (v > 0)
    arrow = "&#8599;" if v > 0 else "&#8600;"
    amount = ("+" if v > 0 else "") + format(v, ".1f") + unit
    return arrow, amount, "vs " + prev_label, (GOOD if good else BAD)

def kpi_card(glyph, icon_bg, glyph_color, label, value, change, unit, lower_is_better=False):
    arrow, amount, comparison, color = trend(change, unit, lower_is_better)
    return ('<td class="stack" width="50%" valign="top" style="padding:6px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="background-color:#F9FCFF;background:rgba(255,255,255,0.68);border:1px solid rgba(255,255,255,0.92);border-radius:10px;box-shadow:0 3px 12px rgba(45,80,140,0.07);">'
            '<tr><td style="padding:16px 16px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
            '<td width="58" valign="middle"><div style="width:46px;height:46px;line-height:46px;border-radius:23px;background:' + icon_bg
            + ';text-align:center;font-size:21px;font-weight:700;color:' + glyph_color + ';">' + glyph + '</div></td>'
            '<td valign="middle" style="font-family:' + FONT + ';">'
            '<div style="font-size:13px;color:' + MUTED + ';">' + label + '</div>'
            '<div style="font-size:28px;font-weight:800;color:' + NAVY + ';line-height:1.15;margin:2px 0;">' + value + '</div>'
            '<div style="font-size:12.5px;color:' + color + ';">'
            + ('<strong style="font-weight:700;">' + arrow + ' ' + esc(amount) + '</strong> ' if amount else '')
            + '<span style="font-weight:400;">' + esc(comparison) + '</span></div>'
            '</td></tr></table></td></tr></table></td>')

def feature_card(icon, label, heading, body_html, image_url, image_left):
    """ONE full-width pre-blended image behind HTML text (not two hard-split cells).

    The baked image MUST already fade into #0B1220 on the text side:
      - product: text LEFT, photo RIGHT
      - store: photo LEFT, text RIGHT
    """
    has_bg = url_ok(image_url)
    attr = ' background="' + esc(image_url) + '"' if has_bg else ''
    bg_css = ("background-image:url('" + css_url(image_url) + "');"
              "background-size:cover;background-position:center;"
              "background-repeat:no-repeat;") if has_bg else ""

    # Only one text column; the other is intentional empty image space.
    # The glass/dark fade comes from the baked background, not a white cell.
    text_td = (
        '<td class="feature-text" width="57%" valign="middle" '
        'style="padding:30px 27px;font-family:' + FONT + ';">'
        '<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
        '<td width="44"><div style="width:34px;height:34px;line-height:34px;'
        'border-radius:9px;background:transparent;border:1px solid #FFFFFF;'
        'text-align:center;font-size:17px;color:#FFFFFF;">' + icon + '</div></td>'
        '<td style="font-size:10px;letter-spacing:2.5px;color:#BCCBDD;">'
        + esc(label) + '</td></tr></table>'
        '<div style="font-size:27px;font-weight:800;color:#FFFFFF;'
        'margin:13px 0 11px;line-height:1.15;">' + esc(heading) + '</div>'
        '<div style="font-size:14px;line-height:1.65;color:#E2E9F2;">'
        + body_html + '</div></td>'
    )
    image_space = '<td class="feature-image-space" width="43%" style="font-size:0;line-height:0;">&nbsp;</td>'
    cells = (image_space + text_td) if image_left else (text_td + image_space)
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="border-radius:22px;overflow:hidden;background:#0B1220;">'
        '<tr><td' + attr + ' bgcolor="#0B1220" '
        'style="background-color:#0B1220;' + bg_css + 'border-radius:22px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        '<tr>' + cells + '</tr></table>'
        '</td></tr></table>'
    )

def money(v):
    return esc(CURRENCY) + fnum(v)

def bold(t):
    return '<strong style="color:#FFFFFF;font-weight:700;">' + esc(t) + '</strong>'

def delta_sentence(pct):
    if pct in (None, ""):
        return ""
    v = float(pct)
    return " Revenue was " + bold(("+" if v > 0 else "") + format(v, ".1f") + "%") + " vs " + esc(prev_label) + "."

# ---------------------------- 4. sections ----------------------------
# --- key metrics (assembled FIRST so they can be placed INSIDE the hero) ---
kpi_inner = ""
if kpi:
    kpi_inner = (
        plain_heading("Key metrics", (month + " vs " + prev_label) if prev_label else month, "#FFFFFF")
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:10px;"><tr>'
        + kpi_card(lucide_icon("revenue", 24), "#000000", "#FFFFFF", "Net Revenue", money(kpi.get("net_revenue")), kpi.get("net_revenue_mom_pct"), "%")
        + kpi_card(lucide_icon("margin", 24), "#000000", "#FFFFFF", "Gross Margin", fnum(kpi.get("gross_margin_pct"), 1) + "%", kpi.get("gross_margin_change_pts"), " pts")
        + '</tr><tr>'
        + kpi_card(lucide_icon("orders", 24), "#000000", "#FFFFFF", "Total Orders", fnum(kpi.get("orders")), kpi.get("orders_mom_pct"), "%")
        + kpi_card(lucide_icon("returns", 24), "#000000", "#FFFFFF", "Return Rate", fnum(kpi.get("return_rate_pct"), 1) + "%", kpi.get("return_rate_change_pts"), " pts", lower_is_better=True)
        + '</tr></table>'
    )
    if kpi.get("latest_month_partial"):
        kpi_inner += ('<div style="background:#FFF4E5;border-radius:8px;padding:8px 12px;'
                      'font-family:' + FONT + ';font-size:12px;color:#92400E;margin-top:10px;">'
                      'Note: ' + esc(month) + ' only has ' + esc(kpi.get("latest_month_days"))
                      + ' days of data, so comparisons with ' + esc(prev_label)
                      + ' are not like-for-like.</div>')
    if parsed_ok:
        kpi_inner += plain_kpi_summary(paragraph("KPI"))
    else:
        fallback = " ".join(clean_line(x) for x in llm_text.split("\n") if clean_line(x))
        kpi_inner += plain_kpi_summary(fallback or "No insights were generated.")

kpi_panel = kpi_inner  # No separate pale-blue/glass container around the four KPI cards

# --- ONE unified hero container; KPI heading and four cards sit directly on the hero image ---
# A taller pre-composed background (email_hero_kpi_extended.png) is recommended:
# photo at the top, fading to pale blue behind the KPI panel.
if url_ok(HERO_IMAGE_URL):
    hero_bg = (
        "background-color:#E9F1FC;"
        "background-image:url('" + css_url(HERO_IMAGE_URL) + "');"
        "background-size:cover;background-position:center top;"
        "background-repeat:no-repeat;"
    )
    hero_attr = ' background="' + esc(HERO_IMAGE_URL) + '"'
else:
    hero_bg = 'background-color:#17273F;'
    hero_attr = ""

hero_fallback_colour = "#E9F1FC" if url_ok(HERO_IMAGE_URL) else "#17273F"



brand_row = (
    '<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
    + ('<td width="32" valign="middle">' + brand_logo(24) + '</td>' if url_ok(BRAND_LOGO_URL) else '')
    + '<td valign="middle" style="font-family:' + FONT + ';font-size:14px;'
    'color:#FFFFFF;font-weight:400;">' + esc(BRAND_NAME) + '</td>'
    '</tr></table>'
) if BRAND_NAME else "&nbsp;"

hero_kpi_html = (
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
    'style="border-radius:0px;overflow:hidden;background:#E9F1FC;">'
    '<tr><td' + hero_attr + ' bgcolor="' + hero_fallback_colour + '" '
    'style="' + hero_bg + 'border-radius:0px;" valign="top">'
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
    # Brand/logo
    '<tr><td class="pad" style="padding:20px 26px 0;">' + brand_row + '</td></tr>'
    # Heading, aligned with the left edge of the KPI panel below
    '<tr><td class="pad" style="padding:42px 26px 39px;">'
    '<div style="font-family:' + FONT + ';font-size:11px;letter-spacing:3px;'
    'color:#D5E2F4;font-weight:700;">' + esc(HERO_LABEL) + '</div>'
    '<div class="h1" style="font-family:' + FONT + ';font-size:38px;font-weight:800;'
    'color:#FFFFFF;line-height:1.1;margin:9px 0 6px;">' + esc(HERO_TITLE) + '</div>'
    '<div style="font-family:' + FONT + ';font-size:19px;color:#FFFFFF;">'
    + esc(month) + '</div>'
    '<div style="font-family:' + FONT + ';font-size:12px;line-height:1.55;'
    'color:#E4EBF7;margin-top:14px;max-width:360px;">'
    + esc(HERO_DESCRIPTION) + '</div>'
    '</td></tr>'
    # KPIs are direct children of the hero background, without an enclosing blue panel
    '<tr><td class="pad" style="padding:16px 26px 26px;">'
    + kpi_panel + '</td></tr>'
    '</table></td></tr></table>'
)

# --- best product ---
product_html = ""
if kpi.get("best_product_name"):
    body = ("The " + bold(kpi.get("best_product_name")) + " was your top performer in " + esc(month) + ", with "
            + bold(fnum(kpi.get("best_product_orders")) + " orders") + ", generating " + bold(money(kpi.get("best_product_revenue")))
            + " in net revenue and accounting for " + bold(fnum(kpi.get("best_product_share_pct"), 1) + "%") + " of the total."
            + delta_sentence(kpi.get("best_product_mom_pct")))
    product_heading = str(kpi.get("best_product_name") or "Top product")
    product_html = feature_card(lucide_icon("product", 24), "TOP PRODUCT", product_heading, body,
                                PRODUCT_IMAGE_URL if url_ok(PRODUCT_IMAGE_URL) else "", image_left=False)

# --- best store ---
store_html = ""
if kpi.get("best_store_id") not in (None, "") or kpi.get("best_store_name"):
    # Prefer a real store name when the upstream KPI node supplies one.
    store_id = str(kpi.get("best_store_id") or "").strip()
    store_heading = str(kpi.get("best_store_name") or "").strip()
    if not store_heading:
        store_heading = store_id if store_id.lower().startswith("store ") else "Store " + store_id
    body = (bold(store_heading) + " was " + esc(month) + "'s top-performing location, generating "
            + bold(money(kpi.get("best_store_revenue"))) + " in net revenue, " + bold(fnum(kpi.get("best_store_share_pct"), 1) + "%")
            + " of the month's total." + delta_sentence(kpi.get("best_store_mom_pct")))
    store_html = feature_card(lucide_icon("store", 24), "TOP STORE", store_heading, body,
                              STORE_IMAGE_URL if url_ok(STORE_IMAGE_URL) else "", image_left=True)

# --- four independent PURE-WHITE chart cards on a medium cool-grey Performance section ---
CARD_META = [
    ("Net revenue by month", (first_label + " - " + month) if first_label else month),
    ("Net revenue by category", month),
    ("Top 5 subcategories", month),
    ("Net revenue by store", month),
]

def chart_panel(i, url):
    """Individual white chart card, plain heading and icon-free dark insight."""
    ttl, meta = CARD_META[i] if i < len(CARD_META) else ("Chart " + str(i + 1), month)
    insight = paragraph(CHART_TAGS[i]) if (parsed_ok and i < len(CHART_TAGS)) else ""
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'bgcolor="#FFFFFF" style="background:#FFFFFF;border:1px solid #E6EAF0;'
        'border-radius:16px;">'
        '<tr><td style="padding:16px;">'
        + plain_heading(ttl, meta)
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'bgcolor="#FFFFFF" style="margin-top:11px;background:#FFFFFF;border-radius:12px;">'
        '<tr><td align="center" style="padding:8px 0;">'
        '<img src="' + esc(url) + '" width="570" alt="' + esc(ttl) + '" '
        'style="display:block;width:100%;max-width:570px;height:auto;border:0;margin:0 auto;">'
        '</td></tr></table>'
        + strip_box(insight)
        + '</td></tr></table>'
    )

charts_html = ""
if charts:
    chart_rows = (
        '<tr><td style="padding:48px 18px 26px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        '<tr>'
        '<td width="18%" style="width:18%;font-size:0;line-height:0;">&nbsp;</td>'
        '<td width="64%" align="center" valign="middle" '
        'style="width:64%;font-family:' + FONT + ';font-size:28px;'
        'line-height:36px;font-weight:800;color:' + NAVY + ';text-align:center;">'
        'PERFORMANCE INSIGHTS'
        '</td>'
        '<td width="18%" align="right" valign="middle" '
        'style="width:18%;font-family:' + FONT + ';font-size:16px;'
        'color:' + MUTED + ';text-align:right;white-space:nowrap;">'
        + esc(month) +
        '</td>'
        '</tr></table>'
        '</td></tr>'
    )
    for i, url in enumerate(charts):
        chart_rows += (
            '<tr><td style="padding:0 18px 16px;">'
            + chart_panel(i, url) + '</td></tr>'
        )
    charts_html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'bgcolor="#E5E5E5" style="background-color:#E5E5E5;">'
        + chart_rows + '</table>'
    )

# --- dark navy Recommended Actions section (no pale-blue container or icon) ---
actions = bullets("ACTIONS") if parsed_ok else []
actions_html = ""
if actions:
    rows_html = "".join(
        '<tr>'
        '<td width="42" valign="top" style="padding:9px 0;">'
        '<span style="display:inline-block;width:30px;height:30px;line-height:30px;'
        'border-radius:50%;background:#FFFFFF;color:#0B1220;font-family:' + FONT + ';'
        'font-size:13px;font-weight:800;text-align:center;">' + str(n + 1) + '</span></td>'
        '<td valign="middle" style="padding:9px 0 9px 5px;font-family:' + FONT + ';'
        'font-size:14px;line-height:1.65;color:#E6EDF7;">'
        + rich(a, "font-weight:700;color:#FFFFFF;") + '</td></tr>'
        for n, a in enumerate(actions)
    )
    actions_html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'bgcolor="#0B1220" style="background:#0B1220;border-radius:0;">'
        '<tr><td style="padding:27px 28px 30px;">'
        '<div style="font-family:' + FONT + ';font-size:22px;line-height:1.3;'
        'font-weight:800;color:#FFFFFF;margin-bottom:15px;">Recommended actions</div>'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        + rows_html + '</table></td></tr></table>'
    )

# ---------------------------- 5. assemble ----------------------------
feature_section = (
    '<table role="presentation" width="100%" '
    'cellpadding="0" cellspacing="0" '
    'style="background:#000000;border-radius:0px;">'
    '<tr><td style="padding:20px;">'
    + product_html
    + '<div style="height:16px;line-height:16px;">&nbsp;</div>'
    + store_html
    + '</td></tr></table>'
)

parts = [hero_kpi_html, feature_section, charts_html, actions_html]

body_rows = ""

for i, p in enumerate(parts):
    if not p:
        continue

    body_rows += '<tr><td>' + p + '</td></tr>'

    
footer = (
    '<tr><td align="center" bgcolor="#F1D88A" '
    'style="padding:24px 24px 22px;background-color:#F1D88A;font-family:' + FONT + ';">'
    + ('<table role="presentation" cellpadding="0" cellspacing="0" align="center" '
       'style="margin:0 auto 8px;"><tr>'
       + ('<td width="32" valign="middle">' + brand_logo(24) + '</td>' if url_ok(BRAND_LOGO_URL) else '')
       + '<td valign="middle" style="font-size:16px;font-weight:400;color:#0B1220;">'
       + esc(BRAND_NAME) + '</td></tr></table>' if BRAND_NAME else '')
    + '<div style="font-size:11px;line-height:1.65;color:#25324A;">'
    'Monthly Performance Intelligence &middot; ' + esc(month) + '<br>'
'Automatically generated for internal performance monitoring'
    '</div></td></tr>'
)

html = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    '<style>@media only screen and (max-width:640px){.wrap{width:100%!important}.stack{display:block!important;width:100%!important;box-sizing:border-box!important}.hpanel{width:100%!important}'
    '.pad{padding-left:16px!important;padding-right:16px!important}.h1{font-size:30px!important}.feature-image-space{display:none!important}.feature-text{display:block!important;width:auto!important;padding:25px!important}}</style></head>'
    '<body style="margin:0;padding:0;background:#FFFFFF;font-family:' + FONT + ';color:' + NAVY + ';">'
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#FFFFFF"><tr><td align="center" style="padding:20px 10px;">'
    '<table role="presentation" class="wrap" width="680" cellpadding="0" cellspacing="0" style="width:680px;max-width:100%;">'
    + body_rows + footer +
    '</table></td></tr></table></body></html>'
)

subject = REPORT_TITLE + (" - " + month if month else "")
return [{"json": {"subject": subject, "html": html, "chart_count": len(charts), "kpis_found": bool(kpi),
                  "insights_parsed": parsed_ok, "sections_found": order, "html_size_kb": round(len(html) / 1024.0, 1)}}]
