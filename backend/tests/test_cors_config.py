from app.core.config import Settings


def test_cors_origins_supports_csv() -> None:
    settings = Settings(cors_origins="http://localhost:3000, http://127.0.0.1:3000")
    assert settings.cors_origin_list == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_cors_origins_supports_json_array() -> None:
    settings = Settings(cors_origins='["http://localhost:3000","http://127.0.0.1:3000"]')
    assert settings.cors_origin_list == ["http://localhost:3000", "http://127.0.0.1:3000"]
