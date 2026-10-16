from __future__ import annotations

import html
import math
import re
import textwrap
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    LongTable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "output/pdf/Odylith_Strategic_Dossier.md"
OUTPUT = ROOT / "output/pdf/Odylith_Strategic_Dossier.pdf"
ASSETS = ROOT / "output/pdf/assets"

FONT_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"

NAVY = "#0B162A"
INK = "#172033"
SLATE = "#475569"
MUTED = "#64748B"
LIGHT = "#F4F7FB"
GRID = "#D8E0EA"
EMERALD = "#12B886"
TEAL = "#0EA5A5"
BLUE = "#3B82F6"
PURPLE = "#8B5CF6"
ORANGE = "#F59E0B"
RED = "#EF4444"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size=size)


def wrap_text(draw, text, fnt, width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=fnt)[2] <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def text_box(draw, xy, title, body="", fill="#FFFFFF", outline=GRID, accent=None, title_size=35, body_size=25):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=28, fill=fill, outline=outline, width=4)
    if accent:
        draw.rounded_rectangle((x0, y0, x0 + 16, y1), radius=8, fill=accent)
    tx = x0 + 38
    ty = y0 + 30
    title_font = font(title_size, True)
    body_font = font(body_size)
    for line in wrap_text(draw, title, title_font, x1 - tx - 28):
        draw.text((tx, ty), line, font=title_font, fill=INK)
        ty += title_size + 8
    if body:
        ty += 12
        for part in body.split("\n"):
            if not part.strip():
                ty += body_size
                continue
            part_font = font(body_size, True) if part.strip().isupper() and len(part.strip()) < 32 else body_font
            for line in wrap_text(draw, part, part_font, x1 - tx - 28):
                draw.text((tx, ty), line, font=part_font, fill=INK if part_font != body_font else SLATE)
                ty += body_size + 8


def arrow(draw, start, end, color=EMERALD, width=10, label=None):
    draw.line((start, end), fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    length = 30
    spread = 0.55
    p1 = (end[0] - length * math.cos(angle - spread), end[1] - length * math.sin(angle - spread))
    p2 = (end[0] - length * math.cos(angle + spread), end[1] - length * math.sin(angle + spread))
    draw.polygon((end, p1, p2), fill=color)
    if label:
        mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 - 30)
        box = draw.textbbox((0, 0), label, font=font(24, True))
        w = box[2] - box[0]
        draw.rounded_rectangle((mid[0] - w / 2 - 12, mid[1] - 5, mid[0] + w / 2 + 12, mid[1] + 34), radius=12, fill="#FFFFFF")
        draw.text((mid[0] - w / 2, mid[1]), label, font=font(24, True), fill=color)


def canvas(title, subtitle=""):
    im = PILImage.new("RGB", (2400, 1400), "white")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 2400, 120), fill=NAVY)
    d.text((90, 32), title, font=font(44, True), fill="white")
    if subtitle:
        d.text((90, 92), subtitle, font=font(21), fill="#B8C5D8")
    d.rectangle((0, 120, 2400, 128), fill=EMERALD)
    d.text((90, 1350), "ODYLITH  •  STRATEGIC DOSSIER  •  3 AUGUST 2026", font=font(20, True), fill=MUTED)
    return im, d


def save(im, name):
    ASSETS.mkdir(parents=True, exist_ok=True)
    im.save(ASSETS / name, optimize=True)


