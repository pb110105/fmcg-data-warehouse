\pset pager off
\set ON_ERROR_STOP on

BEGIN TRANSACTION READ ONLY;

-- 1. Tổng hợp ràng buộc theo schema.
\echo === 1. CONSTRAINT SUMMARY ===

SELECT
    n.nspname AS schema_name,
    COUNT(*) FILTER (WHERE c.contype = 'p') AS primary_keys,
    COUNT(*) FILTER (WHERE c.contype = 'f') AS foreign_keys,
    COUNT(*) FILTER (WHERE c.contype = 'u') AS unique_constraints,
    COUNT(*) FILTER (WHERE c.contype = 'c') AS table_checks
FROM pg_constraint c
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname IN ('audit', 'staging', 'dw')
  AND c.conrelid <> 0
GROUP BY n.nspname
ORDER BY n.nspname;

-- 2. Bảng thiếu khóa chính: kỳ vọng không có dòng nào.
\echo === 2. TABLES WITHOUT PRIMARY KEY ===

SELECT
    n.nspname AS schema_name,
    t.relname AS table_name
FROM pg_class t
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname IN ('audit', 'staging', 'dw')
  AND t.relkind IN ('r', 'p')
  AND NOT EXISTS (
      SELECT 1
      FROM pg_constraint c
      WHERE c.conrelid = t.oid
        AND c.contype = 'p'
  )
ORDER BY n.nspname, t.relname;

-- 3. Khóa chính, khóa ngoại và UNIQUE của kho dữ liệu.
\echo === 3. DW KEY DEFINITIONS ===

SELECT
    c.conrelid::regclass AS table_name,
    CASE c.contype
        WHEN 'p' THEN 'PRIMARY KEY'
        WHEN 'f' THEN 'FOREIGN KEY'
        WHEN 'u' THEN 'UNIQUE'
    END AS constraint_type,
    pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname = 'dw'
  AND c.contype IN ('p', 'f', 'u')
ORDER BY c.conrelid::regclass::text, constraint_type, definition;

-- 4. Ràng buộc chưa được xác thực: kỳ vọng không có dòng nào.
\echo === 4. UNVALIDATED CONSTRAINTS ===

SELECT
    n.nspname AS schema_name,
    c.conname AS constraint_name,
    pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname IN ('audit', 'staging', 'dw')
  AND NOT c.convalidated
ORDER BY n.nspname, c.conname;

-- 5. CHECK của các domain: kiểm soát mã, số lượng và tiền.
\echo === 5. DW DOMAIN CHECKS ===

SELECT
    t.typname AS domain_name,
    pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_type t ON t.oid = c.contypid
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'dw'
ORDER BY t.typname, c.conname;

COMMIT;