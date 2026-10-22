# S3 · Soda Core : intégrité entre tables, portes en SodaCL

Groupe : [À COMPLÉTER]  ·  Date : [À COMPLÉTER]  ·  Rédacteur : [À COMPLÉTER]  ·  Étiquette : `seance-3`

Un constat = un chiffre mesuré (règle, couche) + la preuve qui le reproduit + ce que cela change. Voir `README.md`.

## 1. Checks et configuration (US-12)

Configuration : `soda/configuration.yml` (une source CRM, Bronze, Silver et Gold). Connexion interne : mariadb:3306 ; mapping Windows inchangé : 3307:3306. Soda Core 3.3.5.

Les fichiers source fournis restent inchangés. Les checks Bronze utilisent les noms crm_client, crm_contrat, crm_type_contrat et crm_sinistre. Chaque nom indique sa règle et BRONZE. Ils diagnostiquent les données brutes : un FAILED est une anomalie observée, pas une panne du programme. Aucun scan ne contient d'erreur technique.

| Règle / contrôle | Fichier | Couche | Résultat | Valeur mesurée | Code retour |
|---|---|---|---|---|---|
| RQ-003 telephone du souscripteur renseigne BRONZE | soda/checks/client_bronze_checks.yml | BRONZE | FAILED | 5989 | 2 |
| RQ-005 code postal sur 5 chiffres (France) BRONZE | soda/checks/client_bronze_checks.yml | BRONZE | FAILED | 1456 | 2 |
| RQ-007 pays dans la liste de reference BRONZE | soda/checks/client_bronze_checks.yml | BRONZE | FAILED | 3050 | 2 |
| RQ-015 prospect sans crm_contrat BRONZE | soda/checks/client_bronze_checks.yml | BRONZE | FAILED | 479 | 2 |
| RQ-020 BRONZE duplicate_count(client_id) = 0 | soda/checks/client_bronze_checks.yml | BRONZE | PASSED | 0 | 2 |
| RQ-020 BRONZE missing_count(client_id) = 0 | soda/checks/client_bronze_checks.yml | BRONZE | PASSED | 0 | 2 |
| RQ-009 type de personne autorise BRONZE | soda/checks/client_bronze_checks.yml | BRONZE | FAILED | 200 | 2 |
| RQ-001 date de fin posterieure a la date de debut BRONZE | soda/checks/contrat_bronze_checks.yml | BRONZE | FAILED | 800 | 2 |
| RQ-011 type de crm_contrat connu BRONZE | soda/checks/contrat_bronze_checks.yml | BRONZE | FAILED | 200 | 2 |
| RQ-012 souscripteur existant BRONZE | soda/checks/contrat_bronze_checks.yml | BRONZE | FAILED | 1000 | 2 |
| RQ-018 BRONZE ecart definitions initiales | soda/checks/contrat_bronze_checks.yml | BRONZE | FAILED | 11878 | 2 |
| RQ-020 BRONZE duplicate_count(contrat_id) = 0 | soda/checks/contrat_bronze_checks.yml | BRONZE | PASSED | 0 | 2 |
| RQ-020 BRONZE missing_count(contrat_id) = 0 | soda/checks/contrat_bronze_checks.yml | BRONZE | PASSED | 0 | 2 |
| RQ-010 duree de garantie autorisee BRONZE | soda/checks/contrat_bronze_checks.yml | BRONZE | FAILED | 600 | 2 |
| RQ-013 assure existant (sentinelle 0 exclue) BRONZE | soda/checks/contrat_bronze_checks.yml | BRONZE | FAILED | 300 | 2 |
| RQ-017 crm_sinistre hors periode de garantie BRONZE | soda/checks/sinistre_bronze_checks.yml | BRONZE | FAILED | 1200 | 2 |
| RQ-014 BRONZE taux erreur BAN | soda/checks/sinistre_bronze_checks.yml | BRONZE | FAILED | 12.1 | 2 |
| RQ-020 BRONZE sinistre identifiant renseigne | soda/checks/sinistre_bronze_checks.yml | BRONZE | PASSED | 0 | 2 |
| RQ-020 identifiant de crm_sinistre unique BRONZE | soda/checks/sinistre_bronze_checks.yml | BRONZE | PASSED | 0 | 2 |
| RQ-014 code postal de crm_sinistre sur 5 chiffres BRONZE | soda/checks/sinistre_bronze_checks.yml | BRONZE | PASSED | 0 | 2 |
| RQ-014 BRONZE adresse sinistre renseignee | soda/checks/sinistre_bronze_checks.yml | BRONZE | PASSED | 0 | 2 |

