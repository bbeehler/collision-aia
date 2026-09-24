"""Content and program settings. Requirement IDs must match supabase required_ids().
Requirement wording is AIA Canada's own, from the English and French editions of the Statement."""
from .i18n import lang, t

STATEMENT_VERSION = "2025"
DECLARATION_DAYS = 365
RENEW_WINDOW_DAYS = 90

# (id, section, English, French)
REQS = [
    ("B1", "business",
     "Adhere to all applicable federal, provincial and municipal acts, regulations and standards, including health and safety, environmental, zoning, business licensing and permits, apprenticeship and trade licensing, and consumer privacy and protection.",
     "Se conformer à toutes les lois, réglementations et normes fédérales, provinciales et municipales applicables (santé et sécurité, environnement, zonage, licences et permis d’affaires, exigences liées à l’apprentissage et à la licence de métier, loi sur la protection et la vie privée du consommateur, etc.)."),
    ("B2", "business",
     "Maintain a Garage Liability insurance policy with at least $2,000,000 CAD in coverage.",
     "Maintenir une police d’assurance responsabilité garage avec une couverture minimale de 2 000 000 $ CAD."),
    ("B3", "business",
     "Maintain liability coverage when using a sublet vendor.",
     "Maintenir une couverture de responsabilité lorsqu’on utilise un fournisseur sous‑contrat."),
    ("B4", "business",
     "Maintain an electronic management system to track customer information, repair orders, parts inventory and usage, estimates, invoices and compliance documentation.",
     "Maintenir un système de gestion électronique permettant de suivre efficacement l’information client, les ordres de réparation, l’inventaire des pièces et leur utilisation, les devis, les factures et la documentation de conformité."),
    ("T1", "training",
     "Each technician holds a Certificate of Qualification relevant to their role, or is a registered apprentice, where mandated provincially or territorially.",
     "Chaque technicien doit détenir un Certificat de qualification pertinent à son rôle, ou être apprenti inscrit (là où cela est exigé au niveau provincial ou territorial)."),
    ("T2", "training",
     "The shop maintains I-CAR Canada Gold Class® status, through I-CAR Canada or recognized Training Alliance Partners.",
     "L’atelier doit détenir la reconnaissance or d’I‑CAR Canada, via I‑CAR Canada ou des partenaires reconnus de Training Alliance."),
    ("F1", "facility",
     "The business is located in a permanent structure in a fixed location.",
     "L’entreprise doit être située dans une structure permanente à un emplacement fixe."),
    ("F2", "facility",
     "Procedures and equipment are in place for the safe handling, storage, and disposal or recycling of hazardous materials.",
     "L’établissement doit disposer de procédures et d’équipement pour la manipulation, le stockage, et l’élimination ou le recyclage sécuritaires des matériaux dangereux."),
    ("F3", "facility",
     "A four-point anchoring system that holds vehicles stationary during structural pulls, and a two-point electric/hydraulic pulling system designed for structural pulling.",
     "Avoir un système d’ancrage à quatre points capable de maintenir les véhicules immobiles pendant les tirages structurels, et un système de tirage électrique/hydraulique à deux points conçu pour les tirages structurels."),
    ("F4", "facility",
     "Electronic equipment capable of simultaneous three-dimensional measuring, with print-out ability.",
     "Disposer d’un équipement électronique capable d’effectuer des mesures tridimensionnelles simultanées avec possibilité d’impression."),
    ("F5", "facility",
     "A 200 amp, 220 volt MIG/MAG welder with a minimum 35 per cent duty cycle.",
     "Disposer d’un poste à souder MIG/MAG de 200 AMP, 220 Volts, avec un cycle de service minimal de 35 pour cent."),
    ("F6", "facility",
     "A pulse MIG/MAG welder with silicon bronze / MIG brazing capability.",
     "Disposer d’un poste à souder MIG/MAG à impulsions avec capacité de brasage au bronze‑silicium / MIG."),
    ("F7", "facility",
     "A 220 volt, three-phase inverter-type squeeze-type resistance spot welder (STRSW) capable of 600 lbf (270 daN) clamp force and 10,000 amps at the electrodes.",
     "Disposer d’un poste de soudage de résistance par points (Spot Welder) type STRSW à onduleur triphasé de 220 Volts, capable d’une force de serrage de 600 lbf (270 daN) et de 10 000 AMPères aux électrodes."),
    ("F8", "facility",
     "The ability to safely inspect and analyze vehicle damage, including the underside.",
     "Avoir la capacité de faciliter en toute sécurité l’inspection et l’analyse des dommages du véhicule, y compris le dessous."),
    ("F9", "facility",
     "The ability, or a qualified sublet provider, to remove and install suspension systems, subframes, engines, axles, transaxles, transmissions and other items needed for structural repairs.",
     "Capacité ou preuve d’un fournisseur sous‑contrat qualifié pour retirer / installer les systèmes de suspension, châssis auxiliaires (sub frames), moteurs, essieux, transmissions ou autres composants pour faciliter les réparations structurelles."),
    ("F10", "facility",
     "Equipment and training, or a qualified sublet provider, to recover and recycle all automotive refrigerants on all vehicles.",
     "Équipement et formation ou preuve d’un fournisseur sous‑contrat qualifié pour récupérer/recycler tous les réfrigérants automobiles sur tous les véhicules."),
    ("F11", "facility",
     "Equipment and training, or a qualified sublet provider, to perform four-wheel alignments.",
     "Équipement et formation ou preuve d’un fournisseur sous‑contrat qualifié pour effectuer l’alignement des 4 roues."),
    ("F12", "facility",
     "An enclosed paint booth, paint mixing area and painting respirator system that meet current federal, provincial and municipal laws and bylaws.",
     "Disposer d’une cabine de peinture fermée et d’une aire de mélange de peinture, et d’un système de respirateur de peinture qui respectent toutes les lois et règlements fédéraux, provinciaux et municipaux en vigueur."),
    ("F13", "facility",
     "Equipment and training, or a qualified sublet provider, to perform fixed glass removal and installation.",
     "Équipement et formation ou preuve d’un fournisseur sous‑contrat qualifié pour effectuer la dépose et le montage de vitrage fixe."),
    ("F14", "facility",
     "Training and equipment, or a qualified sublet provider, to complete post-repair ADAS calibrations.",
     "Formation et équipement ou preuve d’un fournisseur sous‑contrat qualifié pour compléter les calibrations des systèmes avancés d’aide à la conduite (SAAC) après réparation."),
    ("F15", "facility",
     "Training and equipment to perform pre- and post-repair vehicle scans, with the ability to print them out.",
     "Disposer de la formation et de l’équipement pour effectuer des scans du véhicule avant et après réparation avec possibilité d’impression."),
    ("P1", "process",
     "Access to vehicle maker (OEM) collision repair procedures for all elements of the repair, including ADAS calibration requirements, for any vehicle being worked on.",
     "Avoir accès aux procédures de réparation de carrosserie des constructeurs (FÉO) pour tous les éléments de la réparation, y compris les exigences de calibration ADAS pour tout véhicule en cours de réparation."),
    ("P2", "process",
     "Access to OEM structural and wheel alignment dimensions (frame rails, strut towers, lower body, floor pans, upper body, camber, caster and steering axis inclination) for any vehicle being worked on.",
     "Avoir accès aux dimensions structurelles et angles d’alignement des roues des constructeurs (FÉO), incluant mais non limité à rails de châssis, tours d’amortisseur, parties inférieures de la carrosserie, planchers, partie supérieure de la carrosserie, inclinaison de la roue (camber), chasse (caster) et inclinaison de l’axe de direction, pour tout véhicule en cours de réparation."),
    ("P3", "process",
     "A robust quality control system focused on safe, quality repairs and adherence to OEM repair standards.",
     "Avoir un système de contrôle de la qualité robuste axé sur l’achèvement de réparations sûres et de qualité et le respect des normes de réparation des FÉO."),
    ("P4", "process",
     "A dedicated process to document that OEM repair procedures were researched and followed, and that structural dimensions were restored.",
     "Disposer d’un processus dédié pour documenter que les procédures de réparation des FÉO ont été recherchées et suivies, et que les dimensions structurelles du véhicule ont été restaurées."),
    ("P5", "process",
     "A dedicated process to document that pre- and post-repair scans and required ADAS calibrations were completed as per OEM recommendations.",
     "Disposer d’un processus dédié pour documenter que les scans avant et après réparation ainsi que les calibrations SAAC requises ont été complétés selon les recommandations des FÉO."),
    ("P6", "process",
     "A written policy on, and the ability to maintain, a limited lifetime workmanship warranty on all repairs (parts excluded).",
     "Avoir une politique écrite, et la capacité de maintenir une garantie à vie limitée relative à la qualité du travail sur toutes les réparations (pièces exclues)."),
]
SECTIONS = ["business", "training", "facility", "process"]
_SECTION_LABELS = {"business": "Business", "training": "Training", "facility": "Facility and equipment", "process": "Repair process"}
REQ_BY_ID = {r[0]: r for r in REQS}
ANSWERS = {"yes": "Yes", "no": "No", "unsure": "Not sure"}


