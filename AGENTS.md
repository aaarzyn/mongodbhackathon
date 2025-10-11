## Mandatory Workflow Principles
- Do not use emoji
- After completing a series of tasks, add a timestamped summary of your work to @PROGRESS.md
- After updating @PROGRESS.md, commit your changes to git

## Core Architecture Principles

### 1. Error Handling & Exception Management
- **Use specific exceptions**: Prefer specific exception types over generic Exception
- **EAFP principle**: "Easier to Ask for Forgiveness than Permission" - use try/except rather than excessive checking
- **Context managers**: Use `with` statements for resource management
- **Custom exceptions**: Create domain-specific exception hierarchies

```python
# Good example
from contextlib import contextmanager
from typing import Iterator

class DataProcessingError(Exception):
    """Base exception for data processing errors."""
    pass

class ValidationError(DataProcessingError):
    """Raised when data validation fails."""
    pass

@contextmanager
def process_file(path: str) -> Iterator[str]:
    """Process a file with proper resource management."""
    try:
        with open(path, 'r') as f:
            yield f.read()
    except FileNotFoundError:
        raise DataProcessingError(f"File not found: {path}")
    except IOError as e:
        raise DataProcessingError(f"Failed to read file: {path}") from e
```

### 2. Type Hints & Static Typing
- **Use type hints**: Add type annotations for function signatures
- **Generic types**: Use `typing` module for complex type hints
- **Type checking**: Use `mypy` for static type checking
- **Runtime validation**: Consider `pydantic` for data validation

```python
# Type hints example
from typing import List, Dict, Optional, Union, TypeVar, Generic
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class Result(Generic[T]):
    """Generic result wrapper."""
    value: Optional[T] = None
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.error is None

def process_data(
    data: List[Dict[str, Union[str, int]]],
    filter_key: str
) -> Result[List[str]]:
    """Process data with type hints."""
    try:
        filtered = [
            str(item.get(filter_key, ''))
            for item in data
            if filter_key in item
        ]
        return Result(value=filtered)
    except Exception as e:
        return Result(error=str(e))
```

### 3. Async/Await & Concurrency
- **asyncio**: Use async/await for I/O-bound operations
- **threading**: Use for CPU-bound operations with GIL limitations
- **multiprocessing**: Use for CPU-intensive parallel processing
- **concurrent.futures**: High-level interface for async execution

```python
# Async example
import asyncio
import aiohttp
from typing import List, Dict

async def fetch_data(session: aiohttp.ClientSession, url: str) -> Dict:
    """Fetch data asynchronously."""
    async with session.get(url) as response:
        return await response.json()

async def fetch_multiple(urls: List[str]) -> List[Dict]:
    """Fetch multiple URLs concurrently."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_data(session, url) for url in urls]
        return await asyncio.gather(*tasks)
```

### 4. Configuration & Dependency Injection
- **Environment variables**: Use `python-dotenv` for .env files
- **Configuration classes**: Use `pydantic` for settings management
- **Dependency injection**: Use explicit dependency passing or libraries like `injector`
- **Feature toggles**: Use environment variables or configuration files

```python
# Configuration example
from pydantic import BaseSettings, Field
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings."""
    app_name: str = "MyApp"
    debug: bool = Field(False, env="DEBUG")
    database_url: str = Field(..., env="DATABASE_URL")
    api_key: str = Field(..., env="API_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

## File and Directory Structure

### Standard Layout
```
python-project/
├── src/                    # Source code
│   └── package_name/       # Main package
│       ├── __init__.py
│       ├── __main__.py     # Entry point for -m execution
│       ├── main.py         # Main application logic
│       ├── models/         # Data models
│       │   ├── __init__.py
│       │   └── user.py
│       ├── services/       # Business logic
│       │   ├── __init__.py
│       │   └── auth.py
│       ├── utils/          # Utility functions
│       │   ├── __init__.py
│       │   └── helpers.py
│       └── api/            # API endpoints (if applicable)
│           ├── __init__.py
│           └── routes.py
├── tests/                  # Test files
│   ├── __init__.py
│   ├── conftest.py        # pytest fixtures
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── test_*.py          # Test modules
├── docs/                  # Documentation
│   ├── conf.py            # Sphinx configuration
│   └── index.rst          # Documentation index
├── scripts/               # Utility scripts
├── data/                  # Data files (if needed)
├── notebooks/             # Jupyter notebooks (if applicable)
├── requirements/          # Dependency files
│   ├── base.txt          # Base requirements
│   ├── dev.txt           # Development requirements
│   └── prod.txt          # Production requirements
├── .env.example           # Example environment variables
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml         # Project configuration
├── setup.py               # Package setup (if distributing)
├── setup.cfg              # Setup configuration
├── MANIFEST.in            # Package manifest
├── Dockerfile             # Container configuration
└── README.md              # Project documentation
```

### File Naming Conventions
- **Python files**: Use snake_case (e.g., `user_service.py`, `auth_handler.py`)
- **Test files**: Prefix with `test_` (e.g., `test_user_service.py`)
- **Constants files**: Use UPPER_CASE for module names containing constants
- **Private modules**: Prefix with underscore (e.g., `_internal.py`)

## Code Style & Standards

### Documentation
- **Docstrings**: Use Google-style or NumPy-style docstrings consistently
- **Type hints**: Include in function signatures
- **Module documentation**: Add module-level docstring at the top
- **Examples**: Include usage examples in docstrings

```python
"""Module for user authentication and authorization.

This module provides functions and classes for handling user
authentication, including login, logout, and permission checking.
"""

