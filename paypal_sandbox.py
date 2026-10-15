import requests
import streamlit as st

PAYPAL_API = "https://api-m.sandbox.paypal.com"


def get_paypal_access_token():
    client_id = st.secrets["PAYPAL_CLIENT_ID"]
    client_secret = st.secrets["PAYPAL_CLIENT_SECRET"]

    response = requests.post(
        f"{PAYPAL_API}/v1/oauth2/token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def test_paypal_connection():
    try:
        token = get_paypal_access_token()
        response = requests.get(
            f"{PAYPAL_API}/v1/catalogs/products",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            params={"page_size": 1},
            timeout=20,
        )
        response.raise_for_status()
        return True, "PayPal Sandbox API connection successful."
    except (requests.RequestException, KeyError, ValueError):
        return False, "PayPal Sandbox connection failed."
    except Exception:
        return False, "PayPal configuration or connection error."
