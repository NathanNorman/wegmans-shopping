# Testing Guide

Automated test suite for the Wegmans Shopping App.

## Quick Start

### Install Test Dependencies
```bash
pip install pytest pytest-cov pytest-timeout httpx
```

### Run All Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_database.py

# Run specific test class
pytest tests/test_api.py::TestCartEndpoints

# Run specific test
pytest tests/test_api.py::TestCartEndpoints::test_add_to_cart
```

### Run Tests by Category
```bash
# Fast unit tests only
pytest -m unit

# Integration tests (require database)
pytest -m integration

# API tests only
pytest -m api

# Skip slow tests
pytest -m "not slow"
```

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and configuration
├── test_auth.py          # Authentication tests
├── test_database.py      # Database operation tests (existing)
├── test_api.py           # API endpoint tests
└── README.md             # This file
```

## Fixtures

Shared test fixtures available in `conftest.py`:

### Database Fixtures
- `db_connection` - Database connection with automatic rollback
- `test_user_id` - Generate test user UUID
- `test_anonymous_user` - Create anonymous user
- `test_authenticated_user` - Create authenticated user

### API Fixtures
- `client` - FastAPI test client
- `test_cart_item` - Sample cart item
- `test_products` - Sample product list

### Example Usage
```python
def test_add_to_cart(test_anonymous_user, test_cart_item):
    """Test uses fixtures automatically"""
    add_to_cart(test_anonymous_user, test_cart_item)
    cart = get_user_cart(test_anonymous_user)
    assert len(cart) == 1
```

## Configuration

Test configuration in `pytest.ini`:
- Test discovery patterns
- Markers for categorization
- Output formatting
- Logging configuration

## Test Categories

### Unit Tests (Fast)
- No external dependencies
- Test individual functions
- Mock database/API calls
- Run frequently during development

### Integration Tests (Slow)
- Require database connection
- Test full workflows
- Real API calls (to test endpoints)
- Run before commits

### API Tests
- Test REST endpoints
- Request/response validation
- Error handling
- CORS and security

### Security Tests
- SQL injection attempts
- Input validation
- Authentication/authorization
- Rate limiting (future)

## Environment Variables

### Required
- `DATABASE_URL` - PostgreSQL connection string (or `TEST_DATABASE_URL`)

### Optional
- `TEST_DATABASE_URL` - Separate test database (recommended)

**Note**: Tests use transaction rollback, so main database can be used safely.

## Writing Tests

### Test Naming Convention
```python
class TestFeatureName:
    """Test description"""

    def test_specific_behavior(self):
        """Test what this test does"""
        # Arrange
        data = {"key": "value"}

        # Act
        result = function_under_test(data)

        # Assert
        assert result == expected_value
```

### Good Test Practices

1. **Arrange-Act-Assert Pattern**
```python
def test_cart_total():
    # Arrange - Set up test data
    cart = [{"price": 1.99, "quantity": 2}]

    # Act - Call function
    total = calculate_total(cart)

    # Assert - Verify result
    assert total == 3.98
```

2. **Use Descriptive Names**
```python
# Good
def test_adding_same_item_twice_increases_quantity():
    ...

# Bad
def test_cart():
    ...
```

3. **Test One Thing**
```python
# Good - Tests one specific behavior
def test_empty_cart_returns_zero_total():
    assert calculate_total([]) == 0

# Bad - Tests multiple things
def test_cart_operations():
    assert len(cart) == 0
    add_item()
    assert len(cart) == 1
    clear_cart()
    assert total == 0
```

4. **Use Fixtures for Setup**
```python
# Good - Uses fixture
def test_with_fixture(test_anonymous_user):
    cart = get_user_cart(test_anonymous_user)
    ...

# Bad - Manual setup in every test
def test_without_fixture():
    user_id = str(uuid.uuid4())
    # Manual DB insert...
    cart = get_user_cart(user_id)
    ...
```

## Coverage Goals

| Component | Current | Target |
|-----------|---------|--------|
| Database operations | 70% | 90% |
| API endpoints | 60% | 85% |
| Authentication | 50% | 80% |
| Utilities | 40% | 70% |
| **Overall** | 55% | 80% |

## Continuous Integration

### GitHub Actions (Future)
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt pytest pytest-cov
      - run: pytest --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Debugging Tests

### Run with Print Statements
```bash
pytest -s  # Disable output capture
```

### Run with Debugger
```bash
pytest --pdb  # Drop into debugger on failure
```

### Show Locals on Failure
```bash
pytest --showlocals  # Already enabled by default
```

### Run Last Failed Tests
```bash
pytest --lf  # Last failed
pytest --ff  # Failed first, then others
```

## Performance Testing

### Benchmark Tests (Future)
```python
def test_search_performance(benchmark):
    """Benchmark search operation"""
    result = benchmark(search_products, "bananas")
    assert len(result) > 0
```

### Load Testing (Future)
```bash
# Using locust or similar
locust -f tests/load_test.py --host=http://localhost:8000
```

## Test Data

### Database Seeding
```python
# tests/seed_data.py
def seed_test_data():
    """Populate database with test data"""
    # Create users, products, lists, etc.
```

### Factories (Future Enhancement)
```python
# Using factory_boy
class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Faker('uuid4')
    email = factory.Faker('email')
    is_anonymous = False
```

## Security Testing

### SQL Injection Tests
```python
def test_sql_injection_in_search():
    """Test SQL injection prevention"""
    malicious_input = "'; DROP TABLE users; --"
    result = search_products(malicious_input)
    # Should not execute SQL, should be escaped
```

### XSS Prevention
```python
def test_xss_in_product_name():
    """Test XSS script injection"""
    product = {
        "name": "<script>alert('XSS')</script>",
        "price": "$1.00"
    }
    # Should be safely escaped
```

## Troubleshooting

### Tests Fail with Database Errors
- Check `DATABASE_URL` is set correctly
- Verify database is running
- Run migrations: `python migrations/migrate.py up`

### Tests Pass Locally but Fail in CI
- Check environment variables in CI
- Verify dependencies in CI match local
- Check database version compatibility

### Slow Tests
- Use `-m "not slow"` to skip slow tests
- Consider mocking external API calls
- Use test database on faster storage

## Future Enhancements

- [ ] Add pytest-xdist for parallel execution
- [ ] Add pytest-timeout for hanging tests
- [ ] Add mutation testing with mutmut
- [ ] Set up code coverage reporting (Codecov)
- [ ] Add load testing with Locust
- [ ] Add security scanning (Bandit)
- [ ] Set up GitHub Actions CI/CD
- [ ] Add pre-commit hooks for running tests

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Python Testing Best Practices](https://realpython.com/pytest-python-testing/)
