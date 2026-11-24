"""Explicit, user-initiated public MIT-BIH dataset download; no hidden data acquisition.
Source: PhysioNet MIT-BIH Arrhythmia Database 1.0.0, DOI 10.13026/C2F305.
License: Open Data Commons Attribution 1.0; users must comply with the original license.
"""
from __future__ import annotations
import argparse,hashlib,json,urllib.request,urllib.parse,time
from pathlib import Path

BASE='https://physionet.org/files/mitdb/1.0.0/'
ALLOW={'100','101','102','103','104','105','106','107','108','109','111','112','113',
       '114','115','116','117','118','119','121','122','123','124','200','201','202',
       '203','205','207','208','209','210','212','213','214','215','217','219','220',
       '221','222','223','228','230','231','232','233','234'}

def download_record(name,out):
    if name not in ALLOW:raise ValueError('Invalid record ID; see valid MIT-BIH IDs')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    results=[]
    for suffix in ('hea','dat','atr'):
        filename=f'{name}.{suffix}';url=BASE+filename
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'VIGILStudioResearch/1.0'}),timeout=60) as resp:
            data=resp.read(30*1024*1024+1)
        if len(data)>30*1024*1024:raise ValueError('Unexpectedly large file')
        dst=out/filename;dst.write_bytes(data)
        results.append({'file':filename,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'url':url})
    manifest={'dataset':'MIT-BIH Arrhythmia Database','version':'1.0.0','doi':'10.13026/C2F305',
              'license':'ODC Attribution 1.0','record':name,'files':results}
    (out/(name+'.provenance.json')).write_text(json.dumps(manifest,indent=2),encoding='utf8')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--records',nargs='+',default=['100'],help='E.g. 100 101 102')
    p.add_argument('--out',default='external_data/mitdb');args=p.parse_args()
    print('Dataset copyright and usage terms apply. Read https://physionet.org/content/mitdb/1.0.0/')
    for record in args.records:
        m=download_record(record,args.out)
        print(f"Downloaded real MIT-BIH record {record}: {sum(x['bytes'] for x in m['files']):,} bytes")