def generate_assets():
    im, d = canvas("MARKET TOPOLOGY", "Demand is a governed state transition; supply is a composite execution route")
    text_box(d, (80, 260, 610, 1000), "ENTERPRISE DEMAND", "Principal • target state • budget • scope • risk • evidence • recovery • acceptance", fill="#EDF8F6", accent=EMERALD)
    text_box(d, (870, 350, 1530, 910), "ODYLITH", "Compile contract\nFilter eligibility\nRoute work / proof / authority\nAdmit or escalate\nIssue receipt", fill="#EAF4FF", accent=BLUE, title_size=48, body_size=30)
    text_box(d, (1790, 210, 2320, 1050), "EXECUTION SUPPLY", "Internal agents • frontier agents • transformation engines • human teams • SIs • specialist vendors", fill="#F3EEFF", accent=PURPLE)
    arrow(d, (610, 620), (870, 620), label="EXECUTION CONTRACT")
    arrow(d, (1530, 620), (1790, 620), label="QUALIFIED DISPATCH")
    arrow(d, (1790, 820), (1530, 820), color=ORANGE, label="EVIDENCE")
    d.text((825, 1110), "Inventory: qualified, time-bounded capacity — not a future outcome", font=font(28, True), fill=INK)
    d.text((730, 1160), "A market exists only after demand is standardized and offers are binding", font=font(26), fill=SLATE)
    save(im, "market_topology.png")

    im, d = canvas("MONEY, AUTHORITY & EVIDENCE", "The customer remains sovereign; Odylith is buyer-funded and supplier-neutral")
    text_box(d, (120, 240, 650, 560), "ENTERPRISE PRINCIPAL", "Owns objectives, money, systems, policy, and residual risk", fill="#EDF8F6", accent=EMERALD)
    text_box(d, (925, 240, 1475, 560), "ODYLITH", "Computes eligibility, dispatch, evidence requirements, and decision receipts", fill="#EAF4FF", accent=BLUE)
    text_box(d, (1750, 240, 2280, 560), "WORKERS / PROVIDERS", "Paid directly by the customer; no rebates or paid ranking", fill="#F3EEFF", accent=PURPLE)
    text_box(d, (925, 850, 1475, 1160), "CUSTOMER SYSTEM", "GitHub, cloud, database, IAM, workflow, or GRC enforces and records", fill="#FFF7E8", accent=ORANGE)
    arrow(d, (650, 340), (925, 340), label="SUBSCRIPTION")
    arrow(d, (1750, 470), (1475, 470), color=ORANGE, label="ACTIONS + EVIDENCE")
    arrow(d, (1200, 560), (1200, 850), label="DECISION TOKEN")
    arrow(d, (650, 980), (925, 980), color=TEAL, label="POLICY / KEYS")
    arrow(d, (650, 190), (1750, 190), color=PURPLE, label="DIRECT PROVIDER PAYMENT")
    save(im, "money_authority_flow.png")

    im, d = canvas("VALUE MIGRATION", "As cognitive supply commoditizes, value moves toward controlled action and legitimate authority")
    stages = [
        ("2026–2028", "Cheap tokens & connectors", "Reliable integrated work", "Credentials • policy • liability", BLUE),
        ("2028–2031", "Specs, routing & routine checks", "Fleet coordination", "Transaction rights • evidence", TEAL),
        ("2031+", "Specialist cognition", "Multi-principal conflict", "Goals • property • enforcement", PURPLE),
        ("SUPERINTELLIGENCE", "Most cognition", "Possibly none", "Authority • finality • sovereignty", RED),
    ]
    for i, (when, cheap, temp, durable, col) in enumerate(stages):
        x = 80 + i * 580
        text_box(d, (x, 260, x + 500, 1050), when, f"COMMODITIZING\n{cheap}\n\nTEMPORARY\n{temp}\n\nDURABLE\n{durable}", fill="#FFFFFF", accent=col, title_size=31, body_size=25)
        if i < len(stages) - 1:
            arrow(d, (x + 500, 650), (x + 570, 650), color=col, width=8)
    save(im, "value_migration.png")

    im, d = canvas("FUTURE-WORLD STRESS TEST", "The thesis survives plural capability and regulation; it dies under accepted provider sovereignty")
    rows = [
        ("Dominant frontier vendor", "Independent audit / exit", "SURVIVES NARROWLY", ORANGE),
        ("Specialized plural models", "Policy, authority, evidence", "BEST CASE", EMERALD),
        ("Near-zero-cost open intelligence", "Secure local operation", "SURVIVES IF LIGHTWEIGHT", TEAL),
        ("Enterprise-built fleets", "Mandates, identities, budgets", "STRONG EXPANSION", BLUE),
        ("Autonomous agent commerce", "Verified mandate", "PARTNER WITH PAYMENTS", PURPLE),
        ("High regulation / liability", "Independent accepted proof", "STRONG IF REQUIRED", ORANGE),
        ("Trusted provider superintelligence", "No external scarcity", "DIES", RED),
    ]
    y = 210
    for label, scarcity, verdict, col in rows:
        d.rounded_rectangle((90, y, 2310, y + 135), radius=22, fill="#FFFFFF", outline=GRID, width=3)
        d.rectangle((90, y, 112, y + 135), fill=col)
        d.text((145, y + 26), label, font=font(29, True), fill=INK)
        d.text((910, y + 30), scarcity, font=font(26), fill=SLATE)
        d.rounded_rectangle((1770, y + 27, 2260, y + 106), radius=18, fill=col)
        d.text((1805, y + 49), verdict, font=font(24, True), fill="white")
        y += 155
    save(im, "scenario_timelines.png")

    im, d = canvas("STRATEGIC ALTERNATIVES", "Present monetization versus durable control-point ownership")
    d.line((300, 1170, 2200, 1170), fill=INK, width=5)
    d.line((300, 1170, 300, 220), fill=INK, width=5)
    d.text((1450, 1200), "PRESENT REVENUE →", font=font(28, True), fill=INK)
    d.text((70, 190), "DURABLE CONTROL ↑", font=font(28, True), fill=INK)
    dots = [
        ("FinOps", 1760, 960, RED),
        ("Generic control tower", 1360, 890, RED),
        ("Managed modernization", 1900, 690, ORANGE),
        ("Private execution facility", 700, 430, BLUE),
        ("Modernization execution assurance", 1530, 410, EMERALD),
        ("Public marketplace", 500, 960, RED),
        ("Authority / receipt network", 890, 270, PURPLE),
    ]
    for label, x, y, col in dots:
        d.ellipse((x - 20, y - 20, x + 20, y + 20), fill=col)
        text_box(d, (x - 160, y + 30, x + 250, y + 145), label, fill="#FFFFFF", outline=col, title_size=23)
    save(im, "strategic_alternatives.png")

    im, d = canvas("90-DAY PAID FALSIFICATION", "Each phase has a commercial or technical stop rule")
    phases = [
        ("0–14", "SELL THE BOUNDARY", "2–3 paid pilots\nreal campaign\nprecommit enforcement", EMERALD),
        ("15–30", "FREEZE CONTRACT", "pre-register cohort\nnative baseline\n2 executor families", BLUE),
        ("31–60", "SHADOW & ATTACK", "300 changes\nresidual evidence\nhuman-cost accounting", PURPLE),
        ("61–75", "BOUNDED ENFORCEMENT", "10+ repos\ndeterministic deny\noutage / bypass drills", ORANGE),
        ("76–90", "FORCE VERDICT", "named control use\n2 annual conversions\nor stop", RED),
    ]
    for i, (days, title, body, col) in enumerate(phases):
        x = 65 + i * 465
        text_box(d, (x, 300, x + 405, 1030), days, f"{title}\n\n{body}", fill="#FFFFFF", outline=col, accent=col, title_size=45, body_size=26)
        if i < len(phases) - 1:
            arrow(d, (x + 405, 660), (x + 455, 660), color=col, width=8)
    save(im, "ninety_day_sequence.png")

    im, d = canvas("REVENUE STAIRCASE", "Every stage stands alone; market features are earned options")
    stages = [
        ("PILOT", "$75K", "90 days"),
        ("ADMISSION", "$150–240K", "ARR"),
        ("PRIVATE DEPLOY", "$300–450K", "ARR"),
        ("MULTI-CLASS ROUTER", "$400–750K", "ARR"),
        ("PRIVATE FACILITY", "$500K–1M", "ARR"),
        ("ASSURANCE NETWORK", "MODULES", "optional"),
    ]
    for i, (name, price, basis) in enumerate(stages):
        x0 = 90 + i * 375
        y1 = 1120 - i * 120
        d.rounded_rectangle((x0, y1 - 330, x0 + 320, y1), radius=24, fill=["#EDF8F6", "#EAF4FF", "#F3EEFF"][i % 3], outline=EMERALD, width=4)
        d.text((x0 + 24, y1 - 290), name, font=font(24, True), fill=INK)
        d.text((x0 + 24, y1 - 210), price, font=font(34, True), fill=EMERALD)
        d.text((x0 + 24, y1 - 145), basis, font=font(24), fill=SLATE)
        if i < 5:
            arrow(d, (x0 + 320, y1 - 165), (x0 + 365, y1 - 165), width=7)
    d.text((660, 1190), "NO OUTCOME FEES • NO TOKEN MARKUP • NO SUPPLIER PLACEMENT", font=font(30, True), fill=RED)
    save(im, "revenue_staircase.png")

    im, d = canvas("MARKET FORMATION", "Control qualified order flow before inviting supply")
    stages = [
        ("M0", "SHADOW EVIDENCE", "No market", SLATE),
        ("M1", "REQUIRED ADMISSION", "Standalone company", EMERALD),
        ("M2", "QUALIFIED ROUTE BOOK", "Buyer-side routing", BLUE),
        ("M3", "STANDING OFFERS", "Private supply", PURPLE),
        ("M4", "SEALED AUCTIONS", "Only if superior", ORANGE),
        ("M5+", "RISK / CLEARING", "Not an investment premise", RED),
    ]
    for i, (code, title, status, col) in enumerate(stages):
        x = 80 + i * 385
        text_box(d, (x, 360, x + 330, 980), code, f"{title}\n\n{status}", fill="#FFFFFF", outline=col, accent=col, title_size=48, body_size=25)
        if i < 5:
            arrow(d, (x + 330, 670), (x + 375, 670), color=col, width=8)
    d.text((360, 1080), "BASE BUSINESS MUST WORK AT M1 • M2–M4 ARE EARNED • M5+ MAY NEVER ARRIVE", font=font(30, True), fill=INK)
    save(im, "market_mechanism.png")

    im, d = canvas("ACTOR RESPONSE MAP", "Every participant optimizes against the mechanism")
    center = (1200, 710)
    text_box(d, (910, 540, 1490, 900), "ODYLITH", "Buyer-funded contract, dispatch, evidence, and admission", fill="#EAF4FF", outline=BLUE, accent=BLUE, title_size=44)
    actors = [
        ("Enterprise", "Hides entropy / sends hard work", (160, 230), EMERALD),
        ("App owner", "Seeks exceptions / bypass", (160, 930), ORANGE),
        ("Supplier", "Cherry-picks / substitutes", (1800, 230), PURPLE),
        ("Verifier", "Uses proxies / can be captured", (1800, 930), RED),
        ("Incumbent", "Bundles / underprices / forecloses", (910, 180), BLUE),
        ("Auditor / insurer", "Demands portable accepted proof", (910, 1040), TEAL),
    ]
    for title, body, (x, y), col in actors:
        text_box(d, (x, y, x + 440, y + 240), title, body, fill="#FFFFFF", outline=col, accent=col, title_size=27, body_size=21)
        sx = x + 220
        sy = y + 120
        arrow(d, (sx, sy), center, color=col, width=6)
    save(im, "actor_response_map.png")

    im, d = canvas("COMPETITIVE CONTROL MAP", "Odylith survives only in the cross-platform consequence seam")
    domains = [
        ("GITHUB / MICROSOFT", "Repo • identity • agents • rules • budget", (90, 250), BLUE),
        ("CLOUDS", "Runtime • IAM • gateway • policy • market", (90, 850), TEAL),
        ("SERVICENOW / SALESFORCE", "Workflow • CMDB • approvals • GRC", (1750, 250), PURPLE),
        ("FRONTIER LABS", "Worker • tools • context • evaluation", (1750, 850), ORANGE),
    ]
    for title, body, (x, y), col in domains:
        text_box(d, (x, y, x + 560, y + 280), title, body, fill="#FFFFFF", outline=col, accent=col, title_size=28, body_size=23)
    text_box(d, (760, 440, 1640, 1000), "ODYLITH SEAM", "Buyer-owned mandate\nCross-vendor authority\nIndependent evidence\nRequired admission\nPortable receipt\nExternal state", fill="#EDF8F6", outline=EMERALD, accent=EMERALD, title_size=46, body_size=29)
    for p in [(650, 390), (650, 990), (1750, 390), (1750, 990)]:
        arrow(d, p, center, color=MUTED, width=6)
    save(im, "competitive_control_map.png")

    im, d = canvas("RISK HEAT MAP", "Likelihood × impact; fatal risks require precommitted stop rules")
    risk_cells = {
        (4, 4): ["No mandatory placement", "Native equivalent"],
        (4, 3): ["Services trap", "Outcome blindness"],
        (3, 4): ["Security incident", "One-provider dominance"],
        (3, 3): ["Code enclosure", "False denial"],
        (4, 2): ["Long procurement", "Data restrictions"],
        (2, 4): ["Trusted SI/provider"],
        (3, 2): ["Telemetry denial"],
        (2, 3): ["Receipt commoditizes"],
    }
    grid_x, grid_y, cell = 430, 240, 190
    colors_grid = ["#EAF7F1", "#FEF3C7", "#FED7AA", "#FCA5A5", "#EF4444"]
    for iy in range(5):
        for ix in range(5):
            score = min(4, (ix + iy) // 2)
            x0 = grid_x + ix * cell
            y0 = grid_y + (4 - iy) * cell
            d.rectangle((x0, y0, x0 + cell, y0 + cell), fill=colors_grid[score], outline="white", width=5)
            labels = risk_cells.get((ix, iy), [])
            ty = y0 + 18
            for label in labels:
                for line in wrap_text(d, label, font(19, True), cell - 24):
                    d.text((x0 + 12, ty), line, font=font(19, True), fill=INK)
                    ty += 23
    d.text((600, 1220), "LIKELIHOOD →", font=font(29, True), fill=INK)
    d.text((120, 650), "IMPACT ↑", font=font(29, True), fill=INK)
    d.text((1530, 350), "FATAL", font=font(36, True), fill=RED)
    d.text((1530, 410), "• Mandatory placement\n• Native incrementality\n• Product reuse\n• Evidence integrity", font=font(27), fill=SLATE, spacing=8)
    save(im, "risk_heat_map.png")

    im, d = canvas("ASSUMPTION DEPENDENCY", "The base company requires 1–7; market upside requires 8–10")
    nodes = [
        "1  Plural consequential routes",
        "2  Reusable work contracts",
        "3  External authoritative evidence",
        "4  Value beyond native controls",
        "5  Mandatory buyer decision",
        "6  Cross-customer product reuse",
        "7  Recurring software economics",
        "8  Move upstream into assignment",
        "9  Binding independent supply",
        "10  Market beats dispatch",
    ]
    for i, label in enumerate(nodes):
        row, col = divmod(i, 5)
        x = 100 + col * 460
        y = 280 + row * 500
        colr = EMERALD if i < 7 else PURPLE
        text_box(d, (x, y, x + 380, y + 230), label, "BASE COMPANY" if i < 7 else "MARKET OPTION", fill="#FFFFFF", outline=colr, accent=colr, title_size=24, body_size=20)
        if col < 4:
            arrow(d, (x + 380, y + 115), (x + 450, y + 115), color=colr, width=6)
        elif row == 0:
            arrow(d, (x + 190, y + 230), (100 + 190, y + 500), color=colr, width=6)
    d.line((90, 690, 2310, 690), fill=ORANGE, width=5)
    d.text((940, 650), "CAPITAL RELEASE GATE", font=font(25, True), fill=ORANGE)
    save(im, "assumption_dependency_graph.png")

    im, d = canvas("FINAL DECISION TREE", "Build only while the evidence earns the next stage")
    nodes = [
        ("2 paid qualified pilots?", 100, 250, EMERALD),
        ("Value beyond configured native stack?", 530, 250, BLUE),
        ("Buyer makes decision required?", 1000, 250, PURPLE),
        ("Reusable at software margins?", 1450, 250, ORANGE),
        ("Second campaign / system?", 1880, 250, TEAL),
        ("STOP", 100, 960, RED),
        ("REQUIRED ASSURANCE", 850, 960, EMERALD),
        ("QUALIFIED ROUTING", 1450, 960, BLUE),
        ("PRIVATE SUPPLY", 1880, 960, PURPLE),
    ]
    for label, x, y, col in nodes:
        text_box(d, (x, y, x + 350, y + 180), label, "", fill="#FFFFFF", outline=col, accent=col, title_size=24)
    for i in range(4):
        x = 450 + i * (430 if i == 0 else 450)
    arrow(d, (450, 340), (530, 340), label="YES")
    arrow(d, (880, 340), (1000, 340), label="YES")
    arrow(d, (1350, 340), (1450, 340), label="YES")
    arrow(d, (1800, 340), (1880, 340), label="YES")
    arrow(d, (275, 430), (275, 960), color=RED, label="NO")
    arrow(d, (705, 430), (275, 960), color=RED, label="NO")
    arrow(d, (1175, 430), (275, 960), color=RED, label="NO")
    arrow(d, (1625, 430), (1025, 960), color=ORANGE, label="NO: NICHE")
    arrow(d, (2055, 430), (1625, 960), color=TEAL, label="YES")
    arrow(d, (1800, 1050), (1880, 1050), color=PURPLE, label="3+ BINDING")
    save(im, "final_decision_tree.png")


pdfmetrics.registerFont(TTFont("Arial", FONT_REG))
pdfmetrics.registerFont(TTFont("Arial-Bold", FONT_BOLD))
pdfmetrics.registerFont(TTFont("Georgia", FONT_SERIF))


class DossierDocTemplate(BaseDocTemplate):
    def beforeDocument(self):
        self._have_h1 = False

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in {"H1", "H2"}:
            level = 0 if flowable.style.name == "H1" else 1
            text = flowable.getPlainText()
            key = getattr(flowable, "_bookmarkName", None)
            if level == 0:
                self._have_h1 = True
            if level == 1 and not self._have_h1:
                return
            if key:
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=level, closed=level == 0)
                self.notify("TOCEntry", (level, text, self.page, key))


