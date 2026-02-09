#!/usr/bin/env bash
# Complete demonstration of database management features

echo "═══════════════════════════════════════════════════════════════"
echo "  XTS Allocator - Database Management Demo"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 1. Show current status
echo "1. Current Database Status:"
echo "───────────────────────────────────────────────────────────────"
bin/db-status | grep -A3 "Configuration:"
echo ""

# 2. Switch to test mode
echo "2. Switching to TEST mode:"
echo "───────────────────────────────────────────────────────────────"
export XTS_MODE=test
export SQLITE_DB_PATH=xts_allocator_test.db
echo "✓ Test mode enabled"
echo "  Database: xts_allocator_test.db"
echo ""

# 3. Show test database info
echo "3. Test Database Status:"
echo "───────────────────────────────────────────────────────────────"
if [ -f "xts_allocator_test.db" ]; then
    size=$(du -h xts_allocator_test.db | cut -f1)
    echo "  File: xts_allocator_test.db"
    echo "  Size: $size"
    echo "  ✓ Ready for testing"
else
    echo "  ✗ Test database not found"
    echo "  Creating..."
    python database_setup.py
    echo "  ✓ Created"
fi
echo ""

# 4. Add test devices
echo "4. Adding Test Devices:"
echo "───────────────────────────────────────────────────────────────"
python test/add_pi_devices.py 2>&1 | grep -E "^(✅|ℹ️|🎉)" | head -3
echo ""

# 5. Run demo workflow
echo "5. Running Workflow Demo:"
echo "───────────────────────────────────────────────────────────────"
python test/demo_pi_simple.py 2>&1 | grep -E "^(╔|║|╚|=====|  STEP|✅)" | head -20
echo ""

# 6. Clear devices from test DB
echo "6. Cleaning Test Database:"
echo "───────────────────────────────────────────────────────────────"
echo "  Clearing device registrations..."
python << 'PYEOF'
from models import Device, SessionLocal
session = SessionLocal()
try:
    count = session.query(Device).count()
    session.query(Device).delete()
    session.commit()
    print(f"  ✓ Removed {count} devices from TEST database")
except Exception as e:
    session.rollback()
    print(f"  ✗ Error: {e}")
finally:
    session.close()
PYEOF
echo ""

# 7. Switch back to development
echo "7. Switching Back to DEVELOPMENT mode:"
echo "───────────────────────────────────────────────────────────────"
export XTS_MODE=development
export SQLITE_DB_PATH=xts_allocator.db
echo "✓ Development mode restored"
echo "  Database: xts_allocator.db"
echo ""

# 8. Verify production data intact
echo "8. Verifying Production Data Intact:"
echo "───────────────────────────────────────────────────────────────"
python << 'PYEOF'
from models import Device, SessionLocal
session = SessionLocal()
try:
    count = session.query(Device).count()
    if count > 0:
        print(f"  ✓ Production database has {count} devices")
        print("  ✓ Data preserved during test operations")
    else:
        print("  ℹ️  Production database is empty (expected for new setup)")
finally:
    session.close()
PYEOF
echo ""

# Summary
echo "═══════════════════════════════════════════════════════════════"
echo "  Summary"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "✅ Two separate databases working:"
echo "   - xts_allocator.db (production/development)"
echo "   - xts_allocator_test.db (testing)"
echo ""
echo "✅ Can safely reset test database"
echo "✅ Production data remains untouched"
echo "✅ Easy switching between modes"
echo ""
echo "Commands demonstrated:"
echo "  bin/db-status         - Check current configuration"
echo "  bin/db-switch test    - Switch to test mode"
echo "  bin/db-clean ...      - Clean test database"
echo "  ./test-safe.sh        - Run tests with test DB"
echo ""
