"""Unified seed script — wipe & rebuild all dev data.

Usage:
    cd backend && uv run python scripts/seed.py

Creates:
  - 3 users (admin, pharmacist, agent)
  - 80 drugs (common Rx across categories)
  - 12 patients with demographics, allergies, conditions
  - 29 prescriptions (manual, mixed statuses incl. 3 rejections + Ibuprofen HIGH-RISK demo)
  - 5 e-prescribe XMLs ingested through the real pipeline (PARSED → worker → PENDING_REVIEW)
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text

from arxi.auth.models import Role, User
from arxi.auth.service import AuthService
from arxi.database import async_session
from arxi.modules.drug.models import Drug
from arxi.modules.intake.models import Prescription, RxStatus
from arxi.modules.intake.service import IntakeService
from arxi.modules.patient.models import Patient

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("seed")

# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------

USERS = [
    {"username": "admin", "password": "admin123", "full_name": "Admin User", "role": Role.ADMIN},
    {"username": "pharmacist", "password": "pharma123", "full_name": "Dr. Sarah Chen, PharmD", "role": Role.PHARMACIST},
    {"username": "agent", "password": "agent123", "full_name": "System Agent", "role": Role.AGENT},
]

PATIENTS = [
    # 0: Maria Johnson — HTN, Hyperlipidemia, T2DM
    {"first_name": "Maria", "last_name": "Johnson", "gender": "F", "date_of_birth": "1984-09-09", "address_line1": "123 Main St", "city": "Miami", "state": "FL", "postal_code": "33101",
     "allergies": [{"substance": "Sulfa drugs", "reaction": "rash", "severity": "moderate"}],
     "conditions": ["Hypertension", "Hyperlipidemia", "Type 2 Diabetes"]},
    # 1: James Rodriguez — Diabetes, HTN
    {"first_name": "James", "last_name": "Rodriguez", "gender": "M", "date_of_birth": "1972-03-15", "address_line1": "456 Oak Ave", "city": "Houston", "state": "TX", "postal_code": "77001",
     "allergies": [],
     "conditions": ["Type 2 Diabetes", "Hypertension"]},
    # 2: Linda Chen — GAD, Insomnia
    {"first_name": "Linda", "last_name": "Chen", "gender": "F", "date_of_birth": "1990-11-22", "address_line1": "789 Elm Dr", "city": "San Jose", "state": "CA", "postal_code": "95110",
     "allergies": [{"substance": "Penicillin", "reaction": "hives", "severity": "moderate"}],
     "conditions": ["Generalized Anxiety Disorder", "Insomnia"]},
    # 3: Robert Williams — AFib, HF, post-MI, DVT (HIGH-RISK demo patient)
    {"first_name": "Robert", "last_name": "Williams", "gender": "M", "date_of_birth": "1965-06-30", "address_line1": "321 Pine Rd", "city": "Chicago", "state": "IL", "postal_code": "60601",
     "allergies": [{"substance": "ACE Inhibitors", "reaction": "angioedema", "severity": "severe"}],
     "conditions": ["Atrial Fibrillation", "Heart Failure", "History of MI", "Deep Vein Thrombosis"]},
    # 4: Sarah Davis — Migraine, GERD
    {"first_name": "Sarah", "last_name": "Davis", "gender": "F", "date_of_birth": "1988-01-14", "address_line1": "555 Maple Ln", "city": "Phoenix", "state": "AZ", "postal_code": "85001",
     "allergies": [],
     "conditions": ["Migraine", "GERD"]},
    # 5: Michael Brown — Chronic Pain, OA
    {"first_name": "Michael", "last_name": "Brown", "gender": "M", "date_of_birth": "1978-08-05", "address_line1": "142 Cedar St", "city": "Denver", "state": "CO", "postal_code": "80201",
     "allergies": [{"substance": "Codeine", "reaction": "nausea", "severity": "moderate"}],
     "conditions": ["Chronic Back Pain", "Osteoarthritis"]},
    # 6: Jennifer Martinez — Asthma, Allergic Rhinitis
    {"first_name": "Jennifer", "last_name": "Martinez", "gender": "F", "date_of_birth": "1995-04-19", "address_line1": "678 Birch Blvd", "city": "Atlanta", "state": "GA", "postal_code": "30301",
     "allergies": [{"substance": "Aspirin", "reaction": "bronchospasm", "severity": "severe"}],
     "conditions": ["Persistent Asthma", "Allergic Rhinitis"]},
    # 7: David Anderson — Gout, BPH
    {"first_name": "David", "last_name": "Anderson", "gender": "M", "date_of_birth": "1960-12-01", "address_line1": "234 Walnut Way", "city": "Seattle", "state": "WA", "postal_code": "98101",
     "allergies": [],
     "conditions": ["Gout", "Benign Prostatic Hyperplasia"]},
    # 8: Patricia Taylor — Hypothyroid, MDD
    {"first_name": "Patricia", "last_name": "Taylor", "gender": "F", "date_of_birth": "1982-07-28", "address_line1": "890 Spruce Ct", "city": "Nashville", "state": "TN", "postal_code": "37201",
     "allergies": [{"substance": "Ibuprofen", "reaction": "GI bleeding", "severity": "severe"}],
     "conditions": ["Hypothyroidism", "Major Depressive Disorder"]},
    # 9: Anthony Thomas — Anticoagulation
    {"first_name": "Anthony", "last_name": "Thomas", "gender": "M", "date_of_birth": "1975-10-11", "address_line1": "567 Willow Dr", "city": "Portland", "state": "OR", "postal_code": "97201",
     "allergies": [],
     "conditions": ["Atrial Fibrillation"]},
    # 10: Karen Garcia — Recurrent UTI, Anxiety
    {"first_name": "Karen", "last_name": "Garcia", "gender": "F", "date_of_birth": "1993-02-08", "address_line1": "345 Aspen Pl", "city": "Austin", "state": "TX", "postal_code": "73301",
     "allergies": [{"substance": "Cephalosporins", "reaction": "rash", "severity": "mild"}],
     "conditions": ["Recurrent UTI", "Anxiety"]},
    # 11: William Lee — GERD, Seasonal Allergies, HTN
    {"first_name": "William", "last_name": "Lee", "gender": "M", "date_of_birth": "1968-05-25", "address_line1": "901 Hickory Ave", "city": "Boston", "state": "MA", "postal_code": "02101",
     "allergies": [{"substance": "Penicillin", "reaction": "anaphylaxis", "severity": "severe"}, {"substance": "Latex", "reaction": "contact dermatitis", "severity": "mild"}],
     "conditions": ["GERD", "Seasonal Allergies", "Hypertension"]},
]

DRUGS = [
    # Cardiovascular
    ("Lisinopril 10mg Tablets", "00093-7180-01", "Lisinopril", "Tablet", "10mg", "Oral", "Teva", "", "ACE inhibitor for hypertension"),
    ("Lisinopril 20mg Tablets", "00093-7181-01", "Lisinopril", "Tablet", "20mg", "Oral", "Teva", "", ""),
    ("Amlodipine 5mg Tablets", "00093-3165-01", "Amlodipine Besylate", "Tablet", "5mg", "Oral", "Teva", "", ""),
    ("Amlodipine 10mg Tablets", "00093-3166-01", "Amlodipine Besylate", "Tablet", "10mg", "Oral", "Teva", "", ""),
    ("Losartan 50mg Tablets", "00093-7367-01", "Losartan Potassium", "Tablet", "50mg", "Oral", "Teva", "", ""),
    ("Losartan 100mg Tablets", "00093-7368-01", "Losartan Potassium", "Tablet", "100mg", "Oral", "Teva", "", ""),
    ("Metoprolol Succinate ER 25mg", "00378-0181-01", "Metoprolol Succinate", "Tablet, ER", "25mg", "Oral", "Mylan", "", ""),
    ("Metoprolol Succinate ER 50mg", "00378-0182-01", "Metoprolol Succinate", "Tablet, ER", "50mg", "Oral", "Mylan", "", ""),
    ("Hydrochlorothiazide 25mg Tablets", "00591-5512-01", "Hydrochlorothiazide", "Tablet", "25mg", "Oral", "Actavis", "", ""),
    ("Carvedilol 25mg Tablets", "00093-8943-01", "Carvedilol", "Tablet", "25mg", "Oral", "Teva", "", ""),
    # Cholesterol
    ("Atorvastatin 20mg Tablets", "00378-2077-01", "Atorvastatin Calcium", "Tablet", "20mg", "Oral", "Mylan", "", ""),
    ("Atorvastatin 40mg Tablets", "00378-2078-01", "Atorvastatin Calcium", "Tablet", "40mg", "Oral", "Mylan", "", ""),
    ("Rosuvastatin 10mg Tablets", "00591-3764-01", "Rosuvastatin Calcium", "Tablet", "10mg", "Oral", "Actavis", "", ""),
    ("Simvastatin 20mg Tablets", "00093-7155-01", "Simvastatin", "Tablet", "20mg", "Oral", "Teva", "", ""),
    # Diabetes
    ("Metformin 500mg Tablets", "00093-1048-01", "Metformin HCl", "Tablet", "500mg", "Oral", "Teva", "", ""),
    ("Metformin 1000mg Tablets", "00093-1049-01", "Metformin HCl", "Tablet", "1000mg", "Oral", "Teva", "", ""),
    ("Glipizide 5mg Tablets", "00093-0316-01", "Glipizide", "Tablet", "5mg", "Oral", "Teva", "", ""),
    ("Januvia 100mg Tablets", "00006-0277-31", "Sitagliptin", "Tablet", "100mg", "Oral", "Merck", "", ""),
    ("Jardiance 10mg Tablets", "00597-0153-30", "Empagliflozin", "Tablet", "10mg", "Oral", "Boehringer", "", ""),
    # Antibiotics
    ("Amoxicillin 500mg Capsules", "00093-3109-01", "Amoxicillin", "Capsule", "500mg", "Oral", "Teva", "", ""),
    ("Azithromycin 250mg Tablets", "00093-7169-01", "Azithromycin", "Tablet", "250mg", "Oral", "Teva", "", "Z-Pack"),
    ("Ciprofloxacin 500mg Tablets", "00093-0864-01", "Ciprofloxacin HCl", "Tablet", "500mg", "Oral", "Teva", "", ""),
    ("Cephalexin 500mg Capsules", "00093-3147-01", "Cephalexin", "Capsule", "500mg", "Oral", "Teva", "", ""),
    ("Doxycycline 100mg Capsules", "00591-5541-01", "Doxycycline Hyclate", "Capsule", "100mg", "Oral", "Actavis", "", ""),
    ("Augmentin 875mg Tablets", "00093-2274-01", "Amoxicillin/Clavulanate", "Tablet", "875mg", "Oral", "Teva", "", ""),
    # Pain / Anti-inflammatory
    ("Ibuprofen 800mg Tablets", "00591-2040-01", "Ibuprofen", "Tablet", "800mg", "Oral", "Actavis", "", ""),
    ("Naproxen 500mg Tablets", "00093-0149-01", "Naproxen", "Tablet", "500mg", "Oral", "Teva", "", ""),
    ("Meloxicam 15mg Tablets", "00093-0058-01", "Meloxicam", "Tablet", "15mg", "Oral", "Teva", "", ""),
    ("Gabapentin 300mg Capsules", "00093-0215-01", "Gabapentin", "Capsule", "300mg", "Oral", "Teva", "", ""),
    ("Gabapentin 600mg Tablets", "00093-0216-01", "Gabapentin", "Tablet", "600mg", "Oral", "Teva", "", ""),
    ("Cyclobenzaprine 10mg Tablets", "00093-0940-01", "Cyclobenzaprine HCl", "Tablet", "10mg", "Oral", "Teva", "", ""),
    # Controlled (CII)
    ("Oxycodone/APAP 5-325mg Tablets", "00591-0388-01", "Oxycodone/Acetaminophen", "Tablet", "5-325mg", "Oral", "Actavis", "CII", ""),
    ("Adderall XR 20mg Capsules", "00555-0791-02", "Amphetamine/Dextroamphetamine", "Capsule, ER", "20mg", "Oral", "Teva", "CII", ""),
    ("Methylphenidate ER 36mg Tablets", "00591-3754-01", "Methylphenidate HCl", "Tablet, ER", "36mg", "Oral", "Actavis", "CII", ""),
    # Controlled (CIV/CV)
    ("Tramadol 50mg Tablets", "00093-0058-05", "Tramadol HCl", "Tablet", "50mg", "Oral", "Teva", "CIV", ""),
    ("Alprazolam 0.5mg Tablets", "00093-5901-01", "Alprazolam", "Tablet", "0.5mg", "Oral", "Teva", "CIV", ""),
    ("Lorazepam 1mg Tablets", "00093-0832-01", "Lorazepam", "Tablet", "1mg", "Oral", "Teva", "CIV", ""),
    ("Zolpidem 10mg Tablets", "00093-5616-01", "Zolpidem Tartrate", "Tablet", "10mg", "Oral", "Teva", "CIV", ""),
    # Mental Health
    ("Sertraline 50mg Tablets", "00093-7198-01", "Sertraline HCl", "Tablet", "50mg", "Oral", "Teva", "", ""),
    ("Sertraline 100mg Tablets", "00093-7199-01", "Sertraline HCl", "Tablet", "100mg", "Oral", "Teva", "", ""),
    ("Escitalopram 10mg Tablets", "00093-5851-01", "Escitalopram Oxalate", "Tablet", "10mg", "Oral", "Teva", "", ""),
    ("Fluoxetine 20mg Capsules", "00093-7196-01", "Fluoxetine HCl", "Capsule", "20mg", "Oral", "Teva", "", ""),
    ("Bupropion XL 150mg Tablets", "00093-7200-01", "Bupropion HCl", "Tablet, ER", "150mg", "Oral", "Teva", "", ""),
    ("Trazodone 50mg Tablets", "00093-0746-01", "Trazodone HCl", "Tablet", "50mg", "Oral", "Teva", "", ""),
    ("Duloxetine 60mg Capsules", "00093-7234-01", "Duloxetine HCl", "Capsule, DR", "60mg", "Oral", "Teva", "", ""),
    ("Quetiapine 100mg Tablets", "00093-8341-01", "Quetiapine Fumarate", "Tablet", "100mg", "Oral", "Teva", "", ""),
    ("Aripiprazole 10mg Tablets", "00093-5278-01", "Aripiprazole", "Tablet", "10mg", "Oral", "Teva", "", ""),
    # Respiratory
    ("Albuterol HFA Inhaler", "00085-1132-01", "Albuterol Sulfate", "Inhaler", "90mcg/act", "Inhalation", "Teva", "", ""),
    ("Montelukast 10mg Tablets", "00093-7203-01", "Montelukast Sodium", "Tablet", "10mg", "Oral", "Teva", "", ""),
    ("Fluticasone 50mcg Nasal Spray", "00093-0740-01", "Fluticasone Propionate", "Nasal Spray", "50mcg", "Nasal", "Teva", "", ""),
    ("Cetirizine 10mg Tablets", "00904-5852-61", "Cetirizine HCl", "Tablet", "10mg", "Oral", "Major", "", ""),
    # GI
    ("Omeprazole 20mg Capsules", "00093-7207-01", "Omeprazole", "Capsule, DR", "20mg", "Oral", "Teva", "", ""),
    ("Pantoprazole 40mg Tablets", "00093-0108-01", "Pantoprazole Sodium", "Tablet, DR", "40mg", "Oral", "Teva", "", ""),
    ("Famotidine 20mg Tablets", "00093-0275-01", "Famotidine", "Tablet", "20mg", "Oral", "Teva", "", ""),
    ("Ondansetron 4mg Tablets", "00093-7247-01", "Ondansetron", "Tablet, ODT", "4mg", "Oral", "Teva", "", ""),
    # Thyroid
    ("Levothyroxine 50mcg Tablets", "00378-1805-01", "Levothyroxine Sodium", "Tablet", "50mcg", "Oral", "Mylan", "", ""),
    ("Levothyroxine 100mcg Tablets", "00378-1810-01", "Levothyroxine Sodium", "Tablet", "100mcg", "Oral", "Mylan", "", ""),
    # Other
    ("Prednisone 10mg Tablets", "00591-5442-01", "Prednisone", "Tablet", "10mg", "Oral", "Actavis", "", ""),
    ("Prednisone 20mg Tablets", "00591-5443-01", "Prednisone", "Tablet", "20mg", "Oral", "Actavis", "", ""),
    ("Tamsulosin 0.4mg Capsules", "00093-7338-01", "Tamsulosin HCl", "Capsule", "0.4mg", "Oral", "Teva", "", ""),
    ("Finasteride 5mg Tablets", "00093-7205-01", "Finasteride", "Tablet", "5mg", "Oral", "Teva", "", ""),
    ("Allopurinol 300mg Tablets", "00093-0217-01", "Allopurinol", "Tablet", "300mg", "Oral", "Teva", "", ""),
    ("Warfarin 5mg Tablets", "00591-5502-01", "Warfarin Sodium", "Tablet", "5mg", "Oral", "Actavis", "", ""),
    ("Clopidogrel 75mg Tablets", "00093-7340-01", "Clopidogrel Bisulfate", "Tablet", "75mg", "Oral", "Teva", "", ""),
    ("Potassium Cl ER 20mEq Tablets", "00591-0405-01", "Potassium Chloride", "Tablet, ER", "20mEq", "Oral", "Actavis", "", ""),
    ("Furosemide 40mg Tablets", "00591-5460-01", "Furosemide", "Tablet", "40mg", "Oral", "Actavis", "", ""),
    ("Spironolactone 25mg Tablets", "00093-0441-01", "Spironolactone", "Tablet", "25mg", "Oral", "Teva", "", ""),
    ("Linagliptin 5mg Tablets", "00597-0143-30", "Linagliptin", "Tablet", "5mg", "Oral", "Boehringer", "", ""),
    ("Montelukast 5mg Chewable", "00093-7204-01", "Montelukast Sodium", "Tablet, Chewable", "5mg", "Oral", "Teva", "", "Pediatric"),
    ("Amoxicillin 250mg/5ml Suspension", "00093-4153-73", "Amoxicillin", "Suspension", "250mg/5ml", "Oral", "Teva", "", "Pediatric"),
    ("Methotrexate 2.5mg Tablets", "00555-0572-02", "Methotrexate", "Tablet", "2.5mg", "Oral", "Teva", "", ""),
    ("Hydroxychloroquine 200mg Tablets", "00093-0223-01", "Hydroxychloroquine Sulfate", "Tablet", "200mg", "Oral", "Teva", "", ""),
    ("Topiramate 25mg Tablets", "00093-0715-01", "Topiramate", "Tablet", "25mg", "Oral", "Teva", "", ""),
    ("Lamotrigine 100mg Tablets", "00093-0223-05", "Lamotrigine", "Tablet", "100mg", "Oral", "Teva", "", ""),
    ("Buspirone 10mg Tablets", "00093-0816-01", "Buspirone HCl", "Tablet", "10mg", "Oral", "Teva", "", ""),
    ("Propranolol 40mg Tablets", "00093-0573-01", "Propranolol HCl", "Tablet", "40mg", "Oral", "Teva", "", ""),
    ("Clonidine 0.1mg Tablets", "00093-0357-01", "Clonidine HCl", "Tablet", "0.1mg", "Oral", "Teva", "", ""),
    ("Sumatriptan 100mg Tablets", "00093-5900-01", "Sumatriptan Succinate", "Tablet", "100mg", "Oral", "Teva", "", ""),
    ("Acyclovir 400mg Tablets", "00093-0208-01", "Acyclovir", "Tablet", "400mg", "Oral", "Teva", "", ""),
    ("Valacyclovir 1g Tablets", "00093-7252-01", "Valacyclovir HCl", "Tablet", "1g", "Oral", "Teva", "", ""),
]

# (patient_idx, drug_idx, prescriber_name, prescriber_npi, qty, days, refills, sig, status, source, written_date)
PRESCRIPTIONS = [
    # Maria Johnson — hypertension + cholesterol (returning patient, multiple Rxs)
    (0, 0, "Dr. Janine Bless", "1939842031", 30, 30, 5, "Take 1 tablet by mouth once daily", "approved", "manual", "2026-02-15"),
    (0, 10, "Dr. Janine Bless", "1939842031", 30, 30, 5, "Take 1 tablet by mouth at bedtime", "approved", "manual", "2026-02-15"),
    (0, 51, "Dr. Janine Bless", "1939842031", 30, 30, 3, "Take 1 tablet by mouth once daily", "pending_review", "manual", "2026-03-10"),
    # James Rodriguez — diabetes + BP
    (1, 14, "Dr. Mark Stevens", "1003000126", 60, 30, 5, "Take 1 tablet by mouth twice daily with meals", "approved", "manual", "2026-01-20"),
    (1, 6, "Dr. Mark Stevens", "1003000126", 30, 30, 5, "Take 1 tablet by mouth once daily in the morning", "approved", "manual", "2026-01-20"),
    (1, 18, "Dr. Mark Stevens", "1003000126", 30, 30, 3, "Take 1 tablet by mouth once daily", "pending_review", "manual", "2026-03-08"),
    # Linda Chen — anxiety + insomnia
    (2, 40, "Dr. Patricia Wong", "1234567893", 30, 30, 2, "Take 1 tablet by mouth once daily", "approved", "manual", "2026-02-01"),
    (2, 43, "Dr. Patricia Wong", "1234567893", 30, 30, 0, "Take 1 tablet by mouth at bedtime as needed", "pending_review", "manual", "2026-03-12"),
    # Robert Williams — cardiac / post-MI (HIGH-RISK demo: on Warfarin + Clopidogrel + Carvedilol)
    (3, 9, "Dr. Alan Foster", "1881674458", 60, 30, 5, "Take 1 tablet by mouth twice daily", "approved", "manual", "2026-01-05"),
    (3, 61, "Dr. Alan Foster", "1881674458", 30, 30, 5, "Take 1 tablet by mouth once daily as directed by INR results", "approved", "manual", "2026-01-05"),
    (3, 62, "Dr. Alan Foster", "1881674458", 30, 30, 5, "Take 1 tablet by mouth once daily", "approved", "manual", "2026-01-05"),
    # ** KEY DEMO Rx: Ibuprofen 800mg for Robert Williams — triple-threat GI bleed risk **
    (3, 25, "Dr. Mark Stevens", "1003000126", 90, 30, 2, "Take 1 tablet by mouth 3 times daily with food", "pending_review", "manual", "2026-03-13"),
    # Sarah Davis — migraine + PPI
    (4, 77, "Dr. Nina Patel", "1346572910", 9, 30, 2, "Take 1 tablet at onset of migraine; may repeat after 2 hours", "approved", "manual", "2026-02-20"),
    (4, 51, "Dr. Nina Patel", "1346572910", 30, 30, 3, "Take 1 capsule by mouth once daily before breakfast", "approved", "manual", "2026-02-20"),
    # Michael Brown — pain management
    (5, 28, "Dr. George Kim", "1528394067", 90, 30, 5, "Take 1 capsule by mouth 3 times daily", "approved", "manual", "2026-02-10"),
    (5, 30, "Dr. George Kim", "1528394067", 30, 10, 0, "Take 1 tablet by mouth 3 times daily as needed for muscle spasm", "rejected", "manual", "2026-03-01"),
    # Jennifer Martinez — asthma
    (6, 48, "Dr. Rosa Gutierrez", "1710583249", 1, 30, 3, "Inhale 2 puffs every 4-6 hours as needed for shortness of breath", "approved", "manual", "2026-03-01"),
    (6, 49, "Dr. Rosa Gutierrez", "1710583249", 30, 30, 5, "Take 1 tablet by mouth at bedtime", "pending_review", "manual", "2026-03-11"),
    # David Anderson — gout + BPH
    (7, 60, "Dr. Thomas Reed", "1962048371", 30, 30, 5, "Take 1 tablet by mouth once daily", "approved", "manual", "2026-01-15"),
    (7, 58, "Dr. Thomas Reed", "1962048371", 30, 30, 5, "Take 1 capsule by mouth 30 minutes after the same meal each day", "approved", "manual", "2026-01-15"),
    # Patricia Taylor — thyroid + depression
    (8, 55, "Dr. Lisa Chang", "1093847562", 30, 30, 5, "Take 1 tablet by mouth once daily on an empty stomach", "approved", "manual", "2026-02-05"),
    (8, 38, "Dr. Lisa Chang", "1093847562", 30, 30, 3, "Take 1 tablet by mouth once daily in the morning", "approved", "manual", "2026-02-05"),
    # Anthony Thomas — anticoagulant
    (9, 61, "Dr. Kevin Park", "1437261890", 30, 30, 3, "Take 1 tablet by mouth once daily as directed by INR results", "pending_review", "manual", "2026-03-09"),
    # Karen Garcia — UTI (acute)
    (10, 21, "Dr. Maria Santos", "1659372048", 10, 5, 0, "Take 1 tablet by mouth twice daily for 5 days", "pending_review", "manual", "2026-03-12"),
    # William Lee — GERD + allergies
    (11, 52, "Dr. Robert Nakamura", "1784930256", 30, 30, 3, "Take 1 tablet by mouth once daily before breakfast", "approved", "manual", "2026-02-28"),
    (11, 50, "Dr. Robert Nakamura", "1784930256", 30, 30, 5, "Take 1 tablet by mouth once daily", "pending_review", "manual", "2026-03-13"),
    # Karen Garcia — Alprazolam rejected (patient safety)
    (10, 34, "Dr. Maria Santos", "1659372048", 60, 30, 3, "Take 1 tablet by mouth twice daily as needed for anxiety", "rejected", "manual", "2026-03-10"),
    # David Anderson — duplicate statin (DUR)
    (7, 10, "Dr. Thomas Reed", "1962048371", 30, 30, 5, "Take 1 tablet by mouth at bedtime", "rejected", "manual", "2026-03-05"),
]

# E-prescribe XMLs — these go through the real ingest pipeline
ESCRIPTS = [
    {
        "msg_id": "ERXMSG-2026-0301",
        "patient": ("Emily", "Parker", "F", "1991-06-14", "44 Lakeview Dr", "Orlando", "FL", "32801"),
        "prescriber": ("Janine", "Bless", "1939842031", "BB8027505"),
        "drug": ("Amoxicillin 500mg Capsules", "00093-3109-01"),
        "qty": 30, "days": 10, "refills": 0,
        "sig": "Take 1 capsule by mouth 3 times daily for 10 days",
        "date": "2026-03-13",
    },
    {
        "msg_id": "ERXMSG-2026-0302",
        "patient": ("Marcus", "Wright", "M", "1980-11-30", "782 River Rd", "Memphis", "TN", "38101"),
        "prescriber": ("Mark", "Stevens", "1003000126", "MS3456789"),
        "drug": ("Atorvastatin 40mg Tablets", "00378-2078-01"),
        "qty": 30, "days": 30, "refills": 5,
        "sig": "Take 1 tablet by mouth at bedtime",
        "date": "2026-03-13",
    },
    {
        "msg_id": "ERXMSG-2026-0303",
        "patient": ("Maria", "Johnson", "F", "1984-09-09", "123 Main St", "Miami", "FL", "33101"),
        "prescriber": ("Janine", "Bless", "1939842031", "BB8027505"),
        "drug": ("Metformin 500mg Tablets", "00093-1048-01"),
        "qty": 60, "days": 30, "refills": 5,
        "sig": "Take 1 tablet by mouth twice daily with meals",
        "date": "2026-03-13",
    },
    {
        "msg_id": "ERXMSG-2026-0304",
        "patient": ("Sarah", "Davis", "F", "1988-01-14", "555 Maple Ln", "Phoenix", "AZ", "85001"),
        "prescriber": ("Nina", "Patel", "1346572910", "NP1234567"),
        "drug": ("Sumatriptan 100mg Tablets", "00093-5900-01"),
        "qty": 9, "days": 30, "refills": 2,
        "sig": "Take 1 tablet at onset of migraine; may repeat after 2 hours; max 2 per day",
        "date": "2026-03-13",
    },
    {
        "msg_id": "ERXMSG-2026-0305",
        "patient": ("Daniel", "Rivera", "M", "1973-04-07", "210 Sunset Blvd", "San Diego", "CA", "92101"),
        "prescriber": ("George", "Kim", "1528394067", "GK9876543"),
        "drug": ("Omeprazole 20mg Capsules", "00093-7207-01"),
        "qty": 30, "days": 30, "refills": 3,
        "sig": "Take 1 capsule by mouth once daily 30 minutes before breakfast",
        "date": "2026-03-13",
    },
]


def _build_newrx_xml(e: dict) -> str:
    p = e["patient"]
    pr = e["prescriber"]
    d = e["drug"]
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Message>
  <Header>
    <MessageID>{e["msg_id"]}</MessageID>
    <SentTime>{e["date"]}T10:30:00Z</SentTime>
  </Header>
  <Body>
    <NewRx>
      <Patient>
        <HumanPatient>
          <Name>
            <FirstName>{p[0]}</FirstName>
            <LastName>{p[1]}</LastName>
          </Name>
          <Gender>{p[2]}</Gender>
          <DateOfBirth><Date>{p[3]}</Date></DateOfBirth>
          <Address>
            <AddressLine1>{p[4]}</AddressLine1>
            <City>{p[5]}</City>
            <StateProvince>{p[6]}</StateProvince>
            <PostalCode>{p[7]}</PostalCode>
          </Address>
        </HumanPatient>
      </Patient>
      <Prescriber>
        <NonVeterinarian>
          <Name>
            <FirstName>{pr[0]}</FirstName>
            <LastName>{pr[1]}</LastName>
          </Name>
          <Identification>
            <NPI>{pr[2]}</NPI>
            <DEANumber>{pr[3]}</DEANumber>
          </Identification>
        </NonVeterinarian>
      </Prescriber>
      <MedicationPrescribed>
        <DrugDescription>{d[0]}</DrugDescription>
        <DrugCoded><ProductCode><Code>{d[1]}</Code></ProductCode></DrugCoded>
        <Quantity><Value>{e["qty"]}</Value></Quantity>
        <DaysSupply>{e["days"]}</DaysSupply>
        <NumberOfRefills>{e["refills"]}</NumberOfRefills>
        <Sig><SigText>{e["sig"]}</SigText></Sig>
        <WrittenDate><Date>{e["date"]}</Date></WrittenDate>
        <Substitutions>0</Substitutions>
      </MedicationPrescribed>
    </NewRx>
  </Body>
</Message>"""


