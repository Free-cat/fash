from bot.copy.en import COPY as EN_COPY


def test_credit_packs_prod_pricing():
    packs = {p.id: p for p in EN_COPY.credit_packs}
    assert packs["single"].stars == 89
    assert packs["starter"].stars == 356
    assert packs["popular"].stars == 799
    assert packs["best"].stars == 1780
    assert packs["popular"].highlight is True


def test_credit_packs_discount_math():
    from bot.config import save_percent

    packs = {p.id: p for p in EN_COPY.credit_packs}
    assert save_percent(packs["single"]) is None
    assert save_percent(packs["starter"]) == 20
    assert save_percent(packs["popular"]) == 40
    assert save_percent(packs["best"]) == 50
