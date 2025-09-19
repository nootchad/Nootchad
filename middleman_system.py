import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
import discord
from discord.ext import commands
from supabase import create_client, Client

logger = logging.getLogger(__name__)

Base = declarative_base()

class ApplicationStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"

class ReportStatus(Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"

class ReportCategory(Enum):
    SCAM = "scam"
    UNPROFESSIONAL = "unprofessional"
    SLOW_RESPONSE = "slow_response"
    FAILED_TRADE = "failed_trade"
    HARASSMENT = "harassment"
    OTHER = "other"

# Modelos de base de datos
class MiddlemanApplication(Base):
    __tablename__ = 'middleman_applications'
    
    id = Column(Integer, primary_key=True)
    discord_user_id = Column(String(20), nullable=False)
    discord_username = Column(String(100), nullable=False)
    roblox_username = Column(String(100), nullable=False)
    experience = Column(Text, nullable=False)
    why_middleman = Column(Text, nullable=False)
    availability = Column(Text, nullable=False)
    additional_info = Column(Text)
    image_urls = Column(Text)  # JSON array de URLs de imágenes
    status = Column(String(20), default=ApplicationStatus.PENDING.value)
    submitted_at = Column(DateTime, default=func.now())
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String(20))
    admin_notes = Column(Text)
    
    # Relaciones
    comments = relationship("ApplicationComment", back_populates="application")

class MiddlemanProfile(Base):
    __tablename__ = 'middleman_profiles'
    
    id = Column(Integer, primary_key=True)
    discord_user_id = Column(String(20), unique=True, nullable=False)
    discord_username = Column(String(100), nullable=False)
    roblox_username = Column(String(100), nullable=False)
    bio = Column(Text)
    specialties = Column(Text)  # JSON array
    total_trades = Column(Integer, default=0)
    successful_trades = Column(Integer, default=0)
    rating_average = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    last_active = Column(DateTime, default=func.now())
    
    # Relaciones
    ratings = relationship("MiddlemanRating", back_populates="middleman")
    comments = relationship("MiddlemanComment", back_populates="middleman")
    reports_as_target = relationship("MiddlemanReport", back_populates="target_middleman")

class MiddlemanRating(Base):
    __tablename__ = 'middleman_ratings'
    
    id = Column(Integer, primary_key=True)
    middleman_id = Column(Integer, ForeignKey('middleman_profiles.id'), nullable=False)
    rater_discord_id = Column(String(20), nullable=False)
    rater_username = Column(String(100), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 estrellas
    comment = Column(Text)
    trade_description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Relación
    middleman = relationship("MiddlemanProfile", back_populates="ratings")

class MiddlemanComment(Base):
    __tablename__ = 'middleman_comments'
    
    id = Column(Integer, primary_key=True)
    middleman_id = Column(Integer, ForeignKey('middleman_profiles.id'), nullable=False)
    commenter_discord_id = Column(String(20), nullable=False)
    commenter_username = Column(String(100), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    is_approved = Column(Boolean, default=False)
    approved_by = Column(String(20))
    approved_at = Column(DateTime)
    
    # Relación
    middleman = relationship("MiddlemanProfile", back_populates="comments")

class ApplicationComment(Base):
    __tablename__ = 'application_comments'
    
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('middleman_applications.id'), nullable=False)
    commenter_discord_id = Column(String(20), nullable=False)
    commenter_username = Column(String(100), nullable=False)
    comment = Column(Text, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relación
    application = relationship("MiddlemanApplication", back_populates="comments")

class MiddlemanReport(Base):
    __tablename__ = 'middleman_reports'
    
    id = Column(Integer, primary_key=True)
    target_middleman_id = Column(Integer, ForeignKey('middleman_profiles.id'), nullable=False)
    reporter_discord_id = Column(String(20), nullable=False)
    reporter_username = Column(String(100), nullable=False)
    category = Column(String(30), nullable=False)
    description = Column(Text, nullable=False)
    evidence_urls = Column(Text)  # JSON array de URLs de evidencia
    status = Column(String(20), default=ReportStatus.OPEN.value)
    created_at = Column(DateTime, default=func.now())
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String(20))
    admin_notes = Column(Text)
    resolution = Column(Text)
    
    # Relación
    target_middleman = relationship("MiddlemanProfile", back_populates="reports_as_target")

class WebhookEvent(Base):
    __tablename__ = 'webhook_events'
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False)
    payload = Column(Text, nullable=False)  # JSON
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime)
    error_message = Column(Text)

