"""Validation en lecture seule : exécuter dans dq_jupyter, depuis le dépôt monté."""
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/s3/validation_us12_us16'
BATCH = 'L-2026-10-01'
ENGINE = create_engine('mysql+pymysql://root:root@mariadb:3306')
TABLES = [('crm','client'), ('crm','contrat'), ('crm','sinistre'),
          ('crm','type_contrat'), ('cif','clients'), ('cif','compte'), ('cif','pays')]

def query(sql, **params):
    with ENGINE.connect() as c:
        return [dict(r) for r in c.execute(text(sql), params).mappings()]

def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def signatures():
    result = {}
    for db, table in TABLES + [('bronze', f'{d}_{t}') for d,t in TABLES]:
        cols = [c['name'] for c in inspect(ENGINE).get_columns(table, schema=db)]
        payload = ','.join('`'+c+'`' for c in cols)
        r = query(f'SELECT COUNT(*) n, COALESCE(SUM(CRC32(JSON_ARRAY({payload}))),0) crc FROM {db}.`{table}`')[0]
        result[f'{db}.{table}'] = {k:int(v) for k,v in r.items()}
    return result

def scan(name, path):
    target = OUT / f'{name}.json'
    p = subprocess.run(['soda','scan','-d','bronze','-c',str(ROOT/'soda/configuration.yml'),
                        str(path),'-srf',str(target)], capture_output=True, text=True)
    (OUT/f'{name}.log').write_text(p.stdout+p.stderr, encoding='utf-8')
    assert target.exists(), p.stdout+p.stderr
    s = json.loads(target.read_text())
    assert not s['hasErrors'] and p.returncode in (0,1,2), p.stdout+p.stderr
    values = {m['identity']:m['value'] for m in s['metrics']}
    checks = [{'nom':c['name'], 'resultat':c['outcome'],
               'valeurs':[values[m] for m in c['metrics']]} for c in s['checks']]
    return {'code_retour':p.returncode, 'checks':checks}

def us12():
    OUT.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load((ROOT/'soda/configuration.yml').read_text())
    sources = {}
    for layer in ['crm','bronze','silver','gold']:
        source = config[f'data_source {layer}']
        assert source['host']=='mariadb' and source['port']==3306 and source['database']==layer
        source_engine = create_engine(URL.create('mysql+pymysql', username=source['username'],
            password=source['password'], host=source['host'], port=source['port'], database=source['database']))
        with source_engine.connect() as connection:
            assert connection.execute(text('SELECT DATABASE()')).scalar()==layer
            sources[layer] = {'connexion':'OK','tables':int(connection.execute(text('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=:s'),{'s':layer}).scalar())}
        source_engine.dispose()
    volumes = {f'{db}_{t}':int(query(f'SELECT COUNT(*) n FROM bronze.{db}_{t}')[0]['n']) for db,t in TABLES}
    assert all(n>0 for n in volumes.values()), 'Table Bronze vide'
    for t in volumes:
        assert int(query(f'SELECT COUNT(*) n FROM bronze.{t} WHERE _batch_id<>:b OR _batch_id IS NULL',b=BATCH)[0]['n'])==0, 'Scan global interdit sur plusieurs lots'
    schema = {t:[c['name'] for c in inspect(ENGINE).get_columns(t,schema='bronze')] for t in volumes}
    before = signatures()
    scans = {}
    for table in ['client','contrat','sinistre']:
        path = ROOT/f'soda/checks/{table}_bronze_checks.yml'
        for key,checks in yaml.safe_load(path.read_text(encoding='utf-8-sig')).items():
            if key.startswith('checks for'):
                for check in checks:
                    settings = next(iter(check.values()))
                    assert re.search(r'RQ-\d{3}', settings['name']) and 'BRONZE' in settings['name']
        scans[table] = scan(table,path)
    demos = {case:scan(case,ROOT/f'soda/checks/us12_{case}.yml') for case in ['pass','warn','fail']}
    for case,code in [('pass',0),('warn',1),('fail',2)]:
        assert demos[case]['code_retour']==code
        assert demos[case]['checks'][0]['resultat']==case
    after = signatures()
    assert before==after, 'Données changées pendant la validation : investiguer sans restaurer automatiquement'
    summary = {status:sum(c['resultat']==status for s in scans.values() for c in s['checks']) for status in ['pass','warn','fail']}
    result = {'date_utc':datetime.now(timezone.utc).isoformat(),'sources':sources,'volumes':volumes,
              'schema':schema,'scans':scans,'demonstrations':demos,'synthese':summary,
              'signatures_avant':before,'signatures_apres':after,'donnees_inchangees':True}
    save('us12.json', result)
    return result

