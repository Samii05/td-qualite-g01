# US-11 — Extraction des lignes en échec

## Objectif
Extraire les lignes qui échouent aux contrôles de qualité des données afin de faciliter leur analyse et leur correction par les équipes concernées.

## Réalisations
- Extraction des lignes en échec pour les règles RQ-001, RQ-002, RQ-003, RQ-005, RQ-009 et RQ-010.
- Ajout des informations de traçabilité : règle, table source, famille d’erreur, cause probable et action proposée.
- Contrôle des clés principales pour les tables `crm_client`, `crm_contrat`, `crm_sinistre` et `cif_clients` : aucune clé absente ou dupliquée détectée.
- Génération d’un export complet et d’un échantillon commenté de 20 lignes.

## Fichiers générés
- `reports/ge/us11_lignes_en_echec.csv`
- `reports/ge/us11_echantillon_20_lignes.csv`
- `reports/ge/us11_echantillon_20_lignes_commentees.csv`

## Résultats observés
L’extraction a produit 9 268 lignes pour les six règles traitées avant l’ajout du contrôle RQ-020. Les résultats de RQ-005 et RQ-009 présentent encore des écarts avec le bilan de référence ; ils doivent être vérifiés avant validation définitive.

## Points restant à finaliser
- Intégrer RQ-020 dans l’export complet et vérifier le résultat final.
- Vérifier les écarts RQ-005 et RQ-009.
- Vérifier la conformité des résultats avec les tests Great Expectations.
