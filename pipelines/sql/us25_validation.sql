-- Validation du golden record et de ses quatre identifiants attendus.
SELECT * FROM gold.v_us25_meunier;

WITH attendus AS (
 SELECT 'crm' source_systeme,'A-4471' source_id
 UNION ALL SELECT 'crm','H-9012'
 UNION ALL SELECT 'crm','S-2208'
 UNION ALL SELECT 'cif','K471226'
)
SELECT COUNT(*) identifiants_attendus,
       SUM(x.cli_id='CLI-000482') identifiants_retrouves,
       100.0*SUM(x.cli_id='CLI-000482')/COUNT(*) couverture_pct
FROM attendus a LEFT JOIN gold.xref_identifiants x
 ON x.source_systeme=a.source_systeme AND x.source_id=a.source_id;

SELECT source_systeme,source_id,COUNT(*) occurrences
FROM gold.xref_identifiants WHERE cli_id='CLI-000482'
GROUP BY source_systeme,source_id HAVING COUNT(*)<>1;

SELECT x.* FROM gold.xref_identifiants x
LEFT JOIN silver.client s ON s.silver_row_id=x.silver_row_id
 AND s.source_systeme=x.source_systeme AND s.source_id=x.source_id
 AND s.bronze_row_id=x.bronze_row_id AND s._batch_id='L-2026-10-01'
WHERE x.cli_id='CLI-000482' AND s.silver_row_id IS NULL;
