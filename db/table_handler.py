from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, String
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel
from sqlalchemy.dialects.mysql import VARCHAR, INTEGER, FLOAT
from sqlalchemy.engine import Engine


#
class TableData(BaseModel):
    table_name: str
    data: list[dict]
    column_definitions: dict[str, str] = None
    create_new: bool = False

def table_exists(engine: Engine, table_name: str) -> bool:
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def get_table_schema(engine: Engine, table_name: str) -> dict:
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return {col['name']: col['type'].__class__.__name__ for col in columns}

def map_column_type(sql_type: str):
    type_map = {
        "String": VARCHAR(255),
        "Integer": INTEGER,
        "Float": FLOAT,
        "Boolean": String(5),
        "DateTime": String(255),
    }
    return type_map.get(sql_type, VARCHAR(255))


