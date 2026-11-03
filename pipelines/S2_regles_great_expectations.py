"""S2 · Règles Great Expectations, rejouables sur une couche au choix.

Mêmes suites que le notebook S2 (US-10) : mêmes expectations, mêmes rule_id, mêmes row_condition.
La couche est choisie par la variable d'environnement COUCHE :
    COUCHE=BRONZE (défaut) -> lit bronze.crm_client, crm_contrat, crm_sinistre, cif_clients
    COUCHE=SILVER          -> lit silver.client (CRM + CIF), silver.contrat, silver.sinistre
Les mesures sont écrites dans dq.dq_history avec cette couche (on remplace celles du lot : idempotent).
"""
import os
import pandas as pd
import great_expectations as gx
from sqlalchemy import create_engine, text

# PARAMÈTRES
BATCH  = os.environ.get("BATCH", "L-2026-10-01")
COUCHE = os.environ.get("COUCHE", "BRONZE").upper()
BASE   = COUCHE.lower()                      # schéma lu : bronze ou silver

engine = create_engine("mysql+pymysql://root:root@mariadb:3306")

def lire(sql, eng=engine, **params):
    return pd.read_sql(text(sql), eng, params=params)

# Règles et référentiel pays (identique à S2, cellule 6)
REGLES = lire("SELECT rule_id, libelle, dimension, severite, seuil_min FROM dq.regle").set_index("rule_id")

def mostly(rule_id):
    """Seuil GE (entre 0 et 1) = seuil_min de la règle (en %)."""
    return float(REGLES.loc[rule_id, "seuil_min"]) / 100

CODES_PAYS = sorted(lire("SELECT code_pays FROM silver.ref_pays").code_pays)

# Contexte GE (identique à S2, cellule 4)
DOSSIER_GE = "/home/jovyan/work/reports/ge" if os.path.isdir("/home/jovyan/work") else "reports/ge"
os.makedirs(DOSSIER_GE, exist_ok=True)
context    = gx.get_context(project_root_dir=DOSSIER_GE)
datasource = context.sources.add_or_update_pandas(name="assurconnect")


# ---------------------------------------------------------------- chargement
def age_a_la_signature(df, naiss):
    """Âge du souscripteur à la date de DÉBUT du contrat (RQ-002), même formule que S2."""
    df = df.merge(naiss, left_on="souscripteur_id", right_on="client_id", how="left")
    dn, dd = pd.to_datetime(df["date_naissance"], errors="coerce"), df["date_debut"]
    pas_encore_anniv = (dd.dt.month < dn.dt.month) | ((dd.dt.month == dn.dt.month) & (dd.dt.day < dn.dt.day))
    df["age_debut"] = dd.dt.year - dn.dt.year - pas_encore_anniv.astype("Int64")
    df["personne_physique"] = df["age_debut"].notna()
    return df

