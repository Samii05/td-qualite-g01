-- Diagnostic US-25 : lecture seule, lot de référence du TD.
SET @batch = 'L-2026-10-01';
SELECT source_systeme, source_id, silver_row_id, bronze_row_id, _batch_id,
       identite_normalisee, adresse_normalisee, cp, ville_normalisee,
       pays_iso, telephone_normalise, email_normalise, date_naissance
FROM silver.client
WHERE _batch_id=@batch AND
 ((source_systeme='crm' AND source_id IN ('A-4471','H-9012','S-2208'))
  OR (source_systeme='cif' AND source_id='K471226'))
ORDER BY source_systeme,source_id;

-- Vérifier l'absence de rattachement préalable contradictoire avant toute insertion.
SELECT * FROM gold.client_unique WHERE cli_id='CLI-000482';
SELECT * FROM gold.xref_identifiants
WHERE cli_id='CLI-000482'
 OR (source_systeme='crm' AND source_id IN ('A-4471','H-9012','S-2208'))
 OR (source_systeme='cif' AND source_id='K471226');

-- Les métadonnées permettent de vérifier le schéma réel sans le modifier.
SELECT table_schema,table_name,column_name,column_type
FROM information_schema.columns
WHERE table_schema='gold' ORDER BY table_name,ordinal_position;
