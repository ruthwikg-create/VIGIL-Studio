"""Research environment tests are engineering tests, NOT clinical validation."""
import io,json, os, stat, zipfile
from pathlib import Path
import numpy as np
import pytest

from vigil_studio.environment.catalog import BY_KEY,select,preset_summary
from vigil_studio.environment.downloads import (
    AcquisitionError,inspect_zip,safe_extract,install_dataset,download_archive,enough_space,sha256)
from vigil_studio.environment.inventory import (
    parse_wfdb_header,build_wfdb_index,directory_stats,resource_status,InventoryError)
from vigil_studio.environment.robustness import stress_test,perturb,ARTIFACTS,save_stress_report,StressTestError
from vigil_studio.environment.cli import report_status,run
from vigil_studio.core.records import Record


def makezip(tmp_path, files, name='fixture.zip'):
    p=tmp_path/name
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():z.writestr(k,v)
    return p

def test_all_catalog_sources_are_pinned():
    s=preset_summary('research-10gb')
    assert s['published_uncompressed_gb_approx']>=15
    assert s['assets_present_in_source_archive'] is False
    assert len(s['datasets'])>=6
    assert all(BY_KEY[i].zip_url.startswith('https://physionet.org/') for i in s['datasets'])
    assert BY_KEY['challenge-2020'].license=='CC BY 4.0'


def test_unknown_catalog_rejected():
    with pytest.raises(KeyError):select(['private-dataset'])
    with pytest.raises(ValueError):select([])


def test_archive_inspection_and_safe_extraction(tmp_path):
    z=makezip(tmp_path,{'folder/100.hea':'100 2 360 650000\n100.dat 212 200 11 1024 0\n',
                        'folder/100.dat':b'waveforms'})
    info=inspect_zip(z)
    assert info['file_entries']==2
    stage=tmp_path/'out'
    safe_extract(z,stage)
    assert (stage/'folder'/'100.hea').read_text().startswith('100 2')
    assert not (stage/'outside').exists()

@pytest.mark.parametrize('name',['../escape.txt','/etc/passwd','C:/Windows/file.txt','dir\\evil.txt'])
def test_zip_slip_rejected(tmp_path,name):
    z=makezip(tmp_path,{name:'bad'})
    with pytest.raises(AcquisitionError):inspect_zip(z)


def test_zip_symlink_rejected(tmp_path):
    z=tmp_path/'symlink.zip'
    with zipfile.ZipFile(z,'w') as f:
        i=zipfile.ZipInfo('link');i.create_system=3;i.external_attr=(stat.S_IFLNK|0o777)<<16
        f.writestr(i,'../../etc')
    with pytest.raises(AcquisitionError,match='Symlink'):inspect_zip(z)


def test_zip_inflation_cap(tmp_path):
    z=makezip(tmp_path,{'data.bin':b'a'*100000})
    with pytest.raises(AcquisitionError,match='size limit'):inspect_zip(z,max_uncompressed=10000)


def test_duplicate_zip_member_rejected_case_insensitive(tmp_path):
    z=makezip(tmp_path,{'A.txt':'one','a.TXT':'two'})
    with pytest.raises(AcquisitionError,match='Repeated'):inspect_zip(z)


def test_license_must_be_accepted(tmp_path):
    with pytest.raises(AcquisitionError,match='must read and accept'):
        install_dataset('mitdb',tmp_path)


def test_valid_local_archive_install_and_receipt(tmp_path):
    z=makezip(tmp_path,{'100.hea':'100 2 360 3600\n100.dat 212 200 11 1024 0\n',
                        '100.dat':b'ABCD'*80})
    ws=tmp_path/'workspace'
    result=install_dataset('mitdb',ws,accept_license=True,local_archive=z)
    assert result['status']=='INSTALLED'
    receipt=ws/'datasets'/'mitdb'/'1.0.0'/'vigil_source_receipt.json'
    info=json.loads(receipt.read_text())
    assert info['archive_sha256']==sha256(z)
    assert info['clinical_validated'] is False
    assert install_dataset('mitdb',ws,accept_license=True,local_archive=z)['status']=='ALREADY_INSTALLED'


def test_existing_folder_without_receipt_rejected(tmp_path):
    (tmp_path/'datasets'/'mitdb'/'1.0.0').mkdir(parents=True)
    z=makezip(tmp_path,{'100.hea':'100 2 360 3600'})
    with pytest.raises(AcquisitionError,match='without a valid installation receipt'):
        install_dataset('mitdb',tmp_path,accept_license=True,local_archive=z)


def test_download_rejects_nonapproved_domain(tmp_path):
    with pytest.raises(AcquisitionError,match='Only catalog-pinned'):
        download_archive('https://example.com/malware.zip',tmp_path/'file.zip',100)


def test_local_disk_space_probe(tmp_path):
    out=enough_space(tmp_path,100,200)
    assert out['free_gb']>0


