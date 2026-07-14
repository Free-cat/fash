from bot.copy.en import COPY as EN_COPY


def test_credit_packs_prod_pricing():
    packs = {p.id: p for p in EN_COPY.credit_packs}
    assert packs["single"].stars == 20
    assert packs["starter"].stars == 50
    assert packs["popular"].stars == 120
    assert packs["best"].stars == 250
    assert packs["popular"].highlight is True
