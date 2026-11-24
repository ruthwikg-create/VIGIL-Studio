"""Research-only, fixed-protocol batch QRS-location assessment on local MIT-BIH.

This evaluates an existing exploratory detector. It does NOT provide a
medical-grade designation, arrhythmia classification, or clinical clearance.
Reference annotations are accessed only by the independent scorer.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from vigil_studio.core.importers import read_wfdb
from vigil_studio.core.ecg_validation import evaluate_ecg_record, export_evaluation_csv, export_evaluation_json
from vigil_studio.core.processing import normalized_type

# Published 48-record MIT-BIH Arrhythmia Database, version 1.0.0.
EXPECTED = tuple('100 101 102 103 104 105 106 107 108 109 111 112 113 114 115 116 117 118 119 121 122 123 124 200 201 202 203 205 207 208 209 210 212 213 214 215 217 219 220 221 222 223 228 230 231 232 233 234'.split())
PROTOCOL_ID = 'vigil-qrs-location-fixed-2026-11-24-v1'
TOLERANCE_SECONDS = 0.150
BOOTSTRAP_SEED = 20261124


def file_hash(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def discover_root(p: Path) -> Path:
    """Permit either an extracted top-level folder or a single nested dataset dir."""
    p = p.expanduser().resolve()
    if not p.is_dir():
        raise ValueError(f'Not an existing dataset folder: {p}')
    if (p / '100.hea').is_file():
        return p
    matches = list(p.glob('*/100.hea'))
    if len(matches) == 1:
        return matches[0].parent
    raise ValueError('Cannot locate 100.hea. Supply the folder containing 100.hea/100.dat/100.atr.')


def preflight(root: Path, records: tuple[str, ...]) -> dict:
    complete, missing, empty = [], [], []
    for rid in records:
        required = [root / (rid + suffix) for suffix in ('.hea', '.dat', '.atr')]
        absent = [p.name for p in required if not p.is_file()]
        if absent:
            missing.append({'record': rid, 'missing_files': absent})
            continue
        zero = [p.name for p in required if p.stat().st_size == 0]
        if zero:
            empty.append({'record': rid, 'empty_files': zero})
            continue
        complete.append(rid)
    return {'expected_records': list(records), 'complete_records': complete, 'missing': missing, 'empty': empty}


def metrics_from_counts(tp: int, fp: int, fn: int) -> dict:
    se = tp / (tp + fn) if tp + fn else None
    ppv = tp / (tp + fp) if tp + fp else None
    f1 = (2 * tp) / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {'tp': tp, 'fp': fp, 'fn': fn,
            'sensitivity': round(se, 6) if se is not None else None,
            'positive_predictive_value': round(ppv, 6) if ppv is not None else None,
            'f1': round(f1, 6) if f1 is not None else None}


def _percentile(vals: list[float], q: float) -> float | None:
    if not vals:
        return None
    vals = sorted(vals)
    pos = (len(vals) - 1) * q
    a, b = math.floor(pos), math.ceil(pos)
    return vals[a] + (vals[b] - vals[a]) * (pos - a)


def record_bootstrap(rows: list[dict], n: int = 1000, seed: int = BOOTSTRAP_SEED) -> dict:
    """Exploratory group bootstrap at subject level where known.

    MIT-BIH records 201 and 202 are from the same subject. Group those
    recordings together to avoid treating them as independent subjects.
    This still is not a prospective-study clinical confidence interval.
    """
    if len(rows) < 2:
        return {}
    groups = {}
    for i, row in enumerate(rows):
        rid = str(row.get('record_id', f'fixture_{i}'))
        group = 'mitbih_subject_201_202' if rid in ('201', '202') else rid
        groups.setdefault(group, []).append(row)
    if len(groups) < 2:
        return {}
    units = list(groups.values())
    rng = random.Random(seed)
    draws = {k: [] for k in ('sensitivity', 'positive_predictive_value', 'f1')}
    for _ in range(n):
        sampled_units = rng.choices(units, k=len(units))
        chosen = [row for unit in sampled_units for row in unit]
        m = metrics_from_counts(sum(int(x['tp']) for x in chosen),
                                sum(int(x['fp']) for x in chosen),
                                sum(int(x['fn']) for x in chosen))
        for key in draws:
            if m[key] is not None:
                draws[key].append(m[key])
    return {k: {'lower_2_5_percentile': round(_percentile(v, .025), 6),
                'upper_97_5_percentile': round(_percentile(v, .975), 6)}
            for k, v in draws.items() if v}


def _safe_name(value: str) -> str:
    # Output identifiers always come from the known public-record allowlist.
    if value not in EXPECTED:
        raise ValueError('Not a supported MIT-BIH record ID')
    return value


def evaluate_one(header: Path, events_dir: Path) -> dict:
    rid = _safe_name(header.stem)
    rec = read_wfdb(header)
    if rec.name != rid:
        raise ValueError('WFDB record name mismatch')
    if abs(rec.fs - 360) > 1e-5:
        raise ValueError(f'Unexpected MIT-BIH sampling frequency: {rec.fs}')
    if rec.annotation.get('source') != 'atr' or not rec.annotation.get('sample'):
        raise ValueError('Original .atr annotations were not imported')
    if rec.duration < 1700:
        raise ValueError(f'Record unexpectedly truncated: {rec.duration:.2f}s')
    channels = [n for n in rec.channels if normalized_type(n) == 'ECG']
    if not channels:
        raise ValueError('No recognized ECG channel')
    # This selection must be decided without using beat reference labels.
    lead = 'MLII' if 'MLII' in channels else channels[0]
    result = evaluate_ecg_record(rec, lead, TOLERANCE_SECONDS)
    metrics = result['comparison']['metrics']
    ev_csv = events_dir / f'{rid}_events.csv'
    ev_json = events_dir / f'{rid}_evaluation.json'
    export_evaluation_csv(result, ev_csv)
    export_evaluation_json(result, ev_json)
    symbols = result['reference']['location_detection_by_reference_symbol']
    return {'record_id': rid, 'lead': lead, 'fs_hz': rec.fs,
            'duration_s': round(rec.duration, 3),
            'n_reference_beats': result['reference']['n_beat_annotations'],
            'n_detector_predictions': result['detector']['n_predictions'],
            **metrics, 'median_abs_timing_error_ms': metrics['median_abs_timing_error_ms'],
            'p95_abs_timing_error_ms': metrics['p95_abs_timing_error_ms'],
            'source_waveform_sha256': rec.sha256,
            'source_annotation_sha256': rec.annotation.get('file_sha256'),
            'per_reference_symbol': symbols,
            'event_csv_sha256': file_hash(ev_csv), 'event_json_sha256': file_hash(ev_json)}


def aggregate(rows: list[dict]) -> dict:
    tp, fp, fn = (sum(int(r[k]) for r in rows) for k in ('tp','fp','fn'))
    pooled = metrics_from_counts(tp, fp, fn)
    macros = {}
    for k in ('sensitivity', 'positive_predictive_value', 'f1'):
        nums = [float(r[k]) for r in rows if r[k] is not None]
        macros[k] = round(sum(nums) / len(nums), 6) if nums else None
    symbols = {}
    for r in rows:
        for sym, data in r['per_reference_symbol'].items():
            d = symbols.setdefault(sym, {'reference': 0, 'detected_within_tolerance': 0, 'missed': 0})
            for key in d:
                d[key] += int(data[key])
    return {'pooled': pooled, 'macro_mean_per_record': macros,
            'subject_cluster_bootstrap_exploratory': record_bootstrap(rows),
            'per_reference_symbol_location_matches': symbols}


def make_report(run: dict) -> str:
    summary = run.get('summary', {})
    m = summary.get('pooled', {})
    lines = [
        '# VIGIL Studio — retrospective ECG beat-location benchmark', '',
        '**RESEARCH-ONLY — NOT MEDICALLY CERTIFIED, APPROVED OR VALIDATED FOR PATIENT CARE**', '',
        f"Protocol ID: `{PROTOCOL_ID}` (150 ms fixed, no post-hoc threshold tuning)",
        f"Dataset: MIT-BIH Arrhythmia Database v1.0.0 (local files; no network)",
        f"Recordings completed: {len(run['records'])} of {len(run['preflight']['expected_records'])}",
        f"Missing/incomplete: {len(run['preflight']['missing']) + len(run['preflight']['empty'])}",
        f"Processing failures: {len(run['errors'])}", '',
        '## Pooled event-location agreement', '',
        f"- TP: {m.get('tp', 'N/A')}; FP: {m.get('fp', 'N/A')}; FN: {m.get('fn', 'N/A')}",
        f"- Sensitivity: {m.get('sensitivity', 'N/A')}",
        f"- Positive predictive value: {m.get('positive_predictive_value', 'N/A')}",
        f"- F1: {m.get('f1', 'N/A')}", '',
        'These metrics measure QRS beat **locations**, not arrhythmia diagnosis, signal-quality calibration or clinical effectiveness.',
        'Any blank, failed or missing records make the complete-dataset benchmark incomplete.', '',
        '## Lowest-sensitivity records', '',
        '| Record | Lead | Reference beats | TP | FP | FN | Sensitivity | PPV |',
        '|---|---|---:|---:|---:|---:|---:|---:|',
    ]
    for r in sorted(run['records'], key=lambda z: (z['sensitivity'] is None, z['sensitivity'] or 0))[:12]:
        lines.append(f"| {r['record_id']} | {r['lead']} | {r['n_reference_beats']} | {r['tp']} | {r['fp']} | {r['fn']} | {r['sensitivity']} | {r['positive_predictive_value']} |")
    lines += ['', '## Data integrity / limitations', '',
              '- Every processed waveform and `.atr` source is represented by an SHA-256 digest.',
              '- Original files are read-only; no medical device interfaces or live alarms are connected.',
              '- Source labels are used only by the scorer, not by the detector.',
              '- The existing heuristic detector is deliberately unchanged from v4.4.',
              '- Records 201 and 202 belong to one subject and are grouped in the exploratory bootstrap.',
              '- This single historical dataset is not external clinical validation.',
              '- The current research application has no established safety classification or regulatory authorization.',
              '- Performance requirements and unacceptable-harm thresholds must be defined with qualified clinicians before clinical study.',
              '- All partial/failed runs and low-performance records must be retained and disclosed.',
              '- Never make diagnosis, suppress alarms, or choose patient treatment from these results.', '']
    if run['errors'] or run['preflight']['missing'] or run['preflight']['empty']:
        lines += ['## Incomplete data or processing errors', '', 'Review `results.json` for exact details.','']
    return '\n'.join(lines)


def execute(dataset: Path, output: Path, record_ids: tuple[str, ...], strict: bool = True) -> tuple[dict, int]:
    root = discover_root(dataset)
    if output.exists():
        raise ValueError(f'Result folder already exists, refusing to overwrite a prior run: {output}')
    output.mkdir(parents=True)
    events_dir = output / 'record_events'
    events_dir.mkdir()
    check = preflight(root, record_ids)
    source_algorithms = [HERE/'vigil_studio/core/ecg_validation.py', HERE/'vigil_studio/core/processing.py',
                         HERE/'vigil_studio/core/importers.py', Path(__file__)]
    protocol = {
        'protocol_id': PROTOCOL_ID,
        'locked_tolerance_seconds': TOLERANCE_SECONDS,
        'detector': 'vigil_heuristic_peak_finder',
        'lead_rule': 'MLII when available else first recognized ECG lead',
        'scoring': 'one-to-one 150ms beat-location matching',
        'data': 'Local published MIT-BIH Arrhythmia Database v1.0.0',
        'model_training': 'none', 'threshold_optimization': 'none',
        'code_sha256': {str(p.relative_to(HERE)): file_hash(p) for p in source_algorithms},
        'clinical_grade': False,
    }
    (output/'locked_protocol.json').write_text(json.dumps(protocol,indent=2), encoding='utf8')
    records, errors = [], []
    for rid in check['complete_records']:
        print(f'[{rid}] Running existing locked detector and comparison...', flush=True)
        try:
            records.append(evaluate_one(root/f'{rid}.hea', events_dir))
        except Exception as exc:
            errors.append({'record': rid, 'error_type': type(exc).__name__, 'reason': str(exc)})
            print(f'[{rid}] FAILED: {type(exc).__name__}: {exc}', file=sys.stderr, flush=True)
    run = {
        'schema': 'vigil-retrospective-qrs-batch-1',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'research_only': True,
        'medical_device_authorized': False,
        'intended_for_patient_care': False,
        'dataset_location': str(root),
        'protocol': protocol, 'preflight': check,
        'records': records, 'errors': errors,
        'summary': aggregate(records),
        'software_environment': {'python': sys.version, 'os': platform.platform()},
        'completion_status': 'COMPLETED' if len(records)==len(record_ids) and not errors else 'INCOMPLETE',
    }
    (output/'results.json').write_text(json.dumps(run, indent=2, allow_nan=False), encoding='utf8')
    cols = ('record_id', 'lead', 'fs_hz', 'duration_s', 'n_reference_beats', 'n_detector_predictions',
            'tp', 'fp', 'fn', 'sensitivity', 'positive_predictive_value', 'f1',
            'median_abs_timing_error_ms','p95_abs_timing_error_ms',
            'source_waveform_sha256','source_annotation_sha256')
    with (output/'per_record_metrics.csv').open('w',newline='',encoding='utf8') as f:
        wr=csv.DictWriter(f, fieldnames=cols)
        wr.writeheader()
        for r in records:
            wr.writerow({k:r.get(k) for k in cols})
    (output/'REPORT.md').write_text(make_report(run), encoding='utf8')
    from vigil_studio.core.professional_reports import write_benchmark_pdf
    write_benchmark_pdf(run,output/'BENCHMARK_RESEARCH_REPORT.pdf')
    complete = run['completion_status'] == 'COMPLETED'
    # A successful process exit means the requested dataset coverage was completed,
    # not that the algorithm achieved a clinical safety threshold.
    return run, (0 if (complete or not strict) else 2)


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description='Research-only fixed-protocol QRS location benchmark on published MIT-BIH data')
    p.add_argument('--dataset',required=True, type=Path,help='Folder containing 100.hea/100.dat/100.atr (or its parent folder)')
    p.add_argument('--out',required=True,type=Path,help='New output folder. Existing output is never overwritten.')
    p.add_argument('--record',choices=EXPECTED,help='Run one record for an engineering smoke test (not complete validation)')
    p.add_argument('--allow-incomplete',action='store_true',help='Allow incomplete dataset exit 0; incomplete status is always shown')
    args=p.parse_args(argv)
    try:
        ids=(args.record,) if args.record else EXPECTED
        run,exit_code=execute(args.dataset,args.out,ids,strict=not args.allow_incomplete)
        print('Completed:',len(run['records']),'of',len(ids),'recordings')
        print('Coverage status:',run['completion_status'])
        print('Results:',args.out.resolve())
        print('NOT CLINICAL VALIDATION. No medical certification, clearance or authorization is claimed.')
        return exit_code
    except Exception as exc:
        print(f'VALIDATION SETUP ERROR: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
