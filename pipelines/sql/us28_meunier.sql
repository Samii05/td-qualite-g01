SELECT g.cli_id, g.nom_reference, g.cp AS cp_gold, g.telephone AS telephone_gold,
       g.email AS email_gold, g._batch_id AS lot_gold,
       x.source_systeme, x.source_id, x.silver_row_id, x.bronze_row_id,
       s._batch_id AS lot_silver, s._processed_at,
       s.identite_normalisee, s.adresse_normalisee, s.telephone_normalise, s.email_normalise,
       CASE WHEN x.source_systeme='crm' THEN b._batch_id ELSE f._batch_id END AS lot_bronze,
       CASE WHEN x.source_systeme='crm' THEN b._row_hash ELSE f._row_hash END AS empreinte_bronze,
       CASE WHEN x.source_systeme='crm' THEN b.raison_sociale ELSE f.column1 END AS identite_bronze,
       CASE WHEN x.source_systeme='crm' THEN b.adresse ELSE f.column4 END AS adresse_bronze,
       CASE WHEN x.source_systeme='crm' THEN b.telephone ELSE f.column8 END AS telephone_bronze,
       CASE WHEN x.source_systeme='crm' THEN b.email ELSE f.column9 END AS email_bronze,
       CASE WHEN x.source_systeme='crm' THEN c.raison_sociale ELSE k.column1 END AS identite_source,
       CASE WHEN x.source_systeme='crm' THEN c.adresse ELSE k.column4 END AS adresse_source,
       CASE WHEN x.source_systeme='crm' THEN 'crm.client' ELSE 'cif.clients' END AS table_source
FROM gold.client_unique g
JOIN gold.xref_identifiants x ON x.cli_id=g.cli_id
JOIN silver.client s ON s.silver_row_id=x.silver_row_id AND s.bronze_row_id=x.bronze_row_id
 AND s.source_systeme=x.source_systeme AND s.source_id=x.source_id AND s._batch_id=g._batch_id
LEFT JOIN bronze.crm_client b ON x.source_systeme='crm' AND b.bronze_row_id=x.bronze_row_id AND b.client_id=x.source_id AND b._batch_id=g._batch_id
LEFT JOIN bronze.cif_clients f ON x.source_systeme='cif' AND f.bronze_row_id=x.bronze_row_id AND f.column0=x.source_id AND f._batch_id=g._batch_id
LEFT JOIN crm.client c ON x.source_systeme='crm' AND c.client_id=x.source_id
LEFT JOIN cif.clients k ON x.source_systeme='cif' AND k.column0=x.source_id
WHERE g.cli_id='CLI-000482' AND g._batch_id='L-2026-10-01'
ORDER BY x.source_systeme,x.source_id
