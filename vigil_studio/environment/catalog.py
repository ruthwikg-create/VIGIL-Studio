"""Curated, version-pinned, official *public* PhysioNet research sources.

Disk sizes are upstream approximations, not an installed-size promise. Sources
remain uninstalled until a user explicitly chooses to download under its license.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class Dataset:
    key: str
    name: str
    version: str
    license: str
    compressed_gb: float
    unpacked_gb: float
    doi: str
    purpose: str
    access: str = "open"

    @property
    def page(self):
        return f"https://physionet.org/content/{self.key}/{self.version}/"

    @property
    def zip_url(self):
        return f"https://physionet.org/content/{self.key}/get-zip/{self.version}/"

    def to_dict(self):
        return {**asdict(self), 'page':self.page, 'archive_url':self.zip_url}

SOURCES = (
    Dataset('mitdb','MIT-BIH Arrhythmia', '1.0.0','ODC-By 1.0',.0735,.1043,'10.13026/C2F305','Expert-annotated ECG beat analysis'),
    Dataset('afdb','MIT-BIH Atrial Fibrillation', '1.0.0','ODC-By 1.0',.4397,.6059,'10.13026/C2MW2D','Long rhythm monitoring'),
    Dataset('nsrdb','MIT-BIH Normal Sinus Rhythm', '1.0.0','ODC-By 1.0',.5827,.5827,'10.13026/C2NK5R','Long duration reference ECG'),
    Dataset('ptb-xl','PTB-XL', '1.0.3','CC BY 4.0',1.7,3.0,'10.13026/kfzx-aw45','12-lead ECG generalization research'),
    Dataset('ecg-arrhythmia','Large-scale 12-lead ECG Arrhythmia', '1.0.0','CC BY 4.0',2.3,5.1,'10.13026/wgex-er52','Cross-device 12-lead signal study'),
    Dataset('challenge-2020','PhysioNet/CinC 2020 12-lead ECG', '1.0.2','CC BY 4.0',4.5,7.5,'10.13026/dvyd-kd57','Independent-source 12-lead benchmarks'),
    Dataset('eegmmidb','EEG Motor Movement and Imagery', '1.0.0','ODC-By 1.0',1.9,3.4,'10.13026/C28G6P','Neuroscience and motor imagery EEG'),
    Dataset('sleep-edfx','Sleep-EDF Expanded', '1.0.0','ODC-By 1.0',8.1,8.1,'10.13026/C2X676','Sleep polysomnography and EEG'),
    Dataset('bidmc','BIDMC PPG and Respiration', '1.0.0','ODC-By 1.0',.2078,.2077,'10.13026/C2208R','PPG and respiration validation'),
    Dataset('semg','Surface EMG Ground Walking', '1.0.0','ODC-By 1.0',.2785,.427,'10.13026/bwvb-ht51','EMG gait and rehabilitation'),
    # The full 2015 challenge ZIP includes nested zips; size of its unpacked
    # tree is not reliably declared by PhysioNet, so exclude from disk totals.
)
BY_KEY={entry.key:entry for entry in SOURCES}
PRESETS={
    'starter':('mitdb','afdb','nsrdb'),
    'research-10gb':('mitdb','afdb','nsrdb','ptb-xl','ecg-arrhythmia','challenge-2020'),
    'research-multimodal-30gb':tuple(d.key for d in SOURCES),
}

def select(keys):
    values=[]
    for key in keys:
        if key not in BY_KEY:raise KeyError(f'Unknown dataset: {key}')
        if key not in (s.key for s in values):values.append(BY_KEY[key])
    if not values:raise ValueError('No datasets selected')
    return tuple(values)

def preset_summary(name):
    if name not in PRESETS:raise KeyError(f'Unknown preset: {name}')
    choices=select(PRESETS[name]);return {
        'preset':name,'datasets':[d.key for d in choices],
        'published_compressed_gb_approx':round(sum(d.compressed_gb for d in choices),3),
        'published_uncompressed_gb_approx':round(sum(d.unpacked_gb for d in choices),3),
        'foundation_weights_gb_approx':1.3855,
        'additional_install_dependencies_and_intermediates':'Variable, disk-space reservation required',
        'assets_present_in_source_archive':False,
    }
