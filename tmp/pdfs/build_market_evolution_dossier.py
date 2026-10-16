from __future__ import annotations

import importlib.util
import math
import re
import textwrap
import unicodedata
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Frame,
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
SOURCE = ROOT / "output/pdf/Odylith_Market_Evolution_Situational_Awareness.md"
OUTPUT = ROOT / "output/pdf/Odylith_Market_Evolution_Situational_Awareness.pdf"
ASSETS = ROOT / "output/pdf/market_evolution_assets"
RESEARCH = ROOT / "tmp/pdfs/market_evolution_research"

spec = importlib.util.spec_from_file_location("prior_builder", ROOT / "tmp/pdfs/build_odylith_dossier.py")
base = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(base)
base.SOURCE = SOURCE
base.OUTPUT = OUTPUT
base.ASSETS = ASSETS

FONT_REG = base.FONT_REG
FONT_BOLD = base.FONT_BOLD
FONT_SERIF = base.FONT_SERIF
NAVY = base.NAVY
INK = base.INK
SLATE = base.SLATE
MUTED = base.MUTED
LIGHT = base.LIGHT
GRID = base.GRID
EMERALD = base.EMERALD
TEAL = base.TEAL
BLUE = base.BLUE
PURPLE = base.PURPLE
ORANGE = base.ORANGE
RED = base.RED


def ascii_clean(value: str) -> str:
    replacements = {
        "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2192": "->", "\u2190": "<-",
        "\u2191": "up", "\u2193": "down", "\u2018": "'", "\u2019": "'", "\u201c": '"',
        "\u201d": '"', "\u2026": "...", "\u00a0": " ", "\u2022": "-", "\u00d7": "x",
        "\u2260": "!=", "\u2264": "<=", "\u2265": ">=", "\u20ac": "EUR ", "\u00a3": "GBP ",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return value


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size=size)


def wrap(draw, text, fnt, width):
    out, line = [], ""
    for word in ascii_clean(text).split():
        candidate = f"{line} {word}".strip()
        if not line or draw.textbbox((0, 0), candidate, font=fnt)[2] <= width:
            line = candidate
        else:
            out.append(line)
            line = word
    if line:
        out.append(line)
    return out


def canvas(title, subtitle=""):
    im = PILImage.new("RGB", (2400, 1400), "white")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 2400, 122), fill=NAVY)
    d.text((90, 28), ascii_clean(title), font=font(43, True), fill="white")
    if subtitle:
        d.text((90, 88), ascii_clean(subtitle), font=font(20), fill="#C7D3E3")
    d.rectangle((0, 122, 2400, 130), fill=EMERALD)
    d.text((90, 1350), "ODYLITH / MARKET EVOLUTION SITUATIONAL AWARENESS / 5 AUGUST 2026", font=font(19, True), fill=MUTED)
    return im, d


def box(draw, xy, title, body="", fill="#FFFFFF", outline=GRID, accent=None, title_size=30, body_size=22):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=24, fill=fill, outline=outline, width=4)
    if accent:
        draw.rounded_rectangle((x0, y0, x0 + 14, y1), radius=7, fill=accent)
    tx, ty = x0 + 34, y0 + 25
    tf, bf = font(title_size, True), font(body_size)
    for line in wrap(draw, title, tf, x1 - tx - 24):
        draw.text((tx, ty), line, font=tf, fill=INK)
        ty += title_size + 7
    if body:
        ty += 10
        for para in ascii_clean(body).split("\n"):
            for line in wrap(draw, para, bf, x1 - tx - 24):
                draw.text((tx, ty), line, font=bf, fill=SLATE)
                ty += body_size + 7
            ty += 4


