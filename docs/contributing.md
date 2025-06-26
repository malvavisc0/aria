---
layout: default
title: Contributing to Aria
---

# Contributing to Aria

Thank you for your interest in contributing to Aria! This guide will help you get started with contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and considerate of others when contributing to the project.

## How to Contribute

There are many ways to contribute to Aria:

1. **Report bugs**: If you find a bug, please create an issue on GitHub with a detailed description of the problem, steps to reproduce it, and your environment details.

2. **Suggest features**: Have an idea for a new feature? Create an issue on GitHub with a detailed description of the feature and why it would be valuable.

3. **Improve documentation**: Help improve the documentation by fixing typos, clarifying explanations, or adding missing information.

4. **Submit code changes**: Fix bugs, implement features, or improve the codebase by submitting pull requests.

## Development Setup

To set up your development environment:

1. **Fork the repository**: Click the "Fork" button on the GitHub repository to create your own copy.

2. **Clone your fork**: 
   ```bash
   git clone https://github.com/your-username/aria.git
   cd aria
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Docker**:
   ```bash
   docker-compose up -d
   ```

## Pull Request Process

1. **Create a branch**: Create a new branch for your changes.
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**: Implement your changes, following the project's coding style and guidelines.

3. **Write tests**: Add tests for your changes to ensure they work as expected.

4. **Run tests**: Make sure all tests pass before submitting your pull request.
   ```bash
   pytest
   ```

5. **Update documentation**: Update the documentation to reflect your changes, if necessary.

6. **Submit a pull request**: Push your changes to your fork and submit a pull request to the main repository.
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Code review**: Wait for a code review from the maintainers. Make any requested changes and push them to your branch.

## Coding Guidelines

- Follow PEP 8 style guidelines for Python code
- Write clear, concise, and descriptive commit messages
- Include comments in your code where necessary
- Write tests for your code
- Keep pull requests focused on a single change

## License

By contributing to Aria, you agree that your contributions will be licensed under the [MIT License](/aria/license.html).

## Questions?

If you have any questions about contributing, feel free to open an issue on GitHub or reach out to the maintainers directly.

Thank you for contributing to Aria!
