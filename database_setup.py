#!/usr/bin/env python3
from models import Base, engine

# creates tables in the database
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