Preuves : `reports/s3/validation_us12_us16/us12.json` et les fichiers JSON/log de ce même dossier. Depuis Jupyter, à la racine /home/jovyan/work :

`soda scan -d bronze -c soda/configuration.yml soda/checks/client_bronze_checks.yml`

Reprendre la même commande avec contrat_bronze_checks.yml puis sinistre_bronze_checks.yml. Les checks utilisent toutes les lignes Bronze : prérequis vérifié, un seul lot L-2026-10-01 dans les sept tables. Le prérequis de scan a été vérifié : un seul lot est présent ; adapter les filtres avant un futur lot.

### Précondition Bronze

Les sept tables sont alimentées (385262 lignes au total), dont 100000 clients, contrats et sinistres. Ces prérequis et le lot unique sont vérifiés par pipelines/validation_us12_us16.py. Les comptages et sommes de contrôle des sources et de Bronze sont identiques avant/après la validation. Preuve : reports/s3/validation_us12_us16/us12.json. Aucune ingestion ni modification de données n'est nécessaire pour reproduire US-12/US-16.

### WARN, FAIL et code retour

Démonstrations isolées sur le comptage réel de crm_contrat (100000 lignes), sans changer une donnée : `soda/checks/us12_pass.yml`, `us12_warn.yml`, `us12_fail.yml`. Résultats constatés : PASS → 0 ; WARN seul → 1 ; FAIL → 2. Donc WARN rend aussi le code non nul dans Soda Core 3.3.5. Un pipeline doit distinguer 1 (avertissement) de 2 (règle en échec), et traiter les erreurs techniques séparément. Les trois scans métier renvoient 2. Ces seuils de comptage sont une démonstration technique, pas une nouvelle règle métier RQ-020. Les logs et JSON sont dans reports/s3/validation_us12_us16/.

### Cohérence avec Great Expectations S2

Comparaison avec la sortie enregistrée de la cellule bilan de `notebooks/S2_01.ipynb` : RQ-001 = 800 ; RQ-003 = 5989 sur 49898 souscripteurs ; RQ-005 = 1456 sur 95437 adresses FR ; RQ-007 = 3050 ; RQ-009 = 200 ; RQ-010 = 600 ; RQ-020 = 0. Ces volumes d'écart concordent avec les scans Bronze. S2 applique mostly=98 % à RQ-005 : 98,474 % est conforme, tandis que le check Soda fourni exige zéro ligne en échec et produit FAILED. Pour RQ-003, GE est sous 98 % et Soda échoue également ; le catalogue classe toutefois cette règle en avertissement. On conserve ici les seuils diagnostiques stricts des gabarits du professeur ; ces scans ne constituent pas à eux seuls la politique finale de publication. Les seuils/sevérités de production restent à valider par le Data Owner. RQ-014 format et BAN sont deux volets distincts : le format peut passer alors que le rapprochement BAN échoue.

### Revalidation personnelle US-12

Exécution UTC : 2026-10-22T17:37:16.919175+00:00 (22/10/2026, fuseau local Europe/Paris). Périmètre de cette intervention : US-12 et US-16 uniquement. Les sections des autres US sont conservées sans modification.

Objectif : prouver les contrôles automatisés sur les trois tables Bronze alimentées et distinguer anomalies métier et erreurs techniques.

| Critère US-12 | Validation mesurée |
|---|---|
| Configuration CRM / Bronze / Silver / Gold | Quatre connexions réelles réussies avec les paramètres du fichier de configuration ; port interne 3306, port Windows 3307 conservé |
| Règle et couche identifiables | Identifiants RQ et BRONZE vérifiés pour chacun des 21 checks principaux |
| Cohérence du schéma | Colonnes réelles inventoriées et 21 checks exécutés sans erreur technique |
| Tables alimentées | client 100000, contrat 100000, sinistre 100000 ; les sept tables totalisent 385262 lignes |
| Résultats des trois scans | 8 PASSED, 13 FAILED, 0 WARN ; chaque scan principal renvoie 2 |
| PASS / WARN / FAIL | Trois démonstrations isolées exécutées : codes 0 / 1 / 2, sans modifier les données ni les seuils métier |
| Porte de qualité exploitable | RQ-007, RQ-011, RQ-012 et RQ-013 restent FAILED ; code 2 distinct d'un WARN seul (1). Une erreur technique est traitée séparément et invalide la validation |
| Reproductibilité et preuves | Script pipelines/validation_us12_us16.py --part all ; JSON et logs dédiés dans reports/s3/validation_us12_us16/ |
| Protection des données | Comptages et sommes CRC sur toutes les colonnes des sept sources et sept tables Bronze identiques avant/après les scans ; aucune ingestion relancée |
| Limites métier | Aucun seuil métier changé. Les écarts GE/Soda déjà expliqués restent applicables ; les décisions de publication relèvent du Data Owner et ne sont pas présentées comme approuvées |

