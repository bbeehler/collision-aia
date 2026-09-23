"""Content and program settings for Check and Declare. Requirement IDs must match supabase required_ids()."""

STATEMENT_VERSION = "2025 Statement (published September 2025)"
DECLARATION_DAYS = 365
RENEW_WINDOW_DAYS = 90

REQS = [
    ("B1", "Business", "Adhere to all applicable federal, provincial and municipal acts, regulations and standards, including health and safety, environmental, zoning, business licensing and permits, apprenticeship and trade licensing, and consumer privacy and protection."),
    ("B2", "Business", "Maintain a Garage Liability insurance policy with at least $2,000,000 CAD in coverage."),
    ("B3", "Business", "Maintain liability coverage when using a sublet vendor."),
    ("B4", "Business", "Maintain an electronic management system to track customer information, repair orders, parts inventory and usage, estimates, invoices and compliance documentation."),
    ("T1", "Training", "Each technician holds a Certificate of Qualification relevant to their role, or is a registered apprentice, where mandated provincially or territorially."),
    ("T2", "Training", "The shop maintains I-CAR Canada Gold Class status, through I-CAR Canada or recognized Training Alliance Partners."),
    ("F1", "Facility and equipment", "The business is located in a permanent structure in a fixed location."),
    ("F2", "Facility and equipment", "Procedures and equipment are in place for the safe handling, storage, and disposal or recycling of hazardous materials."),
    ("F3", "Facility and equipment", "A four-point anchoring system that holds vehicles stationary during structural pulls, and a two-point electric/hydraulic pulling system designed for structural pulling."),
    ("F4", "Facility and equipment", "Electronic equipment capable of simultaneous three-dimensional measuring, with print-out ability."),
    ("F5", "Facility and equipment", "A 200 amp, 220 volt MIG/MAG welder with a minimum 35 per cent duty cycle."),
    ("F6", "Facility and equipment", "A pulse MIG/MAG welder with silicon bronze / MIG brazing capability."),
    ("F7", "Facility and equipment", "A 220 volt, three-phase inverter-type squeeze-type resistance spot welder (STRSW) capable of 600 lbf (270 daN) clamp force and 10,000 amps at the electrodes."),
    ("F8", "Facility and equipment", "The ability to safely inspect and analyze vehicle damage, including the underside."),
    ("F9", "Facility and equipment", "The ability, or a qualified sublet provider, to remove and install suspension systems, subframes, engines, axles, transaxles, transmissions and other items needed for structural repairs."),
    ("F10", "Facility and equipment", "Equipment and training, or a qualified sublet provider, to recover and recycle all automotive refrigerants on all vehicles."),
    ("F11", "Facility and equipment", "Equipment and training, or a qualified sublet provider, to perform four-wheel alignments."),
    ("F12", "Facility and equipment", "An enclosed paint booth, paint mixing area and painting respirator system that meet current federal, provincial and municipal laws and bylaws."),
    ("F13", "Facility and equipment", "Equipment and training, or a qualified sublet provider, to perform fixed glass removal and installation."),
    ("F14", "Facility and equipment", "Training and equipment, or a qualified sublet provider, to complete post-repair ADAS calibrations."),
    ("F15", "Facility and equipment", "Training and equipment to perform pre- and post-repair vehicle scans, with the ability to print them out."),
    ("P1", "Repair process", "Access to vehicle maker (OEM) collision repair procedures for all elements of the repair, including ADAS calibration requirements, for any vehicle being worked on."),
    ("P2", "Repair process", "Access to OEM structural and wheel alignment dimensions (frame rails, strut towers, lower body, floor pans, upper body, camber, caster and steering axis inclination) for any vehicle being worked on."),
    ("P3", "Repair process", "A robust quality control system focused on safe, quality repairs and adherence to OEM repair standards."),
    ("P4", "Repair process", "A dedicated process to document that OEM repair procedures were researched and followed, and that structural dimensions were restored."),
    ("P5", "Repair process", "A dedicated process to document that pre- and post-repair scans and required ADAS calibrations were completed as per OEM recommendations."),
    ("P6", "Repair process", "A written policy on, and the ability to maintain, a limited lifetime workmanship warranty on all repairs (parts excluded)."),
]
SECTIONS = ["Business", "Training", "Facility and equipment", "Repair process"]
REQ_BY_ID = {r[0]: r for r in REQS}
ANSWERS = {"yes": "Yes", "no": "No", "unsure": "Not sure"}

