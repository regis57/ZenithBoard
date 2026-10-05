# SPDX-License-Identifier: GPL-3.0-or-later
"""Aircraft type -> silhouette class.

The wall draws a silhouette that matches the real aircraft design. The class names are:

  narrow   single-aisle airliner, engines under the wings (A320, 737, 757, E-Jets, A220)
  wide     twin/tri wide-body (777, 787, A330, A350, 767, DC-10/MD-11)
  quad     four-engine airliner (747, A380, A340, 707, DC-8, BAe 146, Il-96)
  rearjet  rear-engined T-tail jet (CRJ, ERJ-145, MD-80, DC-9, 727, Fokker, Tu-154)
  turboprop twin turboprop airliner/commuter (ATR, Dash 8, Saab 340, King Air)
  bizjet   business / light jet
  light    single-engine piston or turboprop
  twinprop twin piston (Seneca, Baron, Cessna 310) and old four-engine props
  heli     helicopters, gyrocopters, tilt-rotors
  fighter  swept-wing combat / trainer jets
  delta    delta-wing jets (Rafale, Typhoon, Mirage, Gripen, MiG-21)
  airlifter military transports, tankers' cargo cousins (C-130, C-17, A400M, Il-76, An-124)
  bomber   bombers and flying wings (B-52, B-1, B-2, Tu-95, Tu-160)
  glider   gliders and motor-gliders
  balloon  balloons and airships

Each class can carry a *variant* that changes the drawing a little (e.g. the 747 hump).

Codes are ICAO aircraft type designators. Anything that is not listed here is classified from the
ADS-B emitter category and, when the optional monthly type-data refresh has been downloaded, from
its engine description (see `tools/update_types.py`).
"""

CLASSES = ("narrow", "wide", "quad", "rearjet", "turboprop", "bizjet", "light", "twinprop", "heli",
           "fighter", "delta", "airlifter", "bomber", "glider", "balloon")
MILITARY_CLASSES = ("fighter", "delta", "bomber")


def _s(text):
    return set(text.split())


# --- explicit tables ---------------------------------------------------------------------------
HELI = _s("""
EC35 EC45 EC30 EC20 EC25 EC55 EC75 EC130 EC120 H135 H145 H160 H125 H130 A109 A119 A139 A169 A189 AS50 AS55 AS65
AS32 AS3B AS350 B06 B407 B412 B429 B430 B505 R22 R44 R66 S76 S92 S61 S58 S64 H60 H64 H53 H53S NH90 EH10 LYNX
TIGR MI2 MI4 MI6 MI8 MI10 MI14 MI24 MI26 MI28 MI34 MI38 KA25 KA26 KA27 KA50 KA52 KA62 K226 B105 B212 B214 B222
B230 B427 B47G B206 SCOU PUMA GAZL LAMA ALO2 ALO3 AS55 EXEC EN28 EN48 MD52 MD60 MD90X H500 H269 H47 V22 V280 B609
""")
HELI_VARIANT = {"H47": "tandem", "V22": "tilt", "V280": "tilt", "B609": "tilt", "XV15": "tilt", "JAS4": "tilt"}

