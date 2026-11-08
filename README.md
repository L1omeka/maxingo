# 🦉 Maxingo Bot — Бот для подготовки к ОГЭ на платформе MAX
**Maxingo Bot** — интерактивный образовательный чат-бот в стиле Duolingo для подготовки к ОГЭ и ЕГЭ по 14 школьным предметам на базе Открытого банка заданий ФИПИ.
Бот включает в себя механику ежедневных тренировок, сохранение серии, систему разбора ошибок и автоматические напоминания по расписанию.
---
## 📋 Требования и стек технологий
- **Язык**: Python 3.10+ (рекомендуется Python 3.11)
- **Контейнеризация**: Docker / Docker Compose
- **Основные библиотеки** (`requirements.txt`):
  - `requests` — HTTP-клиент для взаимодействия с API платформы MAX и серверами ФИПИ
  - `apscheduler` — планировщик утренней рассылки заданий и ночной проверки ударного режима
  - `beautifulsoup4` — парсинг и очистка заданий ФИПИ из HTML/MathML
  - `pydantic` — валидация моделей данных и обновлений
  - `python-dotenv` — загрузка конфиденциальных переменных окружения из `.env`
  - `urllib3` — сетевой транспорт
---
## ⚙️ Настройка конфигурации
1. Склонируйте репозиторий или перейдите в папку проекта:
   ```bash
   git clone https://github.com/L1omeka/maxingo
   cd maxingo
   ```
2. Создайте файл `.env` на основе шаблона `.env.example`:
   - В Linux / macOS:
     ```bash
     cp .env.example .env
     ```
   - В Windows (PowerShell):
     ```powershell
     Copy-Item .env.example .env
     ```
3. Откройте `.env` и укажите ваш токен бота:
   ```env
   BOT_TOKEN=ваш_токен_бота_здесь
   ```
---
## 🚀 Вариант 1: Запуск через командную строку (локально)
### 1. Создание и активация виртуального окружения
- **Windows**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```
- **Linux / macOS**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
### 2. Установка зависимостей
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
### 3. Запуск бота
```bash
python Maxingo_Bot.py
```
---
## 🐳 Вариант 2: Запуск через Docker
### Способ A. Сборка и запуск через чистый Docker CLI
1. **Сборка Docker-образа**:
   ```bash
   docker build -t maxingo-bot .
   ```
2. **Запуск контейнера**:
   ```bash
   docker run -d \
     --name maxingo_bot \
     --restart unless-stopped \
     --env-file .env \
     -v $(pwd)/tasks.json:/app/tasks.json \
     -v $(pwd)/users.json:/app/users.json \
     -v $(pwd)/maxingo.log:/app/maxingo.log \
     maxingo-bot
   ```
   *(Для Windows PowerShell замените `$(pwd)` на `${PWD}`)*
3. **Просмотр логов контейнера**:
   ```bash
   docker logs -f maxingo_bot
   ```
4. **Остановка контейнера**:
   ```bash
   docker stop maxingo_bot
   ```
---
### Способ B. Запуск через Docker Compose (рекомендуется)

1. **Запуск в фоновом режиме**:
   ```bash
   docker compose up -d --build
   ```
2. **Просмотр логов**:
   ```bash
   docker compose logs -f
   ```
3. **Остановка**:
   ```bash
   docker compose down
   ```
---
## 🔄 Обновление базы заданий (опционально)
Если требуется актуализировать базу заданий из открытого банка ФИПИ:
```bash
python fipi_parser.py
```
Скрипт автоматически скачает и сохранит задания по всем 14 предметам в файл `tasks.json`.
---
