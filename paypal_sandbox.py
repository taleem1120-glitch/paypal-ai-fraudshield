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
        if token:
            return True, "PayPal Sandbox authentication successful."
        return False, "PayPal did not return an access token."
    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else "unknown"
        return False, f"PayPal authentication failed. HTTP status: {status}"
    except requests.RequestException:
        return False, "Network error while connecting to PayPal Sandbox."
    except (KeyError, ValueError):
        return False, "Missing configuration or invalid PayPal response."
    except Exception:
        return False, "PayPal configuration error."

    

def get_paypal_sandbox_order(order_id):
    """Retrieve a PayPal Sandbox order without capturing payment."""
    if not order_id or not order_id.strip():
        return False, "Order ID is required."

    try:
        token = get_paypal_access_token()

        response = requests.get(
            f"{PAYPAL_API}/v2/checkout/orders/{order_id.strip()}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=20,
        )

        response.raise_for_status()
        return True, response.json()

    except requests.HTTPError as error:
        status = error.response.status_code
        return False, f"PayPal API error: HTTP {status}"

    except requests.RequestException:
        return False, "Network error while retrieving the order."

    except Exception:
        return False, "Unable to retrieve the PayPal Sandbox order."