FIGHTER = _s("""
A10 A4 A6 A3 AMX F104 F111 F117 F14 F15 F16 F16X F18H F18S F22 F35 VF35 F4 F5 F5SA F8 F86 F2 F1 FC1 GJ11 HAR HAWK HUNT
J20 J8A J8B JAGR JH7 KAAN KF21 K50 L15 L159 L39 M346 MG19 MG23 MG25 MG29 MG31 MG44 MT2 Q5 S37 SU17 SU7 SU24 SU25 SU27
SU57 T38 T33 T4 T5YY TOR VAUT Y130 YK28 YURO AJET AT3 CKUO SSAB SBR1 SBR2 SMB2 ETAR MYS4 SWIF SHAW VNOM METR LTNG FOUG
X29 X32 X59 XB1 I22 JL9 KZLA BT7 SB29 SB32 S3 CNBR BUC ME62 JAST SB05 T2 SATA CH1 TPIL HAR Y141 YK38 SOL1
""")
DELTA = _s("""EUFI RFAL MIR2 MIRA MRF1 SB35 SB37 SB39 SGCD SGEF F106 KFIR LCA MG21 J10 X47B Q25 Q28""")
BOMBER = _s("""B1 B2 B21 B52 T160 T22M TU22 TU16 TU95 MYA4 B17 B24 B29""")
AIRLIFTER = _s("""
C130 C30J C17 C5M C141 C15 A400 A124 A225 AN12 AN22 AN70 IL76 C160 C27J G222 C295 CN35 C212 KC2 C1 Y20 E2 P3 A50 AN72
A743 CL2T CL2P BER2 US2 SHIP
""")
AIRLIFTER_VARIANT = {"C17": "jet", "C5M": "jet", "C141": "jet", "C15": "jet", "A124": "jet", "A225": "jet", "IL76": "jet",
                     "KC2": "jet", "C1": "jet", "Y20": "jet", "AN72": "jet", "A743": "jet", "A50": "jet", "C295": "prop2",
                     "CN35": "prop2", "C27J": "prop2", "G222": "prop2", "C212": "prop2", "E2": "prop2", "CL2T": "prop2",
                     "CL2P": "prop2", "BER2": "jet", "US2": "prop4"}

QUAD = _s("""
B701 B703 B720 DC85 DC86 DC87 A342 A343 A345 A346 A388 IL86 IL96 B461 B462 B463 RJ70 RJ85 RJ1H
B741 B742 B743 B744 B748 B74R B74S BLCF K35R K35E KE3 C135 R135 W135 E3CF E3TF E6 BELF CL4G SGUP
""")
QUAD_VARIANT = {"B741": "hump", "B742": "hump", "B743": "hump", "B744": "hump", "B748": "hump", "B74R": "hump",
                "B74S": "hump", "BLCF": "hump", "A388": "deck", "B461": "hiwing", "B462": "hiwing", "B463": "hiwing",
                "RJ70": "hiwing", "RJ85": "hiwing", "RJ1H": "hiwing"}

WIDE = _s("""
A306 A30B A310 A332 A333 A337 A338 A339 A359 A35K A3ST B762 B763 B764 B772 B773 B778 B779 B77L B77W B788 B789 B78X
DC10 MD11 L101 E767 """)
WIDE_VARIANT = {"DC10": "tri", "MD11": "tri", "L101": "tri", "A337": "beluga", "A3ST": "beluga"}

REARJET = _s("""
B712 MD81 MD82 MD83 MD87 MD88 MD90 DC91 DC92 DC93 DC94 DC95 CRJ1 CRJ2 CRJ7 CRJ9 CRJX E135 E145 E45X F28 F70 F100 BA11
B721 B722 R721 R722 T134 T154 T334 IL62 AJ27 YK40 YK42 HF20
""")
REARJET_VARIANT = {"B721": "tri", "B722": "tri", "R721": "tri", "R722": "tri", "T154": "tri", "YK40": "tri", "YK42": "tri",
                   "IL62": "quad"}

BIZJET = _s("""
C25A C25B C25C C25M C500 C501 C510 C525 C526 C550 C551 C55B C560 C56X C650 C680 C68A C700 C750 CL30 CL35 CL60 GL5T
GL7T GLEX GLF2 GLF3 GLF4 GLF5 GLF6 GALX G150 G250 G280 GA3C GA4C GA5C GA6C GA7C GA8C ASTR FA10 FA20 FA50 FA6X
FA7X FA8X F900 F2TH LJ23 LJ24 LJ25 LJ28 LJ31 LJ35 LJ40 LJ45 LJ55 LJ60 LJ70 LJ75 LJ85 E50P E55P E545 E550 E35L E390 H25A
H25B H25C HA4T HDJT PRM1 SF50 EA50 PC24 BE40 BE4W WW23 WW24 JCOM MU30 SJ30 L29A L29B E530 EPIC
""")
BIZJET.discard("EPIC")

