"""Deterministic and interpretable signal checks for *research*, not clinical use.

No alarm is ever automatically silenced or labelled a true/false clinical event.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import math
import re
import csv
from typing import Any

import numpy as np
from scipy.signal import find_peaks, detrend

ENGINE_VERSION = "research-0.1.0"
MAX_BYTES = 12 * 1024 * 1024
MAX_SAMPLES = 300_000
ALLOWED_CHANNELS = ("ECG", "PPG", "ABP", "RESP")
ALIASES = {
    "ecg": "ECG", "ekg": "ECG", "ii": "ECG", "ecgii": "ECG", "mlii": "ECG", "ecglead2": "ECG", "lead2": "ECG",
    "pleth": "PPG", "ppg": "PPG", "photoplethysmogram": "PPG", "spo2wave": "PPG",
    "abp": "ABP", "art": "ABP", "arterialpressure": "ABP", "arterialbp": "ABP",
    "resp": "RESP", "respiration": "RESP", "breathing": "RESP",
}
BLOCKED_IDENTIFIERS = {"patient", "patientid", "patientname", "name", "dob", "birthdate", "mrn", "ssn", "aadhaar", "aadhar", "phone", "address", "email"}


class DataError(ValueError):
    pass


@dataclass(frozen=True)
class InputSignal:
    sample_rate_hz: float
    channels: dict[str, list[float]]
    source_sha256: str
    n_samples: int
    format: str = "csv"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.strip().lower())


def parse_csv(payload: bytes, sample_rate_hz: float) -> InputSignal:
    if not (2 <= sample_rate_hz <= 2000 and math.isfinite(sample_rate_hz)):
        raise DataError("Sampling rate must be between 2 and 2000 Hz")
    if len(payload) > MAX_BYTES:
        raise DataError("CSV exceeds 12 MB safety limit")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DataError("CSV must be UTF-8 encoded") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise DataError("CSV needs a header and numerical signal columns")
    heads = [h.strip() for h in reader.fieldnames if h is not None]
    if any(_slug(h) in BLOCKED_IDENTIFIERS for h in heads):
        raise DataError("Potential identifiers detected. Remove personal-data columns and retry")
    mapping: dict[str, str] = {}
    for header in heads:
        key = ALIASES.get(_slug(header))
        if key and key not in mapping:
            mapping[key] = header
    if not mapping:
        raise DataError("CSV needs at least one supported channel: ECG, PPG, ABP, RESP")
    time_header = next((h for h in heads if _slug(h) in {"time", "times", "second", "seconds", "timestamp"}), None)
    values = {k: [] for k in mapping}
    times: list[float] = []
    for index, row in enumerate(reader):
        if index >= MAX_SAMPLES:
            raise DataError("CSV exceeds 300,000 samples. Import a smaller research segment")
        if time_header is not None:
            try:
                time_value = float(row.get(time_header, ""))
            except (ValueError, TypeError) as exc:
                raise DataError(f"Invalid time coordinate at row {index+2}") from exc
            if not math.isfinite(time_value):
                raise DataError(f"Time coordinate not finite at row {index+2}")
            times.append(time_value)
        for key, header in mapping.items():
            raw = row.get(header, "")
            try:
                value = float(raw) if raw is not None and raw.strip() else float("nan")
            except (ValueError, AttributeError) as exc:
                raise DataError(f"Invalid numeric cell in {key} at row {index+2}") from exc
            values[key].append(value)
    if not values or len(next(iter(values.values()))) < max(30, math.ceil(sample_rate_hz)):
        raise DataError("Need at least one second of readings and at least 30 samples")
    if times:
        differences = np.diff(np.asarray(times, dtype=float))
        if np.any(differences <= 0):
            raise DataError("Time samples must be strictly increasing")
        dt = float(np.median(differences))
        if abs(dt - 1.0 / sample_rate_hz) > max(0.05 / sample_rate_hz, 1e-10):
            raise DataError("CSV timestamps disagree with the supplied sampling frequency")
        if np.any(differences > 1.5 / sample_rate_hz):
            raise DataError("Large timestamp gap; split the file or repair time metadata before importing")
    return InputSignal(sample_rate_hz, values, hashlib.sha256(payload).hexdigest(), len(next(iter(values.values()))))


def _finite_segment(vals: list[float]) -> np.ndarray:
    x = np.asarray(vals, dtype=np.float64)
    return x[np.isfinite(x)]


def quality_features(values: list[float], sample_rate_hz: float) -> dict[str, Any]:
    x = np.asarray(values, dtype=np.float64)
    finite_mask = np.isfinite(x)
    availability = float(np.mean(finite_mask))
    clean = x[finite_mask]
    if len(clean) < 10:
        return {"availability": round(availability, 4), "flatline_fraction": 1.0,
                "high_frequency_fraction": None, "dynamic_range": 0.0,
                "quality_score": 0.0, "label": "unusable", "flags": ["insufficient_finite_samples"]}
    span = float(np.percentile(clean, 99) - np.percentile(clean, 1))
    delta = np.abs(np.diff(x))
    valid_pairs = np.isfinite(delta)
    if span < 1e-9:
        flat_fraction = 1.0
    else:
        flat_fraction = float(np.mean((delta[valid_pairs] <= max(span * 0.0002, 1e-12)))) if np.any(valid_pairs) else 1.0
    # Rough high-frequency energy proxy. Sensitive to edge cases; NOT a validated SQI.
    hf = None
    if len(clean) >= 64 and span > 1e-9:
        centered = clean - np.median(clean)
        power = np.abs(np.fft.rfft(centered)) ** 2
        freqs = np.fft.rfftfreq(len(centered), d=1 / sample_rate_hz)
        total = float(np.sum(power[freqs > 0.25]))
        if total > 0:
            hf = float(np.sum(power[freqs > min(25.0, sample_rate_hz * 0.30)]) / total)
    flags = []
    if availability < 0.98:
        flags.append("missing_or_nonfinite_samples")
    if span < 1e-8 or flat_fraction > 0.50:
        flags.append("possible_flatline")
    if hf is not None and hf > 0.75:
        flags.append("possible_high_frequency_artifact")
    # Heuristic score for UX/research exploration, not calibrated probability.
    score = availability * (1 - min(1.0, flat_fraction * 1.4))
    if hf is not None:
        score *= (1 - min(0.65, hf * 0.45))
    if span < 1e-8:
        score = 0.0
    score = float(np.clip(score, 0, 1))
    label = "review" if score >= 0.70 else "low_quality" if score >= 0.30 else "unusable"
    return {"availability": round(availability, 4), "flatline_fraction": round(flat_fraction, 4),
            "high_frequency_fraction": round(hf, 4) if hf is not None else None,
            "dynamic_range": round(span, 7), "quality_score": round(score, 4),
            "label": label, "flags": flags}


def estimate_rate(values: list[float], sample_rate_hz: float, kind: str) -> dict[str, Any]:
    """Basic peak-detection *exploration*, never a validated vital-sign estimate."""
    if kind not in {"ECG", "PPG", "ABP"}:
        return {"estimated_bpm": None, "peak_count": 0, "reason": "unsupported_channel"}
    x = np.asarray(values, dtype=float)
    # Avoid connecting gaps into artificial peaks.
    if not np.all(np.isfinite(x)) or len(x) < 3 * sample_rate_hz:
        return {"estimated_bpm": None, "peak_count": 0, "reason": "missing_values_or_short_segment"}
    x = detrend(x)
    robust_range = float(np.percentile(x, 95) - np.percentile(x, 5))
    if robust_range < 1e-7:
        return {"estimated_bpm": None, "peak_count": 0, "reason": "flat_signal"}
    distance = max(2, int(sample_rate_hz * (0.30 if kind == "ECG" else 0.35)))
    prominence = robust_range * (0.30 if kind == "ECG" else 0.38)
    # For ECG use dominant polarity; downstream validation must compare against expert QRS.
    choices = []
    for polarity in (1, -1) if kind == "ECG" else (1,):
        peaks, _ = find_peaks(x * polarity, prominence=prominence, distance=distance)
        if len(peaks) >= 3:
            rr = np.diff(peaks) / sample_rate_hz
            bpm = 60.0 / float(np.median(rr))
            if 30 <= bpm <= 220:
                cv = float(np.std(rr) / max(float(np.mean(rr)), 1e-7))
                choices.append((cv, int(len(peaks)), bpm))
    if not choices:
        return {"estimated_bpm": None, "peak_count": 0, "reason": "no_stable_peaks"}
    cv, count, bpm = min(choices, key=lambda v: (v[0], -v[1]))
    return {"estimated_bpm": round(bpm, 1), "peak_count": count,
            "beat_interval_cv": round(cv, 3), "reason": "exploratory_peak_detector"}


def review_signals(data: InputSignal) -> dict[str, Any]:
    if not data.channels:
        raise DataError("No channels")
    channels: dict[str, dict[str, Any]] = {}
    for name, values in data.channels.items():
        if name not in ALLOWED_CHANNELS:
            continue
        quality = quality_features(values, data.sample_rate_hz)
        rate = estimate_rate(values, data.sample_rate_hz, name)
        channels[name] = {**quality, **rate}
    good_rates = [(k, v["estimated_bpm"]) for k, v in channels.items()
                  if k in ("ECG", "PPG", "ABP") and v["quality_score"] >= 0.7
                  and v.get("estimated_bpm") is not None and v.get("beat_interval_cv", 9) < 0.5]
    pairs = [{"a": a, "b": b, "difference_bpm": round(abs(av - bv), 1)}
             for i, (a, av) in enumerate(good_rates) for b, bv in good_rates[i + 1:]]
    if not pairs:
        decision = "INSUFFICIENT_EVIDENCE"
        summary = "Too few independent usable pulse estimates; human waveform review required."
    elif any(p["difference_bpm"] > 12 for p in pairs):
        decision = "DISCORDANT"
        summary = "Available pulse estimates disagree; investigate signal quality and timing."
    else:
        decision = "MULTIMODAL_CONSISTENT"
        summary = "Exploratory pulse rates agree; this does NOT rule out an arrhythmia."
    duration = data.n_samples / data.sample_rate_hz
    chart_stride = max(1, math.ceil(data.n_samples / 1500))
    chart = {k: [round(float(v), 5) if math.isfinite(v) else None for v in values[::chart_stride]]
             for k, values in data.channels.items()}
    return {
        "engine_version": ENGINE_VERSION, "intended_use": "research_only_no_clinical_alarm_control",
        "source_sha256": data.source_sha256, "sample_rate_hz": data.sample_rate_hz,
        "samples": data.n_samples, "duration_seconds": round(duration, 2),
        "decision": decision, "summary": summary, "channels": channels,
        "rate_comparisons": pairs,
        "waveform_preview": {"decimation_step": chart_stride, "channels": chart},
        "limitations": ["Thresholds and peak detector are exploratory and unvalidated",
                        "Multimodal agreement does not exclude malignant arrhythmia",
                        "Never suppress, cancel, delay, or prioritize a live medical alarm from this output"]
    }
