"""Local, single-user case workspace; tamper-evident (not tamper-proof) event chain."""
from __future__ import annotations
from pathlib import Path
import sqlite3,json,hashlib,uuid,datetime,os,shutil,zipfile
from contextlib import contextmanager
from .records import Record,record_to_npz,record_from_npz
from .reporting import safe_csv_text

SCHEMA_VERSION=2

def _digest_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def _now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def _canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)

class Workspace:
    def __init__(self,root=None):
        self.root=Path(root or Path.home()/'VIGILStudio_Workspace').expanduser().resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.records=self.root/'records';self.records.mkdir(exist_ok=True)
        self.dbpath=self.root/'research.sqlite3'
        self._init()
    @contextmanager
    def conn(self):
        c=sqlite3.connect(self.dbpath,timeout=20)
        c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
        try:yield c;c.commit()
        except Exception:c.rollback();raise
        finally:c.close()
    def _init(self):
        with self.conn() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS cases(
                id TEXT PRIMARY KEY,name TEXT NOT NULL,origin TEXT NOT NULL,created TEXT NOT NULL,
                sha256 TEXT NOT NULL,record_path TEXT NOT NULL,metadata_json TEXT NOT NULL,analysis_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reviews(
                id TEXT PRIMARY KEY,case_id TEXT NOT NULL,created TEXT NOT NULL,
                reviewer TEXT NOT NULL,label TEXT NOT NULL,note TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id));
                CREATE TABLE IF NOT EXISTS intervals(
                id TEXT PRIMARY KEY,case_id TEXT NOT NULL,channel TEXT NOT NULL,created TEXT NOT NULL,
                start_s REAL NOT NULL,end_s REAL NOT NULL,group_id TEXT NOT NULL,label TEXT NOT NULL,
                reviewer TEXT NOT NULL,note TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id));
                CREATE INDEX IF NOT EXISTS idx_interval_case ON intervals(case_id);
                CREATE TABLE IF NOT EXISTS experiments(
                id TEXT PRIMARY KEY,created TEXT NOT NULL,name TEXT NOT NULL,config_json TEXT NOT NULL,result_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,utc TEXT NOT NULL,kind TEXT NOT NULL,
                subject TEXT NOT NULL,details_json TEXT NOT NULL,prev_hash TEXT NOT NULL,hash TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_case_date ON cases(created);
                CREATE INDEX IF NOT EXISTS idx_review_case ON reviews(case_id);''')
            cols={row['name'] for row in c.execute('PRAGMA table_info(cases)')}
            if 'artifact_sha256' not in cols:
                c.execute('ALTER TABLE cases ADD COLUMN artifact_sha256 TEXT')
            # Existing records are retained as legacy unverified, not silently blessed.
    def _event(self,c,kind,subject,details):
        row=c.execute('SELECT hash FROM audit ORDER BY seq DESC LIMIT 1').fetchone()
        prev=row['hash'] if row else 'GENESIS'
        payload={'utc':_now(),'kind':kind,'subject':subject,'details':details,'prev_hash':prev}
        digest=hashlib.sha256(_canonical(payload).encode()).hexdigest()
        c.execute('INSERT INTO audit(utc,kind,subject,details_json,prev_hash,hash) VALUES(?,?,?,?,?,?)',
                  (payload['utc'],kind,subject,_canonical(details),prev,digest))
        return digest
    def add_case(self,rec:Record,analysis:dict):
        id=uuid.uuid4().hex[:16]
        path=self.records/(id+'.npz')
        record_to_npz(rec,path)
        try:
            with self.conn() as c:
                c.execute('''INSERT INTO cases
                    (id,name,origin,created,sha256,record_path,metadata_json,analysis_json,artifact_sha256)
                    VALUES(?,?,?,?,?,?,?,?,?)''',
                          (id,rec.name,rec.origin,_now(),rec.sha256,path.name,
                           _canonical(rec.metadata()),_canonical(analysis),_digest_file(path)))
                self._event(c,'import_and_analyze',id,{'sha256':rec.sha256,'name':rec.name,'engine':analysis['engine']})
        except Exception:
            path.unlink(missing_ok=True);raise
        return id
    def get_case(self,id):
        with self.conn() as c:r=c.execute('SELECT * FROM cases WHERE id=?',(id,)).fetchone()
        if not r:raise KeyError('Unknown case')
        record_path=(self.records/r['record_path']).resolve()
        if record_path.parent!=self.records.resolve():raise ValueError('Invalid record path')
        # The immutable source identity alone is insufficient: verify the saved waveform artifact.
        # Legacy v4.4 cases have no stored digest and remain research-only/unverified.
        if r['artifact_sha256'] and _digest_file(record_path) != r['artifact_sha256']:
            raise ValueError('Saved waveform integrity failure: archive hash mismatch')
        rec=record_from_npz(record_path)
        if rec.sha256 != r['sha256'] or rec.n != json.loads(r['metadata_json'])['samples']:
            raise ValueError('Saved waveform integrity failure: metadata mismatch')
        analysis=json.loads(r['analysis_json'])
        return dict(r),rec,analysis
    def verify_record_integrity(self):
        """Read-only integrity inventory; legacy cases never count as verified."""
        with self.conn() as c:
            rows=c.execute('SELECT id,sha256,record_path,artifact_sha256 FROM cases ORDER BY id').fetchall()
        out={'total':len(rows),'verified':0,'failed':0,'unverified_legacy':0,'failures':[]}
        folder=self.records.resolve()
        for row in rows:
            path=(folder/row['record_path']).resolve()
            try:
                if path.parent!=folder or not path.is_file():
                    raise ValueError('Missing or invalid record file')
                if not row['artifact_sha256']:
                    out['unverified_legacy']+=1
                    continue
                if _digest_file(path)!=row['artifact_sha256']:
                    raise ValueError('Waveform archive digest mismatch')
                # Verify that the store and serialized record agree on source identity.
                r=record_from_npz(path)
                if r.sha256 != row['sha256']:
                    raise ValueError('Source identity mismatch')
                out['verified']+=1
            except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, EOFError) as e:
                out['failed']+=1
                out['failures'].append({'case_id':row['id'],'reason':str(e)[:120]})
        return out

    def list_cases(self,search=''):
        with self.conn() as c:
            rows=c.execute('SELECT id,name,origin,created,sha256,metadata_json FROM cases WHERE name LIKE ? ORDER BY created DESC LIMIT 3000',('%'+search+'%',)).fetchall()
        return [{**dict(r),'metadata':json.loads(r['metadata_json'])} for r in rows]
    def add_review(self,id,label,note,reviewer='researcher'):
        allowed={'quality_acceptable','quality_unacceptable','needs_review','not_assessable'}
        if label not in allowed:raise ValueError('Unknown review label')
        if len(note)>2000 or len(reviewer)>100:raise ValueError('Review note is too long')
        rid=uuid.uuid4().hex[:16]
        with self.conn() as c:
            if not c.execute('SELECT 1 FROM cases WHERE id=?',(id,)).fetchone():raise KeyError('Unknown case')
            c.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?)',(rid,id,_now(),reviewer,label,note))
            self._event(c,'human_review',id,{'review_id':rid,'label':label,'reviewer':reviewer})
        return rid
    def reviews(self,id):
        with self.conn() as c:return [dict(x) for x in c.execute('SELECT * FROM reviews WHERE case_id=? ORDER BY created DESC',(id,)).fetchall()]
    def add_interval(self,id,channel,start_s,end_s,group_id,label,reviewer='researcher',note=''):
        """Independent human quality label for a reviewed time span."""
        import math
        if label not in {'quality_acceptable','quality_unacceptable','uncertain'}:
            raise ValueError('Unsupported interval label')
        if not all(math.isfinite(float(x)) for x in (start_s,end_s)) or end_s<=start_s or start_s<0:
            raise ValueError('Invalid annotation time range')
        if not group_id.strip() or len(group_id)>120 or len(reviewer)>120 or len(note)>1000:
            raise ValueError('Valid non-identifying group ID, reviewer and short note required')
        _,rec,_=self.get_case(id)
        if channel not in rec.channels or end_s>rec.duration+1e-6:
            raise ValueError('Channel or time range outside recording')
        aid=uuid.uuid4().hex[:16]
        with self.conn() as c:
            c.execute('INSERT INTO intervals VALUES(?,?,?,?,?,?,?,?,?,?)',
                (aid,id,channel,_now(),float(start_s),float(end_s),group_id,label,reviewer,note))
            self._event(c,'interval_annotation',id,
                        {'annotation_id':aid,'channel':channel,'start_s':start_s,'end_s':end_s,
                         'group_id':group_id,'label':label,'reviewer':reviewer})
        return aid
    def intervals(self,id=None):
        with self.conn() as c:
            if id:
                rows=c.execute('SELECT * FROM intervals WHERE case_id=? ORDER BY created DESC',(id,)).fetchall()
            else:
                rows=c.execute('SELECT * FROM intervals ORDER BY case_id,channel,start_s').fetchall()
        return [dict(x) for x in rows]
    def export_labeled_features(self,path,minimum_overlap=.8):
        """Only independently labelled windows are used; conflicts are excluded.
        The group_id MUST be consistent across all recordings from the same subject.
        """
        import csv
        from .processing import FEATURE_FIELDS
        all_annotations=self.intervals()
        by_key={}
        for a in all_annotations:
            by_key.setdefault((a['case_id'],a['channel']),[]).append(a)
        cols=['group_id','label','case_id','channel','start_s','end_s',*FEATURE_FIELDS]
        count=0;skipped=0
        with Path(path).open('w',newline='',encoding='utf8') as fp:
            writer=csv.DictWriter(fp,fieldnames=cols);writer.writeheader()
            for case in self.list_cases():
                id=case['id']
                with self.conn() as c:
                    row=c.execute('SELECT analysis_json FROM cases WHERE id=?',(id,)).fetchone()
                analysis=json.loads(row['analysis_json'])
                for ch,data in analysis['channels'].items():
                    ann=by_key.get((id,ch),[])
                    for win in data['windows']:
                        length=win['end_s']-win['start_s']
                        labels=[]
                        for a in ann:
                            overlap=max(0,min(win['end_s'],a['end_s'])-max(win['start_s'],a['start_s']))
                            if length>0 and overlap/length>=minimum_overlap and a['label']!='uncertain':
                                labels.append(a)
                        combos={(a['label'],a['group_id']) for a in labels}
                        if len(combos)!=1:
                            skipped+=1;continue
                        label,group=next(iter(combos))
                        writer.writerow({'group_id':safe_csv_text(group),'label':label,'case_id':id,'channel':safe_csv_text(ch),
                            'start_s':win['start_s'],'end_s':win['end_s'],
                            **{k:win[k] for k in FEATURE_FIELDS}})
                        count+=1
        return {'labeled_windows':count,'skipped_windows':skipped,'output':str(path)}
    def add_experiment(self,name,config,result):
        id=uuid.uuid4().hex[:16]
        with self.conn() as c:
            c.execute('INSERT INTO experiments VALUES(?,?,?,?,?)',(id,_now(),name,_canonical(config),_canonical(result)))
            self._event(c,'experiment',id,{'name':name})
        return id
    def list_experiments(self):
        with self.conn() as c:return [dict(x) for x in c.execute('SELECT * FROM experiments ORDER BY created DESC').fetchall()]
    def audit(self):
        with self.conn() as c:return [dict(x) for x in c.execute('SELECT * FROM audit ORDER BY seq').fetchall()]
    def verify_audit(self):
        rows=self.audit();prev='GENESIS'
        for i,row in enumerate(rows,1):
            if row['seq']!=i or row['prev_hash']!=prev:return {'valid':False,'events_checked':i-1,'error':'sequence_or_prev_hash'}
            payload={'utc':row['utc'],'kind':row['kind'],'subject':row['subject'],
                     'details':json.loads(row['details_json']),'prev_hash':prev}
            digest=hashlib.sha256(_canonical(payload).encode()).hexdigest()
            if digest!=row['hash']:return {'valid':False,'events_checked':i-1,'error':'hash_mismatch'}
            prev=digest
        return {'valid':True,'events_checked':len(rows),'head_hash':prev}
    def export_case_json(self,id,path):
        row,rec,analysis=self.get_case(id)
        obj={'id':id,'metadata':rec.metadata(),'analysis':analysis,'reviews':self.reviews(id),
             'research_only':True,'raw_waveforms_not_embedded':True}
        Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')
        return Path(path)
