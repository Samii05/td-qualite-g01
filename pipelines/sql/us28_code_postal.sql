SELECT g.cli_id, g.cp AS cp_gold, g._batch_id AS lot_gold,
       s.source_id, s.source_systeme, s.silver_row_id, s.bronze_row_id,
       s._batch_id AS lot_silver, b._batch_id AS lot_bronze,
       c.cp AS cp_source, b.cp AS cp_bronze, s.cp AS cp_silver,
       s.ville_normalisee, b._row_hash, b._ingested_at, s._processed_at,
       'crm.client' AS table_source
FROM silver.client s
JOIN bronze.crm_client b ON s.source_systeme='crm' AND b.bronze_row_id=s.bronze_row_id
 AND b.client_id=s.source_id AND b._batch_id=s._batch_id
JOIN crm.client c ON c.client_id=s.source_id
LEFT JOIN gold.xref_identifiants x ON x.source_systeme=s.source_systeme AND x.source_id=s.source_id
 AND x.bronze_row_id=s.bronze_row_id AND x.silver_row_id=s.silver_row_id
LEFT JOIN gold.client_unique g ON g.cli_id=x.cli_id AND g._batch_id=s._batch_id
WHERE s._batch_id='L-2026-10-01' AND s.pays_iso='FR' AND b.cp REGEXP '^[0-9]{4}$'
 AND BINARY s.cp=BINARY LPAD(b.cp,5,'0')
ORDER BY (g.cli_id IS NULL),s.bronze_row_id
LIMIT 1