def cover_page(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFillColor(colors.HexColor(NAVY))
    canvas_obj.rect(0, 0, LETTER[0], LETTER[1], fill=1, stroke=0)
    canvas_obj.setFillColor(colors.HexColor(EMERALD))
    canvas_obj.rect(0, 0, 0.18 * inch, LETTER[1], fill=1, stroke=0)
    canvas_obj.restoreState()


def normal_page(canvas_obj, doc):
    canvas_obj.saveState()
    w, h = LETTER
    canvas_obj.setStrokeColor(colors.HexColor(EMERALD))
    canvas_obj.setLineWidth(1.4)
    canvas_obj.line(0.62 * inch, h - 0.52 * inch, w - 0.62 * inch, h - 0.52 * inch)
    canvas_obj.setFont("Arial-Bold", 7.2)
    canvas_obj.setFillColor(colors.HexColor(MUTED))
    canvas_obj.drawString(0.62 * inch, h - 0.39 * inch, "ODYLITH  /  STRATEGIC INVESTMENT DOSSIER")
    canvas_obj.setFont("Arial", 7.2)
    canvas_obj.drawRightString(w - 0.62 * inch, h - 0.39 * inch, "EVIDENCE CUTOFF: 3 AUGUST 2026")
    canvas_obj.setStrokeColor(colors.HexColor(GRID))
    canvas_obj.setLineWidth(0.6)
    canvas_obj.line(0.62 * inch, 0.47 * inch, w - 0.62 * inch, 0.47 * inch)
    canvas_obj.setFont("Arial-Bold", 7.2)
    canvas_obj.setFillColor(colors.HexColor(MUTED))
    canvas_obj.drawString(0.62 * inch, 0.30 * inch, "CONFIDENTIAL • DECISION DOCUMENT")
    canvas_obj.drawRightString(w - 0.62 * inch, 0.30 * inch, f"{canvas_obj.getPageNumber():02d}")
    canvas_obj.restoreState()


styles = getSampleStyleSheet()
S = {}
S["CoverKicker"] = ParagraphStyle("CoverKicker", fontName="Arial-Bold", fontSize=10, leading=13, textColor=colors.HexColor("#8FE3CF"), spaceAfter=18)
S["CoverTitle"] = ParagraphStyle("CoverTitle", fontName="Georgia", fontSize=38, leading=42, textColor=colors.white, spaceAfter=18)
S["CoverSub"] = ParagraphStyle("CoverSub", fontName="Arial", fontSize=15, leading=21, textColor=colors.HexColor("#D4DEED"), spaceAfter=28)
S["CoverQuote"] = ParagraphStyle("CoverQuote", fontName="Georgia", fontSize=13, leading=19, textColor=colors.white, leftIndent=18, rightIndent=18, borderColor=colors.HexColor(EMERALD), borderWidth=0, borderPadding=12)
S["H1"] = ParagraphStyle("H1", fontName="Georgia", fontSize=23, leading=28, textColor=colors.HexColor(NAVY), spaceBefore=4, spaceAfter=14, keepWithNext=True)
S["H2"] = ParagraphStyle("H2", fontName="Arial-Bold", fontSize=14, leading=18, textColor=colors.HexColor(BLUE), spaceBefore=14, spaceAfter=7, keepWithNext=True)
S["H3"] = ParagraphStyle("H3", fontName="Arial-Bold", fontSize=10.5, leading=14, textColor=colors.HexColor(INK), spaceBefore=10, spaceAfter=5, keepWithNext=True)
S["Body"] = ParagraphStyle("Body", fontName="Arial", fontSize=9.1, leading=13.1, textColor=colors.HexColor(INK), spaceAfter=6, splitLongWords=True)
S["Small"] = ParagraphStyle("Small", parent=S["Body"], fontSize=7.5, leading=10.2, textColor=colors.HexColor(SLATE))
S["Bullet"] = ParagraphStyle("Bullet", parent=S["Body"], leftIndent=15, firstLineIndent=-9, bulletIndent=4, spaceAfter=3)
S["Number"] = ParagraphStyle("Number", parent=S["Body"], leftIndent=18, firstLineIndent=-14, bulletIndent=2, spaceAfter=3)
S["Quote"] = ParagraphStyle("Quote", fontName="Georgia", fontSize=10.4, leading=15.2, textColor=colors.HexColor(INK), leftIndent=18, rightIndent=12, borderColor=colors.HexColor(EMERALD), borderWidth=2, borderPadding=9, backColor=colors.HexColor("#F0FAF7"), spaceBefore=7, spaceAfter=9)
S["Code"] = ParagraphStyle("Code", fontName="Courier", fontSize=7.7, leading=10.4, textColor=colors.HexColor(INK), leftIndent=12, rightIndent=12, backColor=colors.HexColor("#F1F5F9"), borderPadding=5, spaceAfter=2)
S["TOCTitle"] = ParagraphStyle("TOCTitle", fontName="Georgia", fontSize=26, leading=31, textColor=colors.HexColor(NAVY), spaceAfter=18)


URL_RE = re.compile(r"https?://[^\s<]+")


def inline_markup(text):
    safe = html.escape(text)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
    safe = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", safe)

    def link(match):
        url = html.unescape(match.group(0)).rstrip(".,)")
        escaped = html.escape(url, quote=True)
        display = url if len(url) <= 72 else url[:68] + "…"
        suffix = match.group(0)[len(match.group(0).rstrip(".,)")) :]
        return f"<link href='{escaped}' color='#2563EB'>{html.escape(display)}</link>{suffix}"

    return URL_RE.sub(link, safe)


def paragraph(text, style="Body"):
    return Paragraph(inline_markup(text), S[style])


def table_flow(rows, width):
    cols = max(len(r) for r in rows)
    rows = [r + [""] * (cols - len(r)) for r in rows]
    weights = []
    for c in range(cols):
        longest = max(len(re.sub(r"\*+", "", row[c])) for row in rows)
        weights.append(max(8, min(42, math.sqrt(longest + 1) * 5)))
    total = sum(weights)
    col_widths = [width * w / total for w in weights]
    font_size = 7.1 if cols >= 5 else 7.6 if cols >= 4 else 8.0
    cell_style = ParagraphStyle("TableCell", parent=S["Body"], fontSize=font_size, leading=font_size + 2.1, spaceAfter=0)
    head_style = ParagraphStyle("TableHead", parent=cell_style, fontName="Arial-Bold", textColor=colors.white)
    data = []
    for ridx, row in enumerate(rows):
        data.append([Paragraph(inline_markup(cell), head_style if ridx == 0 else cell_style) for cell in row])
    table = LongTable(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor(GRID)),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def parse_markdown(text, frame_width):
    lines = text.splitlines()
    story = []
    i = 0
    hcount = 0
    section_started = False
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue
        if stripped == "[PAGEBREAK]":
            story.append(PageBreak())
            i += 1
            continue
        if stripped == "---":
            story.append(Spacer(1, 6))
            i += 1
            continue
        if stripped.startswith("!["):
            match = re.match(r"!\[(.*?)\]\((.*?)\)", stripped)
            if match:
                path = (SOURCE.parent / match.group(2)).resolve()
                if path.exists():
                    img = Image(str(path), width=frame_width, height=frame_width * 1400 / 2400)
                    img.hAlign = "CENTER"
                    story.extend([Spacer(1, 4), img, Paragraph(f"<i>{html.escape(match.group(1))}</i>", S["Small"]), Spacer(1, 8)])
            i += 1
            continue
        if stripped.startswith("# "):
            if section_started:
                story.append(PageBreak())
            section_started = True
            title = stripped[2:].strip()
            p = Paragraph(inline_markup(title), S["H1"])
            p._bookmarkName = f"h1_{hcount}"
            hcount += 1
            story.append(p)
            i += 1
            continue
        if stripped.startswith("## "):
            title = stripped[3:].strip()
            p = Paragraph(inline_markup(title), S["H2"])
            p._bookmarkName = f"h2_{hcount}"
            hcount += 1
            story.append(p)
            i += 1
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(inline_markup(stripped[4:].strip()), S["H3"]))
            i += 1
            continue
        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            rows = []
            for idx, line in enumerate(table_lines):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if idx == 1 and all(re.fullmatch(r":?-{3,}:?", c or "-") for c in cells):
                    continue
                rows.append(cells)
            if rows:
                story.extend([Spacer(1, 5), table_flow(rows, frame_width), Spacer(1, 9)])
            continue
        if stripped.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip()[1:].strip())
                i += 1
            story.append(Paragraph(inline_markup(" ".join(quote_lines)), S["Quote"]))
            continue
        if raw.startswith("    "):
            code_lines = []
            while i < len(lines) and (lines[i].startswith("    ") or not lines[i].strip()):
                if lines[i].strip():
                    code_lines.append(lines[i][4:])
                i += 1
            code_text = "<br/>".join(html.escape(line).replace(" ", "&nbsp;") for line in code_lines)
            story.append(Paragraph(code_text, S["Code"]))
            story.append(Spacer(1, 4))
            continue
        bullet = re.match(r"^-\s+(.*)", stripped)
        number = re.match(r"^(\d+)\.\s+(.*)", stripped)
        if bullet:
            story.append(Paragraph("• &nbsp;" + inline_markup(bullet.group(1)), S["Bullet"]))
            i += 1
            continue
        if number:
            story.append(Paragraph(f"{number.group(1)}. &nbsp;" + inline_markup(number.group(2)), S["Number"]))
            i += 1
            continue
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i]
            ns = nxt.strip()
            if not ns:
                i += 1
                break
            if ns == "---" or ns.startswith(("#", "|", ">", "![")) or nxt.startswith("    ") or re.match(r"^-\s+", ns) or re.match(r"^\d+\.\s+", ns):
                break
            para_lines.append(ns)
            i += 1
        text_value = " ".join(para_lines)
        style = "Small" if text_value.startswith("**[S") else "Body"
        story.append(paragraph(text_value, style))
    return story


