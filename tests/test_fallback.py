from bot.copy import init_copy


def test_fallback_copy_has_contextual_messages():
    copy = init_copy("en")
    assert "{balance}" in copy.fallback_unknown
    assert "clothing photo" in copy.fallback_unknown.lower()
    assert "{count}" in copy.fallback_unknown_with_cart
    assert "full-body" in copy.fallback_onboarding_person.lower()
