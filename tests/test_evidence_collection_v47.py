from pathlib import Path
import json,pytest
from scripts.collect_engineering_evidence import collect,source_manifest,dependency_inventory


def test_evidence_does_not_require_patient_data(tmp_path):
    folder, obj=collect(tmp_path/'report',run_tests=False)
    assert obj['clinical_use_allowed'] is False
    assert obj['test_execution']['status']=='NOT_EXECUTED'
    assert obj['source_file_count']>20
    assert 'research-only' in obj['product']
    assert (folder/'SOURCE_SHA256.json').is_file()
    assert 'CLINICAL USE BLOCKED' in (folder/'EVIDENCE.md').read_text()
    with pytest.raises(FileExistsError):collect(folder,run_tests=False)


def test_source_manifest_cannot_include_workspace_patient_data(tmp_path):
    base=tmp_path/'source';(base/'vigil_studio').mkdir(parents=True)
    (base/'vigil_studio'/'a.py').write_text('x = 1')
    (base/'vigil_studio'/'record_patient123.dat').write_bytes(b'not part of source')
    (base/'workspace').mkdir()
    (base/'workspace'/'clinical.npz').write_bytes(b'raw')
    names=source_manifest(base)
    assert set(names)=={'vigil_studio/a.py'}
    assert all('patient' not in key for key in names)


def test_research_evidence_inventory_respects_missing_packages():
    data=dependency_inventory()
    assert 'numpy' in data and 'cryptography' in data
