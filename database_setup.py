<<<<<<< HEAD
=======
#!/usr/bin/env python3
>>>>>>> fbca4c159573e1b328f31d1278bb8633fd74a9c6
from models import Base, engine

# creates tables in the database
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