class MiddlemanSystem:
    def __init__(self, bot):
        self.bot = bot
        self.engine = None
        self.SessionLocal = None
        self.supabase_client = None
        self.setup_supabase()  # Primero configurar Supabase client
        self.setup_database()  # Luego verificar/crear tablas
        
    def setup_database(self):
        """Crear tablas necesarias usando Supabase client"""
        try:
            if not self.supabase_client:
                logger.error("Cliente de Supabase no disponible")
                return
                
            # Crear tablas usando raw SQL a través de Supabase
            self._create_tables_if_not_exist()
            logger.info("<a:verify2:1418486831993061497> Tablas de base de datos verificadas/creadas exitosamente")
            
        except Exception as e:
            logger.error(f"Error configurando base de datos: {e}")
            
    def _create_tables_if_not_exist(self):
        """Crear las tablas necesarias si no existen - las tablas deben crearse manualmente en Supabase Dashboard"""
        try:
            # Verificar si la tabla ya existe intentando hacer una query
            try:
                result = self.supabase_client.table("middleman_applications").select("id").limit(1).execute()
                logger.info("<a:verify2:1418486831993061497> Tablas de middleman ya existen")
                return True
            except Exception as e:
                if "PGRST205" in str(e) or "Could not find the table" in str(e):
                    logger.warning("⚠️ Tablas de middleman NO existen - deben crearse manualmente en Supabase Dashboard")
                    logger.warning("📋 Necesitas crear estas tablas en Supabase:")
                    logger.warning("   - middleman_applications")
                    logger.warning("   - middleman_profiles")
                    logger.warning("   - middleman_ratings")
                    logger.warning("   - middleman_reports")
                    return False
                else:
                    raise e
            
        except Exception as e:
            logger.error(f"Error verificando tablas: {e}")
            return False
    
    def setup_supabase(self):
        """Configurar cliente de Supabase para storage y funciones"""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            logger.error("SUPABASE_URL o SUPABASE_KEY no encontradas")
            return
        
        try:
            self.supabase_client = create_client(supabase_url, supabase_key)
            logger.info("Cliente de Supabase configurado exitosamente")
        except Exception as e:
            logger.error(f"Error configurando cliente de Supabase: {e}")
    
    def get_db(self) -> Session:
        """Obtener sesión de base de datos"""
        return self.SessionLocal()
    
    def create_application(self, discord_user_id: str, discord_username: str, 
                          roblox_username: str, experience: str, why_middleman: str,
                          availability: str, additional_info: str = "", image_urls: List[str] = None):
        """Crear nueva aplicación de middleman usando Supabase client"""
        if not self.supabase_client:
            return {"success": False, "error": "Sistema de base de datos no disponible"}
            
        try:
            # Verificar si ya tiene una aplicación pendiente
            existing_check = self.supabase_client.table("middleman_applications").select("id").eq("discord_user_id", discord_user_id).eq("status", "pending").execute()
            
            if existing_check.data:
                return {"success": False, "error": "Ya tienes una aplicación pendiente"}
            
            # Crear nueva aplicación
            application_data = {
                "discord_user_id": discord_user_id,
                "discord_username": discord_username,
                "roblox_username": roblox_username,
                "experience": experience,
                "why_middleman": why_middleman,
                "availability": availability,
                "additional_info": additional_info,
                "image_urls": json.dumps(image_urls or []),
                "status": "pending",
                "submitted_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase_client.table("middleman_applications").insert(application_data).execute()
            
            if result.data:
                application_id = result.data[0]["id"]
                logger.info(f"Nueva aplicación de middleman creada por {discord_username} (ID: {application_id})")
                return {"success": True, "application_id": application_id}
            else:
                return {"success": False, "error": "No se pudo crear la aplicación"}
            
        except Exception as e:
            logger.error(f"Error creando aplicación: {e}")
            return {"success": False, "error": str(e)}
    
    def get_application(self, application_id: int):
        """Obtener aplicación por ID usando Supabase client"""
        if not self.supabase_client:
            return None
            
        try:
            result = self.supabase_client.table("middleman_applications").select("*").eq("id", application_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error obteniendo aplicación: {e}")
            return None
    
    def approve_application(self, application_id: int, admin_id: str, admin_notes: str = ""):
        """Aprobar aplicación y crear perfil de middleman usando Supabase client"""
        if not self.supabase_client:
            return {"success": False, "error": "Sistema de base de datos no disponible"}
            
        try:
            # Obtener aplicación
            application = self.get_application(application_id)
            
            if not application:
                return {"success": False, "error": "Aplicación no encontrada"}
            
            if application["status"] != "pending":
                return {"success": False, "error": "La aplicación ya fue procesada"}
            
            # Actualizar aplicación
            update_data = {
                "status": "approved",
                "reviewed_at": datetime.utcnow().isoformat(),
                "reviewed_by": admin_id,
                "admin_notes": admin_notes
            }
            
            self.supabase_client.table("middleman_applications").update(update_data).eq("id", application_id).execute()
            
            # Crear perfil de middleman
            profile_data = {
                "discord_user_id": application["discord_user_id"],
                "discord_username": application["discord_username"],
                "roblox_username": application["roblox_username"],
                "bio": f"Experiencia: {application['experience'][:200]}...",
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "last_active": datetime.utcnow().isoformat()
            }
            
            profile_result = self.supabase_client.table("middleman_profiles").insert(profile_data).execute()
            
            if profile_result.data:
                profile_id = profile_result.data[0]["id"]
                logger.info(f"Aplicación {application_id} aprobada por admin {admin_id}")
                return {"success": True, "profile_id": profile_id}
            else:
                return {"success": False, "error": "No se pudo crear el perfil"}
            
        except Exception as e:
            logger.error(f"Error aprobando aplicación: {e}")
            return {"success": False, "error": str(e)}
    
    def reject_application(self, application_id: int, admin_id: str, admin_notes: str = ""):
        """Rechazar aplicación usando Supabase client"""
        if not self.supabase_client:
            return {"success": False, "error": "Sistema de base de datos no disponible"}
            
        try:
            # Obtener aplicación
            application = self.get_application(application_id)
            
            if not application:
                return {"success": False, "error": "Aplicación no encontrada"}
            
            if application["status"] != "pending":
                return {"success": False, "error": "La aplicación ya fue procesada"}
            
            # Actualizar aplicación
            update_data = {
                "status": "rejected",
                "reviewed_at": datetime.utcnow().isoformat(),
                "reviewed_by": admin_id,
                "admin_notes": admin_notes
            }
            
            self.supabase_client.table("middleman_applications").update(update_data).eq("id", application_id).execute()
            
            logger.info(f"Aplicación {application_id} rechazada por admin {admin_id}")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Error rechazando aplicación: {e}")
            return {"success": False, "error": str(e)}
    
    def get_active_middlemans(self, limit: int = 50):
        """Obtener middlemans activos ordenados por rating"""
        db = self.get_db()
        try:
            return db.query(MiddlemanProfile).filter(
                MiddlemanProfile.is_active == True
            ).order_by(MiddlemanProfile.rating_average.desc()).limit(limit).all()
        finally:
            db.close()
    
    def add_rating(self, middleman_discord_id: str, rater_discord_id: str, 
                   rater_username: str, rating: int, comment: str = "", 
                   trade_description: str = ""):
        """Añadir calificación a middleman"""
        if not self.SessionLocal:
            return {"success": False, "error": "Sistema de base de datos no disponible"}
            
        db = self.get_db()
        try:
            # Encontrar middleman
            middleman = db.query(MiddlemanProfile).filter(
                MiddlemanProfile.discord_user_id == middleman_discord_id
            ).first()
            
            if not middleman:
                return {"success": False, "error": "Middleman no encontrado"}
            
            # Verificar que no haya calificado antes (opcional)
            existing_rating = db.query(MiddlemanRating).filter(
                MiddlemanRating.middleman_id == middleman.id,
                MiddlemanRating.rater_discord_id == rater_discord_id
            ).first()
            
            if existing_rating:
                return {"success": False, "error": "Ya calificaste a este middleman"}
            
            # Crear calificación
            new_rating = MiddlemanRating(
                middleman_id=middleman.id,
                rater_discord_id=rater_discord_id,
                rater_username=rater_username,
                rating=rating,
                comment=comment,
                trade_description=trade_description
            )
            
            db.add(new_rating)
            
            # Actualizar promedio del middleman
            self._update_middleman_rating(db, middleman.id)
            
            db.commit()
            
            logger.info(f"Nueva calificación añadida para middleman {middleman_discord_id}: {rating} estrellas")
            return {"success": True}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error añadiendo calificación: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    def _update_middleman_rating(self, db: Session, middleman_id: int):
        """Actualizar promedio de calificación"""
        ratings = db.query(MiddlemanRating).filter(MiddlemanRating.middleman_id == middleman_id).all()
        
        if ratings:
            total = sum(r.rating for r in ratings)
            average = total / len(ratings)
            
            # Usar update() en lugar de asignar directamente
            db.query(MiddlemanProfile).filter(MiddlemanProfile.id == middleman_id).update({
                MiddlemanProfile.rating_average: round(average, 2),
                MiddlemanProfile.rating_count: len(ratings)
            })
    
    def create_report(self, target_discord_id: str, reporter_discord_id: str,
                     reporter_username: str, category: str, description: str,
                     evidence_urls: List[str] = None):
        """Crear reporte contra middleman"""
        if not self.SessionLocal:
            return {"success": False, "error": "Sistema de base de datos no disponible"}
            
        db = self.get_db()
        try:
            # Encontrar middleman
            middleman = db.query(MiddlemanProfile).filter(
                MiddlemanProfile.discord_user_id == target_discord_id
            ).first()
            
            if not middleman:
                return {"success": False, "error": "Middleman no encontrado"}
            
            report = MiddlemanReport(
                target_middleman_id=middleman.id,
                reporter_discord_id=reporter_discord_id,
                reporter_username=reporter_username,
                category=category,
                description=description,
                evidence_urls=json.dumps(evidence_urls if evidence_urls else [])
            )
            
            db.add(report)
            db.commit()
            
            logger.info(f"Nuevo reporte creado contra middleman {target_discord_id} por {reporter_username}")
            return {"success": True, "report_id": report.id}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creando reporte: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    def get_pending_applications(self, limit: int = 20):
        """Obtener aplicaciones pendientes"""
        if not self.SessionLocal:
            return []
            
        db = self.get_db()
        try:
            return db.query(MiddlemanApplication).filter(
                MiddlemanApplication.status == ApplicationStatus.PENDING.value
            ).order_by(MiddlemanApplication.submitted_at.asc()).limit(limit).all()
        finally:
            db.close()
    
    def get_open_reports(self, limit: int = 20):
        """Obtener reportes abiertos"""
        if not self.SessionLocal:
            return []
            
        db = self.get_db()
        try:
            return db.query(MiddlemanReport).filter(
                MiddlemanReport.status == ReportStatus.OPEN.value
            ).order_by(MiddlemanReport.created_at.asc()).limit(limit).all()
        finally:
            db.close()
    
    def get_active_middlemans(self, limit: int = 50):
        """Obtener middlemans activos ordenados por rating"""
        if not self.SessionLocal:
            return []
            
        db = self.get_db()
        try:
            return db.query(MiddlemanProfile).filter(
                MiddlemanProfile.is_active == True
            ).order_by(MiddlemanProfile.rating_average.desc()).limit(limit).all()
        finally:
            db.close()
    
    def get_application(self, application_id: int):
        """Obtener aplicación por ID"""
        if not self.SessionLocal:
            return None
            
        db = self.get_db()
        try:
            return db.query(MiddlemanApplication).filter(MiddlemanApplication.id == application_id).first()
        finally:
            db.close()
    
    async def upload_image(self, image_data: bytes, filename: str, folder: str = "middleman") -> Optional[str]:
        """Subir imagen a Supabase Storage"""
        if not self.supabase_client:
            logger.error("Cliente de Supabase no disponible")
            return None
            
        try:
            # Crear bucket si no existe
            try:
                self.supabase_client.storage.create_bucket(folder)
            except:
                pass  # Bucket ya existe
            
            # Subir imagen
            file_path = f"{folder}/{filename}"
            response = self.supabase_client.storage.from_(folder).upload(file_path, image_data)
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error subiendo imagen: {response.error}")
                return None
            
            # Obtener URL pública
            public_url = self.supabase_client.storage.from_(folder).get_public_url(file_path)
            return public_url
            
        except Exception as e:
            logger.error(f"Error subiendo imagen a Supabase: {e}")
            return None

# Función para configurar el sistema
def setup_middleman_system(bot):
    """Configurar sistema de middleman"""
    try:
        middleman_system = MiddlemanSystem(bot)
        bot.middleman_system = middleman_system
        logger.info("Sistema de middleman configurado exitosamente")
        return middleman_system
    except Exception as e:
        logger.error(f"Error configurando sistema de middleman: {e}")
        return None