Correction technique : la requête RQ-007 de client_bronze_checks.yml utilise désormais `pays IS NULL OR NOT EXISTS (...)` avec comparaison BINARY exacte. Elle détecte les NULL au lieu de les laisser échapper à NOT IN. Aucun TRIM/UPPER n'est appliqué pour masquer une anomalie ; les espaces et la casse restent significatifs. Le résultat réel reste 3050 échecs. Les autres checks et leurs seuils sont conservés.

Statut US-12 : **TERMINÉE**, sur la base des exécutions et des preuves actuelles, sans approbation métier présumée.

## 2. Bilan d'intégrité (US-16)

Objectif : mesurer RQ-007, RQ-011, RQ-012 et RQ-013, avec deux relations complémentaires. Couche BRONZE, lot L-2026-10-01. Aucune donnée corrigée. Les NULL sont séparés des références non nulles inexistantes. Pour RQ-007, le nombre d'anomalies inclut les NULL ; pour les liens optionnels, ils sont reportés séparément et ne sont pas considérés comme orphelins. Les clés Bronze utilisent utf8mb4_nopad_bin, vérifié pour chaque relation.

| Règle / contrôle | Relation | Testées | NULL | Orphelins non nuls | Anomalies retenues | Taux d'échec | Conclusion |
|---|---|---|---|---|---|---|---|
| RQ-012 | crm_contrat.souscripteur_id → bronze.crm_client.client_id | 100000 | 0 | 1000 | 1000 | 1.0 % | Anomalie bloquante : souscripteur inexistant |
| RQ-013 brut | crm_contrat.assure_id → bronze.crm_client.client_id | 100000 | 0 | 40300 | 40300 | 40.3 % | Diagnostic brut : 40000 sentinelles et 300 références invalides |
| RQ-013 | crm_contrat.assure_id → bronze.crm_client.client_id | 100000 | 0 | 300 | 300 | 0.3 % | Anomalie bloquante après exclusion de la sentinelle |
| RQ-011 | crm_contrat.code_type → bronze.crm_type_contrat.code_type | 100000 | 0 | 200 | 200 | 0.2 % | Anomalie bloquante : type absent du catalogue |
| Lien sinistre | crm_sinistre.contrat_id → bronze.crm_contrat.contrat_id | 100000 | 0 | 0 | 0 | 0.0 % | Normal sur ce lot : tous les contrats existent |
| Lien CIF | cif_compte.column1 → bronze.cif_clients.column0 | 45000 | 0 | 0 | 0 | 0.0 % | Normal sur ce lot : tous les clients CIF existent |
| RQ-007 | crm_client.pays → silver.ref_pays.code_pays | 100000 | 0 | 3050 | 3050 | 3.05 % | Anomalie bloquante : pays absent du référentiel exact ; NULL également non conforme |

La distinction avant/après sentinelle sert uniquement à rendre RQ-013 interprétable dans US-16 : aucune modification de la section US-17, aucune conversion en base. Les 40000 valeurs '0' ne représentent pas des clients manquants ; 300 vrais assurés restent absents. Le taux de 0,3 % porte sur tous les 100000 contrats ; 300/60000 = 0,5 % parmi les références effectivement renseignées après exclusion.

### RQ-007 : NULL, espaces et référentiel

Référentiel réel silver.ref_pays : 250 lignes, 250 codes distincts, 0 NULL. Comparaison exacte BINARY, sans normaliser Bronze.

| Diagnostic pays CRM | Nombre |
|---|---|
| Lignes testées | 100000 |
| NULL | 0 |
| Chaînes vides ou composées de blancs | 400 |
| Valeurs avec espaces extérieurs | 0 |
| Valeurs invalides qui deviendraient valides après TRIM | 0 |

Ces diagnostics peuvent se recouper : ne pas les additionner. Les 3050 anomalies RQ-007 sont dénombrées une seule fois par la condition d'échec. Un test synthétique uniquement en SELECT couvre huit cas (NULL, FR, FR avec espace final, FR avec espace initial, vide, blancs, fr, ZZ) : seul FR passe. Le test vérifie les cas NULL et espaces même s'ils sont absents du lot, sans insertion en base.