from typing import Optional, Dict, Any

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user with username and password.

    Args:
        username: The user's username.
        password: The user's password (will be hashed).

    Returns:
        A dictionary containing user information if authentication
        succeeds, None otherwise.

    Raises:
        ValueError: If username or password is empty.
        DatabaseError: If database connection fails.

    Example:
        >>> user = authenticate_user("alice", "secret123")
        >>> if user:
        ...     print(f"Welcome, {user['name']}!")
    """
    if not username or not password:
        raise ValueError("Username and password are required")

    # Implementation here...
    return None
```

### Logging Standards
- **Structured logging**: Use `structlog` or Python's logging with formatters to log in JSON structure
- **Log levels**: Use appropriate levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Context**: Include relevant context in log messages
- **Performance**: Avoid expensive operations in log statements

```python
import logging
from functools import wraps
from typing import Callable, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def log_execution(func: Callable) -> Callable:
    """Decorator to log function execution."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.info(f"Executing {func.__name__}", extra={
            'function': func.__name__,
            'module': func.__module__
        })
        try:
            result = func(*args, **kwargs)
            logger.info(f"Successfully executed {func.__name__}")
            return result
        except Exception as e:
            logger.error(
                f"Error in {func.__name__}: {str(e)}",
                exc_info=True,
                extra={'function': func.__name__}
            )
            raise
    return wrapper
```

### Testing Requirements
- **pytest**: Use pytest as the primary testing framework
- **Coverage**: Maintain high test coverage (aim for >80%)
- **Fixtures**: Use pytest fixtures for test setup
- **Mocking**: Use `unittest.mock` or `pytest-mock`
- **Property testing**: Use `hypothesis` for property-based testing

```python
# tests/test_user_service.py
import pytest
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st

from src.package_name.services.user import UserService
from src.package_name.models.user import User

@pytest.fixture
def user_service():
    """Create a UserService instance for testing."""
    return UserService()

@pytest.fixture
def mock_database():
    """Create a mock database connection."""
    with patch('src.package_name.services.user.get_db_connection') as mock:
        yield mock

def test_create_user(user_service, mock_database):
    """Test user creation."""
    # Arrange
    mock_database.return_value.save.return_value = True
    user_data = {"name": "Alice", "email": "alice@example.com"}

    # Act
    user = user_service.create_user(**user_data)

    # Assert
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
    mock_database.return_value.save.assert_called_once()

@given(
    name=st.text(min_size=1, max_size=50),
    email=st.emails()
)
def test_user_validation(name, email):
    """Test user validation with random inputs."""
    user = User(name=name, email=email)
    assert user.is_valid()