# Who confirms each credential. The verifier checks the "oec" brands automatically (see verifier/settings.py).
ADMINS = {
    "icar": {"name": "I-CAR Canada", "lookup": "https://www.aiacanada.com/programs/i-car-canada/", "lookup_label": "Open I-CAR Canada",
             "how": "Confirm current Gold Class status with I-CAR Canada."},
    "oec": {"name": "OEC Certified Collision Care", "lookup": "https://autobodylocator.ca/canada", "lookup_label": "Open CPN Auto Body Locator",
            "how": "Checked automatically on CPN Auto Body Locator. If it's here, the automated check needs a person: search {make} near {postal} and confirm the shop's name and address appear."},
    "mitchell": {"name": "Mitchell (GM Canada program administrator)", "lookup": "https://www.mitchell.com/solutions/oem-network-solutions/gm-canada",
                 "lookup_label": "Open Mitchell GM Canada network", "how": "Confirm enrolment in the GM Canada Collision Repair Network with Mitchell, using the program ID the shop provided."},
    "none": {"name": "Administrator not yet mapped", "lookup": None, "lookup_label": None,
             "how": "Confirm the certificate number and expiry with the manufacturer or its program administrator."},
}

PROGRAMS = {"icar-gold": ("I-CAR Gold Class", "icar"), "gm": ("GM Canada Collision Repair Network", "mitchell")}
for _pid, _name in [("ford", "Ford"), ("stellantis", "Stellantis (Chrysler, Dodge, Jeep, Ram)"), ("kia", "Kia"), ("nissan", "Nissan"),
                    ("infiniti", "INFINITI"), ("toyota", "Toyota"), ("lexus", "Lexus"), ("honda", "Honda"), ("acura", "Acura"), ("hyundai", "Hyundai"),
                    ("genesis", "Genesis"), ("subaru", "Subaru"), ("vinfast", "VinFast")]:
    PROGRAMS[_pid] = (_name, "oec")
for _name in ["Audi", "BMW", "Jaguar Land Rover", "Mazda", "Mercedes-Benz", "MINI", "Mitsubishi", "Polestar", "Porsche", "Rivian",
              "Tesla", "Volkswagen", "Volvo"]:
    PROGRAMS["".join(c if c.isalnum() else "-" for c in _name.lower())] = (_name, "none")
PROGRAMS["other"] = ("Other program", "none")

PROVINCES = {"AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick", "NL": "Newfoundland and Labrador",
             "NS": "Nova Scotia", "NT": "Northwest Territories", "NU": "Nunavut", "ON": "Ontario", "PE": "Prince Edward Island",
             "QC": "Quebec", "SK": "Saskatchewan", "YT": "Yukon"}
SCOPES = ["Structural repair", "Aluminum repair", "Glass", "ADAS calibration in-house", "Refinish only"]
STEPS = ["Facility", "Requirements", "Credentials", "Review and guidance", "Declare"]


def program_name(claim_or_id, other_name=None):
    if isinstance(claim_or_id, dict):
        pid, other_name = claim_or_id.get("program"), claim_or_id.get("other_name")
    else:
        pid = claim_or_id
    if pid == "other":
        return other_name or "Other program"
    return PROGRAMS.get(pid, (pid, "none"))[0]


def program_admin(pid):
    return ADMINS[PROGRAMS.get(pid, (pid, "none"))[1]]
