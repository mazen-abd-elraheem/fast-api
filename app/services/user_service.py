"""
Sanaie Platform — User Service
Handles registration, authentication, profile management, and geo-search.
Uses domain exceptions instead of HTTPException.
"""
import uuid
from typing import Optional, List
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.review import Review
from app.enums import UserRole
from app.schemas.user import UserCreate, UserUpdate, UserLocationUpdate
from app.core.security import hash_password, verify_password
from app.core.exceptions import (
    NotFoundException,
    DuplicateException,
    BadRequestException,
)
from app.services.geo_service import GeoService


class UserService:
    """Handles User Registration, Authentication, and Profile management."""

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.user_id == user_id).first()

    @staticmethod
    def create_user(db: Session, user_in: UserCreate) -> User:
        """Register a new user (client or worker)."""
        if UserService.get_by_email(db, user_in.email):
            raise DuplicateException("Email already registered")

        db_user = User(
            user_id=str(uuid.uuid4()),
            name=user_in.name,
            email=user_in.email,
            phone_number=user_in.phone_number,
            password_hash=hash_password(user_in.password),
            role=user_in.role.value,
            latitude=user_in.latitude,
            longitude=user_in.longitude,
            skills=user_in.skills,  # Now stored as JSON array
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Optional[User]:
        """Verify email and password."""
        user = UserService.get_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def update_profile(db: Session, user_id: str, update_data: UserUpdate) -> User:
        """Update user profile fields."""
        user = UserService.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("User", user_id)

        if update_data.name is not None:
            user.name = update_data.name
        if update_data.phone_number is not None:
            user.phone_number = update_data.phone_number
        if update_data.skills is not None:
            user.skills = update_data.skills
        if update_data.profile_image_url is not None:
            user.profile_image_url = update_data.profile_image_url
        if update_data.is_available is not None:
            user.is_available = update_data.is_available
        if update_data.role is not None:
            user.role = update_data.role

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_location(db: Session, user_id: str, location: UserLocationUpdate) -> User:
        """Update user geolocation."""
        user = UserService.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("User", user_id)

        user.latitude = location.latitude
        user.longitude = location.longitude

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_nearby_workers(
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 50.0,
    ) -> list:
        """
        Find workers within a radius using bounding-box pre-filter + Haversine.
        Fixes N+1 by batch-loading ratings.
        """
        # Bounding-box pre-filter to avoid loading all workers
        lat_delta = radius_km / 111.0  # ~111 km per degree
        lng_delta = radius_km / (111.0 * max(abs(float(latitude)) * 0.0175, 0.01))

        workers = (
            db.query(User)
            .filter(
                User.role == "worker",
                User.latitude.isnot(None),
                User.longitude.isnot(None),
                User.latitude.between(latitude - lat_delta, latitude + lat_delta),
                User.longitude.between(longitude - lng_delta, longitude + lng_delta),
            )
            .all()
        )

        # Haversine filter for exact distance
        nearby = GeoService.filter_by_proximity(
            workers, latitude, longitude, radius_km
        )

        if not nearby:
            return []

        # Batch-load ratings (fixes N+1)
        worker_ids = [w.user_id for w, _ in nearby]
        rating_data = (
            db.query(
                Review.worker_id,
                func.avg(Review.rating_score).label("avg_rating"),
                func.count(Review.review_id).label("total_reviews"),
            )
            .filter(Review.worker_id.in_(worker_ids))
            .group_by(Review.worker_id)
            .all()
        )
        ratings_map = {r.worker_id: (float(r.avg_rating), r.total_reviews) for r in rating_data}

        results = []
        for worker, distance in nearby:
            avg_rating, total_reviews = ratings_map.get(worker.user_id, (None, 0))
            results.append({
                "user_id": worker.user_id,
                "name": worker.name,
                "role": worker.role,
                "skills": worker.skills,
                "profile_image_url": worker.profile_image_url,
                "is_available": worker.is_available,
                "avg_rating": round(avg_rating, 2) if avg_rating else None,
                "total_reviews": total_reviews or 0,
                "distance_km": distance,
            })

        return results

    @staticmethod
    def get_worker_rating(db: Session, worker_id: str) -> dict:
        """Get a worker's average rating and total reviews."""
        result = (
            db.query(
                func.avg(Review.rating_score).label("avg_rating"),
                func.count(Review.review_id).label("total_reviews"),
            )
            .filter(Review.worker_id == worker_id)
            .first()
        )
        return {
            "worker_id": worker_id,
            "avg_rating": round(float(result.avg_rating), 2) if result.avg_rating else 0.0,
            "total_reviews": result.total_reviews or 0,
        }
