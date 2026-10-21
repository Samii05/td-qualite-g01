# US-05 — Recouvrement CIF / CRM et source de vérité

## 1. Objectif

Étudier le recouvrement entre les données clients CIF et CRM, identifier les attributs communs et proposer une règle de gouvernance pour déterminer la source de vérité.

## 2. Volumétrie observée

| Indicateur | Résultat |
|---|---:|
| Nombre de lignes CIF | 40 000 |
| Nombre de lignes CRM | 100 000 |
| Identifiants communs par égalité exacte | 0 |

Le rapprochement testé compare `cif_clients.column0` à `crm_client.client_id`. Aucune correspondance exacte n'a été trouvée. Cela ne prouve pas que les deux sources ne contiennent aucun client commun : les identifiants peuvent suivre des conventions différentes.

## 3. Correspondance provisoire des attributs CIF

| Colonne CIF | Attribut supposé | Champ CRM candidat |
|---|---|---|
| `column0` | Identifiant CIF | `client_id` — correspondance non démontrée |
| `column1` | Nom | `nom` |
| `column2` | Prénom | `prenom` |
| `column3` | Date de naissance | `date_naissance` |
| `column4` | Adresse | `adresse` |
| `column5` | Code postal | `cp` |
| `column6` | Ville | `ville` |
| `column7` | Pays | `pays` |
| `column8` | Téléphone | `telephone` |
| `column9` | Email | `email` |

Cette correspondance est une hypothèse fondée sur l'observation d'exemples CIF. Elle doit être confirmée par le dictionnaire de données et par des contrôles sur l'ensemble des lignes.

## 4. Proposition de gouvernance

La source de vérité doit être définie par attribut et selon les règles métier, plutôt que de choisir automatiquement une source pour toutes les données.

- **Identifiant client :** conserver les identifiants propres à chaque système et prévoir une table de correspondance validée.
- **Nom, prénom et date de naissance :** définir la source de référence après confirmation des règles métier et comparaison des valeurs.
- **Adresse, code postal et ville :** définir une règle de priorité documentée et prévoir une mise à jour contrôlée.
- **Téléphone et email :** retenir la source la plus fiable selon les règles métier, la fraîcheur et la validation des coordonnées.

À ce stade, aucune source de vérité définitive n'est attribuée aux attributs personnels : les taux de correspondance et les écarts n'ont pas encore été mesurés.

## 5. Limites et prochaines vérifications

1. Confirmer le dictionnaire de données CIF.
2. Définir une méthode de rapprochement adaptée aux identifiants différents.
3. Mesurer les correspondances et les divergences sur les attributs communs.
4. Valider les règles de source de vérité avec l'équipe.
5. Conserver les requêtes SQL et les résultats comme preuves reproductibles.

Aucune donnée source n'a été modifiée.
