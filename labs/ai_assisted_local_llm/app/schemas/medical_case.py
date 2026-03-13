"""Deeply nested Pydantic models representing a complete EMR-level medical case."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ── Enums ──────────────────────────────────────────────────────────────────────

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class AllergyServerity(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class PriorityLevel(str, Enum):
    STAT = "stat"
    URGENT = "urgent"
    ROUTINE = "routine"


class ManagementCategory(str, Enum):
    MEDICATION = "medication"
    PROCEDURE = "procedure"
    IMAGING = "imaging"
    LAB = "lab"
    CONSULT = "consult"
    LIFESTYLE = "lifestyle"
    OTHER = "other"


# ── Demographics & Vitals ──────────────────────────────────────────────────────

class PatientDemographics(BaseModel):
    age: int = Field(..., ge=0, le=150)
    sex: Sex
    weight_kg: float | None = Field(None, ge=0)
    height_cm: float | None = Field(None, ge=0)
    bmi: float | None = Field(None, ge=0)
    race_ethnicity: str | None = None
    preferred_language: str | None = None


class VitalSigns(BaseModel):
    heart_rate: int | None = Field(None, ge=0, le=300)
    bp_systolic: int | None = Field(None, ge=0, le=350)
    bp_diastolic: int | None = Field(None, ge=0, le=250)
    respiratory_rate: int | None = Field(None, ge=0, le=80)
    spo2: float | None = Field(None, ge=0, le=100)
    temperature_c: float | None = Field(None, ge=20, le=45)
    pain_scale: int | None = Field(None, ge=0, le=10)
    gcs: int | None = Field(None, ge=3, le=15)


# ── History ────────────────────────────────────────────────────────────────────

class ChiefComplaintHPI(BaseModel):
    chief_complaint: str
    hpi_narrative: str
    onset: str | None = None
    duration: str | None = None
    severity: str | None = None
    aggravating_factors: list[str] = Field(default_factory=list)
    alleviating_factors: list[str] = Field(default_factory=list)
    associated_symptoms: list[str] = Field(default_factory=list)


class SystemReview(BaseModel):
    system: str
    positive_findings: list[str] = Field(default_factory=list)
    negative_findings: list[str] = Field(default_factory=list)


class PastMedicalHistory(BaseModel):
    conditions: list[str] = Field(default_factory=list)
    hospitalizations: list[str] = Field(default_factory=list)


class PastSurgicalHistory(BaseModel):
    surgeries: list[str] = Field(default_factory=list)


class FamilyMember(BaseModel):
    relation: str
    conditions: list[str] = Field(default_factory=list)
    alive: bool | None = None


class SocialHistory(BaseModel):
    tobacco: str | None = None
    alcohol: str | None = None
    drugs: str | None = None
    occupation: str | None = None
    living_situation: str | None = None
    exercise: str | None = None


class Medication(BaseModel):
    name: str
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None


class Allergy(BaseModel):
    substance: str
    reaction: str | None = None
    severity: AllergyServerity | None = None


# ── Physical Exam ──────────────────────────────────────────────────────────────

class HEENTExam(BaseModel):
    head: str | None = None
    eyes: str | None = None
    ears: str | None = None
    nose: str | None = None
    throat: str | None = None


class CardiovascularExam(BaseModel):
    rate_rhythm: str | None = None
    murmurs: str | None = None
    jvd: str | None = None
    peripheral_pulses: str | None = None
    edema: str | None = None


class PulmonaryExam(BaseModel):
    effort: str | None = None
    breath_sounds: str | None = None
    wheezes: str | None = None
    crackles: str | None = None
    rhonchi: str | None = None


class AbdominalExam(BaseModel):
    inspection: str | None = None
    bowel_sounds: str | None = None
    tenderness: str | None = None
    guarding: bool | None = None
    rebound: bool | None = None


class NeurologicalExam(BaseModel):
    mental_status: str | None = None
    cranial_nerves: str | None = None
    motor: str | None = None
    sensory: str | None = None
    reflexes: str | None = None
    coordination: str | None = None
    gait: str | None = None


class MusculoskeletalExam(BaseModel):
    inspection: str | None = None
    range_of_motion: str | None = None
    strength: str | None = None
    swelling: str | None = None


class SkinExam(BaseModel):
    color: str | None = None
    turgor: str | None = None
    lesions: str | None = None
    rashes: str | None = None


class PsychiatricExam(BaseModel):
    appearance: str | None = None
    behavior: str | None = None
    mood: str | None = None
    affect: str | None = None
    thought_process: str | None = None
    thought_content: str | None = None


class PhysicalExam(BaseModel):
    general_appearance: str | None = None
    heent: HEENTExam | None = None
    cardiovascular: CardiovascularExam | None = None
    pulmonary: PulmonaryExam | None = None
    abdominal: AbdominalExam | None = None
    neurological: NeurologicalExam | None = None
    musculoskeletal: MusculoskeletalExam | None = None
    skin: SkinExam | None = None
    psychiatric: PsychiatricExam | None = None


# ── Diagnostics ────────────────────────────────────────────────────────────────

class CBC(BaseModel):
    wbc: float | None = None
    hemoglobin: float | None = None
    hematocrit: float | None = None
    platelets: float | None = None
    mcv: float | None = None
    rdw: float | None = None


class BMP(BaseModel):
    sodium: float | None = None
    potassium: float | None = None
    chloride: float | None = None
    bicarbonate: float | None = None
    bun: float | None = None
    creatinine: float | None = None
    glucose: float | None = None
    calcium: float | None = None


class HepaticPanel(BaseModel):
    ast: float | None = None
    alt: float | None = None
    alp: float | None = None
    total_bilirubin: float | None = None
    direct_bilirubin: float | None = None
    albumin: float | None = None
    total_protein: float | None = None


class Coagulation(BaseModel):
    pt: float | None = None
    inr: float | None = None
    ptt: float | None = None


class Urinalysis(BaseModel):
    color: str | None = None
    clarity: str | None = None
    specific_gravity: float | None = None
    ph: float | None = None
    protein: str | None = None
    glucose_ua: str | None = None
    ketones: str | None = None
    blood: str | None = None
    leukocyte_esterase: str | None = None
    nitrites: str | None = None
    wbc_ua: str | None = None
    bacteria: str | None = None


class CardiacMarkers(BaseModel):
    troponin: float | None = None
    bnp: float | None = None
    ck_mb: float | None = None


class MiscLab(BaseModel):
    name: str
    value: str
    unit: str | None = None
    reference_range: str | None = None


class LabResults(BaseModel):
    cbc: CBC | None = None
    bmp: BMP | None = None
    hepatic_panel: HepaticPanel | None = None
    coagulation: Coagulation | None = None
    urinalysis: Urinalysis | None = None
    cardiac_markers: CardiacMarkers | None = None
    misc_labs: list[MiscLab] = Field(default_factory=list)


class ImagingStudy(BaseModel):
    modality: str
    body_part: str
    contrast: bool = False
    findings: str | None = None
    impression: str | None = None


class Diagnostics(BaseModel):
    lab_results: LabResults | None = None
    imaging: list[ImagingStudy] = Field(default_factory=list)
    other_studies: list[str] = Field(default_factory=list)


# ── Assessment & Plan ──────────────────────────────────────────────────────────

class DifferentialDiagnosis(BaseModel):
    rank: int = Field(..., ge=1)
    diagnosis: str
    reasoning: str | None = None


class Assessment(BaseModel):
    differential_diagnoses: list[DifferentialDiagnosis] = Field(default_factory=list)
    working_diagnosis: str | None = None
    final_diagnosis: str | None = None
    clinical_reasoning: str | None = None


class ManagementStep(BaseModel):
    category: ManagementCategory
    description: str
    priority: PriorityLevel = PriorityLevel.ROUTINE


class Plan(BaseModel):
    steps: list[ManagementStep] = Field(default_factory=list)
    disposition: str | None = None
    follow_up: str | None = None
    patient_education: str | None = None


# ── Root Model ─────────────────────────────────────────────────────────────────

class MedicalCase(BaseModel):
    case_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_number: int | None = None
    case_title: str = ""
    specialty: str = "general"
    difficulty: Difficulty = Difficulty.MEDIUM
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    demographics: PatientDemographics
    vitals: VitalSigns | None = None
    chief_complaint_hpi: ChiefComplaintHPI
    review_of_systems: list[SystemReview] = Field(default_factory=list)
    past_medical_history: PastMedicalHistory | None = None
    past_surgical_history: PastSurgicalHistory | None = None
    family_history: list[FamilyMember] = Field(default_factory=list)
    social_history: SocialHistory | None = None
    medications: list[Medication] = Field(default_factory=list)
    allergies: list[Allergy] = Field(default_factory=list)
    physical_exam: PhysicalExam | None = None
    diagnostics: Diagnostics | None = None
    assessment: Assessment | None = None
    plan: Plan | None = None

    @field_validator("case_id", mode="before")
    @classmethod
    def ensure_uuid(cls, v: str) -> str:
        try:
            uuid.UUID(v)
        except (ValueError, AttributeError):
            return str(uuid.uuid4())
        return v

    @field_validator("difficulty", mode="before")
    @classmethod
    def coerce_difficulty(cls, v):
        if isinstance(v, str):
            try:
                return Difficulty(v.lower())
            except Exception:
                return v
        return v