def test_header_parser_and_record_index(tmp_path):
    d=tmp_path/'dataset';d.mkdir()
    (d/'100.hea').write_text('100 2 360 650000\n100.dat 212 200 11 1024 0\n')
    (d/'100.dat').write_bytes(b'data')
    (d/'bad.hea').write_text('invalid')
    assert parse_wfdb_header(d/'100.hea')['channels']==2
    result=build_wfdb_index(d,tmp_path/'indexes'/'mitdb.jsonl')
    assert result['record_headers']==2 and result['invalid_headers']==1
    rows=[json.loads(x) for x in (tmp_path/'indexes'/'mitdb.jsonl').read_text().splitlines()]
    assert rows[0]['record_id']=='100'
    assert rows[0]['dat_present'] is True
    assert rows[0]['fs_hz']==360
    assert rows[0]['header_sha256']


def test_index_cannot_write_inside_source(tmp_path):
    d=tmp_path/'original';d.mkdir()
    with pytest.raises(InventoryError):build_wfdb_index(d,d/'index.jsonl')


def test_directory_inventory(tmp_path):
    (tmp_path/'x.dat').write_bytes(b'abc')
    (tmp_path/'y.hea').write_bytes(b'ab')
    stats=directory_stats(tmp_path)
    assert stats['files']==2 and stats['bytes']==5
    assert stats['by_extension']['.hea']==1


def test_resource_probe_no_network(tmp_path):
    status=resource_status(tmp_path)
    assert status['logical_cpu_cores']>=1 and status['disk_free_gb']>0


def test_fully_offline_status(tmp_path):
    info=report_status(tmp_path)
    assert info['installed_verified_clinical_models']==0
    assert info['foundation_model']['installed'] is False
    assert len(info['datasets'])>=6


def make_record():
    fs=250
    t=np.arange(fs*12)/fs
    x=.2*np.sin(2*np.pi*1.1*t)+.08*np.sin(2*np.pi*15*t)
    return Record({'ECG II':x},fs,'SYNTHETIC_ENGINEERING_TEST','SYNTHETIC_NOT_CLINICAL','')


def test_artifact_scenarios_are_reproducible():
    r=make_record();x=r.channels['ECG II']
    a=perturb(x,r.fs,'motion_bursts',seed=14)
    b=perturb(x,r.fs,'motion_bursts',seed=14)
    assert np.array_equal(a,b)
    assert len(ARTIFACTS)>=8


def test_stress_report_is_not_clinical_validation(tmp_path):
    r=make_record()
    report=stress_test(r,'ECG II',seconds=8)
    assert report['kind']=='ENGINEERING_STRESS_TEST_NOT_CLINICAL_VALIDATION'
    assert len(report['results'])==len(ARTIFACTS)
    assert all(item['human_quality_ground_truth'] is None for item in report['results'])
    target=tmp_path/'stress.json';save_stress_report(report,target)
    assert json.loads(target.read_text())['seed']==42


def test_low_fs_skips_powerline():
    x=np.sin(np.arange(800)/40)
    with pytest.raises(StressTestError):perturb(x,80,'powerline_50hz')


def test_cli_plan_and_status(tmp_path,capsys):
    assert run(['--workspace',str(tmp_path),'plan'])==0
    assert 'published_uncompressed' in capsys.readouterr().out
    assert run(['--workspace',str(tmp_path),'status'])==0
    assert 'NOT_INSTALLED' in capsys.readouterr().out


def test_cli_full_collection_requires_license(tmp_path,capsys):
    assert run(['--workspace',str(tmp_path),'install-preset'])==2
    assert 'Review each upstream license' in capsys.readouterr().err


def test_snapshot_creates_json(tmp_path):
    output=tmp_path/'snapshot.json'
    assert run(['--workspace',str(tmp_path),'snapshot','--out',str(output)])==0
    assert json.loads(output.read_text())['research_only'] is True


def test_publisher_checksum_verification(tmp_path):
    import hashlib
    from vigil_studio.environment.inventory import verify_publisher_sha256s
    p=tmp_path/'data';p.mkdir()
    (p/'100.dat').write_bytes(b'actual-data')
    digest=hashlib.sha256(b'actual-data').hexdigest()
    (p/'SHA256SUMS.txt').write_text(f'{digest}  100.dat\n')
    assert verify_publisher_sha256s(p)['status']=='PASS_MATCHED_ENTRIES'
    (p/'100.dat').write_bytes(b'tampered')
    assert verify_publisher_sha256s(p)['mismatched']==1

def test_missing_publisher_checksum_list_is_not_verified(tmp_path):
    from vigil_studio.environment.inventory import verify_publisher_sha256s
    assert verify_publisher_sha256s(tmp_path)['status']=='NO_PUBLISHER_CHECKSUM_LIST'
