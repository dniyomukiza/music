# Database Migration Instructions

## Problem
The database is missing columns that were added to the models:
- `investment_campaigns.cancelled_at`
- `investment_campaigns.cancellation_reason`
- `book_investments.refunded_at`
- `reviewer_earnings.is_guarantee_payment`
- `reviewer_earnings.notes`
- `refund_requests` table (new table)

## Solution

Run the migration script `add_accountability_columns.sql` on your PostgreSQL database.

---

## Option 1: Using psql (Recommended)

This is the easiest method. Before running, ensure the `DATABASE_URL` environment variable is set to your database connection string.

```bash
# Example of setting the environment variable
export DATABASE_URL="postgresql://user:password@host:port/dbname"

# Run the migration script
./run_migration.sh
```

The script will use the `DATABASE_URL` from your environment.

---

## Option 2: Using Python Script

You can use the `run_migration.py` script. It also uses the `DATABASE_URL` environment variable.

```bash
# Example of setting the environment variable
export DATABASE_URL="postgresql://user:password@host:port/dbname"

# Run the python migration script
./run_migration.py
```

---

## Option 3: Using Database GUI Tool

1. Connect to your PostgreSQL database using:
   - **pgAdmin**
   - **DBeaver**
   - **TablePlus**
   - **DataGrip**
   - Or any PostgreSQL client

2. Open the SQL editor

3. Copy and paste the contents of `add_accountability_columns.sql`

4. Execute the script

---

## Option 4: Using Flask-Migrate (If Set Up)

If you have Flask-Migrate configured:

```bash
# Create a new migration
flask db migrate -m "Add accountability columns"

# Apply the migration
flask db upgrade
```

---

## Option 5: Direct SQL Execution

Connect to your database and run these SQL commands:

```sql
-- Add cancelled_at and cancellation_reason to investment_campaigns
ALTER TABLE investment_campaigns 
ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS cancellation_reason TEXT;

-- Add refunded_at to book_investments
ALTER TABLE book_investments 
ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMP;

-- Add is_guarantee_payment and notes to reviewer_earnings
ALTER TABLE reviewer_earnings 
ADD COLUMN IF NOT EXISTS is_guarantee_payment BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS notes TEXT;

-- Create refund_requests table
CREATE TABLE IF NOT EXISTS refund_requests (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    reason TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP,
    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    refund_transaction_id VARCHAR(100),
    payment_method VARCHAR(50),
    investment_id INTEGER NOT NULL REFERENCES book_investments(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_refund_requests_investment_id ON refund_requests(investment_id);
CREATE INDEX IF NOT EXISTS idx_refund_requests_status ON refund_requests(status);
```

---

## Verify Migration

After running the migration, verify it worked:

```sql
-- Check if columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'investment_campaigns' 
AND column_name IN ('cancelled_at', 'cancellation_reason');

SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'book_investments' 
AND column_name = 'refunded_at';

SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'reviewer_earnings' 
AND column_name IN ('is_guarantee_payment', 'notes');

-- Check if refund_requests table exists
SELECT table_name 
FROM information_schema.tables 
WHERE table_name = 'refund_requests';
```

---

## After Migration

1. **Restart your Flask server** to ensure it picks up the changes
2. **Test the system** - The error should be resolved
3. **Verify functionality** - All accountability features should work

---

## Troubleshooting

### Error: "column already exists"
- This is OK - the `IF NOT EXISTS` clause prevents errors
- The migration is idempotent (safe to run multiple times)

### Error: "permission denied"
- Check database user permissions
- Ensure user has ALTER TABLE privileges

### Error: "relation does not exist"
- Make sure you're connected to the correct database
- Verify table names match your schema

---

## Quick Test

After migration, test by visiting:
- `http://localhost:5000/mybook/investments` - Should load without errors
- `http://localhost:5000/mybook/earnings` - Should work correctly

The ProgrammingError should be resolved! ✅