TURBOPROP = _s("""
AT43 AT44 AT45 AT46 AT72 AT73 AT75 AT76 DH8A DH8B DH8C DH8D SF34 SB20 JS31 JS32 JS41 JS1 JS3 JS20 B190 BE20 BE9L BE9T
BE10 BE30 B350 BE99 BE22 C441 C425 DHC6 D228 D328 F50 F60 F27 E120 E110 E121 AN24 AN26 AN28 AN30 AN32 AN38 L410 L610 SH33
SH36 SC7 SW2 SW3 SW4 MA60 MA6H Y12 Y12F YS11 I114 I112 N250 N219 ATP A748 DHC5 DH4T DHC7 P180 AC80 AC90 AC95 PAY1
PAY2 PAY3 PAY4 PAT4 BN2T DC3T IL18 IL38 ATLA CVLT L188 F406 C408 MU2 BS60 U21 V10 STAR
""")
TURBOPROP_VARIANT = {"DHC7": "quad", "IL18": "quad", "IL38": "quad", "L188": "quad", "CVLT": "quad"}

LIGHT = _s("""
C150 C152 C162 C170 C172 C177 C180 C182 C185 C188 C206 C207 C208 C210 C140 C120 C195 PA18 PA32 PA46 PA24 PA38 PA22
P28A P28B P28R P28T P32R P32T PA11 PA12 PA14 PA16 SR20 SR22 S22T DA40 DA50 DR40 TB20 TB21 BE33 BE35 BE36 BE23 BE24
M20P M20T RV6 RV7 RV8 RV9 RV10 RV12 AA5 AA1 G115 G120 PC12 PC6T TBM7 TBM8 TBM9 M600 M700 P46T K100 K200 K900 E300 E200
CH60 CH70 CH75 CH7A CH7B J3 J4 DV20 DV2 SF25 AC11 YK52 T6 TEX2 PC7 PC9 PC21 TUCA E314 KT1 SIRA SPIT HURI P51 T34P T34T
BT36
""")
TWINPROP = _s("""
PA34 PA44 PA30 PA31 PA23 PA27 BE55 BE56 BE58 BE60 BE65 BE76 BE95 C310 C320 C335 C340 C402 C404 C414 C421 DA42 DA62 P68
AEST AC50 AC56 TRIS BN2P NOMA BE18 B18T
""")
GLIDER = _s("""GLID""")
BALLOON = _s("""BALL""")

# Single-engine props that are high-wing (all others are drawn low-wing)
HIGH_WING_LIGHT = _s("""
C150 C152 C162 C170 C172 C177 C180 C182 C185 C188 C195 C206 C207 C208 C210 C140 C120 PA18 P18T M7T DH2T DH3T K100 K200 K900 STLN PC6T BL8 BL17 CH7A CH7B ULAC J3 J4 TAYB
""")


def _from_category(cat):
    """Last-resort class from the ADS-B emitter category (no type known)."""
    cat = (cat or "").upper()
    return {"A1": "light", "A2": "bizjet", "A3": "narrow", "A4": "narrow", "A5": "wide", "A6": "fighter",
            "A7": "heli", "B1": "glider", "B2": "balloon", "B4": "light", "B6": "light"}.get(cat, "narrow")


_BIZ_WORDS = ("CITATION", "LEARJET", "GULFSTREAM", "GLOBAL", "CHALLENGER", "FALCON", "HAWKER", "BEECHJET", "BEECH 400",
              "PHENOM", "PRAETOR", "LEGACY", "HONDAJET", "ECLIPSE", "WESTWIND", "COMMODORE", "PREMIER", "SJ-30", "LATITUDE",
              "LONGITUDE", "VISION", "JETSTAR")
_MIL_WORDS = ("FIGHTER", "TYPHOON", "MIRAGE", "RAFALE", "GRIPEN", "TORNADO", "HARRIER", "SUKHOI", "MIKOYAN", "MIG-",
              "SUPER HORNET", " F-", "-FIGHTER", "TROLL")
_REAR_WORDS = ("REGIONAL JET", "ERJ-135", "ERJ-145", "MD-8", "DC-9", "FOKKER", "BAC 1-11", "TUPOLEV TU-134")