# ---------------------------------------------------------------------------
# SEED LOGIC
# ---------------------------------------------------------------------------

async def seed():
    async with async_session() as db:
        # --- Wipe existing data ---
        log.info("Wiping existing data...")
        for tbl in [
            "arxi.prescriptions",
            "arxi.patients",
            "arxi.drugs",
            "compliance.audit_log",
            "public.users",
        ]:
            await db.execute(text(f"DELETE FROM {tbl}"))
        await db.commit()
        log.info("  All tables cleared")

        # --- Users ---
        log.info("Seeding users...")
        auth = AuthService(db)
        for u in USERS:
            existing = await db.execute(select(User).where(User.username == u["username"]))
            if existing.scalar_one_or_none():
                log.info("  skip %s (exists)", u["username"])
                continue
            await auth.create_user(**u)
            log.info("  + %s (%s)", u["username"], u["role"].value)

        # Get agent user ID for e-prescribe ingest
        agent_result = await db.execute(select(User).where(User.username == "agent"))
        agent_user = agent_result.scalar_one()

        # --- Drugs ---
        log.info("Seeding %d drugs...", len(DRUGS))
        for name, ndc, generic, form, strength, route, mfr, schedule, desc in DRUGS:
            drug = Drug(
                ndc=ndc, drug_name=name, generic_name=generic,
                dosage_form=form, strength=strength, route=route,
                manufacturer=mfr, dea_schedule=schedule, package_description=desc,
            )
            db.add(drug)
        await db.commit()
        log.info("  + %d drugs", len(DRUGS))

        # --- Patients ---
        log.info("Seeding %d patients...", len(PATIENTS))
        patient_ids = []
        for p in PATIENTS:
            patient = Patient(**p)
            db.add(patient)
            await db.flush()
            patient_ids.append(patient.id)
            log.info("  + %s %s (%s)", p["first_name"], p["last_name"], patient.id[:8])
        await db.commit()

        # --- Prescriptions (manual, pre-linked) ---
        log.info("Seeding %d manual prescriptions...", len(PRESCRIPTIONS))
        for pi, di, prescriber, npi, qty, days, refills, sig, status, source, wdate in PRESCRIPTIONS:
            pat = PATIENTS[pi]
            drug_name, drug_ndc = DRUGS[di][0], DRUGS[di][1]
            rx = Prescription(
                source=source,
                status=RxStatus(status),
                patient_id=patient_ids[pi],
                patient_first_name=pat["first_name"],
                patient_last_name=pat["last_name"],
                patient_dob=pat["date_of_birth"],
                prescriber_name=prescriber,
                prescriber_npi=npi,
                prescriber_dea="",
                drug_description=drug_name,
                ndc=drug_ndc,
                quantity=qty,
                days_supply=days,
                refills=refills,
                sig_text=sig,
                written_date=wdate,
                substitutions=0,
            )
            if status in ("approved", "rejected"):
                admin_result = await db.execute(select(User).where(User.username == "pharmacist"))
                pharmacist = admin_result.scalar_one()
                rx.reviewed_by = pharmacist.id
                rx.reviewed_at = datetime.now(timezone.utc)
                rx.reviewer_name = pharmacist.full_name

            if status == "approved":
                rx.review_notes = "Verified and approved"
                rx.clinical_checks = ["dur_review", "allergy_screening"]
            elif status == "rejected":
                # Structured rejection data varies by case
                drug_name = DRUGS[di][0]
                if "Cyclobenzaprine" in drug_name:
                    rx.rejection_reason = "dur_issue"
                    rx.followup_action = "contact_prescriber"
                    rx.clinical_checks = ["dur_review", "drug_interactions", "patient_profile"]
                    rx.review_notes = (
                        "Patient already on Flexeril from previous provider. "
                        "Duplicate therapy identified during DUR review. "
                        "Contacted Dr. Kim's office for updated Rx."
                    )
                elif "Alprazolam" in drug_name:
                    rx.rejection_reason = "patient_safety"
                    rx.followup_action = "contact_prescriber"
                    rx.clinical_checks = ["dur_review", "drug_interactions", "patient_profile", "dose_range"]
                    rx.review_notes = (
                        "Qty 60 with TID dosing exceeds typical starting dose for new benzodiazepine Rx. "
                        "No prior benzo history in patient profile. High-risk combination with existing "
                        "ciprofloxacin (CYP3A4 inhibitor increases alprazolam levels). "
                        "Recommend lower starting dose and prescriber confirmation."
                    )
                elif "Atorvastatin" in drug_name:
                    rx.rejection_reason = "dur_issue"
                    rx.followup_action = "return_to_prescriber"
                    rx.clinical_checks = ["dur_review", "patient_profile"]
                    rx.review_notes = (
                        "Patient already has active Rx for Atorvastatin 20mg from Dr. Foster. "
                        "New Rx from Dr. Reed is for same drug at different dose without discontinuation. "
                        "Returning to prescriber for clarification on dose change vs duplicate."
                    )
                else:
                    rx.rejection_reason = "prescriber_contact"
                    rx.followup_action = "contact_prescriber"
                    rx.clinical_checks = ["dur_review"]
                    rx.review_notes = "Needs updated prescription \u2014 contact prescriber"
            db.add(rx)
        await db.commit()
        log.info("  + %d prescriptions", len(PRESCRIPTIONS))

        # --- E-prescribe ingest (through real pipeline) ---
        log.info("Ingesting %d e-prescribe XMLs through pipeline...", len(ESCRIPTS))
        svc = IntakeService(db)
        for e in ESCRIPTS:
            xml = _build_newrx_xml(e)
            rx = await svc.ingest_newrx(xml, source="e-prescribe", actor_id=agent_user.id)
            log.info("  + %s → %s | %s %s | %s",
                     e["msg_id"], rx.status.value,
                     e["patient"][0], e["patient"][1],
                     e["drug"][0])

    # --- Summary ---
    async with async_session() as db:
        counts = {}
        for tbl in ["public.users", "arxi.drugs", "arxi.patients", "arxi.prescriptions", "compliance.audit_log"]:
            r = await db.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
            counts[tbl.split(".")[-1]] = r.scalar()

        rx_status = await db.execute(text(
            "SELECT status, COUNT(*) FROM arxi.prescriptions GROUP BY status ORDER BY status"
        ))

        log.info("")
        log.info("=== SEED COMPLETE ===")
        log.info("  Users:         %d", counts["users"])
        log.info("  Drugs:         %d", counts["drugs"])
        log.info("  Patients:      %d", counts["patients"])
        log.info("  Prescriptions: %d", counts["prescriptions"])
        log.info("  Audit logs:    %d", counts["audit_log"])
        log.info("")
        log.info("  Rx by status:")
        for status, count in rx_status.fetchall():
            log.info("    %-16s %d", status, count)
        log.info("")
        log.info("  5 e-prescribes ingested as PARSED — worker will advance to PENDING_REVIEW")
        log.info("  Login: admin/admin123, pharmacist/pharma123")


if __name__ == "__main__":
    asyncio.run(seed())
