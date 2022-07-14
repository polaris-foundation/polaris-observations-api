from flask.testing import FlaskClient


class TestSwaggerUi:
    def test_swagger_ui(self, client: FlaskClient) -> None:
        response = client.get("/ui/")
        assert response.status_code == 200
        assert "text/html" in response.headers["Content-Type"]

    def test_spec_yaml(self, client: FlaskClient) -> None:
        response = client.get("/openapi.yaml")
        assert response.status_code == 200
        assert "text/yaml" in response.headers["Content-Type"]

    def test_spec_json(self, client: FlaskClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "application/json" in response.headers["Content-Type"]