def classify_from_description(name, desc, wtc):
    """Class for a type that is not in the tables, from a long name and the ICAO description (e.g. 'L2J')."""
    name = (name or "").upper()
    desc = (desc or "").upper()
    wtc = (wtc or "").upper()
    kind = desc[:1]
    if kind in ("H", "G", "R", "T"):
        return "heli", ("tilt" if kind in ("R", "T") and "OSPREY" in name else None)
    if desc.startswith("B0") or "BALLOON" in name or "AIRSHIP" in name:
        return "balloon", None
    if "GLIDER" in name or "SAILPLANE" in name:
        return "glider", None
    if desc[1:2] == "0":          # placeholders (drone, parachute, 'ground') - unknown shape
        return None, None
    engines = desc[1:2]
    etype = desc[2:3]
    if etype in ("P", "E") or etype == "M":
        if engines == "1" or kind in ("S", "A"):
            return "light", None
        return "twinprop", ("quad" if engines in ("4", "6") else None)
    if etype == "T":
        if engines == "1":
            return "light", None
        if engines in ("4", "6"):
            return "turboprop", "quad"
        return "turboprop", None
    if etype == "J":
        if any(w in name for w in _MIL_WORDS):
            return "fighter", None
        if engines == "1":
            return ("fighter", None) if wtc == "M" else ("bizjet", None)
        if engines in ("4", "6", "8"):
            return "quad", None
        if engines == "3":
            return ("wide", "tri") if wtc == "H" else ("rearjet", "tri")
        if any(w in name for w in _BIZ_WORDS) or wtc == "L":
            return "bizjet", None
        if any(w in name for w in _REAR_WORDS):
            return "rearjet", None
        return ("wide", None) if wtc == "H" else ("narrow", None)
    return None, None


def classify(code, category=None, long_name=None, desc=None, wtc=None):
    """Return (shape, variant) for an ICAO type code, falling back on category / description."""
    t = (code or "").upper()
    if t:
        if t in HELI:
            return "heli", HELI_VARIANT.get(t)
        if t in GLIDER:
            return "glider", None
        if t in TWINPROP:
            return "twinprop", None
        if t in LIGHT:
            return "light", ("high" if t in HIGH_WING_LIGHT else None)
        if t in BALLOON:
            return "balloon", None
        if t in BOMBER:
            return "bomber", None
        if t in DELTA:
            return "delta", None
        if t in FIGHTER:
            return "fighter", None
        if t in AIRLIFTER:
            return "airlifter", AIRLIFTER_VARIANT.get(t)
        if t in QUAD:
            return "quad", QUAD_VARIANT.get(t)
        if t in WIDE:
            return "wide", WIDE_VARIANT.get(t)
        if t in REARJET:
            return "rearjet", REARJET_VARIANT.get(t)
        if t in BIZJET:
            return "bizjet", None
        if t in TURBOPROP:
            return "turboprop", TURBOPROP_VARIANT.get(t)
        if t in ("A318", "A319", "A320", "A321", "A19N", "A20N", "A21N", "B731", "B732", "B733", "B734", "B735", "B736",
                 "B737", "B738", "B739", "B37M", "B38M", "B39M", "B3XM", "B752", "B753", "BCS1", "BCS3", "E170",
                 "E75L", "E75S", "E190", "E195", "E275", "E290", "E295", "C919", "SU95", "MC23", "A148", "A158"):
            return "narrow", None
        if desc:
            shape, variant = classify_from_description(long_name, desc, wtc)
            if shape:
                if shape == "light":
                    variant = "high" if t in HIGH_WING_LIGHT else variant
                return shape, variant
    cat = (category or "").upper()
    shape = _from_category(cat)
    if shape == "light" and t in HIGH_WING_LIGHT:
        return shape, "high"
    return shape, None


def is_military(shape, db_flags=0):
    """Military look: ADS-B database flag bit 0 (set by readsb when it knows the airframe) or a combat class."""
    try:
        return bool(int(db_flags or 0) & 1) or shape in MILITARY_CLASSES
    except (TypeError, ValueError):
        return shape in MILITARY_CLASSES


