from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

Base = declarative_base()

# Create the database engine
engine = create_engine(settings.mysql_database_url)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = None
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

# def setup_database():
#     Base.metadata.create_all(bind=engine)
# setup_database()


from sqlalchemy.exc import SQLAlchemyError
try:
    with engine.connect() as connection:
        print("Connection successful!")
except SQLAlchemyError as e:
    print(f"Connection failed: {e}")

# if __name__ == "__main__":
#     setup_database()
    # print("All tables have been created successfully!")
