"""
Sanaie Platform — Shared Enums
Single source of truth for all enum types used across models, schemas, and services.
"""
from enum import Enum


class UserRole(str, Enum):
    CLIENT = "client"
    WORKER = "worker"
    CONTRACTOR = "contractor"
    MODERATOR = "moderator"
    EDITOR = "editor"
    ADMIN = "admin"


class JobCategory(str, Enum):
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    PAINTING = "painting"
    CARPENTRY = "carpentry"
    CLEANING = "cleaning"
    GENERAL = "general"
    OTHER = "other"


class JobStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ON_THE_WAY = "on_the_way"
    WORK_STARTED = "work_started"
    COMPLETED = "completed"
    CANCELED = "canceled"


class BidStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    COUNTER_OFFERED = "counter_offered"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