def us16():
    relations = []
    definitions = [
      ('RQ-012','crm_contrat','souscripteur_id','bronze.crm_client','client_id',False),
      ('RQ-013 brut','crm_contrat','assure_id','bronze.crm_client','client_id',False),
      ('RQ-013','crm_contrat','assure_id','bronze.crm_client','client_id',True),
      ('RQ-011','crm_contrat','code_type','bronze.crm_type_contrat','code_type',False),
      ('Lien sinistre','crm_sinistre','contrat_id','bronze.crm_contrat','contrat_id',False),
      ('Lien CIF','cif_compte','column1','bronze.cif_clients','column0',False),
      ('RQ-007','crm_client','pays','silver.ref_pays','code_pays',False)]
    yml = 'checks for crm_client:\n'
    for i,(rule,child,col,parent,key,sentinel) in enumerate(definitions):
        cmp = 'BINARY ' if rule=='RQ-007' else ''
        if not cmp:
            for db,table,column in [('bronze',child,col),(*parent.split('.'),key)]:
                collation=query('SELECT collation_name collation FROM information_schema.columns WHERE table_schema=:d AND table_name=:t AND column_name=:c',d=db,t=table,c=column)[0]['collation']
                assert collation=='utf8mb4_nopad_bin', (db,table,column,collation)
        parent_scope = 'AND _batch_id=:b' if parent.startswith('bronze.') else ''
        exclusion = f"AND c.`{col}`<>'0'" if sentinel else ''
        bad = f"c.`{col}` IS NOT NULL {exclusion} AND {cmp}c.`{col}` NOT IN (SELECT {cmp}`{key}` FROM {parent} WHERE `{key}` IS NOT NULL {parent_scope})"
        sql = f"SELECT COUNT(*) testees, COALESCE(SUM(c.`{col}` IS NULL),0) nuls, COALESCE(SUM({bad}),0) orphelins FROM bronze.{child} c WHERE c._batch_id=:b"
        r = {k:int(v) for k,v in query(sql,b=BATCH)[0].items()}
        r.update(regle=rule,relation=f'{child}.{col} → {parent}.{key}')
        r['anomalies'] = r['orphelins'] + (r['nuls'] if rule=='RQ-007' else 0)
        r['taux_echec'] = round(100*r['anomalies']/r['testees'],6) if r['testees'] else None
        r['sql'] = sql
        relations.append(r)
        soda_bad = f"c.`{col}` IS NULL OR ({bad})" if rule=='RQ-007' else bad
        q = f'SELECT COALESCE(SUM({soda_bad}),0) FROM bronze.{child} c WHERE c._batch_id=:b'
        q = q.replace(':b',"'"+BATCH+"'")
        label = rule if rule.startswith('RQ-') else 'US-16'
        yml += f'  - us16_relation_{i}:\n      name: {label} BRONZE {child}.{col} relation {i}\n      us16_relation_{i} query: |\n        {q}\n      fail: when > 0\n'
    checkfile = ROOT/'soda/checks/us16_relations_checks.yml'
    checkfile.write_text(yml,encoding='utf-8')
    soda = scan('relations',checkfile)
    for i,r in enumerate(relations):
        actual = next(c['valeurs'][0] for c in soda['checks'] if c['nom'].endswith(f'relation {i}'))
        assert actual==r['anomalies'],(r,actual)
        r['soda']=actual
    pays = query("""SELECT COUNT(*) testees, SUM(pays IS NULL) nuls,
      SUM(pays IS NOT NULL AND TRIM(pays)='') vides_ou_blancs,
      SUM(pays IS NOT NULL AND BINARY pays<>BINARY TRIM(pays)) espaces_exterieurs,
      SUM(pays IS NOT NULL AND BINARY pays NOT IN (SELECT BINARY code_pays FROM silver.ref_pays WHERE code_pays IS NOT NULL)
          AND BINARY TRIM(pays) IN (SELECT BINARY code_pays FROM silver.ref_pays WHERE code_pays IS NOT NULL)) corrigeables_par_trim
      FROM bronze.crm_client WHERE _batch_id=:b""",b=BATCH)[0]
    pays = {k:int(v or 0) for k,v in pays.items()}
    reference = query('SELECT COUNT(*) n, COUNT(DISTINCT BINARY code_pays) distincts, SUM(code_pays IS NULL) nuls FROM silver.ref_pays')[0]
    assert reference['n']>0 and reference['n']==reference['distincts'] and not reference['nuls']
    # Jeu de test en SELECT uniquement : aucune table ni donnée insérée.
    fixture = query("""WITH exemples AS (
      SELECT 1 id, CAST(NULL AS CHAR(8) CHARACTER SET utf8mb4) COLLATE utf8mb4_nopad_bin pays UNION ALL SELECT 2,'FR' UNION ALL
      SELECT 3,'FR ' UNION ALL SELECT 4,' FR' UNION ALL SELECT 5,'' UNION ALL SELECT 6,'   '
      UNION ALL SELECT 7,'fr' UNION ALL SELECT 8,'ZZ'
      ) SELECT id, pays IS NULL OR NOT EXISTS (SELECT 1 FROM silver.ref_pays r WHERE BINARY r.code_pays=BINARY exemples.pays) ko FROM exemples ORDER BY id""")
    assert [int(x['ko']) for x in fixture]==[1,0,1,1,1,1,1,1],fixture
    original = json.loads((OUT/'us12.json').read_text())
    for rule,table in [('RQ-007','client'),('RQ-011','contrat'),('RQ-012','contrat'),('RQ-013','contrat')]:
        val=next(c['valeurs'][0] for c in original['scans'][table]['checks'] if c['nom'].startswith(rule))
        assert val==next(r['anomalies'] for r in relations if r['regle']==rule)
    result={'date_utc':datetime.now(timezone.utc).isoformat(),'lot':BATCH,'relations':relations,
            'pays':pays,'reference_pays':{k:int(v or 0) for k,v in reference.items()},
            'fixture_rq007':fixture,'soda':soda,'concordance_sql_soda':True}
    save('us16.json',result)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--part',choices=['us12','us16','all'],default='all')
    args=parser.parse_args()
    if args.part in ['us12','all']:
        r=us12(); print('US-12',r['synthese'],'données inchangées',r['donnees_inchangees'],flush=True)
    if args.part in ['us16','all']:
        r=us16(); print('US-16',[(x['regle'],x['anomalies']) for x in r['relations']],flush=True)
