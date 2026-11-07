"""US-25 limitée au cas Meunier ; US-28 en lecture seule. Aucune reconstruction Silver."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'reports/s4/us25_us28'
BATCH = 'L-2026-10-01'
CLI = 'CLI-000482'
MEMBRES = {('crm','A-4471'),('crm','H-9012'),('crm','S-2208'),('cif','K471226')}
engine = create_engine('mysql+pymysql://root:root@mariadb:3306')

def lire(sql, connexion=None, **params):
    if connexion is not None:
        return [dict(r) for r in connexion.execute(text(sql), params).mappings()]
    with engine.connect() as c:
        return lire(sql, c, **params)

def sauver(nom, resultat):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/nom).write_text(json.dumps(resultat,ensure_ascii=False,default=str,indent=2),encoding='utf8')

def signatures():
    resultat={}
    for base in ['crm','cif','bronze','silver']:
        for table in inspect(engine).get_table_names(schema=base):
            colonnes=inspect(engine).get_columns(table,schema=base)
            noms=','.join('`'+c['name']+'`' for c in colonnes)
            r=lire(f'SELECT COUNT(*) n, COALESCE(SUM(CRC32(JSON_ARRAY({noms}))),0) crc FROM `{base}`.`{table}`')[0]
            resultat[f'{base}.{table}']={k:int(v) for k,v in r.items()}
    return resultat

def membres():
    rows=lire("""SELECT * FROM silver.client WHERE _batch_id=:b AND
      ((source_systeme='crm' AND source_id IN ('A-4471','H-9012','S-2208'))
       OR (source_systeme='cif' AND source_id='K471226')) ORDER BY source_systeme,source_id""",b=BATCH)
    assert len(rows)==4 and {(r['source_systeme'],r['source_id']) for r in rows}==MEMBRES,'Les quatre membres doivent exister une seule fois dans Silver'
    identites={(r['identite_normalisee'],r['adresse_normalisee'],r['cp'],r['ville_normalisee'],r['pays_iso']) for r in rows}
    assert len(identites)==1 and next(iter(identites))==('MEUNIER SARL','27 RUE PASTEUR','69003','LYON','FR'),'Identité ou adresse divergente : revue nécessaire'
    for r in rows:
        table,cle=('crm_client','client_id') if r['source_systeme']=='crm' else ('cif_clients','column0')
        parents=lire(f'SELECT {cle} source_id FROM bronze.{table} WHERE bronze_row_id=:id AND _batch_id=:b',id=r['bronze_row_id'],b=BATCH)
        assert len(parents)==1 and parents[0]['source_id']==r['source_id'],'Traçabilité Silver/Bronze invalide'
    return rows

def plan_us25():
    rows=membres();cif=next(r for r in rows if r['source_systeme']=='cif')
    statut=lire("""SELECT
      MAX(date_debut<='2026-10-01' AND date_fin>='2026-10-01' AND date_derniere_cotisation>='2026-07-01') actif,
      COUNT(*) contrats FROM silver.contrat WHERE _batch_id=:b AND souscripteur_id IN ('A-4471','H-9012','S-2208')""",b=BATCH)[0]
    assert statut['contrats']>0,'Définir le statut métier avant de créer le golden record'
    record={'cli_id':CLI,'nom_reference':cif['identite_normalisee'],'date_naissance':None,
            'cp':cif['cp'],'ville':cif['ville_normalisee'],'pays_iso':cif['pays_iso'],
            'telephone':cif['telephone_normalise'],'email':cif['email_normalise'],
            'nb_identifiants_source':4,'statut_client':'ACTIF' if statut['actif'] else 'INACTIF','_batch_id':BATCH}
    assert record['telephone'] and record['email'],'Donneur CIF incomplet : revue nécessaire'
    attributs={
      'nom_reference':'Identité normalisée commune aux quatre sources ; donneur CIF',
      'adresse':'Adresse complète commune aux quatre sources ; donneur CIF, exposée dans v_us25_meunier car absente du schéma client_unique',
      'cp, ville, pays_iso':'Triplet cohérent pris ensemble sur le CIF ; aucune adresse recomposée entre sources',
      'telephone':'CIF non nul prioritaire, confirmé par A-4471 ; deux autres numéros conservés dans les preuves, sans prétendre savoir lequel est le plus récent',
      'email':'CIF non nul prioritaire, confirmé par A-4471 ; compta@... est une autre adresse, non une preuve de fraîcheur',
      'date_naissance':'NULL : société, aucune naissance inventée',
      'nb_identifiants_source':'Nombre réel des quatre correspondances distinctes',
      'statut_client':'CD-001 sur le même contrat Silver : en cours au 01/10/2026 et cotisation depuis 01/07/2026'}
    return {'membres':rows,'golden_record_propose':record,'adresse_survivante':cif['adresse_normalisee'],
            'regles_survie_proposees':attributs,'donneur':{'source':'cif','id':cif['source_id'],'silver_row_id':cif['silver_row_id'],'bronze_row_id':cif['bronze_row_id']},
            'validation_data_owner':'Non présumée : politique technique proposée pour ce cas explicitement demandé'}

def appliquer_us25():
    plan=plan_us25();record=plan['golden_record_propose'];inserts={'client_unique':0,'xref_identifiants':0}
    with engine.begin() as c:
        old=lire('SELECT * FROM gold.client_unique WHERE cli_id=:cli FOR UPDATE',c,cli=CLI)
        if old:assert old==[record],'CLI existant différent : aucune mise à jour automatique'
        xref=lire("""SELECT * FROM gold.xref_identifiants WHERE cli_id=:cli
         OR (source_systeme='crm' AND source_id IN ('A-4471','H-9012','S-2208'))
         OR (source_systeme='cif' AND source_id='K471226') FOR UPDATE""",c,cli=CLI)
        assert all((x['source_systeme'],x['source_id']) in MEMBRES and x['cli_id']==CLI for x in xref),'Rattachement Gold contradictoire : arrêt sans suppression'
        if not old:
            colonnes=','.join(record);valeurs=','.join(':'+k for k in record)
            c.execute(text(f'INSERT INTO gold.client_unique ({colonnes}) VALUES ({valeurs})'),record);inserts['client_unique']+=1
        for r in plan['membres']:
            attendu={'cli_id':CLI,'source_systeme':r['source_systeme'],'source_id':r['source_id'],'bronze_row_id':r['bronze_row_id'],'silver_row_id':r['silver_row_id']}
            present=[x for x in xref if (x['source_systeme'],x['source_id'])==(r['source_systeme'],r['source_id'])]
            if present:assert present==[attendu],'Identifiants de lignage existants différents : revue nécessaire'
            else:
                c.execute(text('INSERT INTO gold.xref_identifiants (cli_id,source_systeme,source_id,bronze_row_id,silver_row_id) VALUES (:cli_id,:source_systeme,:source_id,:bronze_row_id,:silver_row_id)'),attendu)
                inserts['xref_identifiants']+=1
    # Vue propre à US-25 ; aucune modification de la table partagée ni d'une vue existante.
    vue="""SELECT g.*, s.adresse_normalisee AS adresse_survivante,
      x.source_id AS source_survivante, x.silver_row_id AS silver_row_id_survivant,
      x.bronze_row_id AS bronze_row_id_survivant
      FROM gold.client_unique g JOIN gold.xref_identifiants x ON x.cli_id=g.cli_id
      JOIN silver.client s ON s.silver_row_id=x.silver_row_id AND s.bronze_row_id=x.bronze_row_id
       AND s.source_systeme=x.source_systeme AND s.source_id=x.source_id AND s._batch_id=g._batch_id
      WHERE g.cli_id='CLI-000482' AND x.source_systeme='cif' AND x.source_id='K471226'"""
    with engine.begin() as c:
        exists=lire("SELECT view_definition FROM information_schema.views WHERE table_schema='gold' AND table_name='v_us25_meunier'",c)
        if not exists:c.execute(text('CREATE VIEW gold.v_us25_meunier AS '+vue))
    view=lire('SELECT * FROM gold.v_us25_meunier')
    assert len(view)==1 and view[0]['adresse_survivante']==plan['adresse_survivante']
    rows=lire('SELECT * FROM gold.xref_identifiants WHERE cli_id=:cli',cli=CLI)
    assert len(rows)==4 and len({(r['source_systeme'],r['source_id']) for r in rows})==4
    return {**plan,'insertions':inserts,'golden_record':lire('SELECT * FROM gold.client_unique WHERE cli_id=:cli',cli=CLI)[0],
            'vue':view,'xref':rows,'couverture_identifiants_pct':100,'doublons':0,'statut':'TERMINÉE'}

def us25():
    avant=signatures()
    hors_cible_avant={t:lire(f"SELECT * FROM gold.{t} WHERE cli_id<>:cli",cli=CLI) for t in ['client_unique','xref_identifiants']}
    premier=appliquer_us25();second=appliquer_us25()
    assert second['insertions']=={'client_unique':0,'xref_identifiants':0}
    assert signatures()==avant,'Une table source, Bronze ou Silver a changé : investiguer sans restauration automatique'
    assert hors_cible_avant=={t:lire(f"SELECT * FROM gold.{t} WHERE cli_id<>:cli",cli=CLI) for t in hors_cible_avant}
    resultat={**premier,'relance_insertions':second['insertions'],'sources_bronze_silver_inchanges':True,
              'signatures':avant,'gold_hors_cible_inchange':True,'date_utc':datetime.now(timezone.utc).isoformat()}
    sauver('us25.json',resultat);return resultat

def us28():
    sql=(ROOT/'pipelines/sql/us28_meunier.sql').read_text()
    meunier=lire(sql)
    assert len(meunier)==4
    cp=lire((ROOT/'pipelines/sql/us28_code_postal.sql').read_text())
    sinistre=lire((ROOT/'pipelines/sql/us28_sinistre.sql').read_text())
    tables_gold=inspect(engine).get_table_names(schema='gold')
    resultat={'date_utc':datetime.now(timezone.utc).isoformat(),'lot':BATCH,
      'meunier':{'statut':'DÉMONTRÉ','trace':meunier},
      'code_postal':{'statut':'DÉMONTRÉ' if cp and cp[0]['cli_id'] else 'PARTIELLE','trace':cp,
       'manque':None if cp and cp[0]['cli_id'] else 'Pas de golden record ni de xref pour le client au zéro restauré ; dépend des US-24/27'},
      'sinistre':{'statut':'PARTIELLE','trace_silver_bronze_source':sinistre,'tables_gold_existantes':tables_gold,
       'manque':'Aucune table Gold de sinistres certifiés ni liaison Gold/Silver existante ; dépend de US-27. La normalisation observée ne doit pas être présentée comme une correction métier approuvée.'},
      'statut':'PARTIELLE'}
    sauver('us28.json',resultat);return resultat

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--us',choices=['25','28','plan'],default='plan');a=p.parse_args()
    r=us25() if a.us=='25' else us28() if a.us=='28' else plan_us25()
    print(json.dumps(r,ensure_ascii=False,default=str,indent=2))
