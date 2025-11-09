# Contributing to VoiceToText

[🇷🇺 Русская версия](#русская-версия)

Thank you for your interest in contributing to VoiceToText! This document provides guidelines for contributing.

## Code of Conduct

- Be respectful and considerate
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different viewpoints and experiences

## How to Contribute

### Reporting Bugs

- Use the bug report template
- Include steps to reproduce
- Provide system information (OS, Python version, platform)
- Include relevant error messages or logs

### Suggesting Features

- Use the feature request template
- Clearly describe the feature and its use case
- Explain why this feature would be useful
- Consider potential implementation approaches

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass
6. Run linter (`ruff check .`)
7. Run type checker (`pyright`)
8. Commit your changes (`git commit -m 'Add amazing feature'`)
9. Push to your branch (`git push origin feature/amazing-feature`)
10. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/VoiceToText.git
cd VoiceToText

# Choose your platform
cd platforms/macos  # or linux, or mlx

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

## Platform-Specific Guidelines

### macOS Platform
- Follow macOS development best practices
- Test on multiple macOS versions if possible
- Ensure Core ML compatibility

### Linux Platform
- Test on multiple Linux distributions
- Support both CPU and GPU modes
- Document CUDA requirements

### MLX Platform
- Optimize for Apple Silicon
- Test on M1/M2/M3 devices
- Minimize memory usage

## Coding Standards

- Follow PEP 8 style guide
- Use type hints for all functions
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Write meaningful commit messages

## Testing

- Write tests for new features
- Ensure all existing tests pass
- Aim for good test coverage
- Test on target platform

## Documentation

- Update README.md if needed
- Add docstrings to new functions/classes
- Update CHANGELOG.md for user-facing changes
- Update platform-specific documentation

## Questions?

Feel free to open an issue for any questions or concerns.

Thank you for contributing to VoiceToText! 🎉

---

## 🇷🇺 Русская версия

Спасибо за интерес к участию в разработке VoiceToText! Этот документ содержит руководящие принципы для участия.

## Кодекс поведения

- Будьте уважительны и внимательны
- Приветствуйте новичков и помогайте им учиться
- Фокусируйтесь на конструктивной обратной связи
- Уважайте разные точки зрения и опыт

## Как внести вклад

### Сообщение об ошибках

- Используйте шаблон отчета об ошибке
- Включите шаги для воспроизведения
- Укажите информацию о системе (ОС, версия Python, платформа)
- Включите соответствующие сообщения об ошибках или логи

### Предложение функций

- Используйте шаблон запроса функции
- Четко опишите функцию и ее применение
- Объясните, почему эта функция была бы полезной
- Рассмотрите возможные подходы к реализации

### Pull Requests

1. Форкните репозиторий
2. Создайте ветку функции (`git checkout -b feature/amazing-feature`)
3. Внесите изменения
4. Добавьте тесты при необходимости
5. Убедитесь, что все тесты проходят
6. Запустите линтер (`ruff check .`)
7. Запустите проверку типов (`pyright`)
8. Закоммитьте изменения (`git commit -m 'Add amazing feature'`)
9. Запушьте в ветку (`git push origin feature/amazing-feature`)
10. Откройте Pull Request

## Настройка разработки

```bash
# Клонируйте ваш форк
git clone https://github.com/YOUR_USERNAME/VoiceToText.git
cd VoiceToText

# Выберите вашу платформу
cd platforms/macos  # или linux, или mlx

# Установите зависимости
pip install -r requirements.txt

# Запустите тесты
pytest
```

## Вопросы?

Не стесняйтесь открывать issue для любых вопросов или проблем.

Спасибо за вклад в VoiceToText! 🎉