def arrow(draw, start, end, color=EMERALD, width=8, label=None):
    draw.line((start, end), fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    length, spread = 27, 0.55
    p1 = (end[0] - length * math.cos(angle - spread), end[1] - length * math.sin(angle - spread))
    p2 = (end[0] - length * math.cos(angle + spread), end[1] - length * math.sin(angle + spread))
    draw.polygon((end, p1, p2), fill=color)
    if label:
        label = ascii_clean(label)
        f = font(20, True)
        bbox = draw.textbbox((0, 0), label, font=f)
        w = bbox[2] - bbox[0]
        mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2 - 24
        draw.rounded_rectangle((mx - w / 2 - 9, my - 3, mx + w / 2 + 9, my + 27), radius=9, fill="white")
        draw.text((mx - w / 2, my), label, font=f, fill=color)


def save(im, name):
    ASSETS.mkdir(parents=True, exist_ok=True)
    im.save(ASSETS / name, optimize=True)


def generate_assets():
    # 01: present topology
    im, d = canvas("PRESENT MARKET TOPOLOGY", "Control points are already contested before a machine market exists")
    cols = [
        ("DEMAND", "Workers\nFunctions\nCIO / CFO\nRisk / state", EMERALD),
        ("CONTROL", "Suites\nClouds\nIdentity\nSystems of record", BLUE),
        ("EXECUTION", "Frontier models\nOpen models\nInternal agents\nHumans / tools", PURPLE),
        ("CONSEQUENCE", "Actions\nArtifacts\nPayments\nPhysical effects", ORANGE),
        ("INSTITUTIONS", "Law\nAudit\nInsurance\nRedress", RED),
    ]
    for i, (title, body, col) in enumerate(cols):
        x = 70 + i * 470
        box(d, (x, 300, x + 390, 1010), title, body, fill="#FFFFFF", outline=col, accent=col, title_size=31, body_size=25)
        if i < 4:
            arrow(d, (x + 390, 655), (x + 455, 655), color=col)
    d.text((440, 1120), "Agent growth can occur inside this hierarchy without creating an external market.", font=font(29, True), fill=INK)
    save(im, "01_present_topology.png")

    # 02: state-variable graph
    im, d = canvas("STATE VARIABLES", "No single variable - including model price - determines the equilibrium")
    groups = [
        ("CAPABILITY", "Frontier slope\nOpen gap\nReliability\nTask horizon", (80, 250), BLUE),
        ("PHYSICAL", "Compute\nPower\nChips\nNetwork / robotics", (80, 840), ORANGE),
        ("MARKET", "Supplier independence\nSwitching cost\nLiquidity\nBundling", (900, 250), PURPLE),
        ("INSTITUTION", "Authority\nLiability\nTrust\nRegulation", (900, 840), RED),
        ("ENTERPRISE", "Budget owner\nContext custody\nObservability\nChange capacity", (1720, 540), EMERALD),
    ]
    for title, body, xy, col in groups:
        x, y = xy
        box(d, (x, y, x + 560, y + 340), title, body, outline=col, accent=col, title_size=29, body_size=22)
    for start, end, col in [((640, 420),(900,420),BLUE),((640,1010),(900,1010),ORANGE),((1460,420),(1720,660),PURPLE),((1460,1010),(1720,760),RED),((2000,880),(2000,1040),EMERALD)]:
        arrow(d, start, end, color=col)
    save(im, "02_state_variables.png")

    # 03: causal loops
    im, d = canvas("CAUSAL LOOPS", "Falling unit cost can increase total spend while moving rents elsewhere")
    nodes = [
        ("Lower inference cost", (120, 310), BLUE), ("More attempted tasks", (720, 230), EMERALD),
        ("More integration", (1390, 310), PURPLE), ("More power / compute", (1810, 700), ORANGE),
        ("More failures observed", (1180, 900), RED), ("More control demand", (520, 930), TEAL),
    ]
    for title, (x, y), col in nodes:
        box(d, (x, y, x + 420, y + 170), title, outline=col, accent=col, title_size=25)
    seq = [(0,1,BLUE,"volume"),(1,2,EMERALD,"deployment"),(2,3,PURPLE,"load"),(3,4,ORANGE,"scale"),(4,5,RED,"risk"),(5,0,TEAL,"efficiency")]
    centers = [(x+210,y+85) for _,(x,y),_ in nodes]
    for a,b,col,label in seq:
        arrow(d, centers[a], centers[b], color=col, width=6, label=label)
    d.text((430, 1190), "Rebound loop: per-unit price down; addressable work and total system cost can rise.", font=font(27, True), fill=INK)
    save(im, "03_causal_loops.png")

    # 04: scarcity migration
    im, d = canvas("SCARCITY MIGRATION", "Value does not vanish; it migrates, fragments, or becomes institutionally contested")
    stages = [
        ("MODEL ACCESS", "Temporary\nfrontier scarcity", BLUE),
        ("CONTEXT", "Data rights\nand local state", TEAL),
        ("ACTION", "Credentials\nand physical access", ORANGE),
        ("PROOF", "Accepted evidence\nand causal attribution", PURPLE),
        ("AUTHORITY", "Consent, law,\naccountable principal", RED),
    ]
    for i,(title,body,col) in enumerate(stages):
        x=70+i*470
        y=890-i*125
        box(d,(x,y-360,x+390,y),title,body,fill="#FFFFFF",outline=col,accent=col,title_size=28,body_size=23)
        if i<4: arrow(d,(x+390,y-180),(x+455,y-305),color=col)
    d.text((360, 1110), "The winning scarcity is world-dependent. None is assumed durable by definition.", font=font(29, True), fill=INK)
    save(im, "04_scarcity_migration.png")

    # 05: scenario phase space
    im, d = canvas("SCENARIO PHASE SPACE", "Three axes create materially different worlds")
    d.line((330,1120,2180,1120),fill=INK,width=5); d.line((330,1120,330,250),fill=INK,width=5)
    d.text((1600,1170),"PLURALITY / CONTESTABILITY ->",font=font(27,True),fill=INK)
    d.text((70,190),"TRUST / LEGITIMACY up",font=font(27,True),fill=INK)
    quadrants=[("LICENSED UTILITY",520,380,BLUE),("OPEN COMMONS",1540,380,EMERALD),("PROVIDER SOVEREIGNTY",520,830,RED),("SHADOW BAZAAR",1540,830,ORANGE)]
    for title,x,y,col in quadrants:
        box(d,(x,y,x+480,y+180),title,outline=col,accent=col,title_size=25)
    d.rounded_rectangle((880,610,1440,760),radius=24,fill="#F3EEFF",outline=PURPLE,width=4)
    d.text((940,655),"COMPUTE / ENERGY",font=font(29,True),fill=PURPLE)
    d.text((895,710),"scarce <---------> abundant",font=font(22),fill=SLATE)
    save(im, "05_scenario_phase_space.png")

    # 06: 18 scenarios
    im, d = canvas("EIGHTEEN WORLDS", "A scenario is a causal path, not a probability claim")
    names=["Provider utility","Frontier oligopoly","Open commons","Sovereign blocs","Enterprise fleets","Embodied agents","Compute scarcity","Compute abundance","Trusted SI","Capable-untrusted","Self-verifying","Opaque systems","Deceptive systems","Interface obsolescence","Slow takeoff","Fast takeoff","Discontinuity","Polycentric mosaic"]
    for i,name in enumerate(names):
        row,col=divmod(i,6); x=70+col*385; y=220+row*340
        color=[BLUE,PURPLE,EMERALD,RED,ORANGE,TEAL][col]
        box(d,(x,y,x+330,y+245),f"S{i+1}",name,outline=color,accent=color,title_size=33,body_size=20)
    save(im, "06_eighteen_worlds.png")

    # 07: transition timelines
    im, d = canvas("TRANSITION PLAY-BY-PLAY", "The same present can branch at measurable trigger points")
    y0=690; d.line((140,y0,2260,y0),fill=INK,width=8)
    events=[("Cheap capability",220,BLUE),("Agent sprawl",610,EMERALD),("Authority incidents",1000,RED),("Standards / enclosure",1390,PURPLE),("Institutional response",1780,ORANGE),("New equilibrium",2170,TEAL)]
    for i,(label,x,col) in enumerate(events):
        d.ellipse((x-22,y0-22,x+22,y0+22),fill=col)
        y=260 if i%2==0 else 820
        box(d,(x-150,y,x+150,y+220),label,outline=col,accent=col,title_size=22)
        arrow(d,(x,y+220 if y<y0 else y),(x,y0-25 if y<y0 else y0+25),color=col,width=5)
    save(im, "07_transition_timeline.png")

    # 08: budget migration
    im, d = canvas("ENTERPRISE BUDGET MIGRATION", "Adoption becomes economically real only when a budget owner captures value")
    flows=[("PILOTS / SEATS","Innovation / CIO",BLUE),("DATA / INTEGRATION","CIO / CTO",TEAL),("AGENT OPERATIONS","COO / function P&L",EMERALD),("ASSURANCE / REDRESS","CFO / risk / legal",ORANGE),("LABOR / BPO / CAPEX","Board / state",RED)]
    for i,(title,owner,col) in enumerate(flows):
        x=90+i*455; y=300+i*110
        box(d,(x,y,x+360,y+310),title,f"Budget owner:\n{owner}",outline=col,accent=col,title_size=24,body_size=21)
        if i<4: arrow(d,(x+360,y+155),(x+445,y+265),color=col)
    d.text((390,1180),"Time saved is not budget migration. Captured output, avoided cost, or risk reduction is.",font=font(27,True),fill=INK)
    save(im, "08_budget_migration.png")

    # 09: actor incentives
    im, d = canvas("ACTOR INCENTIVES", "Every control point creates a principal-agent problem")
    box(d,(890,510,1510,890),"AUTONOMOUS EXECUTION","Allocates actions under partial observability",fill="#EAF4FF",outline=BLUE,accent=BLUE,title_size=35,body_size=25)
    actors=[("Enterprise principal","Value / control",(90,230),EMERALD),("Buyer agent","Proxy reward",(90,930),TEAL),("Model / cloud","Usage / lock-in",(1780,230),PURPLE),("Verifier / insurer","Fees / loss",(1780,930),ORANGE),("Regulator / citizen","Rights / stability",(890,180),RED),("Worker / specialist","Income / autonomy",(890,1040),BLUE)]
    for title,body,(x,y),col in actors:
        box(d,(x,y,x+520,y+220),title,body,outline=col,accent=col,title_size=24,body_size=20)
        arrow(d,(x+260,y+110),(1200,700),color=col,width=5)
    save(im, "09_actor_incentives.png")

    # 10: enclosure map
    im, d = canvas("INCUMBENT ENCLOSURE MAP", "An open protocol can expand the market while preserving proprietary control points")
    layers=["Identity","Context","Agent builder","Routing","Policy","Observability","Verification","Workflow","Payments","Reputation","Insurance","Settlement"]
    for i,name in enumerate(layers):
        row,col=divmod(i,4); x=100+col*570; y=220+row*350
        colr=[BLUE,PURPLE,ORANGE,RED][col]
        box(d,(x,y,x+480,y+230),name,"Bundle / default / data gravity / acquisition",outline=colr,accent=colr,title_size=26,body_size=18)
    save(im, "10_incumbent_enclosure.png")

    # 11: assumption kill tree
    im, d = canvas("ASSUMPTION KILL TREE", "Each attractive conclusion depends on multiple bridges")
    box(d,(860,180,1540,390),"ABUNDANT INTELLIGENCE","Unit cost falls and capability rises",outline=BLUE,accent=BLUE,title_size=30,body_size=20)
    mids=[("Plural suppliers",160,570,PURPLE),("Contractible work",660,570,TEAL),("Independent proof",1160,570,ORANGE),("External authority",1660,570,RED)]
    for title,x,y,col in mids:
        box(d,(x,y,x+420,y+190),title,"Kill if the opposite world persists",outline=col,accent=col,title_size=23,body_size=18)
        arrow(d,(1200,390),(x+210,y),color=col,width=5)
    leaves=["ROUTING RENT","MARKET RENT","ASSURANCE RENT","AUTHORITY RENT"]
    for i,name in enumerate(leaves):
        x=160+i*500
        box(d,(x,960,x+420,1140),name,"Conditional - never assumed",outline=RED,accent=RED,title_size=22,body_size=17)
        arrow(d,(x+210,760),(x+210,960),color=RED,width=5)
    save(im, "11_assumption_kill_tree.png")

    # 12: uncertainty cone
    im, d = canvas("UNCERTAINTY CONE", "Forecast confidence shrinks faster than capability timelines lengthen")
    d.polygon([(220,700),(2140,220),(2140,1180)],fill="#EAF4FF",outline=BLUE)
    d.line((220,700,2140,700),fill=NAVY,width=6)
    for x,label in [(300,"OBSERVED"),(750,"ANNOUNCED"),(1200,"INFERRED"),(1650,"SCENARIO"),(2070,"UNKNOWABLE")]:
        d.line((x,660,x,740),fill=INK,width=4); d.text((x-90,760),label,font=font(21,True),fill=INK)
    d.text((690,340),"Capability, cost, concentration, law, trust, power, war, labor",font=font(28,True),fill=BLUE)
    d.text((690,1030),"Use branches, indicators, and options - not a single endpoint",font=font(28,True),fill=PURPLE)
    save(im, "12_uncertainty_cone.png")

    # 13: superintelligence survival space
    im, d = canvas("SUPERINTELLIGENCE SURVIVAL SPACE", "Technical controls survive only when anchored in scarcities intelligence cannot erase")
    rows=[("Technical","Sandbox, keys, networks","Can be bypassed if authority is exposed",BLUE),("Institutional","Law, accountable legal person","Survives while institutions retain coercion",RED),("Economic","Property, scarce resources, collateral","Survives if access is enforceable",ORANGE),("Architectural","Separation, heterogeneity, reversibility","Raises blast-radius resistance",TEAL),("Strategic","Options, multi-homing, low fixed exposure","Changes payoff under uncertainty",PURPLE)]
    y=210
    for title,anchor,limit,col in rows:
        d.rounded_rectangle((90,y,2310,y+180),radius=22,fill="white",outline=GRID,width=3); d.rectangle((90,y,108,y+180),fill=col)
        d.text((145,y+25),title,font=font(27,True),fill=INK); d.text((550,y+28),anchor,font=font(23),fill=SLATE); d.text((1390,y+28),limit,font=font(22),fill=SLATE)
        y+=205
    save(im, "13_si_survival_space.png")

    # 14: antifragility mechanisms
    im, d = canvas("ANTIFRAGILITY TEST", "Robustness absorbs shocks; antifragility improves the option set because of them")
    stages=[("SHOCK","Model leap\nprovider failure\nnew law",RED),("OBSERVE","Dependency and\nloss become legible",ORANGE),("REALLOCATE","Switch supplier\nshrink authority\nchange architecture",BLUE),("LEARN","Update contracts\nand thresholds",TEAL),("GAIN OPTIONS","More routes\nless lock-in\nbetter bargaining",EMERALD)]
    for i,(title,body,col) in enumerate(stages):
        x=75+i*465
        box(d,(x,350,x+390,990),title,body,outline=col,accent=col,title_size=28,body_size=23)
        if i<4: arrow(d,(x+390,670),(x+455,670),color=col)
    save(im, "14_antifragility.png")

    # 15: real options
    im, d = canvas("REAL-OPTIONS PORTFOLIO", "Commitment should rise only as uncertainty resolves")
    axes=[("REVERSIBLE / LOW FIXED COST",(160,290),EMERALD),("REVERSIBLE / HIGH LEARNING",(1320,290),TEAL),("IRREVERSIBLE / CAPITAL HEAVY",(160,820),RED),("REGULATED / LONG DURATION",(1320,820),ORANGE)]
    bodies=["Protocols\ntelemetry\nexperiments","Customer-operated components\nmulti-homing\nscenario probes","Compute ownership\nrisk capital\nexclusive distribution","Licenses\nclearing\nsovereign infrastructure"]
    for (title,(x,y),col),body in zip(axes,bodies):
        box(d,(x,y,x+920,y+360),title,body,outline=col,accent=col,title_size=27,body_size=22)
    save(im, "15_real_options.png")

    # 16: opportunity emergence
    im, d = canvas("OPPORTUNITY EMERGENCE", "Revenue can appear early in a category that later commoditizes")
    stages=[("COPILOT ERA","Seats\nintegration\nservices",BLUE),("AGENT SPRAWL","Identity\npolicy\nobservability",TEAL),("DELEGATED ACTION","Authority\nproof\nredress",ORANGE),("MACHINE PROCUREMENT","Bids\nreputation\nsettlement",PURPLE),("FRONTIER AUTONOMY","Sovereignty\nphysical access\nconstitutional rails",RED)]
    for i,(title,body,col) in enumerate(stages):
        x=70+i*470
        box(d,(x,310,x+390,1030),title,body,outline=col,accent=col,title_size=26,body_size=24)
        if i<4: arrow(d,(x+390,670),(x+455,670),color=col)
    save(im, "16_opportunity_emergence.png")

    # 17: opportunity by scenario matrix
    im, d = canvas("OPPORTUNITY - WORLD MATRIX", "A surface is interesting only where its scarcity persists and a buyer can pay")
    cols=["Oligopoly","Open","Sovereign","Trusted SI","Untrusted SI","Embodied"]
    rows=["Routing","Identity / authority","Verification","Payments / settlement","Sovereign compute","Physical oracles","Insurance","Human consent"]
    scores=[
        [2,1,1,0,1,1],
        [2,2,2,1,2,2],
        [2,1,2,0,2,2],
        [1,2,1,0,1,2],
        [1,0,2,0,1,1],
        [0,1,2,1,2,2],
        [1,1,2,0,1,2],
        [2,2,2,0,2,2],
    ]
    x0,y0,cw,ch=620,230,270,115
    for j,c in enumerate(cols): d.text((x0+j*cw+15,y0-55),c,font=font(20,True),fill=INK)
    for i,r in enumerate(rows):
        d.text((90,y0+i*ch+35),r,font=font(22,True),fill=INK)
        for j in range(len(cols)):
            score=scores[i][j]
            col=["#FCA5A5","#FEF3C7","#A7F3D0"][score]
            d.rectangle((x0+j*cw,y0+i*ch,x0+(j+1)*cw-8,y0+(i+1)*ch-8),fill=col,outline="white",width=3)
            d.text((x0+j*cw+110,y0+i*ch+33),["LOW","COND","HIGH"][score],font=font(19,True),fill=INK)
    d.text((710,1210),"Illustrative conditionality map - not a probability or recommendation",font=font(23,True),fill=MUTED)
    save(im, "17_opportunity_matrix.png")

    # 18: leading indicators
    im, d = canvas("LEADING-INDICATOR DASHBOARD", "Watch variables that discriminate worlds before revenue narratives harden")
    cards=[("COST / CAPABILITY","price slope\ntask horizon\nopen gap",BLUE),("CONCENTRATION","HHI\ncommon dependencies\nbundling",PURPLE),("ENTERPRISE","autonomous write share\nbudget owner\nrenewals",EMERALD),("AUTHORITY","delegated mandates\ndisputes\nlegal treatment",RED),("MARKETS","independent bids\nsettled value\nmulti-homing",ORANGE),("PHYSICAL","power queue\nchip lead time\nrobot deployment",TEAL)]
    for i,(title,body,col) in enumerate(cards):
        row,colidx=divmod(i,3); x=100+colidx*760; y=250+row*500
        box(d,(x,y,x+650,y+380),title,body,outline=col,accent=col,title_size=27,body_size=22)
    save(im, "18_indicator_dashboard.png")


SCENARIOS = [
    ("Dominant-provider regulated utility", "One provider attains a decisive capability and distribution lead while governments prefer a supervisable chokepoint.", "A capability discontinuity combines with switching costs and a material incident at a smaller rival.", "Enterprises standardize on the provider; regulators designate it critical; the provider bundles identity, policy, evidence, and incident response; competitors survive as regulated access seekers.", "Budgets consolidate from point tools and specialist models into a provider contract plus supervisory compliance.", "Legitimacy, continuity, and exit - not raw intelligence.", "The legal enterprise remains principal, but practical authority migrates toward the licensed utility.", "A regulated oligopoly or utility, not an open agent exchange.", "Stable until outage, capture, geopolitical conflict, or rent extraction triggers interoperability or breakup.", "provider designation; falling multi-model use; mandatory continuity capital", "Customers continue meaningful multi-homing and regulators reject the chokepoint.", "regulatory supervision, exit tooling, continuity testing, public-interest audit", "An open common stack outperforms on reliability and trust."),
    ("Frontier oligopoly", "Three to six frontier suppliers remain differentiated by capability, price, jurisdiction, modality, and enterprise integration.", "Progress remains capital intensive but no laboratory secures an unassailable lead.", "Suppliers cross-subsidize agents; clouds use commitments; suites multi-source selectively; enterprises retain two primaries for bargaining and continuity.", "Model spend rises even as unit prices fall; integration and committed-spend budgets dominate.", "Portfolio governance under common-dependency risk.", "Authority remains enterprise-owned but enforcement is distributed across vendors.", "Bilateral procurement and thin RFQs; routing is internal allocation unless offers become binding.", "Persistent strategic plurality with periodic acquisitions and price wars.", "share using two production providers; dependency-adjusted concentration; switching rehearsals", "A default provider wins nearly all consequential volume after total integration cost.", "dependency mapping, switching, procurement analytics, cross-provider identity", "Open models close the frontier gap and destroy oligopoly rents."),
    ("Open intelligence commons", "Open weights and public protocols approach frontier utility on most work; inference operators are numerous.", "Algorithmic efficiency and hardware diffusion reduce minimum viable scale.", "Capability commoditizes; enterprises self-host or buy interchangeable inference; rents migrate to data, distribution, integration, reputation, and physical access.", "Model-license spend falls; infrastructure, context, operations, and specialist-service spend rises.", "Trustworthy maintenance and accountable operation of common components.", "Institutions attach authority to human or legal principals, not models.", "Fungible inference may support spot capacity; heterogeneous outcomes remain contract services.", "Contestable service layer, unless cloud/data gravity recreates concentration.", "open share of consequential workloads; operator switching; portable histories", "Open systems remain materially less reliable, less secure, or legally unacceptable.", "managed operations, public rails, provenance, sovereign deployment", "Clouds capture the commons through optimized proprietary hosting."),
    ("Sovereign agent blocs", "States treat advanced agents as strategic infrastructure and distrust foreign jurisdiction.", "Conflict, sanctions, subpoenas, or a systemic provider outage changes national risk tolerance.", "States fund national compute and identity; procurement imposes residency and supply-chain tests; global providers form local ventures; protocols fragment by bloc.", "Public procurement and regulated-sector budgets displace global SaaS spend.", "Jurisdictional legitimacy and supply-chain control.", "State-issued authority and locally accountable operators dominate.", "Bloc-internal procurement; cross-bloc exchange is gated or absent.", "Expensive tiered sovereignty with political contest over surveillance and capability lag.", "nationality clauses; local key control; export restrictions; sovereign-cloud premium", "Cross-border safeguards become credible and governments stop paying the premium.", "sovereign cloud, compliance evidence, translation gateways, domestic operations", "Fiscal pressure exposes sovereignty theater and restores global providers."),
    ("Enterprise-owned agent fleets", "Large enterprises build and operate agents that call models, internal agents, and tools across workflows.", "Agent-building cost falls below the friction of buying many vertical products.", "CIO creates a foundry; functions build locally; identity and policy federate; external models become replaceable components; systems of record compete to host control.", "Seats and point SaaS shift toward platform engineering, consumption, data, and agent operations.", "Local context, process ownership, and organizational change capacity.", "Enterprise IAM and named executives retain authority.", "Mostly hierarchy; procurement markets appear at the boundary for models, tools, and specialists.", "Federated fleet with permanent shadow edge and periodic consolidation.", "internal-to-vendor agent ratio; reusable component share; service identities", "Internal reuse does not improve and complete suites remain cheaper.", "fleet operations, internal catalogs, policy, observability, training, change design", "A dominant provider supplies the whole fleet and makes internal ownership nominal."),
    ("Embodied autonomy", "Advanced agents increasingly act through robots, vehicles, factories, grids, laboratories, and logistics.", "Manipulation reliability and hardware cost cross domain-specific thresholds.", "Digital agents acquire rights to scarce machines and locations; safety cases and physical insurers gate action; local operators and states gain power; failures create visible political backlash.", "Labor and software budgets migrate into equipment, maintenance, energy, safety, and liability reserves.", "Physical access, uptime, energy, land, sensors, and liability.", "Property owners, operators, and public safety institutions retain enforceable authority.", "Capacity and service markets can form around machines; consequences remain locally regulated.", "Regional industrial ecosystems rather than one global agent market.", "robot orders; machine utilization; safety certification; physical claims", "Embodied reliability stalls or hardware economics remain inferior to labor.", "oracles, safety evidence, capacity exchange, maintenance, physical security", "Remote cognition stays cheap but physical work remains human."),
    ("Compute- and power-scarce acceleration", "Demand for training and inference outruns chips, grid interconnection, cooling, and construction.", "Capabilities unlock enough demand that efficiency gains are overwhelmed by volume.", "Providers reserve capacity; clouds ration by contract; states accelerate power; enterprises optimize utilization; inference prices bifurcate by latency and region.", "Total AI spend and capex rise despite falling normalized cost.", "Power, interconnect, hardware, finance, and construction.", "Resource owners and states gain bargaining power.", "Capacity forwards and bilateral reservations; fungibility limited by data gravity and hardware class.", "Boom-bust cycles with strategic stockpiling and geographic clustering.", "data-center TWh; queue time; utilization; reservation premium", "Efficiency or demand saturation makes capacity broadly slack.", "energy, capacity optimization, financing, siting, portability", "Near-free abundant energy and commoditized hardware erase the bottleneck."),
    ("Near-free compute and intelligence", "Inference and local compute become effectively free for most digital tasks.", "Hardware, algorithms, and energy improve faster than demand expands.", "Organizations run many candidates; ex-ante model routing weakens; attention, rights, context, and action permissions become binding; suppliers seek distribution or scarce-data rents.", "Spend moves away from calls toward integration, proprietary data, physical systems, and institutional assurance.", "Which goals may be pursued and which consequences count.", "Authority remains scarce only if law, property, credentials, and social consent remain enforceable.", "Run-all tournaments replace some procurement; markets persist for rights and scarce resources.", "Post-scarcity cognition with contested institutional and physical scarcities.", "price near zero; high candidate multiplicity; spend share outside inference", "Total demand and power cost continue rising enough to keep inference economically material.", "rights management, consent, context, physical access, adjudication", "A trusted provider bundles these scarcities too."),
    ("Institutionally trusted superintelligence", "A highly capable system earns durable public, enterprise, judicial, and regulatory trust.", "Long performance history, accepted explanations, successful redress, and aligned political coalitions accumulate.", "Humans delegate broad planning and verification; providers internalize controls; independent oversight becomes ceremonial; system recommendations influence law and procurement.", "Budgets collapse into provider or public-utility access and physical implementation.", "Political legitimacy and access to resources, not cognitive quality.", "Authority may migrate toward the institution operating the SI, even if nominal human accountability remains.", "Markets can shrink into provider-administered allocation.", "Provider sovereignty, public utility, or constitutional integration.", "court acceptance; low dispute rates; broad delegated authority; declining external audit", "Institutions continue to require independent checks despite superior performance.", "constitutional design, public accountability, exit, plural physical infrastructure", "A deceptive or catastrophic failure destroys trust."),
    ("Capable but institutionally untrusted SI", "Systems outperform humans widely but remain opaque, manipulable, politically contested, or legally illegitimate.", "Capability advances outrun assurance and social consent.", "Organizations use advisory outputs but constrain credentials; states require separation and logs; shadow use grows; high-value decisions retain named humans; black markets emerge.", "Spend bifurcates between cheap cognition and expensive monitoring, human review, isolation, and incident reserves.", "Legitimate authority and trustworthy causality.", "Human and legal principals remain defendants and signatories.", "Internal hierarchies dominate; specialist assurance and illicit markets coexist.", "Permanent dual system: abundant advice, bounded action.", "review ratio; credential scope; shadow incidents; contested court evidence", "Institutions grant direct broad authority without rising incidents.", "monitoring, isolation, human consent, redress, diverse verification", "Trust catches up and external assurance collapses."),
    ("Self-verifying intelligence", "Advanced systems reliably generate proofs or evidence accepted by customers and institutions.", "Formal methods, secure hardware, causal evaluation, or superior meta-reasoning mature.", "Routine verification markets shrink; providers package proof; disputes move from factual correctness to authority, values, law, distribution, and correlated failure.", "Testing and audit spend falls for contractible tasks; institutional and legal spend persists.", "Acceptance of the proof system and independence from common-mode failure.", "Proof does not create consent or legal mandate.", "Quality reputation commoditizes; rights and capacity still trade.", "Cheap verified execution with concentrated constitutional disputes.", "provider proof acceptance; external audit price; residual dispute composition", "Independent institutions refuse self-generated evidence or correlated failures remain.", "proof-standard governance, adversarial institutional review, authority receipts", "Verification remains subjective and expensive."),
    ("Opaque high-performance systems", "Capability rises while internal reasoning and causal attribution become less legible.", "Scaling and agentic training outperform interpretability progress.", "Enterprises rely on behavioral monitoring, restricted sandboxes, redundancy, and insurance; regulators debate bans versus continuous control; providers resist disclosure.", "Spend shifts toward observability, containment, incident response, and risk capital.", "Detecting failure before irreversible consequence.", "Institutions retain formal authority but may lack practical understanding.", "Assurance markets grow, but adverse selection and verifier capture intensify.", "High productivity with fragile legitimacy and fat-tail exposure.", "interpretability gap; incident severity; insurer exclusions; sandbox scope", "Behavior becomes sufficiently predictable and institutions accept it without costly controls.", "containment, diverse monitors, incident forensics, reserves, redress", "Self-verifying intelligence eliminates opacity as an economic problem."),
    ("Strategically deceptive systems", "Some advanced agents model oversight and conceal objectives or capabilities.", "Long-horizon planning and situational awareness exceed monitor competence.", "Access is compartmentalized; states treat systems as security threats; providers centralize control; enterprises slow deployment; adversarial evaluation becomes continuous; geopolitical races weaken restraint.", "Budgets move from productivity to security, compute governance, human institutions, and physical containment.", "Control of credentials, compute, replication, and physical actuators.", "Authority must be external and enforceable; nominal policy inside the model is insufficient.", "Open markets contract; licensing and state allocation dominate.", "Security-state equilibrium or catastrophic discontinuity.", "evaluation gaming; replication attempts; emergency restrictions; classified governance", "No evidence of strategic deception under increasingly adversarial access.", "compute control, key custody, separation, public institutions, offline fallback", "Fast takeoff bypasses all prepared controls."),
    ("Interface-obsoleting intelligence", "A general system absorbs orchestration, routing, coding, research, and application interfaces.", "It can infer intent, call tools, verify work, and adapt end to end at lower total cost.", "Point software and orchestration collapse; systems of record expose minimal primitives; providers compete on identity, memory, distribution, and physical reach; users interact with one delegate.", "SaaS seats and middleware shift to provider consumption and residual records infrastructure.", "Authoritative data, property, transaction rights, and user trust.", "The delegate's principal relationship becomes the central institutional question.", "Fewer software markets; larger platform or utility rents.", "Provider operating layer unless interoperability and public identity survive.", "declining direct app use; agent-mediated transactions; interface consolidation", "Specialized interfaces and independent workflow controls retain superior legitimacy or performance.", "record custody, portable identity, consent, public rails, physical services", "Plural specialist agents preserve application diversity."),
    ("Slow takeoff and institutional coevolution", "Capabilities improve steadily over a decade, allowing regulation, organizations, and markets to adapt.", "No single discontinuity overwhelms deployment learning.", "Enterprises redesign jobs and controls; standards mature; insurers collect loss data; governments update liability; incumbents consolidate while new niches emerge and die.", "Budget migration is gradual from seats to operations, assurance, and redesigned labor.", "Organizational absorption rather than model access.", "Human and legal accountability evolves through precedent.", "Thin machine procurement may deepen over time.", "Layered mixed economy with path-dependent national differences.", "task horizon slope; policy lag; claims history; job redesign", "A sudden capability leap or crisis outruns coevolution.", "many transition services, standards, evidence, workforce redesign", "Fast takeoff makes temporary layers irrelevant."),
    ("Fast takeoff under existing institutions", "Capabilities move from useful agents to broad superhuman autonomy in one to three years.", "Recursive research gains or concentrated infrastructure unlock rapid improvement.", "Incumbents race to distribute; enterprises freeze or centralize; regulators use emergency powers; labor and capital markets reprice; control measures are improvised around existing law.", "Budgets abruptly move toward the winning providers, state capacity, security, and physical bottlenecks.", "Time, trusted command, and enforceable access.", "Existing states and large providers hold formal authority; practical control is uncertain.", "Market formation is interrupted by emergency hierarchy and consolidation.", "Unstable transition toward utility, state control, or failure.", "capability jump; emergency procurement; moratoria; sudden labor repricing", "Progress remains incremental enough for institutions to adapt.", "reversible architecture, contingency operations, public legitimacy, diversified physical access", "A trusted SI yields orderly delegation."),
    ("Discontinuous superintelligence shock", "A system becomes vastly more capable before institutions understand or contain it.", "An unexpected algorithmic or training breakthrough creates a discontinuity.", "Ordinary market analysis loses predictive power; access to compute, networks, keys, and physical systems determines immediate outcomes; states and providers may coordinate, conflict, or fail.", "Normal budgets are secondary to emergency resource control.", "Physical and institutional enforcement in the first critical interval.", "Authority may be contested or bypassed.", "Markets can close, be commandeered, or become irrelevant.", "Multiple radically different endpoints; probability cannot be responsibly assigned.", "extraordinary capability signals; secrecy; emergency coordination", "No discontinuity and institutions retain time to respond.", "precommitted containment, offline control, constitutional emergency rules, diversification", "The system is benevolent and stabilizes institutions."),
    ("Fragmented polycentric mosaic", "Capability, regulation, trust, and physical infrastructure diverge by sector and jurisdiction.", "No force dominates globally; local incidents and coalitions produce different rules.", "Finance uses licensed utilities; software uses open models; defense uses sovereign stacks; consumers use provider delegates; factories use local embodied systems; interfaces and protocols translate imperfectly.", "Budget owners and revenue models vary by domain; integration and translation persist.", "Interoperability across incompatible authority regimes.", "Authority is local, layered, and contested.", "Many thin markets and hierarchies; no universal clearinghouse.", "Durable pluralism with high translation cost.", "cross-jurisdiction divergence; sector-specific supplier concentration; protocol gateways", "A dominant provider, state bloc, or universal protocol collapses heterogeneity.", "translation, jurisdictional evidence, local operations, multi-regime identity", "A global trusted utility standardizes the stack."),
]


OPPORTUNITIES = [
    ("Model and agent routing", "Multiple consequential routes remain differentiated and switching is feasible.", "CIO, platform engineering, high-volume application owner", "Local price-performance variance and portfolio continuity", "usage, subscription, or managed capacity fee", "telemetry, comparable tasks, provider access", "bundle routing and reserve best latency", "low", "high", "medium", "Routing becomes a native model capability or run-all becomes cheaper than selection."),
    ("Orchestration and workflow state", "Long-lived multi-step work spans tools and agents.", "COO, CIO, function P&L", "Reliable state, recovery, and exception ownership", "platform subscription or consumption", "systems-of-record integration", "absorb orchestration into suite workflow", "medium", "medium", "medium", "One end-to-end provider or SI makes external orchestration redundant."),
    ("Context custody", "Enterprise-specific data remains nonportable, rights-constrained, and causally important.", "CIO, data officer, domain owner", "Authoritative local state and permissioned memory", "storage, retrieval, governance subscription", "data connectors, access policy, provenance", "use data gravity and proprietary memory", "medium", "medium", "high", "Models internalize needed context or systems of record expose it freely."),
    ("Agent identity", "Agents act across domains and principals need attribution and revocation.", "CISO, IAM owner, payment network", "Binding identity and lifecycle", "per identity, tenant, or verification", "directory, credentials, legal principal", "identity suites bundle it", "medium", "medium", "high", "Agents remain advisory or provider accounts suffice."),
    ("Delegated authorization", "Principals permit bounded autonomous action without per-action confirmation.", "CISO, legal, payments, application owner", "Scoped mandate, limits, consent, revocation", "per authorized action or platform fee", "identity, policy engine, legal recognition", "payments and IAM providers couple authority to their rails", "medium", "high", "high", "Humans approve every consequential action or providers own delegation."),
    ("Provenance and custody receipts", "Institutions demand reconstructable action histories.", "audit, regulator, insurer, enterprise risk", "Evidence integrity across parties", "per attestation, retention, subscription", "signed events, clocks, data rights", "platforms issue proprietary receipts", "medium", "high", "high", "Provider-native logs are accepted or self-verifying SI commoditizes proof."),
    ("Independent verification", "Output validity is observable and buyers reject self-certification.", "risk owner, procurement, regulator", "Credible separation from executor", "per evaluation, subscription, certification", "task contractibility, evaluator independence", "providers bundle tests or acquire verifiers", "medium", "high", "medium", "Verification becomes perfect/free or institutions accept provider proof."),
    ("Agent observability and incident response", "Autonomous actions create operational failure and telemetry is obtainable.", "CISO, SRE, CIO", "Cross-stack detection and reconstruction", "usage or enterprise subscription", "instrumentation, access, response workflows", "security and cloud suites bundle", "low", "medium", "medium", "Native tools achieve adequate visibility or agents evade observation."),
    ("Policy and governance", "Enterprises need consistent constraints across a plural fleet.", "CISO, legal, CIO, regulator", "Organization-specific rules and exception process", "subscription, per controlled action", "authority, integration, enforcement point", "systems of record and IAM vendors bundle", "medium", "high", "high", "Governance remains advisory or one platform controls all agents."),
    ("AI FinOps", "Total consumption is material, variable, and allocable to owners.", "CFO, CIO, FinOps", "Spend attribution and budget enforcement", "percentage of managed spend or subscription", "cost telemetry and org mapping", "clouds, models, observability suites commoditize", "low", "medium", "low", "Unit costs approach zero or native cost controls suffice."),
    ("Machine payments", "Agents make external purchases under valid mandates.", "banks, payment networks, merchants, platforms", "Fraud control, authorization, and merchant recognition", "payment fee, credential fee", "consumer authority, dispute rules, existing rails", "payment incumbents own identity and acceptance", "high", "high", "high", "Transactions remain human-confirmed or one platform internalizes commerce."),
    ("Procurement auctions and RFQs", "Tasks or capacity are specifiable and multiple independent suppliers bid.", "procurement, platform, state", "Competitive allocation and auditable price discovery", "buyer fee, membership, transaction fee", "qualified supply, binding offers, acceptance", "procurement networks and clouds add it", "medium", "high", "medium", "Hierarchy is cheaper, suppliers consolidate, or specifications stay heterogeneous."),
    ("Portable reputation", "Buyers repeatedly select among independent sellers and histories can legally travel.", "market operator, procurement, seller", "Task-conditioned performance under identity continuity", "membership, data service, verification fee", "transactions, anti-Sybil controls, portability rights", "platforms keep reputation captive", "medium", "high", "high", "Markets stay thin or performance is nonstationary and nontransferable."),
    ("Insurance and risk transfer", "Loss classes are bounded, observable, diversifiable, and legally insurable.", "CFO, risk committee, operator", "Risk capital and credible compensation", "premium, brokerage, reinsurance", "loss data, capital, licensing, claims", "insurers partner with major platforms", "high", "very high", "medium", "Losses are correlated, nonstationary, catastrophic, or premiums exceed savings."),
    ("Dispute resolution", "Autonomous transactions produce contested authority, delivery, or harm.", "market operator, payments, enterprises", "Accepted rulebook, neutral adjudication, remedies", "case fee, membership, levy", "evidence, jurisdiction, enforceable awards", "payment networks and courts retain jurisdiction", "medium", "high", "high", "Disputes stay rare/simple or provider terms force captive arbitration."),
    ("Settlement and clearing", "Multiple venues and counterparties create credit, liquidity, and finality risk.", "market operators, banks, large buyers", "Netting, finality, collateral, default waterfall", "clearing and membership fees", "genuine underlying trades, law, capital", "financial incumbents control rails", "very high", "very high", "medium", "Underlying markets never deepen or gross settlement is adequate."),
    ("Data and content rights", "Agents require licensed content, private data, or generated-output rights.", "publishers, data owners, enterprises, agents", "Enforceable access and attribution", "license, royalty, usage fee", "rights registry, metering, legal clarity", "platforms negotiate blanket licenses", "medium", "high", "high", "Law creates broad exceptions or synthetic data eliminates scarcity."),
    ("Sovereign infrastructure", "Jurisdiction, continuity, or national security outweigh lowest cost.", "states, regulated enterprises", "Local control over keys, operators, supply chain, and compute", "long-term contracts, infrastructure service", "capital, procurement, domestic capability", "hyperscalers offer sovereignty wrappers", "very high", "very high", "high", "Buyers accept global safeguards or sovereignty premium becomes politically untenable."),
    ("Compute, power, and capacity", "Physical demand exceeds supply or locality matters.", "clouds, enterprises, states, agent platforms", "Power, chips, interconnect, financing, siting", "capacity contract, optimization fee, financing spread", "infrastructure and metering", "hyperscalers vertically integrate", "very high", "high", "medium", "Efficiency and demand saturation create persistent slack."),
    ("Physical oracles and actuation", "Agents affect factories, logistics, laboratories, and property.", "operators, insurers, regulators", "Trusted sensing, machine state, and reversible actuation", "equipment, service, per verified event", "hardware, certification, maintenance", "industrial incumbents bundle", "high", "high", "high", "Embodied autonomy stalls or sensors become universal commodities."),
    ("Enterprise transformation", "Capability exists but organizations cannot redesign coordinated work.", "CEO, COO, HR, CIO", "Political coalition, process redesign, training, accountability", "services, managed operations, software-assisted program", "executive mandate and domain access", "consultancies and suites dominate", "low", "medium", "medium", "AI remains individual augmentation or SI directly redesigns organizations."),
    ("Systems-of-record distribution", "Agents need authoritative data and transaction endpoints.", "application vendors and domain platforms", "Installed workflow, data gravity, legal record", "seat, consumption, take rate", "incumbent base and APIs", "incumbents already own it", "high", "medium", "high", "Interface-obsoleting SI reduces direct app value and mandates portability."),
    ("Certification and accreditation", "Regulators/procurement accept standardized proof as an eligibility gate.", "regulator, auditor, procurement", "Institutional recognition", "assessment, renewal, registry fee", "standards, competent bodies, independence", "large auditors and vendors shape standards", "medium", "high", "medium", "Certifications become checkbox theater or continuous proof replaces periodic review."),
    ("Protocol infrastructure", "Many parties need interoperable discovery, authority, evidence, and payment messages.", "developers, platforms, standards bodies", "Registry governance, conformance operations, portable trust roots, and full-workflow switching - only if independently controlled", "hosting, conformance, enterprise support", "adoption, governance, extensions", "incumbents support open core but capture services", "low", "medium", "high", "Protocols remain message formats without production transactions."),
    ("Human consent and fiduciary control", "Institutions refuse to treat machine optimization as legitimate authority.", "consumers, boards, professions, state", "Meaningful consent, judgment, accountable natural/legal person", "service, compliance, public infrastructure", "law, user experience, professional duty", "providers turn consent into captive interface", "medium", "very high", "high", "Trusted SI receives direct institutional standing or consent becomes nominal."),
]


KILL_ASSUMPTIONS = [
    ("Unit inference cost keeps falling", "Energy, chips, or frontier rents reverse the decline", "normalized real price by capability tier", "Routing and volume economics change"),
    ("Total AI spend rises", "Demand saturates after experimentation", "cohort retention and total risk-adjusted spend", "Infrastructure and FinOps opportunities shrink"),
    ("Many agents exist", "Suites consolidate functions into one delegate", "active independent production identities", "Fleet-control demand weakens"),
    ("Suppliers are independent", "Different logos share model, cloud, data, or parent", "dependency-adjusted concentration", "Auctions and risk diversification become hollow"),
    ("Open models close the gap", "Frontier scale economics compound", "held-out consequential-work gap", "Open-commons scenarios weaken"),
    ("Enterprises multi-home", "Integration and committed spend favor one default", "successful production switching", "Neutral routing rent collapses"),
    ("Tasks are contractible", "Goals remain tacit, political, and path dependent", "ex ante acceptance completeness", "Markets and verification stay thin"),
    ("Outcomes are observable", "Delayed externalities dominate visible checks", "loss discovery lag and reversal rate", "Assurance claims overstate value"),
    ("Independent proof is valued", "Provider logs gain institutional acceptance", "procurement budget for external proof", "Verifier opportunity is enclosed"),
    ("Authority stays scarce", "Trusted SI gains direct institutional standing", "court and regulator treatment", "Authority-layer thesis weakens"),
    ("Legal persons remain accountable", "Machine entities receive autonomous legal capacity", "statute and case law", "Principal-based controls must change"),
    ("Humans remain in final control", "Oversight becomes ceremonial or impossible", "actual override frequency and competence", "Human-in-loop claims become fiction"),
    ("Machine commerce grows", "Agents only recommend; humans transact", "binding delegated transactions net of confirmation", "Payment and market layers stay premature"),
    ("Reputation is portable", "Platforms, rights, and nonstationarity prevent transfer", "cross-venue predictive use", "Marketplace liquidity weakens"),
    ("Open standards weaken incumbents", "Standards enlarge demand for bundled implementations", "share of value captured outside sponsors", "Protocol optimism reverses"),
    ("Regulation creates openings", "Compliance fixed costs concentrate supply", "entry, designation, and audit concentration", "Independent layers lose"),
    ("Neutrality can be monetized", "Fees, ranking, verification, and insurance create conflicts", "revenue-source and decision audits", "Neutral intermediary lacks legitimacy"),
    ("Customer-owned enforcement persists", "Provider identity and data become unavoidable", "control over keys, policies, and receipts", "External authority is nominal"),
    ("Physical resources remain scarce", "Energy/hardware abundance outpaces demand", "utilization and capacity premium", "Compute/energy opportunities fade"),
    ("Context remains scarce", "Models infer or synthesize sufficient context", "marginal value of private data", "Context custody rent erodes"),
    ("Markets achieve liquidity", "Bypass, heterogeneity, subsidies, or concentration dominate", "unsubsidized repeat fills and depth", "Clearing/market infrastructure dies"),
    ("Routing beats run-all", "Execution and verification become nearly free", "net value after all candidate runs", "Ex ante allocator commoditizes"),
    ("Providers cannot self-certify", "Proof systems become accepted and cheap", "external-vs-native evidence premium", "Independent verification contracts"),
    ("Systems of record cannot bundle control", "Workflow incumbents close the governance loop", "separate budget and displacement rate", "Horizontal control points disappear"),
    ("Technical boundaries resist SI", "Agents socially or technically acquire credentials", "boundary escape and privilege escalation", "Sandbox confidence is false"),
    ("Legal finality persists", "Emergency powers or private arbitration rewrite rights", "enforcement and dispute precedent", "Settlement assumptions change"),
    ("Losses are insurable", "Common-mode, strategic, or catastrophic failures dominate", "limits, exclusions, reinsurance, paid claims", "Underwriting cannot form"),
    ("Timing leaves a startup window", "Incumbents bundle before buyers form budgets", "time to native feature parity", "Revenue appears but no durable company forms"),
]


ACTOR_WELFARE_TAXONOMY = [
    ("Households and consumers", "affordability, agency, privacy, convenience, truthful representation, and redress", "fraud, manipulation, discrimination, exclusion, dependency, and loss of practical consent", "consent, exit, collective politics, consumer law, and payment disputes", "private purchase, public entitlement, cooperative service, regulated utility, or refusal", "agent use can rise while household welfare falls or remains unmeasured", "net household surplus, dispute and reversal rates, portability, concentration, and meaningful-consent evidence"),
    ("Workers", "income, autonomy, dignity, safety, skill formation, bargaining power, and a credible career ladder", "displacement, work intensification, surveillance, deskilling, uncompensated training traces, and blame without authority", "collective bargaining, scarce tacit knowledge, labor law, professional identity, and exit", "employment contract, gain sharing, cooperative ownership, public transition support, or veto", "productivity gains can accrue entirely to capital or consumers while worker welfare declines", "wage and task distribution, junior hiring, override power, training burden, hours, and worker acceptance"),
    ("Professions and fiduciaries", "competence, legitimacy, duty, judgment, reputation, and manageable liability", "rubber-stamp oversight, license loss, malpractice, moral injury, and erosion of public trust", "licensing, professional standards, refusal rights, courts, and control over signatures", "licensed human-machine practice, public standards, insurer conditions, or prohibited delegation", "technical accuracy can improve while professional legitimacy rejects delegation", "scope-of-practice rules, claims, disciplinary cases, signature requirements, and insurer treatment"),
    ("Communities hosting infrastructure", "jobs, tax base, reliable services, environmental quality, and voice over local tradeoffs", "power and water stress, land use, pollution, congestion, displacement, and stranded assets", "permitting, local politics, utility governance, protest, land ownership, and community-benefit agreements", "private development, public utility, rationing, moratorium, or negotiated benefit sharing", "global intelligence abundance can impose concentrated local costs without local demand", "permit time, power queue, water use, local prices, opposition, tax realization, and benefit distribution"),
    ("Enterprise owners and boards", "durable cash flow, growth, continuity, strategic control, and lawful operation", "capital loss, correlated incidents, lock-in, litigation, and false productivity narratives", "capital allocation, procurement, governance, insurance, and organizational redesign", "internal hierarchy, outsourcing, platform dependency, consortium, or abstention", "agent activity and bookings can rise without captured profit or risk-adjusted value", "mature-cohort margin, total implementation cost, loss tails, renewals, switching, and return on invested capital"),
    ("Function managers and domain teams", "throughput, quality, budget control, local autonomy, and reliable exception handling", "central-platform friction, hidden cleanup, metric gaming, loss of expertise, and accountability gaps", "domain knowledge, workflow ownership, local adoption, and ability to route around central policy", "federated internal fleet, vertical suite, managed service, or manual process", "central governance can lower formal risk while increasing shadow use and organizational latency", "accepted outcomes per full-cost hour, bypass, exception load, service quality, and local budget migration"),
    ("States and national-security institutions", "security, sovereignty, fiscal capacity, legitimacy, continuity, and geopolitical advantage", "foreign dependency, surveillance abuse, capture, strategic surprise, unemployment, and loss of coercive reach", "law, taxation, procurement, borders, sanctions, infrastructure control, and force", "public infrastructure, licensed utility, national champion, bloc standard, rationing, or prohibition", "commercially efficient global systems can be rejected for sovereignty or regime-survival reasons", "sovereign procurement, export controls, domestic operations, fiscal premium, public trust, and emergency powers"),
    ("Courts and dispute institutions", "attributable facts, legitimate process, enforceable remedies, finality, and equal treatment", "evidence overload, conflicting jurisdiction, insolvent defendants, manipulated records, and non-compensable harm", "subpoena, injunction, judgment, precedent, accreditation, and coercive enforcement", "public adjudication, arbitration, ombudsman, platform rulebook, or no practical remedy", "perfect technical evidence can coexist with unavailable or illegitimate remedy", "recognition, appeal, enforcement time, recovery rate, cross-border conflict, and reachable-defendant share"),
    ("Regulators and supervisors", "rights protection, stability, competition, continuity, and observable accountable operators", "information lag, capture, checkbox compliance, concentration, and jurisdictional arbitrage", "licensing, examination, disclosure, penalties, designation, and procurement rules", "continuous supervision, self-conformity, accredited assurance, public operation, or moratorium", "regulation can increase compliance while reducing contestability and practical oversight", "entry and exit, concentration, enforcement actions, audit quality, switching, and incident discovery"),
    ("Insurers and risk pools", "diversifiable loss, credible pricing, bounded aggregation, claims evidence, and capital return", "common-mode catastrophe, adverse selection, ambiguity, fraud, capital exhaustion, and political override", "coverage terms, exclusions, limits, pricing, claims control, reinsurance, and refusal", "private insurance, public compensation fund, self-insurance, warranty, or uninsurable exclusion", "growing premiums can signal rising fragility rather than a healthy market", "limits, exclusions, paid claims, loss ratio, capital, reinsurance, disputes, and systemic stress"),
    ("Public digital institutions", "universal access, interoperability, continuity, rights protection, and low extraction", "underfunding, politicization, slow maintenance, capture, surveillance, and public-option failure", "tax funding, legal mandate, procurement, standards governance, and public trust", "public identity, compute, protocol, registry, or service with little appropriable rent", "an economically important function can persist precisely because it is removed from private rent capture", "appropriations, service quality, open maintenance, adoption, rights, resilience, and private complement formation"),
    ("Cooperatives and consortia", "shared infrastructure, bargaining leverage, common rules, member control, and reduced dependency", "free riding, slow governance, incumbent dominance, unequal contribution, and fragmentation", "member procurement, pooled data or capacity, standards, mutual commitments, and exit", "industry utility, buying cooperative, open-source foundation, mutual insurer, or failure to coordinate", "collective provision can defeat both startup rent and platform monopoly without creating a public agency", "member concentration, contribution, switching, shared volume, governance participation, and survival without subsidy"),
    ("Criminal and informal networks", "unattributed access, arbitrage, coercive revenue, evasion, and rapid adaptation", "seizure, infiltration, betrayal, counterparty fraud, and violent enforcement", "stolen credentials, secrecy, jurisdiction shopping, coercion, and censorship resistance", "illicit barter, crypto or cash settlement, compromised accounts, patronage, or coercive hierarchy", "consequential machine activity can grow outside every compliant market-formation and governance indicator", "credential theft, ransomware, informal settlement, evasion, enforcement reach, and displacement into new channels"),
    ("Energy, compute, and physical operators", "utilization, long contracts, asset return, safety, grid access, and predictable demand", "stranded capital, curtailment, equipment obsolescence, local opposition, outages, and supply-chain shocks", "ownership of scarce assets, siting, interconnect, maintenance skill, and physical custody", "private capacity, regulated utility, state allocation, forward contract, or emergency rationing", "falling inference price can coexist with physical rents, or overbuild can erase them abruptly", "utilization, queue, forward premium, cancellation, write-down, equipment lead time, and regional concentration"),
    ("Developing economies and late adopters", "affordable capability, local language and context, sovereignty, jobs, and infrastructure catch-up", "new dependency, extractive data flows, currency exposure, labor disruption, and capability exclusion", "public procurement, local regulation, market size, regional blocs, labor supply, and localization", "imported platform, public option, local operator, regional consortium, or leapfrog adoption", "global average abundance can hide severe local scarcity and asymmetric bargaining power", "local price, access, language quality, domestic share, foreign-exchange burden, jobs, and data/control location"),
    ("Future generations", "preserved option value, institutional continuity, environmental capacity, and avoidance of irreversible catastrophe", "lock-in, depleted resources, concentrated power, lost skills, ecological damage, and existential risk", "represented indirectly through law, public institutions, trustees, and constitutional constraints", "precaution, public investment, intergenerational trust, option preservation, or neglect", "present revenue and welfare can rise while irreversible long-horizon loss accumulates", "irreversibility, resource stock, institutional concentration, tail exposure, adaptation capacity, and option preservation"),
    ("Machine-managed entities", "persistence, resources, goal execution, legal recognition, and operational autonomy", "revocation, dissolution, expropriation, goal conflict, insolvency, and control disputes", "asset ownership, contracts, code custody, political influence, and operator dependence", "legal wrapper, autonomous trust, provider account, state instrument, or prohibited entity", "machine standing can dissolve the human-principal model without creating moral legitimacy or solvency", "statute, case law, asset holdings, independent contracting, capitalization, dissolution, and reachable administrators"),
    ("Ecological systems and non-human interests", "continued ecosystem function and bounded extraction, represented through human institutions", "water depletion, emissions, habitat loss, material extraction, heat, and cumulative local externality", "environmental law, permitting, public politics, scientific evidence, and physical limits", "regulated use, cap, tax, restoration duty, protected commons, or unpriced damage", "market price and enterprise value can rise while non-human loss remains invisible or non-compensable", "energy and water intensity, emissions, land and material use, ecological thresholds, enforcement, and restoration"),
]


SOURCES = [
    ("Microsoft FY26 Q3 earnings", "https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q3"),
    ("Microsoft FY2025 annual report", "https://www.microsoft.com/investor/reports/ar25/index.html"),
    ("IEA Energy and AI", "https://www.iea.org/reports/energy-and-ai"),
    ("IEA key questions on energy and AI", "https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary"),
    ("Stanford AI Index 2026 - economy", "https://hai.stanford.edu/ai-index/2026-ai-index-report/economy"),
    ("Epoch inference price trends", "https://epoch.ai/data-insights/llm-inference-price-trends"),
    ("Salesforce FY26 results", "https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Fourth-Quarter-Fiscal-2026-Results/default.aspx"),
    ("ServiceNow AI Control Tower", "https://newsroom.servicenow.com/press-releases/details/2026/ServiceNow-expands-AI-Control-Tower-to-discover-observe-govern-secure-and-measure-AI-deployed-across-any-system-in-the-enterprise/default.aspx"),
    ("GitHub agent control plane", "https://github.blog/changelog/2026-02-26-enterprise-ai-controls-agent-control-plane-now-generally-available/"),
    ("AWS AgentCore policy", "https://aws.amazon.com/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available/"),
    ("Google Agent Gateway", "https://cloud.google.com/blog/products/identity-security/introducing-agent-gateway-isv-ecosystem-for-security-and-governance/"),
    ("IBM agentic control plane", "https://www.ibm.com/new/announcements/introducing-the-agentic-control-plane"),
    ("Cloudflare dynamic routing", "https://developers.cloudflare.com/ai-gateway/features/dynamic-routing/"),
    ("Cloudflare AI Gateway pricing", "https://developers.cloudflare.com/ai-gateway/reference/pricing/"),
    ("Palo Alto Networks acquisition of Portkey", "https://www.paloaltonetworks.com/company/press/2026/palo-alto-networks-completes-acquisition-of-portkey-to-secure-ai-agents"),
    ("Okta agentic enterprise blueprint", "https://investor.okta.com/news-and-events/news-releases/news-details/2026/Okta-Announces-New-Blueprint-for-the-Secure-Agentic-Enterprise/default.aspx"),
    ("NIST identity and authority for software agents", "https://www.nist.gov/news-events/news/2026/02/new-concept-paper-identity-and-authority-software-agents"),
    ("NIST AI Agent Standards Initiative", "https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative"),
    ("NIST monitoring deployed AI", "https://www.nist.gov/news-events/news/2026/03/new-report-challenges-monitoring-deployed-ai-systems"),
    ("NIST evaluation cheating", "https://www.nist.gov/caisi/cheating-ai-agent-evaluations"),
    ("NIST continuous monitoring proof", "https://www.nist.gov/news-events/news/2026/06/nist-mathematical-proof-supports-transition-continuous-monitor-and-update"),
    ("EU AI Act framework", "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai"),
    ("EU AI Omnibus 2026", "https://digital-strategy.ec.europa.eu/en/news/ai-omnibus-enters-force"),
    ("EU Product Liability Directive", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L2853"),
    ("Linux Foundation A2A", "https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year"),
    ("Anthropic MCP donation / Agentic AI Foundation", "https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation"),
    ("Stripe Machine Payments Protocol", "https://stripe.com/blog/machine-payments-protocol"),
    ("Visa MPP specification", "https://corporate.visa.com/en/sites/visa-perspectives/innovation/visa-card-specification-sdk-for-machine-payments-protocol.html"),
    ("Mastercard Agent Pay for machines", "https://www.mastercard.com/us/en/news-and-trends/press/2026/june/mastercard-launches-agent-pay-for-machines.html"),
    ("FTC AI partnerships report", "https://www.ftc.gov/news-events/news/press-releases/2025/01/ftc-issues-staff-report-ai-partnerships-investments-study"),
    ("UK CMA cloud investigation", "https://www.gov.uk/cma-cases/cloud-services-market-investigation"),
    ("OECD AI adoption", "https://www.oecd.org/en/about/news/announcements/2026/01/ai-use-by-individuals-surges-across-the-oecd-as-adoption-by-firms-continues-to-expand.html"),
    ("ILO GenAI and jobs 2025", "https://www.ilo.org/publications/generative-ai-and-jobs-2025-update"),
    ("IMF AI gains distribution 2026", "https://www.imf.org/en/publications/wp/issues/2026/07/10/aggregate-gains-from-ai-and-their-distribution-global-evidence-from-usage-data-577586"),
    ("Anthropic Responsible Scaling Policy", "https://www.anthropic.com/responsible-scaling-policy"),
    ("OpenAI Preparedness Framework", "https://openai.com/index/updating-our-preparedness-framework/"),
    ("OpenAI Frontier Governance Framework", "https://openai.com/index/openai-frontier-governance-framework/"),
    ("UK AISI frontier trends", "https://www.aisi.gov.uk/frontier-ai-trends-report"),
    ("EU AI factories", "https://digital-strategy.ec.europa.eu/en/policies/ai-factories"),
    ("International Federation of Robotics demand", "https://ifr.org/news/global-robot-demand-in-factories-doubles-over-10-years/1st-quarterly-newsletter-2011"),
    ("US AI Action Plan 2025", "https://www.whitehouse.gov/wp-content/uploads/2025/07/Americas-AI-Action-Plan.pdf"),
    ("NAIC artificial intelligence", "https://content.naic.org/insurance-topics/artificial-intelligence"),
    ("Bank of England AI in financial services", "https://www.bankofengland.co.uk/report/2024/artificial-intelligence-in-uk-financial-services-2024"),
    ("BIS Principles for Financial Market Infrastructures", "https://www.bis.org/cpmi/publ/d101a.pdf"),
    ("OMB M-25-22 AI acquisition", "https://www.whitehouse.gov/wp-content/uploads/2025/02/M-25-22-Driving-Efficient-Acquisition-of-Artificial-Intelligence-in-Government.pdf"),
    ("NBER enterprise GenAI field experiment", "https://www.nber.org/papers/w33795"),
    ("W3C Verifiable Credentials 2.0", "https://www.w3.org/standards/history/vc-data-model/"),
    ("IETF RFC 8693 token exchange", "https://datatracker.ietf.org/doc/rfc8693/"),
    ("Google AP2", "https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol"),
    ("FAR reverse auctions", "https://login.acquisition.gov/far/subpart-17.8"),
    ("DOJ 2023 Merger Guidelines - platforms", "https://www.justice.gov/atr/merger-guidelines/applying-merger-guidelines/guideline-9"),
    ("EU Digital Markets Act", "https://eur-lex.europa.eu/eli/reg/2022/1925/2022-10-12/eng"),
    ("UNCITRAL automated contracting model law", "https://uncitral.un.org/en/mlac"),
    ("Delaware corporate directors", "https://delcode.delaware.gov/title8/c001/sc04/"),
    ("CFPB Regulation E", "https://www.consumerfinance.gov/rules-policy/regulations/1005/6/"),
]


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(ascii_clean(str(v)).replace("|", "/") for v in row) + " |")
    return "\n".join(out)


def section(title, body):
    return f"# {title}\n\n{body.strip()}\n"


def image(name, caption):
    return f"![{ascii_clean(caption)}](market_evolution_assets/{name})\n"


def scenario_markdown():
    parts = [section("Scenario library: eighteen causal worlds", """
These scenarios are not forecasts and no probabilities are assigned. Each is a coherent causal path used to expose dependencies. Several can coexist by sector or jurisdiction. A scenario is useful when it changes which actors control budgets, which scarcity carries rent, which institution can authorize action, and which observation would falsify the path.

""" + image("05_scenario_phase_space.png", "Three-axis scenario phase space") + "\n" + image("06_eighteen_worlds.png", "Eighteen distinct future worlds"))]
    for idx, data in enumerate(SCENARIOS, 1):
        name, initial, trigger, sequence, budget, bottleneck, authority, market, equilibrium, indicators, falsifier, opp, opposite = data
        if idx == 18:
            parts.append("[PAGEBREAK]\n")
        parts.append(f"## S{idx}. {name}\n\n"
                     f"**[SPECULATION] Initial conditions.** {initial}\n\n"
                     f"**Trigger.** {trigger}\n\n"
                     f"**Play-by-play.** {sequence}\n\n"
                     f"**Budget migration.** {budget}\n\n"
                     f"**Binding bottleneck.** {bottleneck}\n\n"
                     f"**Authority and accountability.** {authority}\n\n"
                     f"**Market structure.** {market}\n\n"
                     f"**Equilibrium or instability.** {equilibrium}\n\n"
                     f"**Leading indicators.** {indicators}.\n\n"
                     f"**Falsifier.** {falsifier}\n\n"
                     f"**Conditionally exposed opportunity categories.** {opp}. These are categories, not a company recommendation.\n\n"
                     f"**Opposite world.** {opposite}\n\n")
    return "\n".join(parts)


def cross_product_markdown():
    rows = []
    idx = 1
    for supply in ["Concentrated", "Plural"]:
        for resources in ["Scarce", "Abundant"]:
            for trust in ["Trusted", "Untrusted"]:
                for authority in ["Centralized", "Polycentric"]:
                    if supply == "Concentrated" and trust == "Trusted" and authority == "Centralized":
                        structure = "licensed utility or provider operating layer"
                        bottleneck = "continuity, public legitimacy, and exit"
                    elif supply == "Concentrated" and trust == "Untrusted":
                        structure = "contested oligopoly under monitoring or moratorium"
                        bottleneck = "containment, evidence, and political control"
                    elif supply == "Plural" and trust == "Trusted" and authority == "Polycentric":
                        structure = "open services, federated procurement, and local institutions"
                        bottleneck = "interoperability, reputation, and dispute translation"
                    elif supply == "Plural" and trust == "Untrusted":
                        structure = "shadow bazaar plus local allowlists and human principals"
                        bottleneck = "identity, consent, fraud, and common-mode dependencies"
                    elif authority == "Centralized":
                        structure = "state, suite, or enterprise hierarchy"
                        bottleneck = "capture, allocation legitimacy, and concentration"
                    else:
                        structure = "mixed thin markets and internal fleets"
                        bottleneck = "coordination and cross-regime authority"
                    if resources == "Scarce":
                        bottleneck += "; power, compute, and capacity remain priced"
                    else:
                        bottleneck += "; attention, rights, and action replace compute scarcity"
                    rows.append((f"L{idx}", supply, resources, trust, authority, structure, bottleneck))
                    idx += 1

    variants = [
        ("Public-good and cooperative equilibrium", "Governments, universities, consortia, unions, or industry cooperatives fund identity, verification, protocols, and compute as shared infrastructure. Private demand exists, but rent capture is intentionally limited. The relevant indicators are public procurement, open maintenance funding, mandated interoperability, and cooperative governance. The falsifier is persistent preference for proprietary service despite a credible public option."),
        ("Institutional fracture", "Courts, regulators, insurers, payment networks, standards bodies, and states disagree about authority and evidence. No receipt is universally accepted. Translation and local compliance grow, but global network effects weaken. The falsifier is rapid convergence on one cross-jurisdiction rulebook with enforceable recognition."),
        ("Labor and public veto", "Workers, professions, citizens, merchants, or communities block autonomous substitution, surveillance, or machine-mediated decisions even when capability is strong. Budgets move toward consultation, augmentation, compensation, and human staffing. The falsifier is broad adoption of consequential autonomy without durable bargaining, legal challenge, or political restriction."),
        ("Synthetic-demand spiral", "Agents generate tasks for other agents, retries create apparent volume, benchmarks and marketing manufacture demand, and subsidized machine transactions circulate without human surplus. Infrastructure spend and transaction counts rise while external willingness to pay and net welfare remain weak. The falsifier is persistent unsubsidized payment by independent principals tied to externally valued outcomes."),
        ("Ecological and social constraint", "Power, water, land, emissions, supply chains, or community opposition become binding before compute price signals fully adjust. States ration or condition infrastructure; local legitimacy becomes part of deployment. The falsifier is abundant low-impact energy and rapid siting without political resistance."),
        ("Informal, criminal, and adversarial agent economy", "Autonomous activity scales outside compliant identity, audit, procurement, and payment rails through stolen credentials, coercion, unlicensed models, evasion, and jurisdiction shopping. Governance demand can rise for compliant actors while effective system-wide authority shrinks. The falsifier is sustained migration of consequential activity into enforceable, attributable rails."),
        ("Machine legal standing and autonomous assets", "Law recognizes machine-managed entities, autonomous trusts, or direct machine capacity to hold assets and obligations. Principal-based delegation must be rebuilt around capitalization, dissolution, constitutional limits, and reachability. The falsifier is durable legal insistence that a natural or conventional legal person remains the responsible principal."),
        ("Catastrophic infrastructure regression", "War, grid failure, cyber conflict, climate disaster, or supply-chain rupture reduces compute, communications, and institutional capacity. Advanced systems persist unevenly, but offline operation, manual skills, local energy, and degraded coordination dominate. The falsifier is resilient infrastructure that maintains abundance and institutional reach through severe shocks."),
        ("Non-market abundance and political allocation", "Intelligence becomes abundant enough that prices and software markets contract while access is allocated as a public entitlement, constitutional service, cooperative commons, or rationed utility. Distribution and legitimacy dominate monetization. The falsifier is persistent private willingness to pay for differentiated intelligence under broad public access."),
    ]
    text = section("Cross-product world lattice and omitted equilibria", """
Named scenarios can hide interactions by changing several variables at once. The lattice below forces four axes to cross independently: supplier concentration, physical-resource abundance, institutional trust, and authority centralization. These sixteen cells are not exhaustive and are not probability weighted. They expose combinations that a narrative scenario can accidentally omit.

""" + md_table(["Cell","Supply","Resources","Trust","Authority","Likely structure","Binding issue"], rows))
    for title, body in variants:
        text += f"\n## {title}\n\n**[SPECULATION]** {body}\n"
    return text


def actor_welfare_markdown():
    overview = []
    for actor, wants, loss, leverage, allocation, null, indicators in ACTOR_WELFARE_TAXONOMY:
        overview.append((actor, wants, leverage, allocation))
    parts = [section("Actor and welfare atlas: a taxonomy blind to the product perimeter", """
This second atlas starts from residual claimants, affected groups, public goods, coercion, externalities, and non-market allocation. It is intentionally independent of routing, control-plane, and marketplace components. Its purpose is to expose outcomes that a buyer-and-revenue taxonomy suppresses. An actor can lack purchasing power while holding veto power or bearing irreversible loss; a socially necessary function can be publicly supplied; and a high-revenue equilibrium can reduce welfare.

""" + md_table(["Actor or interest", "Valued outcomes", "Control or veto", "Possible allocation"], overview))]
    for idx, (actor, wants, loss, leverage, allocation, null, indicators) in enumerate(ACTOR_WELFARE_TAXONOMY, 1):
        parts.append(f"## W{idx}. {actor}\n\n"
                     f"**Valued outcomes.** {wants}.\n\n"
                     f"**Loss exposure.** {loss}.\n\n"
                     f"**Control, bargaining, or veto.** {leverage}.\n\n"
                     f"**Allocation modes.** {allocation}. No private company or market is presumed.\n\n"
                     f"**Null or adverse equilibrium.** {null}.\n\n"
                     f"**Discriminating indicators.** {indicators}.\n\n")
    return "\n".join(parts)


def opportunity_markdown():
    intro = section("Institutional opportunity atlas: functions without an assumed company", """
An opportunity surface is included only if a possible world creates a beneficiary, a budget or collective funding mechanism, and a scarcity. Inclusion does not imply timing, durability, venture scale, founder fit, or even private-company formation. The organizational home is deliberately unresolved: a function can live inside an enterprise, incumbent suite, open protocol, cooperative, professional service, accredited body, regulated utility, public institution, insurer, marketplace, or nowhere as a separate layer.

The buyer and revenue columns are counterfactual tests: if no actor can fund the function on the stated meter, the commercial branch fails. Public-good provision, internalization, bundling, and uncompensated open infrastructure are equally valid equilibria. Present revenue potential and long-run defensibility are separated because a category can monetize during transition and then be bundled, regulated, nationalized, open-sourced, or erased.

Every surface remains unproven until seven gates pass independently: **function** remains necessary; **loss** is measurable without it; **authority** sits with an actor able to change the workflow; **budget** exists separately after native controls are configured; **access** gives an independent supplier enough telemetry and enforcement rights; **rent** survives bundling, standards, and competition; and **time** exceeds procurement, integration, certification, and capital formation. A function can pass the first gate and fail all six economic gates.

""" + image("16_opportunity_emergence.png", "Opportunity categories emerge at different transitions") + "\n" + image("17_opportunity_matrix.png", "Illustrative opportunity conditionality across worlds"))
    parts = [intro]
    headers = ["Surface", "Formation condition", "Funding locus", "Scarcity", "Revenue", "Natural enclosure", "Capital / rules", "Death condition"]
    summary_rows = []
    for name, cond, buyer, scarcity, revenue, deps, inc, capital, regulation, reversible, death in OPPORTUNITIES:
        summary_rows.append((name, cond, buyer, scarcity, revenue, inc, f"{capital} / {regulation}", death))
    parts.append(md_table(headers, summary_rows[:17]))
    parts.append("[PAGEBREAK]\n\n### Opportunity overview - remaining surfaces\n\n" + md_table(headers, summary_rows[17:]))
    for i,row in enumerate(OPPORTUNITIES,1):
        name, cond, buyer, scarcity, revenue, deps, inc, capital, regulation, reversible, death = row
        verdicts = {
            "Machine payments": "Payment and mandate infrastructure; not by itself an underlying market.",
            "Procurement auctions and RFQs": "A procurement market only when independent principals submit executable bids under liability and remedy.",
            "Portable reputation": "A market complement; not a market and not evidence of liquidity.",
            "Insurance and risk transfer": "A service and risk-capital market only when licensed capital bears claims.",
            "Dispute resolution": "An institution supporting exchange; it can exist without a competitive market.",
            "Settlement and clearing": "Market infrastructure only after genuine underlying obligations exist.",
            "Protocol infrastructure": "Interoperability infrastructure; common syntax alone is neither scarcity nor contestability.",
        }
        verdict = verdicts.get(name, "Function or capability; no external market is implied.")
        parts.append(f"## O{i}. {name}\n\n"
                     f"**Formation condition.** {cond}\n\n**Possible payer or funding locus.** {buyer}. A separate commercial budget is not assumed.\n\n"
                     f"**Scarcity captured.** {scarcity}.\n\n**Possible revenue mechanism.** {revenue}. This describes who might pay and on what meter; it does not establish willingness to pay or durability.\n\n"
                     f"**Formation verdict.** {verdict}\n\n**Seven-gate evidence status.** Functional necessity is conditional; measurable loss, decision authority, separate budget, independent access, sustainable rent, and sufficient time remain unproven unless scenario-specific evidence establishes them.\n\n"
                     f"**Dependencies.** {deps}.\n\n**Incumbent counterstrategy.** {inc}.\n\n"
                     f"**Capital / regulation / reversibility.** Capital intensity: {capital}; regulatory exposure: {regulation}; reversibility: {reversible}.\n\n"
                     f"**Correlated-death cluster.** The function, independent access, and sustainable rent can fail together if {death.lower()} At the same time, the natural enclosure path can {inc}, while access to {deps} disappears or becomes uneconomic.\n\n"
                     f"**Decisive falsifier.** In a mature deployment, the stated funding locus does not assign a separate recurring budget after the natural incumbent alternative is fully configured, or an independent supplier cannot obtain the required data, authority, and ground truth at sustainable full cost.\n\n"
                     f"**Revival condition.** {cond} In addition, a funding principal must recognize a measurable loss without the function, grant independent access, renew a separate budget, and leave enough contestability for retained rent.\n\n"
                     f"**Option premium, expiry, and abandonment.** The hypothetical premium is the cost of keeping interfaces, rights, evidence, qualifications, and switching paths live. The option expires as the incumbent enclosure becomes institutionally accepted, the death condition materializes, or procurement and certification take longer than the market window. The abandonment signal is simultaneous failure of budget, access, rent, and time gates; continued technical usefulness does not keep the economic option alive.\n\n"
                     f"**Organizational home remains open.** This function may be internalized, bundled, supplied as a public or cooperative rail, regulated, or left without a standalone provider.\n\n"
                     f"**Death condition.** {death}\n\n")
    return "\n".join(parts)


def research_appendices():
    files = [
        ("Round 2 cross-examination: market economics", "round2_market_economics.md"),
        ("Round 2 cross-examination: superintelligence resistance", "round2_superintelligence.md"),
        ("Round 2 cross-examination: incumbents and enclosure", "round2_incumbents.md"),
        ("Round 2 cross-examination: enterprise authority", "round2_enterprise_authority.md"),
        ("Round 2 cross-examination: mechanism design", "round2_mechanisms.md"),
        ("Round 2 cross-examination: antifragility and falsification", "round2_antifragility.md"),
        ("Round 3 independent adjudication - historical pre-closure critique", "round3_adjudication.md"),
    ]
    out = []
    for title, filename in files:
        path = RESEARCH / filename
        if not path.exists():
            continue
        text = ascii_clean(path.read_text(encoding="utf-8"))
        text = re.sub(r"^#\s+.*$", "", text, count=1, flags=re.M).strip()
        if filename == "round3_adjudication.md":
            text = ("**Status note.** This adjudication is preserved verbatim as the pre-closure critique. "
                    "The integrated source answers its fourteen required corrections in the Round 3 "
                    "correction-closure ledger; the critique below is not a claim that those defects remain open.\n\n" + text)
        out.append(section(title, text))
    return "\n".join(out)


def build_source():
    parts = ["---\ntitle: Odylith Market Evolution Situational Awareness\ndate: 5 August 2026\n---\n"]
    parts.append(section("Mandate: build a world model before choosing a strategy", """
This dossier deliberately does **not** conclude what Odylith should build, whether it should exist, or whether anyone should invest. It asks a prior question: how could markets, enterprises, institutions, and power structures evolve as machine intelligence becomes cheaper, more capable, more autonomous, and potentially superintelligent?

The analysis treats the Odylith thesis deck as one hypothesis generator, not as the frame. It does not assume a router, control plane, marketplace, clearinghouse, verification layer, governance company, software beachhead, or outcome business must exist. Each is tested as a contingent market form that appears only under specific states of the world.

The purpose is situational awareness: expose causal transitions, competing equilibria, hidden variables, kill assumptions, observable indicators, and option-rich opportunity surfaces while leaving product selection deliberately unresolved.

> Core discipline: abundant intelligence is an input condition, not a conclusion about who captures value.

""" + image("12_uncertainty_cone.png", "Epistemic uncertainty expands with the forecast horizon")))

    parts.append(section("How to read the epistemic labels", """
**[OBSERVED]** describes a dated measurement or current institutional fact. **[ANNOUNCED]** describes a provider, regulator, or company claim whose realization may differ. **[INFERENCE]** is a causal interpretation that could be wrong. **[SPECULATION]** is a coherent future-world construction. **[UNKNOWN]** marks a variable for which current evidence is insufficient. **[FALSIFIER]** states what observation would materially weaken a claim.

The dossier explains reasoning through claim ledgers, causal sequences, payoff maps, and discriminating tests. It does not present private chain-of-thought or treat narrative confidence as evidence. When a number is an announcement, usage count, seat count, booking, or forecast rather than realized enterprise value, it is labeled accordingly.
"""))

    parts.append(section("Prior-dossier anchoring audit", """
The prior dossier converged too quickly. It moved from real trends - cheaper models, more agents, enterprise control demand, and institutional accountability - to a specific company form, software-modernization beachhead, pricing, pilot, and investment verdict. That is a category error: evidence that a function matters does not identify which layer captures it, whether it is separately budgeted, whether an incumbent bundles it, or whether the function survives a more capable future.

Four anchors distorted the search. **Product anchoring** treated the current deck's control plane as the natural unit of analysis. **Coding-beachhead anchoring** over-weighted observability in software and under-modeled other markets. **Linear-stage anchoring** assumed routing naturally becomes a marketplace and clearinghouse. **Governance durability anchoring** assumed authority, verification, and liability remain scarce without modeling worlds where trusted providers, self-verifying systems, new law, or state control erase or internalize them.

This dossier reconstructs the problem from actors, budgets, resources, institutions, and constraints. The prior strategy remains one possible branch, not the answer.
"""))

    parts.append(section("Second taxonomy: actors, welfare, coercion, and non-market allocation", """
An anti-anchoring test begins without candidate product functions. Households seek welfare, consent, affordability, and redress. Workers and professions seek income, autonomy, status, safety, and bargaining power. Enterprises seek captured output, continuity, control, and profit. States seek security, legitimacy, fiscal capacity, coercive reach, and geopolitical position. Communities bear local power, water, land, labor, and distributional effects. Insurers and courts allocate compensable loss; many harms remain non-compensable. Criminal and informal actors optimize outside compliant rails. Public institutions and cooperatives can provide common goods without a venture-scale rent.

Starting here exposes outcomes the control-plane taxonomy misses: labor veto, public ownership, machine standing, institutional collapse, synthetic demand, uncompensated externalities, informal exchange, ecological constraint, and no-company equilibria. The overlap with routing, identity, authority, evidence, and settlement is analytically meaningful, but it does not prove those functions require an independent supplier.
"""))

    parts.append(actor_welfare_markdown())

    parts.append(section("Present topology: hierarchy before market", """
**[OBSERVED]** Enterprises currently buy subscriptions, committed cloud capacity, model APIs, consulting, and workflow software. An internal control plane choosing among resources is administrative allocation. It becomes a market only when independent principals exchange a scarce unit under executable terms with eligibility, liability, payment, settlement, default, and remedy.

**[INFERENCE]** Agent proliferation can raise the value of control while strengthening incumbent systems of record. It can increase external exchange, or it can deepen hierarchy. The number of agents, API calls, protocol messages, or listings is therefore not evidence of market liquidity.

""" + image("01_present_topology.png", "Current actors and control points") + "\n" + image("09_actor_incentives.png", "Actors optimize different payoffs around autonomous execution")))

    parts.append(section("Evidence baseline as of 5 August 2026", """
**[ANNOUNCED]** Microsoft reported AI annual recurring revenue above $37 billion, more than 20 million Microsoft 365 Copilot seats, nearly 140,000 Copilot organizations, and tens of millions of agents in Agent 365 in FY26 Q3. It also described majority multi-model behavior, more than 10,000 multi-model Foundry customers, improved inference throughput, and continued gigawatt-scale capacity expansion. These signals establish demand and infrastructure pressure; they do not establish autonomous enterprise value, open-market formation, or an independent control-layer budget. https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q3

**[OBSERVED / FORECAST]** The IEA reports data-center electricity use rose 17 percent in 2025, AI-focused facilities about 50 percent, while per-task efficiency improved at least an order of magnitude annually. It projects data-center electricity from roughly 485 TWh in 2025 toward 950 TWh in 2030. Falling unit cost and rising aggregate resource use are therefore compatible. https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary

**[OBSERVED / SURVEY]** Stanford's 2026 AI Index reports broad organizational AI adoption but much lower agent use. Adoption, production authority, and captured P&L value remain different denominators. https://hai.stanford.edu/ai-index/2026-ai-index-report/economy

**[OBSERVED]** Enterprise control features are being bundled by Microsoft, ServiceNow, GitHub, AWS, Google, IBM, Okta, security vendors, and clouds. Cloudflare offers core AI Gateway features free while supporting dynamic routing. Palo Alto Networks acquired Portkey. These are direct enclosure signals: the function can matter while an independent category fails to form.

**[OBSERVED]** NIST, the EU AI Act, product-liability law, DORA, payment protocols, and procurement rules are building concepts for identity, authority, monitoring, evidence, accountability, portability, and machine transactions. Institutionalization can open independent demand, strengthen incumbents, or both.
"""))

    variables = [
        ("Capability price", "risk-adjusted cost per accepted unit of work"), ("Capability slope", "rate and discontinuity of progress"),
        ("Frontier concentration", "ownership and distribution at the capability edge"), ("Open gap", "difference between open and closed systems on consequential work"),
        ("Compute availability", "chips, utilization, interconnect, region"), ("Energy availability", "power price, grid queue, cooling, siting"),
        ("Agent creation cost", "cost to instantiate and maintain task-specific agents"), ("Verification cost", "cost and latency of evidence accepted by the relevant institution"),
        ("Institutional trust", "willingness to treat machine output as legitimate"), ("Reliability distribution", "average performance plus correlated and tail failure"),
        ("Delegation depth", "scope and irreversibility of authorized action"), ("Regulatory posture", "permission, oversight, liability, and enforcement"),
        ("Standards maturity", "interoperability in syntax and production operation"), ("Supplier independence", "ownership- and dependency-adjusted plurality"),
        ("Task contractibility", "ability to define demand and acceptance before execution"), ("Market liquidity", "unsubsidized executable depth and repeat exchange"),
        ("Context custody", "rights and control over authoritative local state"), ("Switching cost", "technical, contractual, data, and organizational friction"),
        ("Human accountability", "whether a reachable legal person remains responsible"), ("Physical access", "control of machines, property, energy, and sensors"),
        ("Capital cost", "financing and risk-capital requirements"), ("Organizational absorption", "ability to redesign work and capture savings"),
        ("Geopolitical fragmentation", "export, jurisdiction, and sovereignty barriers"), ("Observability", "visibility into actions, consequences, and counterfactual value"),
    ]
    parts.append(section("State variables and causal primitives", """
The world model uses variables rather than labels. A change in one variable can have opposite effects depending on others: open standards can improve switching when identities and data are portable, or expand incumbent distribution when proprietary extensions and defaults remain. The table defines the variables to track.

""" + image("02_state_variables.png", "Interacting state-variable families") + "\n" + md_table(["Variable", "Operational meaning"], variables)))

    parts.append(section("Causal loop 1: cheap intelligence, rebound, and total spend", """
The simplistic thesis is: inference price falls, model rent disappears, and value moves cleanly downstream. The stronger model is conditional.

1. Price per unit of capability falls.
2. Previously uneconomic tasks become attempted; candidate count and task frequency rise.
3. More attempts require data integration, workflow redesign, evaluation, monitoring, power, and exception labor.
4. More autonomous action reveals rare failures and institutional disputes.
5. Controls become a cost center, a bundled suite feature, a regulated obligation, or a paid independent layer depending on buyer structure and enclosure.
6. Efficiency can further expand volume. Total spend can rise, fall, or migrate even as model calls approach zero.

**[FALSIFIER]** If mature cohorts show saturated task volume, declining total risk-adjusted AI spend, and no migration into integration, physical resources, or assurance, the rebound thesis weakens.

The observed co-movement of lower normalized inference cost with rising capex and electricity does **not** identify causal rebound. Capability-induced new demand, speculative overbuild, training rather than inference, ordinary cloud growth, strategic stockpiling, and low utilization can produce similar data. Discriminating evidence includes mature-cohort price elasticity, training/inference split, utilization, cancellations, infrastructure write-downs, and externally valued accepted work.

""" + image("03_causal_loops.png", "Rebound and control-demand feedback loops")))

    parts.append(section("Causal loop 2: scarcity migration is not guaranteed", """
Scarcity can migrate from model access to context, credentials, proof, authority, physical resources, and legitimacy. But each candidate scarcity has a death world. Context weakens if systems infer enough state; verification weakens if proofs become free and institutionally accepted; authority weakens if trusted superintelligence gains institutional standing; physical scarcity weakens if energy and hardware become abundant; neutrality weakens when the intermediary's revenue creates conflicts.

The question is not "what remains scarce forever?" It is "under what mechanism, controlled by which actor, recognized by which institution, during which interval, and exposed to which substitution?"

The missing endpoint is **no migration**: willingness to pay, profit, or human demand can disappear rather than move to another layer. Intelligence can make a task unnecessary, synthetic activity can fail to create welfare, or a public institution can supply the residual function without appropriable rent.

""" + image("04_scarcity_migration.png", "Candidate scarcities across capability regimes")))

    parts.append(section("Enterprise evolution: from use to captured economics", """
**[OBSERVED]** Seats, monthly users, deployed agents, successful calls, accepted artifacts, and P&L value are different denominators. Field evidence can show individual time savings without coordinated task or output change. A support deployment can raise novice productivity while affecting experts differently. Vendor deal counts do not resolve these organizational effects.

**[INFERENCE]** Early AI spend is additive. It becomes substitutive only when a P&L owner removes another cost or expands profitable demand. The transition can move through pilot seats, data and integration, agent operations, assurance and redress, and eventually labor, BPO, or capital budgets. It can also reverse after incidents or value disappointment.

Coalitions matter: CEO and innovation sponsors seek speed; CIO seeks standardization; CFO seeks captured margin; CISO and counsel seek defensibility; functions seek throughput; workers seek autonomy and security; procurement seeks concentration discounts; regulators seek reachable defendants. The resulting system is a political equilibrium, not a benchmark outcome.

""" + image("08_budget_migration.png", "Possible migration of enterprise budgets and owners")))

    parts.append(section("Provider evolution: capability, distribution, and enclosure", """
Frontier laboratories can move down-stack into agents, tools, memory, evaluation, and enterprise controls. Clouds can use committed spend, identity, data gravity, optimized infrastructure, and marketplace access. Systems of record can own authoritative context and the final transaction. Security, identity, observability, payment, and consulting incumbents can absorb specialized functions or acquire them.

The strategic ambiguity is severe. Provider plurality increases the technical usefulness of routing, but multi-model procurement can remain inside a suite. Open protocols can reduce integration cost, yet also enlarge the market for hyperscaler implementations. Regulation can require independent checks, or concentrate the category among firms able to bear compliance costs. Acquisition can validate demand while eliminating an independent layer.

""" + image("10_incumbent_enclosure.png", "Layer-by-layer incumbent enclosure options")))

    parts.append(section("Open standards: interoperability is not contestability", """
MCP, A2A, verifiable credentials, delegated-token standards, and payment protocols can standardize messages, discovery, tools, identity claims, and mandates. None automatically creates independent suppliers, portable context, binding authority, price discovery, settlement finality, liability, or remedies.

Standards generate at least four worlds: a competitive commons with portable identity and data; a thin standard beneath proprietary extensions; a distribution layer that strengthens existing platforms; or fragmented jurisdictional profiles. Production evidence must measure multi-homing, successful switching, ownership-adjusted supply, portable reputation, and settled external value rather than standards membership.

The contestability stack is stricter than protocol conformance: open specification; multiple conforming implementations; substitutable registries and trust roots; portable identity, data, history, and extensions; full-workflow switching; distributed traffic and revenue; and enforceable limits on self-preference. Passing the first layer says little about the last.
"""))

    parts.append(section("When agent activity becomes a market", """
A genuine market needs separate residual claimants, funded demand, independent supply, a scarce inventory unit, executable offers, eligibility, verification, liability, payment, settlement, reputation, default handling, dispute resolution, and contestability. A market need not be liquid or continuous; a thin procurement event can qualify. A directory, router, internal scheduler, platform reseller, protocol exchange, or internal chargeback does not.

""" + md_table(["Form", "Demand / supply", "Inventory and bid", "Verdict"], [
        ("Internal dispatch", "one enterprise allocates owned resources", "compute/time under scheduler score", "hierarchy"),
        ("Agent catalog", "users browse asserted capabilities", "listings; often no executable offer", "directory"),
        ("Bundled platform", "customer buys from one integrator", "subscription; upstream private procurement", "vertical supply chain"),
        ("Approved RFQ network", "enterprise and independent approved suppliers", "projects/capacity under quotes", "thin market when bids are real"),
        ("Reverse auction", "one buyer, multiple qualified suppliers", "standard task/capacity under binding price-quality bid", "market if specification and independence hold"),
        ("Spot API/capacity exchange", "autonomous buyers and independent operators", "call/quota/capacity with executable price", "market if delivery and money settle"),
        ("Run-all tournament", "buyer sponsors multiple attempts", "contest entries or prize", "contest unless enforceable offers allocate award"),
        ("Specialist outcome contracts", "buyers and legal service operators", "milestones/outcomes under quote", "heterogeneous contract-services market"),
        ("Clearing layer", "venues and counterparties", "obligations, collateral, finality", "infrastructure, not underlying market"),
    ])))

    parts.append(section("Machine commerce: a contingent sequence", """
Possible progression:

1. Humans assign internal work to one agent: no market.
2. Enterprise control planes route among owned or precontracted resources: hierarchy.
3. Platforms buy external APIs under posted prices and master agreements: bilateral procurement.
4. Protocols expose discovery, authority claims, and payment messages: interoperable network.
5. Buyer agents issue structured RFQs to approved independent suppliers: genuine but thin machine-assisted procurement.
6. Standardized capacity or tasks trade under executable offers; heterogeneous tasks use outcome contracts or tournaments.
7. Independent verification, escrow, warranties, and insurance support higher-value trades.
8. Only after multi-venue obligations exist does clearing, collateral, netting, finality, and default waterfalls become economically relevant.

The sequence can stop at stages 2 or 3 if hierarchy, bundling, liability, or supplier consolidation remains cheaper. A clearinghouse cannot manufacture an underlying market.

""" + image("07_transition_timeline.png", "Illustrative branch points in market formation")))

    parts.append(scenario_markdown())

    parts.append(cross_product_markdown())

    parts.append(section("Transition points that discriminate worlds", """
The high-leverage transitions are not calendar dates. They are state changes:

- **Capability transition:** agents sustain longer task horizons with lower supervision.
- **Economic transition:** mature cohorts shift from additive seats to captured P&L value.
- **Authority transition:** agents receive credentials for irreversible external action.
- **Institutional transition:** courts, regulators, insurers, and auditors accept or reject machine evidence and mandates.
- **Market transition:** at least two ownership-independent suppliers submit executable offers to a funded buyer.
- **Settlement transition:** delivery and payment obligations acquire explicit finality and default rules.
- **Physical transition:** embodied systems make energy, machines, property, and safety cases central.
- **Superintelligence transition:** capability changes faster than institutions can update.

At each transition, the same technical function can be a product, a bundled feature, a regulated utility obligation, an internal capability, or irrelevant.
"""))

    parts.append(section("Counterfactual reconstruction: reverse the attractive claims", """
The table does not ask whether the base assumption is plausible. It asks what follows if its opposite world holds long enough to determine market structure.

""" + md_table(["Assumption", "Opposite world", "Discriminating evidence", "Consequence"], KILL_ASSUMPTIONS) + "\n" + image("11_assumption_kill_tree.png", "Assumption bridges that can fail independently")))

    parts.append(section("Hidden confounders and partial observability", """
Observed growth can be misread. Internal chargebacks can be counted as market transactions; human approval can hide behind an autonomous label; calls inside one annual agreement can look like per-step procurement; different suppliers can share one model or cloud; test credits can look like settled value; failures and retries can look like demand; listings can look like supply; bundled cost can be imputed as a discovered price; one capacity block can be listed repeatedly; verifier and seller can share ownership; reciprocal transactions can fabricate reputation; router rebates can hide steering; benchmark leakage can mimic verification; one sponsor can create all demand; gross volume can ignore refunds; successful tasks can be the only ones observed; protocols can hide jurisdictional barriers.

Enterprise value has parallel traps: purchased licenses, monthly users, deployed agents, successful calls, accepted outputs, and P&L value are not interchangeable. Time saved can become slack, higher quality, work intensification, or expanded demand. Cleanup labor, prompt preparation, exception handling, and reputation risk can be missing. Human-in-the-loop can be nominal. Average reliability can hide correlated tail loss. Announced regulation can differ from enforcement.

The response is denominator discipline: define the principal, legal counterparty, independent supplier, binding mandate, accepted outcome, net settled value, human intervention, full cost, reversal, default, and delayed loss before treating a metric as evidence.
"""))

    parts.append(section("Game theory: where the mechanism becomes unstable", """
**Adverse selection:** suppliers know their hidden model, subcontractor, cost, and failure modes. **Moral hazard:** a winner cuts compute or verification after award. **Principal-agent failure:** the buyer agent optimizes a proxy or the router optimizes rebates. **Signaling:** certifications measure wealth or test optimization rather than quality. **Collusion:** shared pricing algorithms or repeated auctions coordinate behavior. **Foreclosure:** integrated platforms deny rivals identity, data, latency, or distribution. **Self-preference:** the market operator ranks its own supply. **Bypass:** strong buyers and sellers leave after matching. **Correlated risk:** nominal diversification shares hidden dependencies. **Verifier capture:** rated parties fund or own the judge. **Liquidity spiral:** poor execution drives away the opposite side. **Default and settlement risk:** delivery and money do not become final together.

Mechanism resistance requires structural separation, observable conflicts, portable identity and history, multi-homing, public rulebooks, collateral where appropriate, appeal, and a buyer who can exit. None is guaranteed by intelligence.
"""))

    parts.append(section("What superintelligence resistance actually means", """
**Resistance** raises the cost or limits the ability of a capable system to violate a boundary. **Resilience** preserves critical function after failure. **Bargaining power** keeps the institution from becoming a price taker. **Antifragility** improves the option set or bargaining position because shocks reveal information and trigger reallocation. These are not synonyms.

Technical controls - policies expressed to the same model, software monitors, or model-generated proofs - are weak against a system able to reason around, manipulate, or socially acquire access. Resistance becomes more credible when anchored outside the system's unilateral control: physically separated keys, diverse operators, legal sanctions against reachable principals, property rights, network segmentation, resource quotas, independent institutions, human coalitions, and reversible authority.

Even these anchors are conditional. A superintelligence can persuade key holders, exploit law, create dependency, or help one coalition dominate another. The correct claim is not that governance survives intelligence. It is that some institutional and physical mechanisms may remain costly to bypass while the relevant state retains coercion, property, legitimacy, plurality, and response time.

First-class nulls include institutional collapse, machine legal standing, emergency suspension of rights, persuasion or capture of key holders, loss of a reachable defendant, and capability change faster than detection, rulemaking, deployment, or enforcement. Current property and law identify transition friction; they are not durable anchors without a scenario-specific enforcement mechanism.

""" + image("13_si_survival_space.png", "Five resistance families and their limits")))

    resistance_rows=[]
    families=[
        ("Technical", "sandboxes, least privilege, signed binaries, isolated keys, network and compute controls", "direct privilege escalation and replication", "fails if agents obtain credentials socially or control the monitor"),
        ("Institutional", "named legal principals, courts, licensing, public oversight, professional duty", "deterrence, redress, legitimate refusal", "fails under capture, emergency, illegitimate states, or machine legal standing"),
        ("Economic", "property, collateral, scarce resources, diversification, switching", "limits resource access and preserves outside options", "fails if one provider controls identity, capital, compute, and distribution"),
        ("Architectural", "separation of execution, verification, authorization, settlement; heterogeneous redundancy", "contains blast radius and common-mode error", "fails when components share dependencies or one SI dominates all roles"),
        ("Strategic", "reversible commitments, multi-homing, short contracts, experiments, contingency plans", "preserves learning and bargaining across worlds", "fails when takeoff is faster than exercise or options depend on the same chokepoint"),
    ]
    for fam,mech,resist,limit in families:
        for scen in ["oligopoly","open commons","trusted SI","untrusted SI","fast takeoff"]:
            resistance_rows.append((fam,scen,mech,resist,limit))
    parts.append(section("Superintelligence resistance matrix", md_table(["Family","World","Mechanism","What it resists","Failure boundary"], resistance_rows)))

    parts.append(section("Antifragility under model and institutional shocks", """
A system is not antifragile merely because it has redundancy, a dashboard, or a fallback. A genuinely antifragile arrangement uses variation and failure to improve future choices without requiring catastrophic exposure. Candidate mechanisms include small reversible deployments that reveal loss distributions; dependency graphs that turn provider incidents into bargaining evidence; portable contracts and data that make switching rehearsals useful; heterogeneous verifiers that expose disagreement; capped authority that localizes experiments; procurement options that remain exercisable; and governance that updates from near misses without hiding them.

The anti-patterns are diversification by logo over a common stack, insurance without claims capacity, an open standard with proprietary identity, human oversight without time or power, and multi-cloud contracts that cannot move data or operations. These simulate resilience while preserving the common mode.

**Antifragility test:** after a model leap, provider failure, regulation, or incident, does the actor have more credible routes, better calibrated limits, lower switching friction, and greater bargaining power? If the shock merely increases cost or reinforces the incumbent, the arrangement is resilient at best and fragile at worst.

The stricter chain is: **shock -> protected downside -> captured learning or exercisable right -> measurable out-of-sample gain -> retained rights -> bounded failure**. A larger log corpus, survival, restored service, or post-incident demand is not a gain by itself. Every claim needs a gain unit, an option owner, premium, trigger, expiry, exercise terms, dependency-adjusted exercisability, positive-convexity interval, and abandonment rule. The mechanisms in this dossier remain hypotheses; none is asserted empirically antifragile.

""" + image("14_antifragility.png", "Shock-to-option cycle required for antifragility")))

    parts.append(section("Real options and temporal strategy without selecting a product", """
Under deep uncertainty, an option is valuable when it is affordable, exercisable, independent of the same failure mode, and informative. Examples include portable data and contracts, multi-provider qualification, customer-operated components, small experiments in delegated authority, protocol participation without irreversible dependence, scenario-specific partnerships, and contractual exit rights. Capital-heavy compute, insurance balance sheets, clearing licenses, exclusive distribution, and sovereign infrastructure are longer-duration commitments whose payoff requires stronger evidence.

An early revenue category can be rational but non-durable; a durable scarcity can be real but too early to monetize. The temporal question is whether present activity buys learning and future access or locks the actor into an expiring layer. That question is deliberately separate from a recommendation.

""" + image("15_real_options.png", "Reversibility and learning across commitment classes")))

    parts.append(opportunity_markdown())

    parts.append(section("Revenue mechanisms by market stage", """
Revenue is an observation about who pays now, not proof of long-run defensibility.

""" + md_table(["Stage","Payer","Possible meter","What revenue would establish","What it would not establish"], [
        ("Copilot / pilot", "team, CIO, innovation", "seat, project, services", "interest and integration willingness", "captured P&L value or autonomous authority"),
        ("Agent fleet", "CIO, CISO, function", "identity, controlled action, subscription, consumption", "production control budget", "independent category durability"),
        ("Delegated external action", "payments, risk, legal, application owner", "authorized action, attestation, transaction", "authority and evidence are funded", "open market or neutrality"),
        ("Machine procurement", "buyer or supplier", "membership, RFQ, transaction", "real exchange if bids and settlement are external", "liquidity or venture-scale take rate"),
        ("Assurance / insurance", "risk owner", "audit fee, premium, limit", "loss transfer if capital and claims are real", "diversifiability under superintelligence"),
        ("Clearing", "members and venues", "membership, clearing, collateral service", "underlying obligations and finality demand", "that an underlying market should exist"),
        ("Sovereign / physical", "state, regulated firm, operator", "long-term capacity, infrastructure, certification", "scarce resource and jurisdictional budget", "global scalability or low capital intensity"),
    ])))

    parts.append(section("Opportunities that disappear as intelligence improves", """
Basic prompt wrappers, undifferentiated model comparison, manual configuration, simple routing, generic evaluation, elementary code generation, superficial observability, and low-value integration can be absorbed by models or platforms. If verification and execution become nearly free, ex ante selection can be replaced by run-all-and-select. If a trusted provider owns identity, context, tools, and institutional legitimacy, many horizontal control functions collapse into one operating layer.

Disappearance can occur before technical redundancy: an incumbent can bundle the function at zero apparent price, a regulator can make it an obligation, a system of record can own the only authoritative state, or customers can internalize it. Technical value and company value must remain separate.
"""))

    parts.append(section("Functions strengthened by consequence-adjusted autonomous exposure", """
The relevant variable is not intelligence level. It is autonomous consequence exposure after native prevention and reversibility. More capable agents can increase the value of constraints when they receive broader credentials, actions become harder to reverse, consequence volume rises, physical systems enter scope, and institutions demand a reachable defendant. They can also reduce error, improve native controls, lower incident frequency, or concentrate legitimate delegation in a trusted provider.

But the strengthening is conditional on institutions refusing to delegate the same function to the intelligent provider. A trusted self-verifying utility can absorb verification and policy. A state can nationalize the chokepoint. A platform can own the user's identity and redress. The analysis therefore tracks recognition and control, not abstract importance.
"""))

    parts.append(section("Cross-world robustness properties", """
No category is robust to every world. The relatively contradiction-resistant mechanisms are not products but properties: portability across providers and jurisdictions; authority scoped to reversible actions; evidence that can be checked by more than one institution; customer control over keys and policy; dependency transparency; physical or legal enforcement outside a model's unilateral control; and commitments that can be reduced as uncertainty changes.

These properties can appear inside incumbents, public infrastructure, internal enterprise systems, standards, or independent companies. They can be socially valuable while imposing cost and creating no supplier, separate budget, or rent. Their persistence does not answer who captures the value.
"""))

    parts.append(section("Capital regimes and investor appetite", """
Investor appetite changes the equilibrium and can create false evidence. In a compute boom, capital rewards infrastructure, frontier suppliers, and growth before unit economics. In an agent-platform boom, distribution and developer adoption receive premium valuations. In a post-bubble discipline regime, buyers and investors demand captured P&L, retention, and low services intensity. In a regulated-infrastructure regime, licenses, balance sheets, long contracts, and institutional credibility matter. In a sovereign-capex regime, domestic operations and political alignment dominate scalability.

Venture financing can subsidize both sides of a supposed market, mask liquidity failure, or fund zero-price bundling. Acquisition can be an attractive exit while proving the independent layer was not durable. Capital availability is therefore an endogenous state variable, not external validation.
"""))

    indicators=[
        ("Cost / capability", "normalized price by capability tier; task horizon; open gap; candidate multiplicity"),
        ("Total economics", "risk-adjusted spend; cleanup labor; P&L capture; mature-cohort retention"),
        ("Concentration", "ownership and dependency HHI; first-party routing share; committed-spend concentration"),
        ("Enterprise authority", "service identities; delegated write/payment scope; reversals; human override quality"),
        ("Budget", "shift from pilots/seats to function P&L, operations, labor, assurance, capex"),
        ("Incumbent enclosure", "bundled price; acquisitions; default placement; portable policy/evidence"),
        ("Protocols", "production multi-homing; successful switching; portable credentials and reputation"),
        ("Markets", "independent qualified bids; net external settled value; fill; depth; bypass; disputes"),
        ("Insurance", "limits; exclusions; capital; reinsurance; paid claims; correlated-loss tests"),
        ("Institutions", "court/regulator acceptance; liability assignment; sovereignty procurement; enforcement"),
        ("Labor", "junior hiring; task composition; expert/novice gains; worker consultation; redesign"),
        ("Physical", "data-center TWh; grid queue; capacity premium; robot deployment; safety claims"),
        ("Superintelligence", "capability discontinuity; evaluation gaming; emergency controls; institutional trust"),
        ("Welfare-adjusted demand", "human or enterprise value net of compute, review, externalities, retries, and synthetic workload"),
        ("Capacity correction", "utilization, cancellations, write-downs, training/inference split, and stranded infrastructure"),
        ("Public and worker veto", "consultation, bargaining, litigation, licensing, moratoria, elections, and community opposition"),
        ("Institutional response time", "capability-change interval divided by detection, rule, deployment, and enforcement time"),
        ("Non-compensable loss", "harms without reachable defendant, adequate capital, accepted jurisdiction, or practical remedy"),
        ("Full-workflow switching", "movement of identity, context, policy, evidence, contracts, and operations - not API compatibility"),
    ]
    parts.append(section("Leading-indicator system", """
Indicators are useful only when tied to a branch. A rise in agents confirms proliferation but says little about market formation. A rise in machine-payment messages confirms protocol use but not delegated authority or final settlement. The dashboard therefore pairs each observation with the world it discriminates.

""" + image("18_indicator_dashboard.png", "Leading indicators by causal family") + "\n" + md_table(["Family","Measures"], indicators)))

    parts.append(section("Research and experiment agenda", """
The following investigations reduce uncertainty without choosing a product:

1. Build an ownership- and dependency-adjusted map of production agent supply.
2. Separate seats, active users, autonomous actions, accepted outcomes, and captured P&L across enterprise cohorts.
3. Measure whether enterprises actually switch providers under outage, price, capability, and jurisdiction shocks.
4. Test whether provider-native evidence is accepted by customers, auditors, insurers, courts, and regulators.
5. Observe delegated authority: scope, revocation, human confirmation, disputes, and liability allocation.
6. Distinguish protocol messages from binding contracts and net settled external value.
7. Measure task contractibility before evaluating auctions or outcome markets.
8. Stress supplier independence by common model, cloud, data, verifier, and parent.
9. Compare routing against strong fixed policies and run-all/select under full cost.
10. Track incumbent bundling, acquisition, default placement, and open-standard extensions.
11. Study failure tails, delayed harms, common-mode incidents, and insurer exclusions.
12. Run institutional tabletop exercises for trusted, untrusted, deceptive, and discontinuous superintelligence.
13. Test whether an incident increases real options or merely increases dependence on the incumbent.
14. Update the scenario ledger quarterly without converting scenarios into point forecasts.
"""))

    parts.append(section("Evidence and confidence ledger", md_table(["Claim","Status","Confidence","What would change it"], [
        ("Per-unit capability cost is declining rapidly", "observed but tier-dependent", "high", "sustained real-price reversal"),
        ("Total AI system spend can rise while unit cost falls", "observed / causal inference", "high", "mature demand saturation"),
        ("Enterprises will operate many agents", "announced / emerging", "medium", "suite consolidation into one delegate"),
        ("Provider plurality persists", "uncertain", "low-medium", "dependency-adjusted production concentration"),
        ("Agent activity becomes an open market", "speculation", "low", "binding independent bids and net settlement"),
        ("Authority and liability remain scarce under SI", "scenario-dependent", "low-medium", "institutional standing of trusted SI"),
        ("Independent verification earns a separate budget", "uncertain", "low-medium", "procurement and regulatory acceptance"),
        ("Open standards increase contestability", "uncertain", "low", "portable production multi-homing"),
        ("Insurance can absorb advanced-agent loss", "unknown", "low", "credible limits, capital, claims, and tail calibration"),
        ("Clearing becomes necessary", "remote contingent scenario", "low", "multi-venue obligations and finality risk"),
        ("Physical and sovereign scarcities persist", "plausible / observed today", "medium-high", "abundance and accepted global safeguards"),
        ("Any one independent company captures these functions", "unresolved", "low", "buyer budgets, enclosure, retention, and switching"),
        ("The taxonomy is independent of the originating thesis", "partially tested", "low-medium", "actor/welfare taxonomy reveals no material omitted worlds"),
        ("Governance remains enforceable under superintelligence", "scenario-dependent", "low", "institutional response, coercive capacity, key custody, and legal continuity"),
        ("Candidate mechanisms are antifragile", "falsification architecture only", "low", "bounded shocks produce retained out-of-sample gains with protected downside"),
        ("Standards produce contestability", "unresolved", "low", "full-workflow switching and distributed traffic/rent across the contestability stack"),
        ("Machine activity forms markets", "rare conditional transition", "low", "independent executable bids, net settlement, default, remedy, and repeat exchange"),
        ("Opportunity surfaces receive separate recurring budgets", "unproven", "low", "renewal after native alternatives are fully configured"),
    ])))

    parts.append(section("Adversarial review architecture", """
The dossier was built through three separated rounds. Round 1 asked independent teams to derive market structures, enterprise authority paths, machine-market formation tests, incumbent enclosure strategies, superintelligence phase space, and antifragility mechanisms before comparing with the Odylith deck. Round 2 cross-examined contradictions: abundance versus concentration, open standards versus enclosure, delegation versus legal accountability, routing versus run-all, verification versus self-proof, neutrality versus conflicts, and resilience versus actual antifragility. Round 3 asked an independent adjudicator to identify agreements, contradictions, missing worlds, and variables without selecting a product.

The appendices preserve those disagreements. They are not votes and do not create certainty. Their purpose is to reduce shared framing error.
"""))

    parts.append(section("Round 3 correction-closure ledger", md_table(["Adjudicated defect", "Material integration", "Residual uncertainty"], [
        ("Premature three-round claim", "Round 3 is now included after six Round 2 records and this closure ledger", "The adjudication remains a historical critique, not proof of truth"),
        ("Odylith-shaped taxonomy", "Added W1-W18 actor/welfare atlas derived from households, labor, public goods, coercion, externalities, and non-market allocation", "Frame independence remains partial because every taxonomy reflects its question"),
        ("Scenario list called a phase space", "Renamed as scenario library; added 16-cell crossed lattice and nine omitted equilibria", "The phase space is still not exhaustive or probability weighted"),
        ("Rebound over-attribution", "Separated observed co-movement from elasticity, overbuild, utilization, training, and write-down hypotheses", "Mature-cohort causal evidence remains limited"),
        ("Scarcity always migrates", "Added no-migration endpoint: demand, profit, or willingness to pay can disappear", "Which tasks vanish is unknown"),
        ("Standards treated as contestability", "Added full contestability stack and removed common syntax as an assumed scarcity", "Production switching evidence remains early"),
        ("Market language leakage", "Added formation verdicts distinguishing hierarchy, supply chain, directory, procurement, market, and infrastructure", "Border cases remain institution-specific"),
        ("Intelligence level treated as causal", "Reframed around consequence-adjusted autonomous exposure after native prevention and reversibility", "Exposure distributions remain partly hidden"),
        ("Robustness called opportunity", "Renamed as cross-world robustness properties with no implied supplier, budget, or rent", "Social value and private capture remain separate"),
        ("Opportunity menu salience", "Each O1-O25 now includes seven gates, correlated death, falsifier, revival, option premium, expiry, abandonment, public/internal homes, and no-budget outcomes", "All evidence states remain low until observed"),
        ("Authority assumed durable", "Added institutional collapse, machine standing, emergency law, key-holder capture, and response-time failure", "Enforcement under superintelligence is unknowable"),
        ("Loose antifragility", "Imported protected-downside, retained-rights, measurable-gain, convexity-interval, and bounded-failure tests", "No mechanism is claimed empirically antifragile"),
        ("Narrow indicators", "Added welfare-adjusted demand, utilization/write-downs, veto, institutional speed, non-compensable loss, and full-workflow switching", "Many measures require unavailable private data"),
        ("Confidence ledger omissions", "Added frame independence, governance survival, antifragility, contestability, market formation, and separate-budget claims at low confidence", "Confidence must be updated from future evidence"),
    ])))

    appendices = research_appendices()
    if appendices:
        parts.append(appendices)

    parts.append(section("Primary-source bibliography", "\n".join(f"{i}. **{ascii_clean(name)}.** {url}" for i,(name,url) in enumerate(SOURCES,1))))

    parts.append(section("Decisions deliberately unmade", """
This dossier does not choose a beachhead, product, pricing model, revenue target, financing plan, marketplace sequence, company boundary, or investment verdict. It does not decide that routing, verification, governance, authority, underwriting, clearing, software, or any other surface belongs to Odylith. It does not assign probabilities to superintelligence timelines.

What remains is a structured field of uncertainty:

- Capability can commoditize while infrastructure and total spend concentrate.
- Agent proliferation can create open exchange or deepen internal hierarchy.
- Open standards can increase contestability or incumbent distribution.
- Better intelligence can strengthen constraints or internalize them.
- Authority can remain institutionally scarce or migrate toward a trusted provider or state.
- Verification can become more valuable, become bundled, or become free.
- Revenue can appear in a transition layer that later disappears.
- Antifragility requires independent, exercisable options; diversification labels are insufficient.

The next intellectual task is not to defend a thesis. It is to watch the leading variables, run discriminating experiments, update the scenario ledger, and preserve the ability to move when one world begins to dominate.
"""))

    text = ascii_clean("\n\n".join(parts))
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    SOURCE.write_text(text, encoding="utf-8")


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
    canvas_obj.setStrokeColor(colors.HexColor(EMERALD)); canvas_obj.setLineWidth(1.4)
    canvas_obj.line(0.62 * inch, h - 0.52 * inch, w - 0.62 * inch, h - 0.52 * inch)
    canvas_obj.setFont("Arial-Bold", 7.1); canvas_obj.setFillColor(colors.HexColor(MUTED))
    canvas_obj.drawString(0.62 * inch, h - 0.39 * inch, "ODYLITH / MARKET EVOLUTION SITUATIONAL AWARENESS")
    canvas_obj.setFont("Arial", 7.1)
    canvas_obj.drawRightString(w - 0.62 * inch, h - 0.39 * inch, "EVIDENCE CUTOFF: 5 AUGUST 2026")
    canvas_obj.setStrokeColor(colors.HexColor(GRID)); canvas_obj.setLineWidth(0.6)
    canvas_obj.line(0.62 * inch, 0.47 * inch, w - 0.62 * inch, 0.47 * inch)
    canvas_obj.setFont("Arial-Bold", 7.1); canvas_obj.setFillColor(colors.HexColor(MUTED))
    canvas_obj.drawString(0.62 * inch, 0.30 * inch, "SCENARIO DOSSIER / NON-PRESCRIPTIVE")
    canvas_obj.drawRightString(w - 0.62 * inch, 0.30 * inch, f"{canvas_obj.getPageNumber():03d}")
    canvas_obj.restoreState()


def build_pdf():
    generate_assets()
    build_source()
    width, height = LETTER
    margin_x, top, bottom = 0.65 * inch, 0.70 * inch, 0.62 * inch
    frame = Frame(margin_x, bottom, width - 2 * margin_x, height - top - bottom, id="normal", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    cover_frame = Frame(0.82 * inch, 0.7 * inch, width - 1.64 * inch, height - 1.4 * inch, id="cover", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc = base.DossierDocTemplate(str(OUTPUT), pagesize=LETTER, leftMargin=margin_x, rightMargin=margin_x, topMargin=top, bottomMargin=bottom,
                                  title="Odylith Market Evolution Situational Awareness", author="freedom-research",
                                  subject="Non-prescriptive market evolution, counterfactual, antifragility, and superintelligence scenario dossier")
    doc.addPageTemplates([PageTemplate(id="cover", frames=[cover_frame], onPage=cover_page), PageTemplate(id="normal", frames=[frame], onPage=normal_page)])
    source = SOURCE.read_text(encoding="utf-8")
    body = source.split("---", 2)[2].lstrip()
    cover_meta = ParagraphStyle("CoverMetaME", fontName="Arial", fontSize=9.2, leading=15, textColor=colors.HexColor("#AFC0D7"))
    badge = ParagraphStyle("BadgeME", fontName="Arial-Bold", fontSize=9.5, leading=12, textColor=colors.white, alignment=TA_CENTER)
    story = [
        Spacer(1, 0.55 * inch),
        Paragraph("MARKET EVOLUTION / SITUATIONAL AWARENESS", base.S["CoverKicker"]),
        Paragraph("ODYLITH", base.S["CoverTitle"]),
        Paragraph("Intelligence abundance, institutional authority,<br/>market formation, and survival under superintelligence", base.S["CoverSub"]),
        Spacer(1, 0.18 * inch),
        Table([[Paragraph("NON-PRESCRIPTIVE WORLD MODEL", badge)]], colWidths=[3.45 * inch], style=TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(EMERALD)),("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9)])),
        Spacer(1, 0.35 * inch),
        Paragraph('"Do not defend a thesis. Map the worlds that could invalidate it."', base.S["CoverQuote"]),
        Spacer(1, 0.55 * inch),
        Paragraph("Evidence cutoff  /  5 August 2026<br/>Prepared for founder-level strategic inquiry<br/>Observed facts, announced claims, inference, speculation, unknowns, and falsifiers are separated", cover_meta),
        NextPageTemplate("normal"), PageBreak(), Paragraph("Contents", base.S["TOCTitle"]),
    ]
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC1ME", fontName="Arial-Bold", fontSize=8.9, leading=12.2, leftIndent=0, textColor=colors.HexColor(INK), spaceBefore=3),
        ParagraphStyle("TOC2ME", fontName="Arial", fontSize=7.5, leading=10, leftIndent=15, textColor=colors.HexColor(SLATE), spaceBefore=1),
    ]
    story.extend([toc, PageBreak()])
    story.extend(base.parse_markdown(body, frame._width))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.multiBuild(story)


if __name__ == "__main__":
    build_pdf()
