# S4 · PySpark : construire silver puis gold

Groupe : [À COMPLÉTER]  ·  Date : [À COMPLÉTER]  ·  Rédacteur : [À COMPLÉTER]  ·  Étiquette : `seance-4`

Un constat = un chiffre mesuré (règle, couche) + la preuve qui le reproduit + ce que cela change. Voir `README.md`.

## 1. Silver et quarantaine (US-21, US-22)

Scripts ou notebooks (chemins) : [À COMPLÉTER]

Traitements appliqués (pays, code postal, identité, autres), avec le nombre de lignes touchées par chacun :

| Traitement | Table | Lignes modifiées | Garde-fou (ce que le traitement ne doit pas faire) |
|---|---|---|---|
| … | … | … | … |
| … | … | … | … |
| … | … | … | … |

Invariant silver + rejets = bronze :

| Table | Lignes bronze | Lignes silver | Lignes rejetées | Écart |
|---|---|---|---|---|
| client (crm) | … | … | … | … |
| client (cif) | … | … | … | … |
| contrat | … | … | … | … |
| sinistre | … | … | … | … |

Rejets par règle (`dq.rejets`) :

| Règle | Table | Lignes rejetées | Raison métier |
|---|---|---|---|
| … | … | … | … |
| … | … | … | … |

Idempotence : le traitement relancé deux fois donne le même résultat (preuve) : [À COMPLÉTER]

## 2. Porte S : bronze contre silver (US-23)

| Règle | Sévérité | Taux bronze | Taux silver | Écart | Explication de l'écart |
|---|---|---|---|---|---|
| … | … | … | … | … | … |
| … | … | … | … | … | … |
| … | … | … | … | … | … |
| … | … | … | … | … | … |
| … | … | … | … | … | … |

Toute règle dont le taux baisse de bronze à silver doit être expliquée : [À COMPLÉTER]

Règles bloquantes de la porte S toutes conformes sur silver ? Sinon, lesquelles et pourquoi : [À COMPLÉTER]

## 3. Dédoublonnage et golden record (US-24, US-25)

| Paramètre | Valeur retenue | Justification |
|---|---|---|
| Normalisation appliquée avant comparaison | … | … |
| Clé(s) de blocage | … | … |
| Mesure de similarité | … | … |
| Seuil de fusion automatique | … | … |
| Seuil de la zone de revue | … | … |

| Mesure | Valeur |
|---|---|
| Groupes de doublons trouvés | … |
| Paires fusionnées automatiquement | … |
| Paires en zone de revue | … |
| Précision sur les 200 paires étiquetées | … |
| Rappel sur les 200 paires étiquetées | … |
| Identités distinctes obtenues | … |

Golden record de la Société Meunier — US-25 (Mohamed, 07/11/2026) :

**TERMINÉE techniquement.** Périmètre limité au cas fil rouge explicitement demandé ; aucune règle de rapprochement général US-24 ni de certification/publication US-27 n'est ajoutée.

| Identifiant source | Système | CLI attribué | Ligne Silver | Ligne Bronze |
|---|---|---|---|---|
| K471226 | cif | CLI-000482 | 115970 | 16620 |
| A-4471 | crm | CLI-000482 | 34219 | 34450 |
| H-9012 | crm | CLI-000482 | 73325 | 73793 |
| S-2208 | crm | CLI-000482 | 87512 | 88069 |

Lot des quatre correspondances : L-2026-10-01. Couverture des identifiants attendus : **100 % (4/4)**. Aucun identifiant rattaché deux fois ; aucune ligne sans parent Silver. Le rapprochement est confirmé par l'identité normalisée commune MEUNIER SARL et le même tuple adresse/code postal/ville/pays (27 RUE PASTEUR, 69003, LYON, FR). Les identifiants ne sont pas déduits du seul patronyme : cas fil rouge du TD, trois CRM et un CIF identifié puis confirmé dans Silver et Bronze.