### Concordance et preuves

Les sept mesures SQL concordent exactement avec les sept métriques Soda du fichier dédié soda/checks/us16_relations_checks.yml. Le scan relationnel renvoie 2 pour les anomalies présentes ; les relations sans anomalie passent. RQ-007, RQ-011, RQ-012 et RQ-013 concordent aussi avec les scans principaux US-12. Les deux liens complémentaires portent US-16 : aucun identifiant RQ fictif n'est attribué à une règle absente du catalogue.

Preuves : pipelines/validation_us12_us16.py (requêtes SQL et assertions), reports/s3/validation_us12_us16/us16.json (mesures, diagnostics, test synthétique), relations.json et relations.log (Soda), us12.json (scans principaux et prérequis). Reproduction depuis /home/jovyan/work : `python pipelines/validation_us12_us16.py --part all`. Les cellules US-12 puis US-16 exécutent ces mêmes fonctions, sans appeler pipelines/s3_integrite.py qui traite aussi les US des collègues.

| Critère US-16 | Validation |
|---|---|
| RQ-007 / 011 / 012 / 013 couvertes | Oui, mesures réexécutées sur Bronze |
| Requêtes et jointures | Comparaison exacte, références Bronze filtrées sur le même lot, aucune multiplication des lignes par jointure |
| Orphelins et NULL distingués | Colonnes distinctes pour chaque relation ; aucun NULL observé sur ce lot |
| Sentinelle prise en compte | 40300 avant, 300 après ; aucune prise en charge supplémentaire de l'US-17 |
| RQ-007 complète | Référentiel contrôlé ; NULL et espaces vérifiés sur données réelles et jeu SELECT synthétique |
| Table de synthèse complète | Sept lignes avec population, NULL, anomalies, taux et conclusion, dont RQ-007 |
| Concordance Soda / SQL | Assertions réussies pour les sept relations et les quatre RQ des scans principaux |
| Décisions honnêtes | Corrections à proposer au Data Steward / Data Owner ; aucune approbation attribuée |

Conséquence métier : les contrats avec souscripteur, assuré réel ou type inexistant doivent être instruits avant certification ; les pays hors référentiel demandent une décision de standardisation ou une correction à la source. La mesure est faite par l'ingénieur qualité. Le traitement métier est proposé au Data Steward et au Data Owner, sans validation présumée et sans modification des sources ou de Bronze.

Statut US-16 : **TERMINÉE** pour le contrôle et sa justification ; les anomalies métier demeurent volontairement visibles.

## 3. Valeur sentinelle (US-17)

| Contrôle | Orphelins | Preuve |
|---|---|---|
| Sur `assure_id`, avant traitement de la sentinelle | … | … |
| Sur `assure_id`, après traitement | … | … |

Écart chiffré et convention écrite (comment la valeur sentinelle est traitée, par qui, dans quelle couche) : [À COMPLÉTER]

Pourquoi le premier contrôle est trompeur : [À COMPLÉTER]

## 4. Statuts et garantie (US-18, US-19)

| Règle | Couche | Lignes testées | Échecs | Taux |
|---|---|---|---|---|
| RQ-015 (prospect sans contrat) | … | … | … | … |
| RQ-016 | … | … | … | … |
| RQ-017 (sinistre hors garantie) | … | … | … | … |

Règle de correction du statut proposée au Data Owner (texte, rôle, date) : [À COMPLÉTER]. Reportez-la dans `JOURNAL_DECISIONS.md`.

## 5. Définition unique du client actif (US-14)

Requête (chemin) : [À COMPLÉTER]

| Direction | Chiffre obtenu avec la requête unique |
|---|---|
| Commerciale | … |
| Sinistres | … |
| Risques | … |

Contrôle RQ-018 (écart entre définitions) : [À COMPLÉTER]

## 6. Critères de fin

- [ ] Un scan renvoie un code retour non nul quand une règle bloquante échoue.
- [ ] Chaque contrôle porte l'identifiant de sa règle et la couche mesurée.
- [ ] Les trois directions obtiennent le même chiffre avec la requête unique.
- [ ] La valeur sentinelle est expliquée et traitée.

## 7. Difficultés, écarts avec l'attendu, reprise

Difficultés rencontrées et temps perdu : [À COMPLÉTER]

Point de reprise utilisé (oui / non, lequel) : [À COMPLÉTER]

Ce que nous ferions autrement : [À COMPLÉTER]
