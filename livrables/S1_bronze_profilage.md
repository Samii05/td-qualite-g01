# S1 · Stack Docker, profilage, construction de bronze

Groupe : [À COMPLÉTER]  ·  Date : [À COMPLÉTER]  ·  Rédacteur : [À COMPLÉTER]  ·  Étiquette : `seance-1`

Rappel : un constat = un chiffre mesuré (règle, couche) + la preuve qui le reproduit + ce que cela change. Voir `README.md`.

## 1. Inventaire des sources (US-01)

| Source | Table | Lignes | Clé primaire | Observation chiffrée |
|---|---|---|---|---|
| crm | client | … | … | … |
| crm | contrat | … | … | … |
| crm | sinistre | … | … | … |
| crm | type_contrat | … | … | … |
| cif | clients | … | … | … |
| cif | compte | … | … | … |
| cif | pays | … | … | … |

Preuve (notebook, requête) : [À COMPLÉTER]

## 2. Bronze et porte B (US-02, US-03)

Méthode d'ingestion en trois lignes (lecture, conversion, métadonnées, relance du lot) : [À COMPLÉTER]

Réconciliation RQ-021 (comptage) et RQ-022 (somme de contrôle), pour le lot mesuré :

| Table bronze | Lignes source | Lignes bronze | Écart de comptage | Écart de somme de contrôle |
|---|---|---|---|---|
| crm_client | … | … | … | … |
| crm_contrat | … | … | … | … |
| crm_sinistre | … | … | … | … |
| crm_type_contrat | … | … | … | … |
| cif_clients | … | … | … | … |
| cif_compte | … | … | … | … |
| cif_pays | … | … | … | … |

Épreuves de la porte (à documenter, avec la preuve de chacune) :

| Épreuve | Résultat obtenu | Preuve |
|---|---|---|
| Relance du même lot : doublons créés | … | … |
| Écart introduit volontairement sur une copie : la porte échoue-t-elle ? | … | … |
| Un problème de conversion rencontré (décimales, NULL, accents) et sa correction | … | … |

## 3. Profil de crm.client (US-06, US-07)

Au moins cinq constats chiffrés.

| N° | Colonne | Indicateur (nulls, vides, distincts, motif…) | Valeur mesurée | Ce que cela change pour la qualité |
|---|---|---|---|---|
| 1 | … | … | … | … |
| 2 | … | … | … | … |
| 3 | … | … | … | … |
| 4 | … | … | … | … |
| 5 | … | … | … | … |

Motifs (conformes / non conformes) :

| Attribut | Motif testé | Lignes conformes | Lignes non conformes | Exemple de valeur non conforme |
|---|---|---|---|---|
| Code postal | … | … | … | … |
| Téléphone | … | … | … | … |
| Pays | … | … | … | … |

Preuve (notebook, requête) : [À COMPLÉTER]


## 4. Dictionnaire du CIF (US-04)

Pour cette User Story, j'ai analysé la table `cif.clients`, qui contient 40 000 enregistrements et dix colonnes anonymes, nommées de `column0` à `column9`.

J'ai d'abord examiné leur structure et quelques lignes, puis j'ai calculé le nombre de valeurs distinctes, les valeurs manquantes, les longueurs et certains motifs. Cela m'a permis de proposer les noms métier suivants.

| Colonne d'origine | Nom proposé | Type SQL | Justification chiffrée |
|---|---|---|---|
| column0 | Identifiant client CIF | VARCHAR(10) | 40 000 valeurs distinctes sur 40 000 lignes, aucune manquante, longueur fixe de 7 caractères. Les 40 000 identifiants respectent le motif `K` suivi de six chiffres. |
| column1 | Nom / raison sociale | VARCHAR(120) | 731 valeurs distinctes, aucune manquante, longueur de 3 à 31 caractères. |
| column2 | Prénom | VARCHAR(80) | 180 valeurs distinctes, 645 manquantes, longueur de 3 à 10 caractères pour les valeurs présentes. |
| column3 | Date de naissance | VARCHAR(10) | 21 081 valeurs distinctes, 645 manquantes. Les 39 355 dates renseignées suivent le format `JJ/MM/AAAA`. |
| column4 | Adresse postale | VARCHAR(120) | 9 811 valeurs distinctes, aucune manquante, longueur de 11 à 31 caractères. |
| column5 | Code postal | VARCHAR(10) | 188 valeurs distinctes, aucune manquante, longueur de 4 à 8 caractères. |
| column6 | Commune | VARCHAR(80) | 172 valeurs distinctes, aucune manquante, longueur de 3 à 24 caractères. |
| column7 | Code pays | VARCHAR(5) | 9 codes distincts de deux lettres, aucune valeur manquante. Le code FR représente 39 401 clients sur 40 000. |
| column8 | Téléphone | VARCHAR(25) | 33 676 valeurs distinctes, 6 324 manquantes. Les 33 676 numéros renseignés respectent le motif testé : zéro suivi de neuf chiffres. |
| column9 | Adresse e-mail | VARCHAR(120) | 21 128 valeurs distinctes, 18 872 manquantes. Les valeurs renseignées respectent le contrôle simple de structure d'une adresse e-mail. |

### Analyse et interprétation

Ce travail m'a permis de retrouver la signification probable des dix colonnes du système CIF en m'appuyant sur les données, plutôt que sur des suppositions.

J'ai constaté que les identifiants CIF étaient tous distincts et conformes au format testé. En revanche, certaines informations sont stockées sous forme de texte, notamment les dates de naissance, ce qui nécessitera une conversion contrôlée lors de la standardisation des données.

J'ai également observé que 645 enregistrements n'avaient ni prénom ni date de naissance. Ces lignes pourraient correspondre à des personnes morales, mais cette interprétation reste à confirmer par une analyse des noms.

Enfin, les coordonnées de contact ne sont pas toutes renseignées : 6 324 téléphones et 18 872 e-mails sont manquants. Cette situation devra être prise en compte dans les futurs contrôles de qualité, sans considérer automatiquement toutes ces absences comme des erreurs.

**Preuve reproductible :** `notebooks/S1_US04_Dictionnaire_CIF.ipynb`

**Source analysée :** `cif.clients` (40 000 lignes).

**Rôle concerné :** Data Steward — proposition du dictionnaire métier, à valider avec le Data Owner.

## 5. Trois définitions du « client actif » (US-09)

| Direction | Définition utilisée | Nombre de clients | Écart avec la définition de la fiche CD-001 |
|---|---|---|---|
| Commerciale | … | … | … |
| Sinistres | … | … | … |
| Risques | … | … | … |

Conséquence pour la gouvernance, en trois phrases : [À COMPLÉTER]

## 6. Critères de fin (cochez, avec la preuve si elle n'est pas dans une section ci-dessus)

- [ ] Les sept tables bronze existent et chaque ligne porte ses quatre métadonnées.
- [ ] La porte B ne montre aucun écart de comptage ni de somme de contrôle.
- [ ] Relancer l'ingestion du même lot ne crée aucun doublon.
- [ ] Un écart introduit volontairement fait échouer la porte.
- [ ] RQ-021 est écrite dans `dq.dq_history` (couche BRONZE).

## 7. Difficultés, écarts avec l'attendu, reprise

Difficultés rencontrées et temps perdu : [À COMPLÉTER]

Point de reprise utilisé (oui / non, lequel) : [À COMPLÉTER]

Ce que nous ferions autrement : [À COMPLÉTER]
