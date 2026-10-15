FraudShield AI

Explainable Payment Risk Intelligence — PayPal Sandbox + Machine Learning Prototype

Overview

FraudShield AI is an interactive payment risk analysis prototype developed for the PayPal AI Hackathon 2026.

It combines PayPal Sandbox API integration, rule-based risk scoring, and machine learning anomaly detection to demonstrate how suspicious transaction patterns can be identified and explained.

Live Demo: https://paypal-ai-fraudshield.streamlit.app/

Source Code: https://github.com/taleem1120-glitch/paypal-ai-fraudshield

Key Features

- PayPal Sandbox OAuth authentication
- Create test orders using the PayPal Orders API
- Retrieve Sandbox orders by order ID
- Automatically load retrieved order amounts into the analysis form
- Rule-based risk scoring from 0 to 100
- Machine learning anomaly detection using Isolation Forest
- Human-readable risk explanations and review recommendations
- Fictional transaction simulator
- Session-based transaction analysis history
- Downloadable CSV analysis reports

PayPal Integration

FraudShield AI connects to the official PayPal Sandbox API.

Implemented capabilities include:

1. Authenticate using PayPal Sandbox OAuth 2.0.
2. Create a Sandbox test order for USD 1.00.
3. Retrieve a Sandbox order using its order ID.
4. Extract the order amount and status.
5. Use the retrieved amount in the risk analysis workflow.

Sandbox orders may have a "CREATED" status. Creating an order does not mean that a payment has been approved, captured, or completed.

Risk indicators are entered manually and are not verified by PayPal.

Artificial Intelligence

The application uses an Isolation Forest machine learning model trained on synthetic transaction data.

It evaluates transaction amounts and selected risk indicators to identify statistical anomalies.

The application also calculates an independent rule-based risk score and provides explanations for the selected indicators.

Important: Statistical anomalies are not proof of fraud. The model has not been validated against real-world fraud datasets.

Technology Stack

- Python
- Streamlit
- Scikit-learn
- NumPy
- Pandas
- Requests
- PayPal Sandbox REST API
- GitHub
- Streamlit Community Cloud

Run Locally

Clone the repository:

git clone https://github.com/taleem1120-glitch/paypal-ai-fraudshield.git
cd paypal-ai-fraudshield

Install dependencies:

pip install -r requirements.txt

Configure the following Streamlit secrets using credentials from your own PayPal Developer Sandbox application:

PAYPAL_CLIENT_ID = "your_sandbox_client_id"
PAYPAL_CLIENT_SECRET = "your_sandbox_client_secret"
PAYPAL_MODE = "sandbox"

Never commit real API credentials to the public repository.

Start the application:

streamlit run app.py

Demonstration Workflow

1. Open the live application.
2. Test PayPal Sandbox authentication.
3. Create a USD 1.00 Sandbox order.
4. Copy the generated order ID.
5. Retrieve the order using the lookup form.
6. Confirm that the order amount is loaded into the transaction analysis form.
7. Select risk indicators and analyze the transaction.
8. Review the risk score, anomaly result, explanations, and recommended action.
9. Download the analysis history as a CSV file.

Limitations

FraudShield AI is a demonstration prototype.

- No real payments are processed.
- PayPal integration uses the Sandbox environment only.
- The machine learning model uses synthetic training data.
- Risk indicators are supplied manually.
- Risk scores are illustrative and are not validated fraud probabilities.
- Transaction analysis history is stored only during the Streamlit session.
- Results must not be used for real payment approval, rejection, or fraud enforcement decisions.

License

MIT License.

Hackathon

Developed as a prototype for the PayPal AI Hackathon 2026.
