#!/bin/bash
# Database migration script
# Usage: ./migrate.sh [command]
#
# Handles database schema migrations using Alembic.
# For fresh databases, creates schema using database_setup.py then stamps.
# For existing databases, runs Alembic migrations to upgrade schema.
#
#   Commands:
#     upgrade    - Upgrade database to latest version (default)
#     downgrade  - Downgrade database one version
#     current    - Show current migration version
#     history    - Show migration history
#     create MSG - Create new migration (autogenerate)
#     stamp      - Stamp database with current head (for fresh DBs)
#     reset      - Reset database (WARNING: destroys all data)
#     help       - Show this help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

DB_FILE="xts_allocator.db"
COMMAND="${1:-upgrade}"

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${RED}Error: venv not found. Run ./run.sh setup first.${NC}"
    exit 1
fi

# Check for alembic
if ! python3 -c "import alembic" 2>/dev/null; then
    echo -e "${YELLOW}Installing alembic...${NC}"
    pip install alembic --quiet
fi

case "$COMMAND" in
    upgrade)
        echo -e "${GREEN}Upgrading database to latest version...${NC}"
        if [ ! -f "$DB_FILE" ]; then
            echo -e "${YELLOW}Database not found, creating fresh database with current schema...${NC}"
            python database_setup.py
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Stamping database at head version...${NC}"
                alembic stamp head
                echo -e "${GREEN}✓ Database created and stamped${NC}"
            else
                echo -e "${RED}✗ Failed to create database${NC}"
                exit 1
            fi
        else
            echo -e "${YELLOW}Running migrations...${NC}"
            alembic upgrade head
            echo -e "${GREEN}✓ Database upgraded${NC}"
        fi
        ;;
    
    downgrade)
        echo -e "${YELLOW}Downgrading database one version...${NC}"
        alembic downgrade -1
        echo -e "${GREEN}✓ Database downgraded${NC}"
        ;;
    
    current)
        echo -e "${GREEN}Current migration version:${NC}"
        alembic current
        ;;
    
    history)
        echo -e "${GREEN}Migration history:${NC}"
        alembic history
        ;;
    
    create)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Migration message required${NC}"
            echo "Usage: ./migrate.sh create \"your migration message\""
            exit 1
        fi
        echo -e "${GREEN}Creating new migration: $2${NC}"
        alembic revision --autogenerate -m "$2"
        echo -e "${GREEN}✓ Migration created${NC}"
        ;;
    
    stamp)
        echo -e "${YELLOW}Stamping database with current head...${NC}"
        alembic stamp head
        echo -e "${GREEN}✓ Database stamped${NC}"
        ;;
    
    reset)
        echo -e "${RED}WARNING: This will delete the database and recreate it!${NC}"
        read -p "Are you sure? (yes/no): " -r
        if [[ $REPLY == "yes" ]]; then
            echo -e "${YELLOW}Removing database...${NC}"
            rm -f "$DB_FILE"
            echo -e "${GREEN}Creating fresh database...${NC}"
            alembic upgrade head
            echo -e "${GREEN}✓ Database reset complete${NC}"
        else
            echo -e "${YELLOW}Reset cancelled${NC}"
            exit 0
        fi
        ;;
    
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo "Usage: ./migrate.sh [command]"
        echo ""
        echo "Commands:"
        echo "  upgrade    - Upgrade database to latest version (default)"
        echo "  downgrade  - Downgrade database one version"
        echo "  current    - Show current migration version"
        echo "  history    - Show migration history"
        echo "  create MSG - Create new migration with message"
        echo "  stamp      - Stamp database with current head"
        echo "  reset      - Reset database (destroys all data)"
        exit 1
        ;;
esac
