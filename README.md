
# FraudShield AI

Explainable Payment Risk Intelligence — AI-Powered Fraud Risk Analysis Prototype

## Overview

FraudShield AI is an interactive prototype designed to demonstrate how rule-based risk assessment and machine learning can work together to identify potentially unusual payment transactions and support human review.

The application is built with Python and Streamlit and is publicly deployed.

Live Demo: https://shield.streamlit.app

## Key Features 

- Interactive transaction risk assessment
- Rule-based risk scoring from 0 to 100
- Machine learning anomaly detection using Isolation Forest
- Risk explanations based on configured indicators
- Recommended actions and analysis summaries
- Publicly accessible Streamlit demonstration

## Technology Stack

- Python
- Streamlit
- Scikit-learn
- NumPy
- Pandas
- GitHub
- Streamlit Community Cloud

## How It Works

Users enter a transaction amount and select relevant risk indicators:

1. Customer and payment countries differ
2. New customer account
3. Unusual transaction activity

The application calculates a rule-based score and separately evaluates statistical anomalies using an Isolation Forest model trained on synthetic data.

The resulting interface displays risk indicators, anomaly detection results, explanations, and recommended review actions.

## Running Locally

Install dependencies:

pip install -r requirements.txt

Launch the application:

streamlit run app.py

## Current Limitations

This project is a demonstration prototype.

- The machine learning model uses synthetic training data.
- Statistical anomalies do not establish fraud.
- Risk scores are illustrative and have not been validated against real payment fraud datasets.
- The application does not process real payments.
- PayPal API and Sandbox integration are not yet implemented.
- Outputs must not be used for real-world payment approval or rejection decisions.

## Planned Development

- Explore PayPal Sandbox integration, subject to developer access and applicable requirements
- Add transaction simulation workflows
- Improve model evaluation and explainability
- Develop additional transaction analysis features
- Prepare a technical demonstration and submission materials

## Repository

https://github.com/taleem1120-glitch/paypal-ai-fraudshield

## License

MIT License