Golden record mesuré : nom **MEUNIER SARL**, CP **69003**, ville **LYON**, pays **FR**, téléphone **0478473441**, courriel **contact@meunier-sarl.fr**, statut **ACTIF**, naissance NULL et quatre identifiants sources.

Règles de survie proposées et appliquées techniquement pour ce cas (aucune approbation Data Owner présumée) :

| Attribut | Valeur / source retenue | Règle | Limite métier |
|---|---|---|---|
| Nom | MEUNIER SARL ; CIF K471226 | Identité normalisée commune aux quatre membres | Ne démontre pas à elle seule l'identité juridique de tous les homonymes |
| Adresse | 27 RUE PASTEUR ; CIF K471226 | Adresse commune, exposée dans gold.v_us25_meunier | Le schéma partagé gold.client_unique ne contient pas de champ adresse : la table n'a pas été altérée |
| CP / ville / pays | 69003 / LYON / FR ; CIF | Garder les attributs de la même adresse, sans recomposition entre sources | Pas de preuve de fraîcheur de l'adresse |
| Téléphone | 0478473441 ; CIF, confirmé par A-4471 | Priorité au CIF non nul ; les autres numéros restent dans les preuves | Les trois numéros distincts ne permettent pas d'inférer lequel est le plus récent |
| Courriel | contact@meunier-sarl.fr ; CIF, confirmé par A-4471 | Priorité au CIF non nul ; adresse comptabilité conservée dans la preuve | Une adresse comptable et une adresse de contact ont des usages différents |
| Naissance | NULL | Société : aucune date inventée | Pas de date de création légale dans les champs disponibles |
| Statut | ACTIF | Au moins un même contrat Silver en cours au 01/10/2026 et cotisation depuis le 01/07/2026 (CD-001) | Calcul technique, aucune certification Gold de tous les contrats présumée |
| Nombre d'identifiants | 4 | Comptage réel des correspondances distinctes | Ne remplace pas le dédoublonnage global de US-24 |

Première exécution : 1 ligne Gold et 4 correspondances insérées. Relance : **0 insertion, aucune suppression ni mise à jour**. Toute collision avec un autre CLI ou des correspondances différentes provoque un arrêt. La vue propre à US-25 présente une seule ligne et conserve le donneur CIF de l'adresse. Les signatures des sources CRM/CIF, Bronze et Silver avant/après sont identiques ; Gold hors cible est inchangé.

Preuves : pipelines/s4_us25_us28.py, pipelines/sql/us25_meunier_diagnostic.sql, pipelines/sql/us25_validation.sql ; reports/s4/us25_us28/us25_creation_initiale.json, us25.json et sql_verification.json. Reproduction dans /home/jovyan/work : `python pipelines/s4_us25_us28.py --us 25`.

Prérequis observés le 07/11/2026 : Silver était vide malgré les sorties enregistrées du notebook. Le code existant des cellules de préparation, normalisation et construction initiale US-21/22 a été exécuté une seule fois, sans modification du code des collègues. Un garde-fou a interdit tout DELETE touchant une ligne existante. Conservation mesurée : client CRM 100000 = 99350 Silver + 650 rejets ; CIF 40000 = 40000 + 0 ; contrat 100000 = 98600 + 1400 ; sinistre 100000 = 100000 + 0. La cellule de reconstruction du test d'idempotence n'a pas été relancée. Les sorties historiques et le code US-21/22/23 sont conservés tels quels ; cette intervention ne revalide pas à elle seule toute US-23.

Les règles de survie sont une proposition technique de l'ingénieur qualité au Data Owner ; voir JOURNAL_DECISIONS.md, entrée propre à US-25.

## 4. Gold et client actif (US-27)

| Table gold | Lignes | Lignes écartées (porte G) | Règles responsables |
|---|---|---|---|
| client_unique | … | … | … |
| xref_identifiants | … | … | … |
| contrat_certifie | … | … | … |
| sinistre_certifie | … | … | … |

Orphelins dans gold (contrat sans client, sinistre sans contrat) : [À COMPLÉTER]

Client actif publié par la vue `v_client_actif` : [À COMPLÉTER]. Écart avec la définition de la fiche CD-001 : [À COMPLÉTER]

