"""Generate the three demo inputs (static/samples/*.png), their annotation boxes
(demo_boxes.json) and the app icons. Run once: python make_samples.py"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
OUT = ROOT / "static" / "samples"
OUT.mkdir(parents=True, exist_ok=True)
GF = "/usr/share/fonts/truetype/google-fonts/"
DJ = "/usr/share/fonts/truetype/dejavu/"


def font(name, size):
    bold = "Bold" in name or "Medium" in name
    fallbacks = ["segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf",  # Windows
                 "/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf"]                   # macOS / Linux
    for p in (GF + name, DJ + name, name, *fallbacks):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def norm(box, W, H, pad=8):
    x0, y0, x1, y1 = box
    return [max(0, round((y0 - pad) / H * 1000)), max(0, round((x0 - pad) / W * 1000)),
            min(1000, round((y1 + pad) / H * 1000)), min(1000, round((x1 + pad) / W * 1000))]


def union(*boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def sub_box(draw, xy, line, sub, f):
    """Pixel box of substring `sub` inside `line` drawn at xy."""
    i = line.index(sub)
    x = xy[0] + draw.textlength(line[:i], font=f)
    w = draw.textlength(sub, font=f)
    t = draw.textbbox(xy, line, font=f)
    return (x, t[1], x + w, t[3])


def rounded(draw, box, r, fill):
    draw.rounded_rectangle(box, r, fill=fill)


# ---------------------------------------------------------------- text messages
def sms(name, sender, sub, lines, regions_spec, footer=None, W=900, H=1300):
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_sm, f_md, f_msg = font("Poppins-Regular.ttf", 24), font("Poppins-Medium.ttf", 28), font("Poppins-Regular.ttf", 33)
    # status bar
    d.text((48, 26), "9:41", font=font("Poppins-Medium.ttf", 30), fill="black")
    d.rounded_rectangle((W - 120, 34, W - 64, 58), 6, outline="black", width=3)
    d.rectangle((W - 116, 38, W - 78, 54), fill="black")
    # header
    d.text((40, 100), "‹", font=font("Poppins-Regular.ttf", 64), fill="#0A84FF")
    cx = W // 2
    d.ellipse((cx - 46, 96, cx + 46, 188), fill="#A6ABB8")
    d.ellipse((cx - 16, 114, cx + 16, 146), fill="white")
    d.pieslice((cx - 32, 150, cx + 32, 214), 180, 360, fill="white")
    d.rectangle((0, 189, W, 200), fill="white")
    sb = d.textbbox((0, 0), sender, font=f_md)
    sxy = (cx - (sb[2] - sb[0]) / 2, 204)
    d.text(sxy, sender, font=f_md, fill="black")
    sender_box = d.textbbox(sxy, sender, font=f_md)
    d.line((0, 262, W, 262), fill="#E3E3E8", width=2)
    tb = d.textbbox((0, 0), sub, font=f_sm)
    d.text((cx - (tb[2] - tb[0]) / 2, 292), sub, font=f_sm, fill="#8E8E93")
    # bubble
    lh, x0, y0 = 46, 74, 372
    widths = [d.textlength(t, font=f_msg) for t, _ in lines]
    bw = max(widths) + 64
    bh = len(lines) * lh + 44
    rounded(d, (44, y0 - 22, 44 + bw, y0 - 22 + bh), 40, "#E9E9EB")
    line_boxes = []
    for i, (t, style) in enumerate(lines):
        xy = (x0, y0 + i * lh)
        color = "#0A63D6" if style == "link" else "black"
        d.text(xy, t, font=f_msg, fill=color)
        bb = d.textbbox(xy, t, font=f_msg) if t else (x0, xy[1], x0, xy[1] + 30)
        if style == "link":
            d.line((bb[0], bb[3] + 3, bb[2], bb[3] + 3), fill=color, width=2)
        line_boxes.append((xy, t, bb))
    if footer:
        fy = y0 - 22 + bh + 60
        for j, ft in enumerate(footer):
            fb = d.textbbox((0, 0), ft, font=f_sm)
            d.text((cx - (fb[2] - fb[0]) / 2, fy + j * 36), ft, font=f_sm, fill="#0A84FF" if j else "#8E8E93")
    # input bar
    d.rounded_rectangle((120, H - 120, W - 40, H - 50), 35, outline="#D1D1D6", width=2)
    d.text((150, H - 106), "Text Message", font=f_sm, fill="#C7C7CC")
    d.ellipse((40, H - 118, 100, H - 58), fill="#E9E9EB")
    d.text((58, H - 120), "+", font=font("Poppins-Regular.ttf", 44), fill="#8E8E93")

    regions = []
    for spec in regions_spec:
        boxes = []
        for ref in spec["refs"]:
            if ref == "sender":
                boxes.append(sender_box)
            elif isinstance(ref, int):
                boxes.append(line_boxes[ref][2])
            else:
                li, s = ref
                xy, t, _ = line_boxes[li]
                boxes.append(sub_box(d, xy, t, s, f_msg))
        regions.append({"id": spec["id"], "kind": spec["kind"], "label": spec["label"],
                        "text": spec["text"], "box_2d": norm(union(*boxes), W, H)})
    img.save(OUT / f"{name}.png")
    return regions


boxes = {}

boxes["toll"] = sms(
    "toll", "+1 (639) 412-0587", "Text Message • Today 9:41 AM",
    [("E-ZPass New York: FINAL NOTICE.", ""),
     ("Your vehicle has an unpaid toll", ""),
     ("balance of $6.99. To avoid a $50.00", ""),
     ("late fee and suspension of your", ""),
     ("driving privileges, pay by 10/13:", ""),
     ("https://ezpassny-tolls.top/pay", "link"),
     ("", ""),
     ("(Please reply Y, then exit the text", ""),
     ("message and open it again to", ""),
     ("activate the link.)", "")],
    [
        {"id": "r1", "kind": "flag", "label": "Random personal number", "text": "+1 (639) 412-0587", "refs": ["sender"]},
        {"id": "r2", "kind": "fact", "label": "Amount: $6.99", "text": "$6.99", "refs": [(2, "$6.99")]},
        {"id": "r3", "kind": "flag", "label": "Threats and a 2-day deadline", "text": "To avoid a $50.00 late fee and suspension of your driving privileges, pay by 10/13",
         "refs": [(2, "To avoid a $50.00"), 3, 4]},
        {"id": "r4", "kind": "flag", "label": "Look-alike link", "text": "https://ezpassny-tolls.top/pay", "refs": [5]},
        {"id": "r5", "kind": "flag", "label": "'Reply Y' trick", "text": "Please reply Y, then exit the text message and open it again to activate the link.", "refs": [7, 8, 9]},
    ],
    footer=["The sender is not in your contact list.", "Report Junk"],
)

boxes["coned"] = sms(
    "coned", "26633", "Text Message • Today 8:02 AM",
    [("Con Edison: Your October bill for", ""),
     ("account ending 4471 is ready.", ""),
     ("Amount: $84.21, due 11/02. View or", ""),
     ("pay in the Con Edison app or at", ""),
     ("coned.com. Reply HELP for help,", ""),
     ("STOP to opt out.", "")],
    [
        {"id": "r1", "kind": "fact", "label": "$84.21 due Nov 2", "text": "Amount: $84.21, due 11/02", "refs": [(2, "Amount: $84.21, due 11/02.")]},
        {"id": "r2", "kind": "fact", "label": "Official site, no link to tap", "text": "coned.com", "refs": [(4, "coned.com.")]},
    ],
)

# ---------------------------------------------------------------- hospital bill
W, H = 900, 1260
img = Image.new("RGB", (W, H), "#FDFDFB")
d = ImageDraw.Draw(img)
fb, fr, fs, fh = font("Carlito-Bold.ttf", 30), font("Carlito-Regular.ttf", 24), font("Carlito-Regular.ttf", 21), font("Carlito-Bold.ttf", 24)
d.rectangle((60, 60, 112, 112), fill="#2B5D8C")
d.text((74, 64), "R", font=font("Carlito-Bold.ttf", 40), fill="white")
d.text((128, 58), "Riverside Mercy Medical Center", font=fb, fill="#1E2A38")
d.text((128, 94), "450 Riverside Blvd, Brooklyn, NY 11201", font=fs, fill="#555")
d.text((640, 64), "PATIENT STATEMENT", font=fh, fill="#2B5D8C")
y = 160
d.line((60, y, W - 60, y), fill="#2B5D8C", width=3)
meta = [("Statement date", "October 1, 2026"), ("Account number", "RM-2048-7731"), ("Patient", "Jordan Lee"), ("Insurance", "Bluebridge Health PPO")]
for i, (k, v) in enumerate(meta):
    d.text((60, y + 24 + i * 34), k, font=fs, fill="#666")
    d.text((260, y + 22 + i * 34), v, font=fr, fill="#1E2A38")
due_box_xy = (560, y + 26)
d.rectangle((540, y + 18, W - 60, y + 150), outline="#2B5D8C", width=2)
d.text((560, y + 30), "AMOUNT DUE", font=fh, fill="#2B5D8C")
amt_xy = (560, y + 62)
d.text(amt_xy, "$3,097.50", font=font("Carlito-Bold.ttf", 44), fill="#1E2A38")
amt_box = d.textbbox(amt_xy, "$3,097.50", font=font("Carlito-Bold.ttf", 44))
dd_xy = (560, y + 114)
d.text(dd_xy, "Due by October 30, 2026", font=fr, fill="#B22")
dd_box = d.textbbox(dd_xy, "Due by October 30, 2026", font=fr)

y = 340
d.rectangle((60, y, W - 60, y + 40), fill="#E8EEF5")
for x, t in [(72, "Date"), (190, "Description"), (610, "Charges"), (735, "You owe")]:
    d.text((x, y + 8), t, font=fh, fill="#1E2A38")
rows = [
    ("08/14/26", ["Emergency department visit, level 4", "Insurance paid $1,710.00"], "$1,960.00", "$250.00"),
    ("08/14/26", ["Emergency physician services", "Coastline ER Physicians (out-of-network)", "Insurance paid $0.00 — not in network"], "$2,847.50", "$2,847.50"),
]
ry = y + 56
row_boxes = []
for date_, desc, ch, owe in rows:
    top = ry
    d.text((72, ry), date_, font=fr, fill="#1E2A38")
    for j, line in enumerate(desc):
        d.text((190, ry + j * 30), line, font=fr if j == 0 else fs, fill="#1E2A38" if j == 0 else "#666")
    d.text((610, ry), ch, font=fr, fill="#1E2A38")
    d.text((735, ry), owe, font=fr, fill="#1E2A38")
    ry += len(desc) * 30 + 26
    row_boxes.append((180, top - 4, W - 66, ry - 20))
    d.line((60, ry - 10, W - 60, ry - 10), fill="#DDD", width=1)
d.text((520, ry + 10), "Total patient balance", font=fs, fill="#666")
d.text((735, ry + 8), "$3,097.50", font=fh, fill="#1E2A38")

y = ry + 90
para = [
    "Thank you for choosing Riverside Mercy. Your insurance has processed the",
    "claims above. The remaining balance is your responsibility.",
    "",
    "Pay online at riversidemercy.org/pay or call Patient Financial Services",
    "at (718) 555-0142, Monday–Friday, 8am–6pm.",
    "",
    "If this balance is not paid by the due date, your account may be",
    "referred to an outside collection agency.",
]
pb = []
for i, line in enumerate(para):
    xy = (60, y + i * 32)
    d.text(xy, line, font=fr, fill="#333")
    pb.append(d.textbbox(xy, line, font=fr) if line else None)
d.line((60, H - 150, W - 60, H - 150), fill="#BBB", width=1)
d.text((60, H - 130), "Please detach and return this portion with your payment.", font=fs, fill="#777")
d.text((60, H - 96), "Account RM-2048-7731   •   Amount enclosed: $__________", font=fr, fill="#333")
img.save(OUT / "bill.png")

boxes["bill"] = [
    {"id": "r1", "kind": "fact", "label": "Amount due: $3,097.50", "text": "$3,097.50", "box_2d": norm(amt_box, W, H)},
    {"id": "r2", "kind": "fact", "label": "Due Oct 30", "text": "Due by October 30, 2026", "box_2d": norm(dd_box, W, H)},
    {"id": "r3", "kind": "flag", "label": "Out-of-network ER doctor billed in full", "text": "Emergency physician services, Coastline ER Physicians (out-of-network), Insurance paid $0.00", "box_2d": norm(row_boxes[1], W, H, pad=2)},
    {"id": "r4", "kind": "fact", "label": "Collections warning", "text": "may be referred to an outside collection agency", "box_2d": norm(union(pb[6], pb[7]), W, H)},
]

(ROOT / "demo_boxes.json").write_text(json.dumps(boxes, indent=1), encoding="utf-8")

# ---------------------------------------------------------------- icons
def icon(size, path):
    s = size
    im = Image.new("RGB", (s, s), "#16234A")
    dr = ImageDraw.Draw(im)
    # envelope security tint
    step = max(4, s // 32)
    for k in range(-s, s * 2, step):
        dr.line((k, 0, k - s, s), fill="#1E2E5C", width=max(1, s // 128))
    # envelope
    m = s * 0.2
    dr.rounded_rectangle((m, s * 0.3, s - m, s * 0.72), radius=s * 0.04, fill="#F2F4F8")
    dr.line((m + s * 0.02, s * 0.32, s / 2, s * 0.52, s - m - s * 0.02, s * 0.32), fill="#16234A", width=max(2, s // 48))
    # check stamp
    r = s * 0.15
    cx, cy = s * 0.7, s * 0.68
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#1C8A63", outline="#F2F4F8", width=max(2, s // 64))
    dr.line((cx - r * 0.45, cy, cx - r * 0.1, cy + r * 0.38, cx + r * 0.5, cy - r * 0.35), fill="white", width=max(3, s // 28), joint="curve")
    im.save(path)


icon(512, ROOT / "static" / "icon-512.png")
icon(192, ROOT / "static" / "icon-192.png")
icon(180, ROOT / "static" / "apple-touch-icon.png")
print("samples + boxes + icons written")
