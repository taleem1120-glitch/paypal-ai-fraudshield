"""Sandbox-only API boundary. Never return raw responses on failures."""
import base64
import json
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

PAYPAL_API = "https://api-m.sandbox.paypal.com"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        # Do not forward Authorization to a redirected destination.
        return None


def urlopen(request, timeout):
    return build_opener(_NoRedirect()).open(request, timeout=timeout)


class PayPalError(Exception):
    """Safe, customer-visible API failure."""


def _request(path, headers, payload=None, form=False):
    data = payload.encode() if form else (
        json.dumps(payload).encode() if payload is not None else None
    )
    request = Request(PAYPAL_API + path, data=data, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ValueError
        return result
    except HTTPError as error:
        if error.code == 401:
            raise PayPalError(
                "PayPal Sandbox authentication failed (HTTP 401). "
                "The credentials were rejected by PayPal."
            ) from None
        raise PayPalError(
            f"PayPal Sandbox request failed (HTTP {error.code})."
        ) from None
    except (URLError, TimeoutError, OSError):
        raise PayPalError(
            "Network error while connecting to PayPal Sandbox."
        ) from None
    except (ValueError, TypeError):
        raise PayPalError(
            "PayPal Sandbox returned an invalid response."
        ) from None


def get_paypal_access_token():
    try:
        import streamlit as st
        client_id = st.secrets["PAYPAL_CLIENT_ID"]
        client_secret = st.secrets["PAYPAL_CLIENT_SECRET"]
        if not client_id or not client_secret:
            raise ValueError
        auth = base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode()
    except Exception:
        raise PayPalError(
            "PayPal Sandbox credentials are not configured."
        ) from None

    result = _request(
        "/v1/oauth2/token",
        {
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        "grant_type=client_credentials",
        form=True,
    )
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        raise PayPalError(
            "PayPal Sandbox did not return a valid access token."
        )
    return token


def _safe_call(operation):
    try:
        return True, operation()
    except PayPalError as error:
        return False, str(error)
    except Exception:
        return False, "Unable to complete the PayPal Sandbox request."


def test_paypal_connection():
    def authenticate():
        get_paypal_access_token()
        return "PayPal Sandbox authentication successful."

    return _safe_call(authenticate)


def get_paypal_sandbox_order(order_id):
    if not isinstance(order_id, str) or not re.fullmatch(
        r"[A-Za-z0-9-]{1,64}", order_id.strip()
    ):
        return False, "A valid Order ID is required."

    def retrieve():
        token = get_paypal_access_token()
        return _request(
            f"/v2/checkout/orders/{order_id.strip()}",
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )

    return _safe_call(retrieve)


def create_paypal_sandbox_order():
    def create():
        token = get_paypal_access_token()
        result = _request(
            "/v2/checkout/orders",
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": "USD",
                            "value": "1.00",
                        }
                    }
                ],
            },
        )
        if not isinstance(result.get("id"), str) or not result["id"]:
            raise PayPalError(
                "PayPal Sandbox returned an invalid order."
            )
        return result

    return _safe_call(create)
