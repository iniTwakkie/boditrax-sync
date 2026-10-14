"""Boditrax ``BodyMetricTypeId`` -> metric name and unit.

Names match the Boditrax app's own CSV export. Units follow the metric's
native scale; ``Gender`` is a numeric code (see the app) and score-type
metrics are unit-less.
"""

METRICS: dict[int, tuple[str, str]] = {
    1: ("BodyWeight", "kg"),
    2: ("FatPercentage", "%"),
    3: ("FatMass", "kg"),
    4: ("FatFreeMass", "kg"),
    5: ("MuscleMass", "kg"),
    6: ("MuscleScore", "score"),
    7: ("BoneMass", "kg"),
    8: ("WaterMass", "kg"),
    10: ("BodyMassIndex", "bmi"),
    12: ("VisceralFatRating", "rating"),
    13: ("BasalMetabolicRatekJ", "kJ"),
    14: ("BmrScore", "score"),
    15: ("MetabolicAge", "years"),
    18: ("Age", "years"),
    25: ("Height", "cm"),
    30: ("LegMuscleScore", "score"),
    40: ("ExtraCellularWaterMass", "kg"),
    42: ("IntraCellularWaterMass", "kg"),
    46: ("TrunkFatMass", "kg"),
    49: ("TrunkMuscleMass", "kg"),
    56: ("LeftArmFatMass", "kg"),
    59: ("LeftArmMuscleMass", "kg"),
    61: ("RightArmFatMass", "kg"),
    64: ("RightArmMuscleMass", "kg"),
    66: ("LeftLegFatMass", "kg"),
    69: ("LeftLegMuscleMass", "kg"),
    71: ("RightLegFatMass", "kg"),
    74: ("RightLegMuscleMass", "kg"),
    75: ("RightLegMuscleMassScore", "score"),
    76: ("PhaseAngleRightLegLeftLeg", "degrees"),
    77: ("PhaseAngleLeftLegLeftArm", "degrees"),
    78: ("PhaseAngleRightLeg", "degrees"),
    79: ("PhaseAngleLeftLeg", "degrees"),
    80: ("PhaseAngleRightArm", "degrees"),
    81: ("PhaseAngleLeftArm", "degrees"),
    83: ("PhaseAngleRightLegRightArm", "degrees"),
    88: ("RestingHeartRate", "bpm"),
    90: ("SystolicPressure", "mmHg"),
    91: ("DiastolicPressure", "mmHg"),
    172: ("SarcopeniaSMI", "score"),
    173: ("SarcopeniaASMBW", "score"),
    174: ("Protein", "kg"),
    180: ("Gender", "code"),
    182: ("HDLLevel", "mmol/L"),
    183: ("LDLLevel", "mmol/L"),
    184: ("Triglycerides", "mmol/L"),
    185: ("NonHDLLevel", "mmol/L"),
    186: ("TotalCholesterolHDL", "ratio"),
    187: ("TotalCholesterol", "mmol/L"),
    255: ("BoditraxScore", "score"),
}

METRIC_UNITS: dict[str, str] = {name: unit for name, unit in METRICS.values()}

# Metric columns in BodyMetricTypeId order, used by the wide CSV layout.
METRIC_COLUMNS: list[str] = [name for _, (name, _) in sorted(METRICS.items())]