```

## Common Patterns & Anti-Patterns

### Do's
- [GOOD] Use context managers for resource management
- [GOOD] Follow PEP 8 style guide
- [GOOD] Use type hints for better code clarity
- [GOOD] Write comprehensive docstrings
- [GOOD] Use virtual environments for isolation
- [GOOD] Implement proper logging
- [GOOD] Write tests before or alongside code
- [GOOD] Use list/dict/set comprehensions appropriately
- [GOOD] Handle exceptions specifically

### Don'ts
- [BAD] Don't use mutable default arguments
- [BAD] Don't use `import *`
- [BAD] Don't ignore exception handling
- [BAD] Don't use global variables unnecessarily
- [BAD] Don't write overly complex comprehensions
- [BAD] Don't modify lists while iterating
- [BAD] Don't use `eval()` or `exec()` with user input
- [BAD] Don't hardcode sensitive information

## Development Workflow

### Feature Development
1. **Design first**: Define interfaces and data structures
2. **Write tests**: Create failing tests (TDD approach)
3. **Implement incrementally**: Build in small, testable chunks
4. **Document**: Write docstrings and update documentation
5. **Refactor**: Clean up code while tests pass
6. **Review**: Self-review before submitting

### Code Review Checklist
- [ ] Follows PEP 8 and project style guide
- [ ] Has proper type hints
- [ ] Includes comprehensive tests
- [ ] Documentation is clear and complete
- [ ] No linting errors (black, flake8, mypy pass)
- [ ] Exception handling is appropriate
- [ ] Security best practices followed
- [ ] Performance considerations addressed

## Performance Considerations

### Optimization Strategies
- **Profiling**: Use `cProfile` and `line_profiler`
- **Caching**: Use `functools.lru_cache` for expensive operations
- **Lazy evaluation**: Use generators for large datasets
- **Vectorization**: Use NumPy/Pandas for numerical operations
- **Async I/O**: Use asyncio for concurrent I/O operations

```python
from functools import lru_cache
from typing import Iterator, List
import time

@lru_cache(maxsize=128)
def expensive_calculation(n: int) -> int:
    """Cache expensive calculation results."""
    time.sleep(0.1)  # Simulate expensive operation
    return n ** 2

def process_large_dataset(data: List[int]) -> Iterator[int]:
    """Process large dataset using generators."""
    for item in data:
        if item % 2 == 0:
            yield expensive_calculation(item)

# Efficient processing
results = list(process_large_dataset(range(1000)))
```

## Security & Privacy

### Security Best Practices
- **Input validation**: Always validate and sanitize user input
- **SQL injection**: Use parameterized queries
- **Secrets management**: Use environment variables, never hardcode
- **Dependencies**: Regularly update and audit dependencies
- **Authentication**: Use established libraries (e.g., `passlib`)

```python
import secrets
import hashlib
from typing import Tuple

def generate_secure_token() -> str:
    """Generate a cryptographically secure token."""
    return secrets.token_urlsafe(32)

def hash_password(password: str) -> Tuple[str, str]:
    """Hash password with salt."""
    salt = secrets.token_hex(32)
    pwdhash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return salt, pwdhash.hex()

def verify_password(password: str, salt: str, pwdhash: str) -> bool:
    """Verify password against hash."""
    new_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return new_hash.hex() == pwdhash
```

## Tooling & Development Environment

### Essential Tools
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing
- **coverage**: Code coverage
- **pre-commit**: Git hooks

### Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run all checks
black src tests
isort src tests
flake8 src tests
mypy src
pytest --cov=src
```

### IDE Configuration
- **VS Code**: Python extension with pylance
- **PyCharm**: Professional or Community edition
- **Configuration**: `.editorconfig`, `pyproject.toml`, `setup.cfg`

## Common Dependencies

### Core Libraries
- **requests/httpx**: HTTP client libraries
- **pydantic**: Data validation
- **click/typer**: CLI frameworks
- **fastapi/flask**: Web frameworks
- **sqlalchemy**: Database ORM
- **celery**: Task queue

### Testing Libraries
- **pytest**: Testing framework
- **pytest-cov**: Coverage plugin
- **pytest-mock**: Mocking helpers
- **hypothesis**: Property-based testing
- **factory-boy**: Test fixtures
- **responses**: Mock HTTP responses

### Development Tools
- **black**: Code formatter
- **isort**: Import organizer
- **flake8**: Linter
- **mypy**: Type checker
- **pre-commit**: Git hooks
- **tox**: Test automation

## Example Prompts for Claude

### Implementing New Features
```
Implement a REST API endpoint for user management using FastAPI with:
- CRUD operations for users
- JWT authentication
- Input validation with Pydantic models
- Proper error handling and status codes
- Comprehensive tests using pytest
- OpenAPI documentation
```

### Fixing Issues
```
Fix the async database connection pool issue in src/db/connection.py
where connections are not being properly released. The error occurs
when running concurrent requests. Ensure proper context manager usage
and add tests to verify the fix.
```

### Refactoring
```
Refactor the data processing module to use pandas DataFrames instead
of raw dictionaries. Maintain backward compatibility, improve performance
for large datasets, and add type hints throughout. Include benchmarks
comparing the old and new implementations.
```

### Performance Optimization
```
Optimize the image processing pipeline in src/imaging/processor.py
for better performance. Profile the current implementation, identify
bottlenecks, and implement improvements using multiprocessing or
async I/O where appropriate. Target 50% performance improvement.
