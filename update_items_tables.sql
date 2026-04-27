-- Update items and items_review tables to add master_item and preprocessing columns

-- 1. Modify items table
ALTER TABLE items ADD COLUMN master_item VARCHAR(255);
ALTER TABLE items ADD COLUMN preprocessing JSONB;

-- 2. Modify items_review table
ALTER TABLE items_review ADD COLUMN master_item VARCHAR(255);
ALTER TABLE items_review ADD COLUMN preprocessing JSONB;

-- 3. Update indexes
CREATE INDEX IF NOT EXISTS idx_items_master_item ON items(master_item);
CREATE INDEX IF NOT EXISTS idx_items_review_master_item ON items_review(master_item);

-- Commit transaction
COMMIT;