def preparer_contrat(df, naiss):
    for c in ["date_debut", "date_fin"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["duree_garantie_mois"] = pd.to_numeric(df["duree_garantie_mois"], errors="coerce")
    return age_a_la_signature(df, naiss)

NOMS_CIF = {"column0": "id_cif", "column1": "nom_ou_raison_sociale", "column2": "prenom",
            "column3": "date_naissance", "column4": "adresse", "column5": "cp", "column6": "ville",
            "column7": "pays", "column8": "telephone", "column9": "email"}

def charger_bronze():
    """Exactement S2 (cellule 8) : table bronze -> (nature, données)."""
    donnees = {}
    for table, (nature, cle) in {"crm_client": ("client", "client_id"), "crm_contrat": ("contrat", "contrat_id"),
                                 "crm_sinistre": ("sinistre", "sinistre_id"), "cif_clients": ("cif", "id_cif")}.items():
        df = lire(f"SELECT * FROM bronze.{table} WHERE _batch_id = :b", b=BATCH)
        if nature == "cif":
            df = df.rename(columns=NOMS_CIF)
        df["source_systeme"] = df["_source_system"]
        df["cle"] = df[cle]
        if nature == "contrat":
            naiss = lire("SELECT client_id, date_naissance FROM bronze.crm_client WHERE _batch_id = :b", b=BATCH)
            df = preparer_contrat(df, naiss)
        donnees[table] = (nature, df)
    return donnees

def charger_silver():
    """Silver : mêmes données, colonnes renommées vers les noms attendus par les suites S2."""
    cl = lire("SELECT * FROM silver.client WHERE _batch_id = :b", b=BATCH).rename(columns={
        "pays_iso": "pays", "telephone_normalise": "telephone", "email_normalise": "email"})
    cl["cle"] = cl["source_id"]
    ct = lire("SELECT * FROM silver.contrat WHERE _batch_id = :b", b=BATCH)
    ct["cle"] = ct["contrat_id"]
    naiss = cl.loc[cl.source_systeme == "crm", ["source_id", "date_naissance"]].rename(columns={"source_id": "client_id"})
    ct = preparer_contrat(ct, naiss)
    sn = lire("SELECT * FROM silver.sinistre WHERE _batch_id = :b", b=BATCH)
    sn["cle"] = sn["sinistre_id"]
    # silver.client contient CRM et CIF : on les teste séparément, comme en bronze
    return {"client":     ("client",   cl[cl.source_systeme == "crm"].reset_index(drop=True)),
            "contrat":    ("contrat",  ct),
            "sinistre":   ("sinistre", sn),
            "client_cif": ("cif",      cl[cl.source_systeme == "cif"].reset_index(drop=True))}


# ---------------------------------------------------------------- suites (identiques à S2, cellule 12)
SOUSCRIPTEUR_CRM = dict(row_condition='source_systeme == "crm" and type_personne == "souscripteur"', condition_parser="pandas")
FRANCE           = dict(row_condition='pays == "FR"', condition_parser="pandas")

def regles_client(v):
    # RQ-003 : téléphone du souscripteur ni nul, ni vide, ni blanc
    v.expect_column_values_to_not_be_null(column="telephone", mostly=mostly("RQ-003"), meta={"rule_id": "RQ-003"}, **SOUSCRIPTEUR_CRM)
    v.expect_column_values_to_match_regex(column="telephone", regex=r"\S", mostly=mostly("RQ-003"), meta={"rule_id": "RQ-003"}, **SOUSCRIPTEUR_CRM)
    # RQ-009 : type de personne parmi les 3 valeurs autorisées
    v.expect_column_values_to_be_in_set(column="type_personne", value_set=["prospect", "souscripteur", "assure"],
                                        meta={"rule_id": "RQ-009", "nuls_en_echec": True})

def regles_adresse(v):
    # RQ-005 : code postal à 5 chiffres, adresses en France seulement (CRM et CIF)
    v.expect_column_values_to_match_regex(column="cp", regex=r"^\d{5}$", mostly=mostly("RQ-005"),
                                          meta={"rule_id": "RQ-005", "nuls_en_echec": True}, **FRANCE)
    # RQ-007 : pays dans la liste de référence
    v.expect_column_values_to_be_in_set(column="pays", value_set=CODES_PAYS, meta={"rule_id": "RQ-007", "nuls_en_echec": True})

def regles_contrat(v):
    # RQ-001 : date de fin strictement après la date de début
    v.expect_column_pair_values_A_to_be_greater_than_B(column_A="date_fin", column_B="date_debut", or_equal=False, meta={"rule_id": "RQ-001"})
    # RQ-002 : souscripteur PERSONNE PHYSIQUE de 18 ans ou plus à la date de début
    v.expect_column_values_to_be_between(column="age_debut", min_value=18, meta={"rule_id": "RQ-002"},
                                         row_condition="personne_physique == True", condition_parser="pandas")
    # RQ-010 : durée de garantie parmi 12, 24, 36, 60
    v.expect_column_values_to_be_in_set(column="duree_garantie_mois", value_set=[12, 24, 36, 60],
                                        meta={"rule_id": "RQ-010", "nuls_en_echec": True})

def cle_primaire(v):
    # RQ-020 : clé primaire jamais nulle et unique
    v.expect_column_values_to_not_be_null(column="cle", meta={"rule_id": "RQ-020"})
    v.expect_column_values_to_be_unique(column="cle", meta={"rule_id": "RQ-020"})

SUITES = {"client":   [regles_client, regles_adresse, cle_primaire],
          "contrat":  [regles_contrat, cle_primaire],
          "sinistre": [cle_primaire],
          "cif":      [regles_adresse, cle_primaire]}


# ---------------------------------------------------------------- validation (identique à S2, cellules 10 et 14)
def valider(nom, df, ajouter_regles):
    try:
        asset = datasource.get_asset(nom)
    except Exception:
        asset = datasource.add_dataframe_asset(name=nom)
    batch = asset.build_batch_request(dataframe=df)
    context.add_or_update_expectation_suite(expectation_suite_name=f"{nom}_suite")
    v = context.get_validator(batch_request=batch, expectation_suite_name=f"{nom}_suite")
    ajouter_regles(v)
    v.save_expectation_suite(discard_failed_expectations=False)
    return v.validate().results

def main():
    donnees = charger_silver() if COUCHE == "SILVER" else charger_bronze()
    prefixe = "silver_" if COUCHE == "SILVER" else ""      # suites silver à part : celles de bronze ne sont pas écrasées
    mesures = []
    for table, (nature, df) in donnees.items():
        resultats = valider(prefixe + table, df, lambda v: [f(v) for f in SUITES[nature]])
        par_regle = {}
        for r in resultats:
            meta = r.expectation_config.meta
            n  = r.result["element_count"]
            ko = r.result["unexpected_count"] + (r.result.get("missing_count", 0) if meta.get("nuls_en_echec") else 0)
            t0, k0 = par_regle.get(meta["rule_id"], (n, 0))
            par_regle[meta["rule_id"]] = (t0, k0 + ko)
        for rule, (n, ko) in par_regle.items():
            mesures.append({"rule_id": rule, "table": table, "testees": int(n), "echecs": int(ko)})

    bilan = pd.DataFrame(mesures).sort_values(["rule_id", "table"]).reset_index(drop=True)
    # Historisation (identique à S2, cellule 31) : on remplace les mesures du lot, pas de doublon
    with engine.begin() as conn:
        for _, m in bilan.iterrows():
            conn.execute(text("""DELETE FROM dq.dq_history
                                 WHERE batch_id = :b AND couche = :c AND rule_id = :r AND table_cible = :t"""),
                         {"b": BATCH, "c": COUCHE, "r": m.rule_id, "t": m.table})
            conn.execute(text("""INSERT INTO dq.dq_history (batch_id, couche, rule_id, table_cible, nb_testees, nb_echecs)
                                 VALUES (:b, :c, :r, :t, :n, :e)"""),
                         {"b": BATCH, "c": COUCHE, "r": m.rule_id, "t": m.table, "n": int(m.testees), "e": int(m.echecs)})
    bilan["taux"] = (100 * (bilan.testees - bilan.echecs) / bilan.testees).round(3)
    print(f"Great Expectations · couche {COUCHE} · lot {BATCH}")
    print(bilan.to_string(index=False))

if __name__ == "__main__":
    main()