def build_pdf():
    generate_assets()
    width, height = LETTER
    margin_x = 0.65 * inch
    top = 0.70 * inch
    bottom = 0.62 * inch
    frame = Frame(margin_x, bottom, width - 2 * margin_x, height - top - bottom, id="normal", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    cover_frame = Frame(0.82 * inch, 0.7 * inch, width - 1.64 * inch, height - 1.4 * inch, id="cover", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc = DossierDocTemplate(str(OUTPUT), pagesize=LETTER, leftMargin=margin_x, rightMargin=margin_x, topMargin=top, bottomMargin=bottom, title="Odylith Strategic Investment Dossier", author="freedom-research", subject="Adversarial market, product, and investment analysis")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame], onPage=cover_page),
        PageTemplate(id="normal", frames=[frame], onPage=normal_page),
    ])

    source = SOURCE.read_text(encoding="utf-8")
    body = source.split("---", 1)[1].lstrip()
    story = [
        Spacer(1, 0.75 * inch),
        Paragraph("STRATEGIC INVESTMENT DOSSIER", S["CoverKicker"]),
        Paragraph("ODYLITH", S["CoverTitle"]),
        Paragraph("From abundant intelligence<br/>to controlled consequence", S["CoverSub"]),
        Spacer(1, 0.25 * inch),
        Table([[Paragraph("THESIS VERDICT  •  CONDITIONAL BUILD", ParagraphStyle("Badge", fontName="Arial-Bold", fontSize=10, leading=13, textColor=colors.white, alignment=TA_CENTER))]], colWidths=[3.2 * inch], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(EMERALD)), ("BOX", (0, 0), (-1, -1), 0, colors.HexColor(EMERALD)), ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)])),
        Spacer(1, 0.42 * inch),
        Paragraph("“Intelligence is becoming abundant. Consequence is not.”", S["CoverQuote"]),
        Spacer(1, 0.72 * inch),
        Paragraph("Decision date  •  3 August 2026<br/>Prepared for founder and investment committee<br/>Evidence cutoff  •  3 August 2026", ParagraphStyle("CoverMeta", fontName="Arial", fontSize=9.2, leading=15, textColor=colors.HexColor("#AFC0D7"))),
        NextPageTemplate("normal"),
        PageBreak(),
        Paragraph("Contents", S["TOCTitle"]),
    ]
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC1", fontName="Arial-Bold", fontSize=9.2, leading=13, leftIndent=0, firstLineIndent=0, textColor=colors.HexColor(INK), spaceBefore=4),
        ParagraphStyle("TOC2", fontName="Arial", fontSize=8, leading=11, leftIndent=15, firstLineIndent=0, textColor=colors.HexColor(SLATE), spaceBefore=1),
    ]
    story.extend([toc, PageBreak()])
    story.extend(parse_markdown(body, frame._width))
    doc.multiBuild(story)


if __name__ == "__main__":
    build_pdf()
