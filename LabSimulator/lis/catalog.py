"""The lab's own test catalog: fills in unit and range when an order arrives (staff can change them)."""

# LOINC code -> (unit, reference range). Typical adult values, for the demo only.
CATALOG = {
    '1742-6': ('U/L', '7-56'),          # ALT
    '1920-8': ('U/L', '10-40'),         # AST
    '1975-2': ('mg/dL', '0.1-1.2'),     # Total bilirubin
    '1751-7': ('g/dL', '3.5-5.0'),      # Albumin
    '6301-6': ('', '0.8-1.1'),          # INR (no unit)
    '2160-0': ('mg/dL', '0.6-1.3'),     # Creatinine
    '2951-2': ('mmol/L', '135-145'),    # Sodium
    '1834-1': ('ng/mL', '0-10'),        # AFP
    '5195-3': ('index', '0-0.9'),       # HBsAg
    '13955-0': ('index', '0-0.9'),      # HCV antibody
}


def defaults_for(code):
    return CATALOG.get(code, ('', ''))