def section_label(key):
    return t(_SECTION_LABELS[key])


def req_text(r):
    return r[3] if lang() == "fr" else r[2]


def answer_label(key):
    return t(ANSWERS.get(key, "Unanswered"))


def statement_name():
    return t("AIA Canada's 2025 Statement on minimum Canadian standards in collision repair")


# Who confirms each credential. "oec" brands are checked automatically on CPN Auto Body Locator.
ADMINS = {
    "icar": {"name": "I-CAR Canada", "lookup": "https://www.aiacanada.com/programs/i-car-canada/", "lookup_label": "Open I-CAR Canada",
             "how": "Confirm current Gold Class® status with I-CAR Canada."},
    "oec": {"name": "OEC Certified Collision Care", "lookup": "https://autobodylocator.ca/canada", "lookup_label": "Open CPN Auto Body Locator",
            "how": "Checked automatically on CPN Auto Body Locator. If it is here, the automated check needs a person: search {make} near {postal} and confirm the shop's name and address appear."},
    "mitchell": {"name": "Mitchell (GM Canada program administrator)", "lookup": "https://www.mitchell.com/solutions/oem-network-solutions/gm-canada",
                 "lookup_label": "Open Mitchell GM Canada network", "how": "Confirm enrolment in the GM Canada Collision Repair Network with Mitchell, using the program ID the shop provided."},
    "none": {"name": "Administrator not yet mapped", "lookup": None, "lookup_label": None,
             "how": "Confirm the certificate number and expiry with the manufacturer or its program administrator."},
}

