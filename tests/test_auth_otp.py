from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_signin_page_loads():
    response = client.get("/signin")
    assert response.status_code == 200
    assert "Sign in with OTP" in response.text


def test_request_and_verify_otp_for_email():
    response = client.post(
        "/api/request-otp",
        json={"identifier": "user@example.com"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert "otp" in payload

    otp = payload["otp"]
    verify_response = client.post(
        "/api/verify-otp",
        json={"identifier": "user@example.com", "otp": otp},
    )
    assert verify_response.status_code == 200, verify_response.text
    assert verify_response.json()["success"] is True
