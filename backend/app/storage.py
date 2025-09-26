import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func

Base = declarative_base()

class VehiclePosition(Base):
    """Historical vehicle position data."""
    __tablename__ = 'vehicle_positions'

    id = Column(Integer, primary_key=True)
    vehicle_id = Column(String(50), nullable=False, index=True)
    route_id = Column(String(50), nullable=True, index=True)
    trip_id = Column(String(50), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float, nullable=True)
    bearing = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    ghost_score = Column(Integer, default=0)
    is_ghost = Column(Boolean, default=False)
    detection_rules = Column(Text, nullable=True)  # JSON string

class RecurringGhost(Base):
    """Tracks vehicles that are frequently flagged as ghosts."""
    __tablename__ = 'recurring_ghosts'

    id = Column(Integer, primary_key=True)
    vehicle_id = Column(String(50), nullable=False, unique=True, index=True)
    total_flags = Column(Integer, default=0)
    last_flag_time = Column(DateTime, nullable=True)
    first_flag_time = Column(DateTime, nullable=True)
    avg_ghost_score = Column(Float, default=0.0)
    is_recurring = Column(Boolean, default=False)

class DatabaseStorage:
    def __init__(self):
        # Database connection
        db_host = os.getenv("POSTGRES_HOST", "postgres")
        db_name = os.getenv("POSTGRES_DB", "ghostbus")
        db_user = os.getenv("POSTGRES_USER", "ghostbus")
        db_password = os.getenv("POSTGRES_PASSWORD", "ghostbus123")

        database_url = f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}"
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def save_vehicle_position(self, vehicle_data: Dict):
        """Save vehicle position to database."""
        with self.get_session() as session:
            position = VehiclePosition(
                vehicle_id=vehicle_data['vehicle_id'],
                route_id=vehicle_data.get('route_id'),
                trip_id=vehicle_data.get('trip_id'),
                latitude=vehicle_data['lat'],
                longitude=vehicle_data['lon'],
                speed=vehicle_data.get('speed'),
                bearing=vehicle_data.get('bearing'),
                timestamp=datetime.fromtimestamp(vehicle_data['timestamp']),
                ghost_score=vehicle_data.get('ghost_score', 0),
                is_ghost=vehicle_data.get('is_ghost', False),
                detection_rules=str(vehicle_data.get('detection_rules', {}))
            )
            session.add(position)
            session.commit()

    def get_vehicle_history(self, vehicle_id: str, days: int = 7) -> List[Dict]:
        """Get historical positions for a vehicle over the last N days."""
        cutoff_time = datetime.now() - timedelta(days=days)

        with self.get_session() as session:
            positions = session.query(VehiclePosition).filter(
                VehiclePosition.vehicle_id == vehicle_id,
                VehiclePosition.timestamp >= cutoff_time
            ).order_by(VehiclePosition.timestamp.desc()).all()

            return [{
                'vehicle_id': pos.vehicle_id,
                'route_id': pos.route_id,
                'lat': pos.latitude,
                'lon': pos.longitude,
                'speed': pos.speed,
                'bearing': pos.bearing,
                'timestamp': pos.timestamp.timestamp(),
                'ghost_score': pos.ghost_score,
                'is_ghost': pos.is_ghost,
                'detection_rules': eval(pos.detection_rules) if pos.detection_rules else {}
            } for pos in positions]

    def update_recurring_ghost_stats(self, vehicle_id: str, ghost_score: int, is_ghost: bool):
        """Update recurring ghost statistics for a vehicle."""
        with self.get_session() as session:
            recurring = session.query(RecurringGhost).filter(
                RecurringGhost.vehicle_id == vehicle_id
            ).first()

            if not recurring:
                recurring = RecurringGhost(
                    vehicle_id=vehicle_id,
                    total_flags=0,
                    first_flag_time=None,
                    last_flag_time=None,
                    avg_ghost_score=0.0,
                    is_recurring=False
                )
                session.add(recurring)

            if is_ghost:
                if not recurring.first_flag_time:
                    recurring.first_flag_time = datetime.now()
                recurring.last_flag_time = datetime.now()
                recurring.total_flags += 1

                # Update average ghost score
                if recurring.total_flags > 1:
                    recurring.avg_ghost_score = (
                        (recurring.avg_ghost_score * (recurring.total_flags - 1) + ghost_score) /
                        recurring.total_flags
                    )
                else:
                    recurring.avg_ghost_score = ghost_score

                # Mark as recurring if flagged more than 5 times in the last 7 days
                if recurring.total_flags >= 5:
                    recurring.is_recurring = True

            session.commit()

    def get_recurring_ghosts(self, days: int = 7) -> List[Dict]:
        """Get list of recurring ghost vehicles."""
        cutoff_time = datetime.now() - timedelta(days=days)

        with self.get_session() as session:
            recurring = session.query(RecurringGhost).filter(
                RecurringGhost.is_recurring == True,
                RecurringGhost.last_flag_time >= cutoff_time
            ).all()

            return [{
                'vehicle_id': r.vehicle_id,
                'total_flags': r.total_flags,
                'first_flag_time': r.first_flag_time.timestamp() if r.first_flag_time else None,
                'last_flag_time': r.last_flag_time.timestamp() if r.last_flag_time else None,
                'avg_ghost_score': r.avg_ghost_score,
                'is_recurring': r.is_recurring
            } for r in recurring]

    def get_ghost_statistics(self, days: int = 7) -> Dict:
        """Get comprehensive ghost statistics."""
        cutoff_time = datetime.now() - timedelta(days=days)

        with self.get_session() as session:
            # Total positions
            total_positions = session.query(func.count(VehiclePosition.id)).filter(
                VehiclePosition.timestamp >= cutoff_time
            ).scalar()

            # Ghost positions
            ghost_positions = session.query(func.count(VehiclePosition.id)).filter(
                VehiclePosition.timestamp >= cutoff_time,
                VehiclePosition.is_ghost == True
            ).scalar()

            # Unique vehicles
            unique_vehicles = session.query(func.count(func.distinct(VehiclePosition.vehicle_id))).filter(
                VehiclePosition.timestamp >= cutoff_time
            ).scalar()

            # Recurring ghosts
            recurring_count = session.query(func.count(RecurringGhost.id)).filter(
                RecurringGhost.is_recurring == True,
                RecurringGhost.last_flag_time >= cutoff_time
            ).scalar()

            return {
                'total_positions': total_positions or 0,
                'ghost_positions': ghost_positions or 0,
                'ghost_percentage': (ghost_positions / total_positions * 100) if total_positions > 0 else 0,
                'unique_vehicles': unique_vehicles or 0,
                'recurring_ghosts': recurring_count or 0,
                'analysis_period_days': days
            }

# Global storage instance
_storage = None

def get_storage() -> DatabaseStorage:
    """Get or create storage instance."""
    global _storage
    if _storage is None:
        _storage = DatabaseStorage()
    return _storage