PROGRAMS = {"icar-gold": ("I-CAR® Gold Class®", "icar"), "gm": ("GM Canada Collision Repair Network", "mitchell")}
for _pid, _name in [("ford", "Ford"), ("stellantis", "Stellantis (Chrysler, Dodge, Jeep, Ram)"), ("kia", "Kia"), ("nissan", "Nissan"),
                    ("infiniti", "INFINITI"), ("toyota", "Toyota"), ("lexus", "Lexus"), ("honda", "Honda"), ("acura", "Acura"),
                    ("hyundai", "Hyundai"), ("genesis", "Genesis"), ("subaru", "Subaru"), ("vinfast", "VinFast")]:
    PROGRAMS[_pid] = (_name, "oec")
for _name in ["Audi", "BMW", "Jaguar Land Rover", "Mazda", "Mercedes-Benz", "MINI", "Mitsubishi", "Polestar", "Porsche", "Rivian",
              "Tesla", "Volkswagen", "Volvo"]:
    PROGRAMS["".join(c if c.isalnum() else "-" for c in _name.lower())] = (_name, "none")
PROGRAMS["other"] = ("Other program", "none")

_PROVINCES = {
    "AB": ("Alberta", "Alberta"), "BC": ("British Columbia", "Colombie-Britannique"), "MB": ("Manitoba", "Manitoba"),
    "NB": ("New Brunswick", "Nouveau-Brunswick"), "NL": ("Newfoundland and Labrador", "Terre-Neuve-et-Labrador"),
    "NS": ("Nova Scotia", "Nouvelle-Écosse"), "NT": ("Northwest Territories", "Territoires du Nord-Ouest"), "NU": ("Nunavut", "Nunavut"),
    "ON": ("Ontario", "Ontario"), "PE": ("Prince Edward Island", "Île-du-Prince-Édouard"), "QC": ("Quebec", "Québec"),
    "SK": ("Saskatchewan", "Saskatchewan"), "YT": ("Yukon", "Yukon"),
}
PROVINCES = list(_PROVINCES)
SCOPES = ["Structural repair", "Aluminum repair", "Glass", "ADAS calibration in-house", "Refinish only"]  # stored in English
STEPS = ["Facility", "Requirements", "Credentials", "Review and guidance", "Declare"]


def province_name(code):
    p = _PROVINCES.get(code)
    return (p[1] if lang() == "fr" else p[0]) if p else (code or "")


def program_name(claim_or_id, other_name=None):
    if isinstance(claim_or_id, dict):
        pid, other_name = claim_or_id.get("program"), claim_or_id.get("other_name")
    else:
        pid = claim_or_id
    if pid == "other":
        return other_name or t("Other program")
    return t(PROGRAMS.get(pid, (pid, "none"))[0])


def program_admin(pid):
    return ADMINS[PROGRAMS.get(pid, (pid, "none"))[1]]


def admin_name(pid):
    return t(program_admin(pid)["name"])
