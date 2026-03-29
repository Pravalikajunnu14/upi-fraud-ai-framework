# Testing Guide

This document describes how to run tests for the UPI Fraud AI Framework.

## Setup

Install test dependencies:

```bash
pip install pytest pytest-cov
```

## Running Tests

### Run all tests

```bash
pytest backend/tests -v
```

### Run specific test file

```bash
pytest backend/tests/test_auth.py -v
```

### Run specific test class

```bash
pytest backend/tests/test_auth.py::TestAuthRegister -v
```

### Run specific test function

```bash
pytest backend/tests/test_auth.py::TestAuthRegister::test_register_success -v
```

### Run with coverage report

```bash
pytest backend/tests --cov=backend --cov-report=html --cov-report=term-missing
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Run by marker

```bash
# Integration tests only
pytest backend/tests -m integration

# Unit tests only (if added)
pytest backend/tests -m unit
```

## Test Structure

### conftest.py

Provides shared fixtures for all tests:

- `app`: Flask application with test database
- `client`: Flask test client
- `admin_token` / `user_token`: JWT tokens for different roles
- `admin_headers` / `user_headers`: HTTP headers with authorization
- `sample_transaction`: Valid transaction data
- `suspicious_transaction`: Transaction likely to be flagged as fraud
- Various invalid transaction fixtures for negative testing

### test_auth.py

Tests for authentication endpoints (`/api/auth/*`):

- **TestAuthRegister**: Registration with valid/invalid data
- **TestAuthLogin**: Login with correct/incorrect credentials
- **TestAuthJWT**: JWT token generation and validation
- **TestAuthEdgeCases**: Edge cases like long passwords, case sensitivity
- **TestAuthInvalidJson**: Invalid JSON payloads

### test_transactions.py

Tests for transaction endpoints (`/api/transactions/*`):

- **TestTransactionCheck**: Fraud detection with valid/invalid inputs
- **TestTransactionBlocking**: Transaction blocking functionality
- **TestTransactionList**: Listing and paginating transactions
- **TestTransactionGet**: Retrieving individual transactions
- **TestTransactionValidationErrors**: Comprehensive validation

### test_dashboard.py

Tests for dashboard endpoints (`/api/dashboard/*`):

- **TestDashboardStats**: Statistics endpoint
- **TestDashboardFeed**: Live transaction feed
- **TestDashboardHeatmap**: Geographic fraud heatmap
- **TestDashboardAlerts**: Fraud alerts
- Error cases and pagination

## Coverage Goals

Target: **>80% code coverage**

Current coverage after these tests should cover:
- All authentication flows
- Transaction validation and fraud checking
- Dashboard statistics and feeds
- Error handling and edge cases

Tracked files:
```
backend/routes/auth.py
backend/routes/transactions.py
backend/routes/dashboard.py
backend/utils/validators.py
backend/database/db.py
```

## Adding New Tests

1. Create a test function prefixed with `test_`:
   ```python
   def test_my_feature(client, user_headers):
       response = client.get("/api/endpoint", headers=user_headers)
       assert response.status_code == 200
   ```

2. Use fixtures from `conftest.py`:
   ```python
   def test_with_data(client, user_headers, sample_transaction):
       response = client.post("/api/transactions/check", 
                             headers=user_headers,
                             json=sample_transaction)
       assert response.status_code == 200
   ```

3. Add appropriate markers:
   ```python
   @pytest.mark.integration
   def test_database_interaction(client):
       ...
   ```

## Common Issues

### Import errors

Ensure the backend package path is correct in conftest.py. The project structure should be:

```
upi_fraud_ai_framework/
  backend/
    app.py
    config.py
    tests/
      conftest.py  
      test_auth.py
      ...
  pytest.ini
```

### Database not found

Tests use a temporary SQLite database. Ensure `backend/database/schema.sql` exists and is correct.

### JWT token issues

Tokens are generated in fixtures. If auth tests fail, ensure bcrypt is installed:

```bash
pip install bcrypt
```

## Continuous Integration

Recommended CI/CD integration:

```bash
# In your CI pipeline
pytest backend/tests -v --cov=backend --cov-report=xml
```

This generates coverage in XML format (compatible with most CI systems).

## Performance

Run tests with timeout to catch hanging tests:

```bash
pytest backend/tests --timeout=30
```

(Requires `pytest-timeout` package)

## Debugging

Run with verbose output and stop on first failure:

```bash
pytest backend/tests -vvs -x
```

Use `pytest --pdb` to drop into debugger on failure.
