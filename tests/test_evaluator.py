from scripts.evaluate_qrs import match_events

def test_one_to_one_matching():
    out=match_events([100,200,300],[100,101,205],fs=250,tolerance_s=.03)
    assert out['tp']==2 and out['fp']==1 and out['fn']==1
