def test_app_boots_without_error():
    from vills.core.main import create_app

    app = create_app()
    assert app.title == "Vills"


def test_routes_under_v1_prefix():
    from vills.core.main import create_app

    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v1/health" in paths
    assert "/api/v1/health/ready" in paths