# Short names for the most common types, so the wall can show a model name before any data refresh.
# The monthly refresh (tools/update_types.py) adds the full list.
NAMES = {
    "A318": "Airbus A318", "A319": "Airbus A319", "A320": "Airbus A320", "A321": "Airbus A321",
    "A19N": "Airbus A319neo", "A20N": "Airbus A320neo", "A21N": "Airbus A321neo", "BCS1": "Airbus A220-100",
    "BCS3": "Airbus A220-300", "A332": "Airbus A330-200", "A333": "Airbus A330-300", "A339": "Airbus A330-900",
    "A342": "Airbus A340-200", "A343": "Airbus A340-300", "A346": "Airbus A340-600", "A359": "Airbus A350-900",
    "A35K": "Airbus A350-1000", "A388": "Airbus A380-800", "A400": "Airbus A400M Atlas", "A306": "Airbus A300-600",
    "B733": "Boeing 737-300", "B734": "Boeing 737-400", "B737": "Boeing 737-700", "B738": "Boeing 737-800",
    "B739": "Boeing 737-900", "B38M": "Boeing 737 MAX 8", "B39M": "Boeing 737 MAX 9", "B744": "Boeing 747-400",
    "B748": "Boeing 747-8", "B752": "Boeing 757-200", "B763": "Boeing 767-300", "B772": "Boeing 777-200",
    "B77W": "Boeing 777-300ER", "B788": "Boeing 787-8", "B789": "Boeing 787-9", "B78X": "Boeing 787-10",
    "E170": "Embraer E170", "E75L": "Embraer E175", "E190": "Embraer E190", "E195": "Embraer E195",
    "CRJ2": "Bombardier CRJ-200", "CRJ7": "Bombardier CRJ-700", "CRJ9": "Bombardier CRJ-900", "E145": "Embraer ERJ-145",
    "MD82": "McDonnell Douglas MD-82", "MD11": "McDonnell Douglas MD-11", "DC10": "McDonnell Douglas DC-10",
    "B722": "Boeing 727-200", "AT72": "ATR 72", "AT76": "ATR 72-600", "AT75": "ATR 72-500", "DH8D": "Dash 8 Q400",
    "SF34": "Saab 340", "BE20": "King Air 200", "C208": "Cessna Caravan", "PC12": "Pilatus PC-12", "TBM9": "Daher TBM 900",
    "C172": "Cessna 172", "C182": "Cessna 182", "P28A": "Piper Cherokee", "SR22": "Cirrus SR22", "DA40": "Diamond DA40",
    "C25C": "Cessna Citation CJ4", "C56X": "Cessna Citation Excel", "C680": "Cessna Citation Sovereign",
    "GLF5": "Gulfstream G550", "GLF6": "Gulfstream G650", "GLEX": "Bombardier Global 6000", "FA7X": "Dassault Falcon 7X",
    "F2TH": "Dassault Falcon 2000", "LJ45": "Learjet 45", "E55P": "Embraer Phenom 300", "PC24": "Pilatus PC-24",
    "EC35": "Airbus H135", "EC45": "Airbus H145", "H160": "Airbus H160", "A109": "Agusta A109", "R44": "Robinson R44",
    "S92": "Sikorsky S-92", "H60": "Sikorsky UH-60 Black Hawk", "H47": "Boeing CH-47 Chinook", "NH90": "NH90",
    "F16": "F-16 Fighting Falcon", "F15": "F-15 Eagle", "F18H": "F/A-18 Hornet", "F18S": "F/A-18 Super Hornet",
    "F22": "F-22 Raptor", "F35": "F-35 Lightning II", "EUFI": "Eurofighter Typhoon", "RFAL": "Dassault Rafale",
    "MIR2": "Dassault Mirage 2000", "SB39": "Saab Gripen", "TOR": "Panavia Tornado", "A10": "A-10 Thunderbolt II",
    "AJET": "Alpha Jet", "C130": "C-130 Hercules", "C30J": "C-130J Super Hercules", "C17": "C-17 Globemaster III",
    "C5M": "C-5M Super Galaxy", "IL76": "Ilyushin Il-76", "A124": "Antonov An-124", "A225": "Antonov An-225",
    "K35R": "KC-135 Stratotanker", "E3TF": "E-3 Sentry", "B52": "B-52 Stratofortress", "B1": "B-1 Lancer",
    "B2": "B-2 Spirit", "TU95": "Tupolev Tu-95", "T160": "Tupolev Tu-160", "GLID": "Glider", "BALL": "Balloon",
}


def type_name(code, long_names=None):
    code = (code or "").upper()
    if long_names and code in long_names:
        return long_names[code]
    return NAMES.get(code)
