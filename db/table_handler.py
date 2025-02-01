from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, String
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel
from sqlalchemy.dialects.mysql import VARCHAR, INTEGER, FLOAT
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Dict, Any, Optional
import logging
from auth.auth_handler import verify_auth

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, connection_url: str):
        self.engine = create_engine(
            connection_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800  # Recycle connections after 30 minutes
        )
        self.Session = sessionmaker(bind=self.engine)
    
    @contextmanager
    def get_session(self):
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

class TableData(BaseModel):
    table_name: str
    data: list[dict]
    column_definitions: dict[str, str] = None
    create_new: bool = False

def table_exists(engine: Engine, table_name: str) -> bool:
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def get_table_schema(engine: Engine, table_name: str) -> Optional[Dict[str, Any]]:
    try:
        inspector = inspect(engine)
        if not table_exists(engine, table_name):
            return None
        
        columns = inspector.get_columns(table_name)
        return {
            col['name']: {
                'type': col['type'].__class__.__name__,
                'nullable': col['nullable'],
                'default': col['default'],
            }
            for col in columns
        }
    except SQLAlchemyError as e:
        logger.error(f"Error getting schema for table {table_name}: {e}")
        raise HTTPException(status_code=500, detail="Database error")

def map_column_type(sql_type: str):
    type_map = {
        "String": VARCHAR(255),
        "Integer": INTEGER,
        "Float": FLOAT,
        "Boolean": String(5),
        "DateTime": String(255),
    }
    return type_map.get(sql_type, VARCHAR(255))