Effet de la quarantaine sur l'intégrité en aval (un client écarté laisse-t-il des contrats orphelins ?) : [À COMPLÉTER]

## 5. Traçabilité de trois données (US-28)

Contribution Mohamed, 07/11/2026. **PARTIELLE : un parcours Gold → source complet, deux parcours démontrés seulement de Silver à la source.** Ne pas cocher le critère des trois traces complètes avant la disponibilité des données Gold manquantes.

| Donnée | Gold | Silver | Bronze / lot | Source et transformation observée |
|---|---|---|---|---|
| Société Meunier | CLI-000482, quatre xref | Quatre lignes listées en US-25, jointes aux mêmes source_systeme/source_id/bronze_row_id | Quatre lignes listées ci-dessus ; L-2026-10-01 | crm.client : A-4471, H-9012, S-2208 ; cif.clients : K471226. Identités harmonisées vers MEUNIER SARL, donneur CIF pour les attributs de survie |
| Code postal à zéro initial | **Absent** : aucune ligne xref ni client_unique pour A-10062 | silver.client, ligne 69, CP 01500 | bronze.crm_client, ligne 70, lot L-2026-10-01, CP 1500 | crm.client, clé A-10062, CP initial 1500 ; restauration du zéro initial par le code S4 existant, limitée à une adresse FR |
| Adresse de sinistre | **Absent** : aucune table Gold de sinistres certifiés | silver.sinistre, ligne 3588, adresse 75 BOULEVARD VOLTAIRE | bronze.crm_sinistre, ligne 3588, lot L-2026-10-01, adresse 75 bd Voltaire | crm.sinistre, clé SIN0003588, adresse initiale 75 bd Voltaire ; développement de l'abréviation et mise en majuscules ; rapprochement exact après normalisation avec BAN006854 |

Le parcours Meunier restitue les identifiants de ligne et les lots Gold/Silver/Bronze ainsi que les valeurs sources. Le parcours CP expose explicitement cli_id NULL : aucun client Gold n'a été créé uniquement pour faire réussir une trace. Le parcours adresse constate une correction de format ("bd" vers "BOULEVARD"), pas une correction métier approuvée de l'adresse réelle. La référence BAN est retrouvée par la requête, sans inventer ni modifier l'adresse source.

Requêtes reproductibles : pipelines/sql/us28_meunier.sql, us28_code_postal.sql et us28_sinistre.sql. Résultats : reports/s4/us25_us28/us28.json. Reproduction dans /home/jovyan/work : `python pipelines/s4_us25_us28.py --us 28` ; aucune écriture métier pour US-28.

Manques précis :

- Le client A-10062 attend son attribution de CLI et sa xref dans les traitements US-24/27. Gold ne contient actuellement que le cas Meunier de US-25.
- Les tables Gold actuelles sont client_unique et xref_identifiants (plus la vue US-25). Une table de sinistres certifiés et sa liaison de ligne vers silver.sinistre sont nécessaires pour compléter le troisième parcours ; elles relèvent de US-27.

L'ingénieur qualité conserve ces deux limites visibles et demande leur réalisation aux responsables des US-24/27. Aucun chiffre ni identifiant Gold fictif n'est utilisé et aucun traitement des autres US n'est réécrit.

## 6. Critères de fin

- [ ] Pour chaque table, silver + rejets = bronze, sans suppression silencieuse.
- [ ] Relancer le traitement deux fois donne le même résultat.
- [ ] Les règles bloquantes de la porte S sont conformes sur silver.
- [ ] Le gold ne contient aucun orphelin ; le client actif est publié par une seule vue.
- [ ] Les trois traces remontent du gold à la source avec identifiants de ligne et de lot.

## 7. Difficultés, écarts avec l'attendu, reprise

Difficultés rencontrées et temps perdu : [À COMPLÉTER]

Point de reprise utilisé (oui / non, lequel, à quel moment) : [À COMPLÉTER]

Ce que nous ferions autrement : [À COMPLÉTER]
