from typing import List
from pydantic import BaseModel


class FarmerProfile(BaseModel):
    state: str
    land_acres: float
    category: str
    annual_income: float
    crop_type: str
    has_bank_account: bool
    has_aadhaar: bool


# ── Helper ─────────────────────────────────────────────
KHARIF_CROPS  = ["rice", "cotton", "maize", "sugarcane", "groundnut", "soybean"]
RABI_CROPS    = ["wheat", "pulses", "mustard", "barley", "gram"]
ALL_CROPS     = KHARIF_CROPS + RABI_CROPS


SCHEMES = [
    {
        "id": "pm_kisan",
        "name": "PM-KISAN",
        "full_name": "Pradhan Mantri Kisan Samman Nidhi",
        "benefit": "₹6,000/year in 3 installments directly to bank account",
        "ministry": "Ministry of Agriculture",
        "documents": ["Aadhaar Card", "Land record (Khatauni)",
                      "Bank passbook", "Mobile linked to Aadhaar"],
        "apply_at": "pmkisan.gov.in or nearest CSC centre",
        "not_eligible_reason": "Only for farmers with land between 0-5 acres",
        "check": lambda p: (
            p.has_aadhaar and
            p.has_bank_account and
            0 < p.land_acres <= 5
        )
    },
    {
        "id": "pmfby_kharif",
        "name": "PMFBY (Kharif)",
        "full_name": "Pradhan Mantri Fasal Bima Yojana — Kharif Season",
        "benefit": "Crop insurance at only 2% premium for Kharif crops (rice, maize, cotton etc.)",
        "ministry": "Ministry of Agriculture",
        "documents": ["Aadhaar Card", "Land record / Khasra",
                      "Bank passbook", "Sowing certificate"],
        "apply_at": "pmfby.gov.in or your bank branch",
        "not_eligible_reason": "Only for Kharif crops (rice, cotton, maize, sugarcane)",
        "check": lambda p: (
            p.has_aadhaar and
            p.land_acres > 0 and
            p.crop_type.lower() in KHARIF_CROPS
        )
    },
    {
        "id": "pmfby_rabi",
        "name": "PMFBY (Rabi)",
        "full_name": "Pradhan Mantri Fasal Bima Yojana — Rabi Season",
        "benefit": "Crop insurance at only 1.5% premium for Rabi crops (wheat, pulses etc.)",
        "ministry": "Ministry of Agriculture",
        "documents": ["Aadhaar Card", "Land record / Khasra",
                      "Bank passbook", "Sowing certificate"],
        "apply_at": "pmfby.gov.in or your bank branch",
        "not_eligible_reason": "Only for Rabi crops (wheat, pulses, mustard, gram)",
        "check": lambda p: (
            p.has_aadhaar and
            p.land_acres > 0 and
            p.crop_type.lower() in RABI_CROPS
        )
    },
    {
        "id": "kcc",
        "name": "Kisan Credit Card",
        "full_name": "Kisan Credit Card Scheme",
        "benefit": "Credit up to ₹3 lakh at 4% interest for farming expenses",
        "ministry": "RBI / NABARD",
        "documents": ["Aadhaar Card", "Land ownership proof",
                      "Passport size photo", "Bank account details"],
        "apply_at": "Any nationalized bank or cooperative bank",
        "not_eligible_reason": "Annual income must be below ₹3 lakh",
        "check": lambda p: (
            p.has_aadhaar and
            p.land_acres >= 0.5 and
            p.has_bank_account and
            p.annual_income <= 300000
        )
    },
    {
        "id": "smam",
        "name": "SMAM Subsidy",
        "full_name": "Sub-Mission on Agricultural Mechanisation",
        "benefit": "Up to 50% subsidy on farm machinery for small & marginal farmers",
        "ministry": "Ministry of Agriculture",
        "documents": ["Aadhaar Card", "Land record",
                      "Caste certificate (SC/ST)", "Bank passbook"],
        "apply_at": "agrimachinery.nic.in",
        "not_eligible_reason": "Only for farmers with less than 5 acres of land",
        "check": lambda p: (
            p.land_acres > 0 and
            p.land_acres < 5 and
            p.has_aadhaar
        )
    },
    {
        "id": "soil_health",
        "name": "Soil Health Card",
        "full_name": "Soil Health Card Scheme",
        "benefit": "Free soil testing + personalised fertilizer recommendation",
        "ministry": "Ministry of Agriculture",
        "documents": ["Aadhaar Card", "Land details"],
        "apply_at": "soilhealth.dac.gov.in or nearest agriculture office",
        "not_eligible_reason": "Requires land ownership",
        "check": lambda p: p.land_acres > 0
    },
    {
        "id": "enam",
        "name": "eNAM",
        "full_name": "National Agriculture Market",
        "benefit": "Sell crops online at best price across India, transparent bidding",
        "ministry": "Ministry of Agriculture",
        "documents": ["Aadhaar Card", "Bank passbook", "Mobile number"],
        "apply_at": "enam.gov.in or nearest APMC mandi",
        "not_eligible_reason": "Requires at least 1 acre of land to sell surplus",
        "check": lambda p: (
            p.has_aadhaar and
            p.has_bank_account and
            p.land_acres >= 1
        )
    },
    {
        "id": "pmkmy",
        "name": "PM-KMY",
        "full_name": "Pradhan Mantri Kisan Maandhan Yojana",
        "benefit": "₹3,000/month pension after age 60 for small & marginal farmers",
        "ministry": "Ministry of Agriculture",
        "documents": ["Aadhaar Card", "Bank passbook",
                      "Land record", "Age proof"],
        "apply_at": "maandhan.in or nearest CSC centre",
        "not_eligible_reason": "Only for farmers with ≤2 acres land and income ≤₹1 lakh",
        "check": lambda p: (
            p.has_aadhaar and
            p.has_bank_account and
            p.land_acres <= 2 and
            p.annual_income <= 100000
        )
    },
    {
        "id": "cotton_mission",
        "name": "Cotton Mission",
        "full_name": "National Mission on Cotton Technology",
        "benefit": "Free high-yield cotton seeds + technical training for cotton farmers",
        "ministry": "Ministry of Textiles",
        "documents": ["Aadhaar Card", "Land record", "Bank passbook"],
        "apply_at": "Nearest Krishi Vigyan Kendra or agriculture office",
        "not_eligible_reason": "Only for cotton farmers",
        "check": lambda p: (
            p.has_aadhaar and
            p.crop_type.lower() == "cotton" and
            p.land_acres >= 1
        )
    },
    {
        "id": "sugarcane_frp",
        "name": "Sugarcane FRP",
        "full_name": "Fair and Remunerative Price for Sugarcane",
        "benefit": "Guaranteed minimum price (FRP) for sugarcane by government",
        "ministry": "Ministry of Consumer Affairs",
        "documents": ["Aadhaar Card", "Land record",
                      "Bank passbook", "Sugar mill registration"],
        "apply_at": "Nearest sugar mill or agriculture office",
        "not_eligible_reason": "Only for sugarcane farmers",
        "check": lambda p: (
            p.crop_type.lower() == "sugarcane" and
            p.has_aadhaar and
            p.land_acres >= 0.5
        )
    },
    {
        "id": "pulses_mission",
        "name": "Pulses Mission",
        "full_name": "National Food Security Mission — Pulses",
        "benefit": "Free certified seeds, fertilizer subsidy, and training for pulse farmers",
        "ministry": "Ministry of Agriculture",
        "documents": ["Aadhaar Card", "Land record", "Bank passbook"],
        "apply_at": "Nearest Krishi Vigyan Kendra or Block Agriculture Office",
        "not_eligible_reason": "Only for pulse crop farmers (arhar, moong, urad, chana)",
        "check": lambda p: (
            p.has_aadhaar and
            p.crop_type.lower() == "pulses" and
            p.land_acres > 0
        )
    },
    {
        "id": "maize_mission",
        "name": "Maize Mission",
        "full_name": "National Food Security Mission — Maize",
        "benefit": "Subsidised hybrid maize seeds + ₹5,000/acre support for maize farmers",
        "ministry": "Ministry of Agriculture",
        "documents": ["Aadhaar Card", "Land record", "Bank passbook"],
        "apply_at": "Nearest Block Agriculture Office or KVK",
        "not_eligible_reason": "Only for maize farmers",
        "check": lambda p: (
            p.has_aadhaar and
            p.crop_type.lower() == "maize" and
            p.land_acres > 0
        )
    },
    {
        "id": "wheat_msp",
        "name": "Wheat MSP",
        "full_name": "Minimum Support Price — Wheat Procurement",
        "benefit": "Guaranteed MSP of ₹2,275/quintal for wheat directly from government",
        "ministry": "Ministry of Food & Consumer Affairs",
        "documents": ["Aadhaar Card", "Land record",
                      "Bank passbook", "Farmer registration on mandi portal"],
        "apply_at": "Nearest government procurement centre or mandi",
        "not_eligible_reason": "Only for wheat farmers",
        "check": lambda p: (
            p.crop_type.lower() == "wheat" and
            p.has_aadhaar and
            p.has_bank_account and
            p.land_acres > 0
        )
    },
    {
        "id": "rice_msp",
        "name": "Rice MSP",
        "full_name": "Minimum Support Price — Paddy Procurement",
        "benefit": "Guaranteed MSP of ₹2,183/quintal for paddy directly from government",
        "ministry": "Ministry of Food & Consumer Affairs",
        "documents": ["Aadhaar Card", "Land record",
                      "Bank passbook", "Farmer registration on mandi portal"],
        "apply_at": "Nearest government procurement centre or mandi",
        "not_eligible_reason": "Only for rice/paddy farmers",
        "check": lambda p: (
            p.crop_type.lower() == "rice" and
            p.has_aadhaar and
            p.has_bank_account and
            p.land_acres > 0
        )
    },
]


def check_eligibility(profile: FarmerProfile) -> List[dict]:
    results = []
    for scheme in SCHEMES:
        try:
            is_eligible = scheme["check"](profile)
        except Exception:
            is_eligible = False

        results.append({
            "id":                   scheme["id"],
            "name":                 scheme["name"],
            "full_name":            scheme["full_name"],
            "benefit":              scheme["benefit"],
            "ministry":             scheme["ministry"],
            "documents":            scheme["documents"],
            "apply_at":             scheme["apply_at"],
            "not_eligible_reason":  scheme.get("not_eligible_reason", ""),
            "eligible":             is_eligible,
        })

    results.sort(key=lambda x: x["eligible"], reverse=True)
    return results