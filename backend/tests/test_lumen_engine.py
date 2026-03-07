from app.models.preview import TimeOfDay
from app.services.lumen_engine import LumenEngine


def test_lumen_engine_profiles_match_expected_kelvin() -> None:
    assert LumenEngine.profile_for(TimeOfDay.SUNRISE).kelvin == 2500
    assert LumenEngine.profile_for(TimeOfDay.NOON).kelvin == 5600
    assert LumenEngine.profile_for(TimeOfDay.GOLDEN_HOUR).kelvin == 3000
    assert LumenEngine.profile_for(TimeOfDay.MIDNIGHT).kelvin == 5000
