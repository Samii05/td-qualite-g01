-- La table Gold de sinistres certifiés n'existe pas encore : ne pas inventer un lien Gold.
-- Preuve partielle reproductible, de Silver à la source CRM.
SELECT s.sinistre_id, s.silver_row_id, s.bronze_row_id,
       s._batch_id AS lot_silver, b._batch_id AS lot_bronze,
       c.adresse_sinistre AS adresse_source, b.adresse_sinistre AS adresse_bronze,
       s.adresse_normalisee AS adresse_silver, b.cp_sinistre AS cp_bronze, s.cp AS cp_silver,
       s.ville_normalisee, b._row_hash, b._ingested_at, s._processed_at,
       (SELECT MIN(r.id_ban) FROM silver.ref_ban r
         WHERE UPPER(CONCAT(r.numero,' ',r.voie))=s.adresse_normalisee
          AND r.code_postal=s.cp AND UPPER(r.commune)=s.ville_normalisee) AS reference_ban,
       'crm.sinistre' AS table_source
FROM silver.sinistre s
JOIN bronze.crm_sinistre b ON b.bronze_row_id=s.bronze_row_id AND b._batch_id=s._batch_id AND b.sinistre_id=s.sinistre_id
JOIN crm.sinistre c ON c.sinistre_id=s.sinistre_id
WHERE s._batch_id='L-2026-10-01'
 AND BINARY UPPER(TRIM(b.adresse_sinistre))<>BINARY s.adresse_normalisee
 AND EXISTS (SELECT 1 FROM silver.ref_ban r WHERE r.code_postal=s.cp AND UPPER(r.commune)=s.ville_normalisee AND UPPER(CONCAT(r.numero,' ',r.voie))=s.adresse_normalisee)
ORDER BY s.bronze_row_id
LIMIT 1

