import pytest
from vigil_studio.core.importers import open_record,read_csv

def test_csv_with_time_infers_fs(tmp_path):
    p=tmp_path/'sample.csv'
    p.write_text('time_s,ECG,PPG\n'+'\n'.join(f'{i/100:.2f},{i*.003},{i*.002}' for i in range(100)))
    r=read_csv(p);assert abs(r.fs-100)<.01;assert r.n==100

def test_csv_with_explicit_fs(tmp_path):
    p=tmp_path/'signal.csv';p.write_text('ECG,PPG\n'+'\n'.join('0.1,0.2' for _ in range(100)))
    assert open_record(p,100).n==100

def test_pii_column_blocked(tmp_path):
    p=tmp_path/'private.csv';p.write_text('patient_id,ECG\n'+'\n'.join('person,0.2' for _ in range(100)))
    with pytest.raises(ValueError,match='identifier'):read_csv(p,100)

def test_missing_fs_rejected(tmp_path):
    p=tmp_path/'wave.csv';p.write_text('ECG\n'+'\n'.join('0.5' for _ in range(100)))
    with pytest.raises(ValueError,match='frequency'):read_csv(p)

def test_mismatch_time_rate(tmp_path):
    p=tmp_path/'time.csv';p.write_text('time,ECG\n'+'\n'.join(f'{i*.01},0.2' for i in range(100)))
    with pytest.raises(ValueError,match='disagree'):read_csv(p,125)

def test_unsupported_extension(tmp_path):
    p=tmp_path/'model.pkl';p.write_text('some bytes')
    with pytest.raises(ValueError,match='Supported'):open_record(p)
