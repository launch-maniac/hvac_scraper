# Contributing to HVAC Business Scraper

Thank you for your interest in contributing to the HVAC Business Scraper! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- GitHub account
- Basic knowledge of Flask and web scraping

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/hvac-business-scraper.git
   cd hvac-business-scraper
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

5. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your development settings
   ```

6. **Run the application**
   ```bash
   ./scripts/start.sh
   ```

## 🔄 Development Workflow

### Branching Strategy

We use Git Flow for branch management:

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `hotfix/*` - Critical bug fixes
- `release/*` - Release preparation

### Creating a Feature

1. **Create a feature branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Run tests
   pytest tests/
   
   # Run code quality checks
   black src/
   flake8 src/
   mypy src/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description
   
   - Detailed description of changes
   - Any breaking changes
   - References to issues"
   ```

5. **Push and create pull request**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

## 📝 Code Style Guidelines

### Python Code Style

We follow PEP 8 with some modifications:

- **Line length**: 88 characters (Black default)
- **Imports**: Use isort for import organization
- **Type hints**: Use type hints for all functions
- **Docstrings**: Use Google-style docstrings

Example:
```python
def scrape_business_data(location: str, business_type: str = "HVAC") -> List[Dict[str, Any]]:
    """Scrape business data from Google Maps.
    
    Args:
        location: The location to search in
        business_type: Type of business to search for
        
    Returns:
        List of business data dictionaries
        
    Raises:
        ScrapingError: If scraping fails
    """
    pass
```

### Frontend Code Style

- **HTML**: Use semantic HTML5 elements
- **CSS**: Use Tailwind CSS classes, avoid custom CSS when possible
- **JavaScript**: Use modern ES6+ syntax, prefer const/let over var

## 🧪 Testing Guidelines

### Writing Tests

- Write tests for all new functionality
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern
- Mock external dependencies

Example:
```python
def test_scrape_business_data_returns_valid_results():
    """Test that scraping returns properly formatted business data."""
    # Arrange
    scraper = HVACScraper()
    location = "Boise, ID"
    
    # Act
    results = scraper.scrape_business_data(location)
    
    # Assert
    assert isinstance(results, list)
    assert len(results) > 0
    assert all('name' in business for business in results)
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/

# Run specific test file
pytest tests/test_scraper.py

# Run tests matching pattern
pytest -k "test_scraper"
```

## 📚 Documentation

### Code Documentation

- Use clear, descriptive variable and function names
- Add docstrings to all public functions and classes
- Include type hints for better code understanding
- Comment complex logic and business rules

### User Documentation

- Update README.md for user-facing changes
- Add examples for new features
- Update API documentation for new endpoints
- Include screenshots for UI changes

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Clear description** of the issue
2. **Steps to reproduce** the problem
3. **Expected behavior** vs actual behavior
4. **Environment details** (OS, Python version, browser)
5. **Screenshots** if applicable
6. **Error messages** and stack traces

Use the bug report template when creating issues.

## 💡 Feature Requests

For new features, please:

1. **Check existing issues** to avoid duplicates
2. **Describe the problem** you're trying to solve
3. **Propose a solution** with implementation details
4. **Consider alternatives** and their trade-offs
5. **Provide use cases** and examples

Use the feature request template when creating issues.

## 🔒 Security

### Reporting Security Issues

**Do not** report security vulnerabilities through public GitHub issues.

Instead, email security@yourcompany.com with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Security Best Practices

- Never commit secrets or credentials
- Use environment variables for configuration
- Validate all user inputs
- Follow OWASP security guidelines
- Keep dependencies updated

## 📋 Pull Request Guidelines

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] No merge conflicts with target branch
- [ ] Commit messages follow convention

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass
- [ ] New tests added
- [ ] Manual testing completed

## Screenshots (if applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process

1. **Automated checks** must pass (tests, linting, security)
2. **Code review** by at least one maintainer
3. **Manual testing** for UI/UX changes
4. **Documentation review** for user-facing changes

## 🏷️ Commit Message Convention

We use Conventional Commits:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```bash
feat(scraper): add support for multiple cities
fix(auth): resolve login session timeout issue
docs(api): update endpoint documentation
test(scraper): add unit tests for data validation
```

## 🎯 Development Priorities

### High Priority
- Performance improvements
- Security enhancements
- Bug fixes
- Mobile optimization

### Medium Priority
- New scraping sources
- Additional export formats
- UI/UX improvements
- Integration features

### Low Priority
- Code refactoring
- Documentation improvements
- Developer tooling
- Nice-to-have features

## 🤝 Community Guidelines

### Be Respectful
- Use welcoming and inclusive language
- Respect different viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what's best for the community

### Be Collaborative
- Help others learn and grow
- Share knowledge and resources
- Provide constructive feedback
- Support fellow contributors

### Be Professional
- Keep discussions on-topic
- Avoid personal attacks or harassment
- Respect project maintainers' decisions
- Follow the code of conduct

## 📞 Getting Help

### Resources
- **Documentation**: Check the docs/ directory
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact maintainers directly for sensitive issues

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Email**: security@yourcompany.com for security issues
- **Project Board**: Track development progress

## 🎉 Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes for significant contributions
- GitHub contributor graphs
- Special mentions for outstanding contributions

Thank you for contributing to the HVAC Business Scraper! 🚀

