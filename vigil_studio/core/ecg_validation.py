"""Independent, research-only ECG beat-location benchmarking.

Reference labels are never used to predict peaks or to choose the detection
threshold.  MIT-BIH beat symbols are *reference annotations*, not diagnoses.
This is not an arrhythmia classifier or a clinically validated QRS detector.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from .processing import detect_peaks, normalized_type

# WFDB / MIT-BIH beat annotations; '+' and rhythm/noise markers are excluded.
BEAT_SYMBOLS = frozenset({
    'N', 'L', 'R', 'B', 'A', 'a', 'J', 'S', 'V', 'r', 'F',
    'e', 'j', 'n', 'E', '/', 'f', 'Q', '?',
})


def reference_beats(annotation: dict, max_sample: int | None = None) -> list[dict]:
    if not annotation or annotation.get('source') != 'atr':
        raise ValueError('An original WFDB .atr reference annotation is required. Do not use manual quality labels as heartbeat ground truth.')
    samples, symbols = annotation.get('sample', []), annotation.get('symbol', [])
    if len(samples) != len(symbols):
        raise ValueError('Reference annotation positions/symbols differ in length')
    result = []
    last = -1
    for s, label in zip(samples, symbols):
        sample = int(s)
        if sample < 0 or sample < last:
            raise ValueError('Reference samples must be ordered, non-negative integers')
        last = sample
        if label in BEAT_SYMBOLS and (max_sample is None or sample < max_sample):
            result.append({'sample': sample, 'symbol': label})
    return result


def pair_beats(ref_samples, predicted_samples, fs: float, tolerance_s: float = .15):
    """Maximum-cardinality ordered 1:1 matching within a fixed tolerance.

    The threshold is fixed *before* examining the reference labels. Both
    matched and unmatched events are retained so counts are auditable.
    """
    if not math.isfinite(fs) or fs <= 0:
        raise ValueError('Invalid sampling frequency')
    if not math.isfinite(tolerance_s) or not .01 <= tolerance_s <= .25:
        raise ValueError('Tolerance must be between 10 ms and 250 ms')
    refs = np.sort(np.asarray(ref_samples, dtype=np.int64))
    pred = np.sort(np.asarray(predicted_samples, dtype=np.int64))
    if (len(refs) and refs[0] < 0) or (len(pred) and pred[0] < 0):
        raise ValueError('Event positions must be non-negative')
    if len(np.unique(refs)) != len(refs) or len(np.unique(pred)) != len(pred):
        raise ValueError('Duplicate event sample positions are not allowed')
    tol = int(round(fs * tolerance_s))
    i = j = 0
    matches = []
    missing = []
    extra = []
    while i < len(refs) and j < len(pred):
        a, b = int(refs[i]), int(pred[j])
        if abs(a - b) <= tol:
            matches.append({'reference_sample': a, 'predicted_sample': b,
                            'signed_error_ms': round((b-a)*1000/fs, 3)})
            i += 1; j += 1
        elif a < b:
            missing.append(a); i += 1
        else:
            extra.append(b); j += 1
    missing.extend(int(v) for v in refs[i:])
    extra.extend(int(v) for v in pred[j:])
    tp, fp, fn = len(matches), len(extra), len(missing)
    errors = np.asarray([abs(m['signed_error_ms']) for m in matches], dtype=float)
    sensitivity = tp/(tp+fn) if tp+fn else None
    ppv = tp/(tp+fp) if tp+fp else None
    f1 = 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None
    metrics = {
        'tp': tp, 'fp': fp, 'fn': fn,
        'sensitivity': round(sensitivity, 6) if sensitivity is not None else None,
        'positive_predictive_value': round(ppv, 6) if ppv is not None else None,
        'f1': round(f1, 6) if f1 is not None else None,
        'median_abs_timing_error_ms': round(float(np.median(errors)), 3) if len(errors) else None,
        'p95_abs_timing_error_ms': round(float(np.percentile(errors, 95)), 3) if len(errors) else None,
    }
    return {'metrics': metrics, 'matches': matches,
            'missed_reference_samples': missing, 'unmatched_prediction_samples': extra}


def evaluate_ecg_record(record, channel: str, tolerance_s: float = .15) -> dict:
    if channel not in record.channels or normalized_type(channel) != 'ECG':
        raise ValueError('Select an ECG channel in this recording')
    ref = reference_beats(record.annotation, record.n)
    if not ref:
        raise ValueError('This recording contains no reference beat annotations')
    # Signal only: annotations are NOT passed to this detector.
    predicted = detect_peaks(record.channels[channel], record.fs, 'ECG').astype(int)
    evaluation = pair_beats([b['sample'] for b in ref], predicted, record.fs, tolerance_s)
    matched_samples={m['reference_sample'] for m in evaluation['matches']}
    per_symbol={}
    for b in ref:
        value=per_symbol.setdefault(b['symbol'],{'reference':0,'detected_within_tolerance':0,'missed':0})
        value['reference']+=1
        if b['sample'] in matched_samples:value['detected_within_tolerance']+=1
        else:value['missed']+=1
    return {
        'schema': 'vigil-ecg-reference-benchmark-1',
        'research_only': True,
        'record_name': record.name,
        'record_sha256': record.sha256,
        'channel': channel,
        'fs_hz': float(record.fs),
        'duration_s': float(record.duration),
        'reference': {
            'source': 'published WFDB .atr',
            'n_beat_annotations': len(ref),
            'n_all_annotations': len(record.annotation.get('sample', [])),
            'file_sha256': record.annotation.get('file_sha256'),
            'beats': ref,
            'location_detection_by_reference_symbol': per_symbol,
        },
        'detector': {'name': 'vigil_heuristic_peak_finder', 'version': '1.0',
                     'uses_reference_labels_for_inference': False,
                     'n_predictions': int(len(predicted)),
                     'predicted_samples': predicted.tolist()},
        'comparison': {'tolerance_s': tolerance_s, **evaluation},
        'limitations': [
            'This measures agreement with published event locations, not arrhythmia classification.',
            'No reference labels enter the detector or its thresholds.',
            'An individual recording is not a clinical validation or generalization study.',
            'Reference beat symbols are not signal quality labels.',
            'Sensitivity and PPV exclude all non-beat reference events.',
        ],
    }


def annotation_counts(annotation: dict, max_sample=None) -> dict[str, int]:
    counts = {}
    for item in reference_beats(annotation, max_sample):
        counts[item['symbol']] = counts.get(item['symbol'], 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def export_evaluation_json(result: dict, path) -> Path:
    path = Path(path)
    if result.get('schema') != 'vigil-ecg-reference-benchmark-1':
        raise ValueError('Unrecognized research evaluation format')
    path.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf8')
    return path


def export_evaluation_csv(result: dict, path) -> Path:
    path = Path(path)
    cmp = result['comparison']
    fs = float(result['fs_hz'])
    with path.open('w', newline='', encoding='utf8') as f:
        w = csv.writer(f)
        w.writerow(['event_type', 'reference_sample', 'predicted_sample', 'reference_time_s',
                    'prediction_time_s', 'signed_timing_error_ms'])
        for m in cmp['matches']:
            a, b = m['reference_sample'], m['predicted_sample']
            w.writerow(['TP', a, b, f'{a/fs:.6f}', f'{b/fs:.6f}', m['signed_error_ms']])
        for a in cmp['missed_reference_samples']:
            w.writerow(['FN', a, '', f'{a/fs:.6f}', '', ''])
        for b in cmp['unmatched_prediction_samples']:
            w.writerow(['FP', '', b, '', f'{b/fs:.6f}', ''])
    return path
