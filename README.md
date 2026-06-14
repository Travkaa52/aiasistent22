# 🤖 Business AI Assistant Bot

Telegram-бот с **Business Mode** и ИИ на базе **Gemini** для личного использования в бизнесе.  
Отвечает твоим контактам от твоего имени, помнит историю каждого диалога, управляется через панель в боте.

---

## ✨ Что умеет

| Функция | Описание |
|---|---|
| 🧠 **Автоответы с ИИ** | Gemini 2.5 Flash отвечает от твоего имени в Business чатах |
| 📚 **История диалогов** | Помнит контекст каждой переписки (настраиваемая глубина) |
| 📋 **Заметки о контактах** | Добавь заметку `/note USER_ID текст` — ИИ учтёт её при ответах |
| 🔑 **Статические автоответы** | Быстрые ответы по ключевым словам (приоритет выше ИИ) |
| 🔕 **Блокировка контактов** | `/block_contact USER_ID` — заблокировать автоответ конкретному |
| 📣 **Рассылка** | Отправить сообщение всем пользователям |
| 👥 **Менеджеры** | Делегировать доступ к панели другим |
| 🛡 **Антиспам** | Фильтры ссылок и запрещённых слов |
| 📊 **Статистика и аналитика** | Сколько сообщений, топ пользователей, активность по дням |
| ✏️ **Кастомный промпт** | Настрой характер и знания ИИ прямо из панели |

---

## ⚙️ Установка

### 1. Получи необходимые данные

- **BOT_TOKEN** — создай бота у [@BotFather](https://t.me/BotFather) и подключи Business Mode  
- **OWNER_ID** — твой Telegram ID (узнай у [@userinfobot](https://t.me/userinfobot))  
- **GEMINI_KEY** — получи на [aistudio.google.com](https://aistudio.google.com/app/apikey)

### 2. Настройка

```bash
git clone / распакуй архив
cd aiasistent

pip install -r requirements.txt

cp .env.example .env
# Открой .env и заполни все поля
```

### 3. Запуск

```bash
python bot.py
```

---

## 🔧 Настройка .env

```env
BOT_TOKEN=1234567890:ABC...
OWNER_ID=123456789
GEMINI_KEY=AIza...

# Имя и бизнес (используются в промпте ИИ)
OWNER_NAME=Алексей Иванов
BUSINESS_NAME=ООО «Техно Плюс»
BUSINESS_DESCRIPTION=Продаём IT-оборудование оптом и в розницу. Работаем по всей стране.

AI_LANGUAGE=ru
AI_HISTORY_DEPTH=10   # Сколько прошлых сообщений помнит ИИ в одном чате
```

---

## 📱 Управление через бота

### Основные команды

| Команда | Что делает |
|---|---|
| `/admin` | Открыть панель администратора |
| `/note USER_ID текст` | Добавить заметку о контакте (ИИ её учтёт) |
| `/get_note USER_ID` | Посмотреть заметку |
| `/block_contact USER_ID` | Запретить автоответы этому контакту |
| `/unblock_contact USER_ID` | Разрешить снова |
| `/history_clear CHAT_ID` | Очистить историю конкретного чата |

### Режимы ИИ (настраивается в панели → 🧠 Настройки ИИ)

- **🧠 Умный** — сначала ищет в статических автоответах, потом Gemini
- **⚡ Всегда ИИ** — всегда генерирует ответ нейросетью
- **🔕 Выключен** — ИИ молчит (только статические автоответы)

---

## 🚀 Деплой на сервер

### Systemd (Linux)

```ini
# /etc/systemd/system/aibot.service
[Unit]
Description=Business AI Bot
After=network.target

[Service]
WorkingDirectory=/home/user/aiasistent
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable aibot
systemctl start aibot
systemctl status aibot
```

### GitHub Actions (из исходного .github/workflows)

Задай секреты в Settings → Secrets репозитория:
- `BOT_TOKEN`, `OWNER_ID`, `GEMINI_KEY`, `OWNER_NAME` и другие из .env

---

## 📂 Структура проекта

```
aiasistent/
├── bot.py                  # Точка входа
├── requirements.txt
├── .env.example
├── config/
│   └── config.py           # Все настройки
├── database/
│   └── database.py         # SQLite: пользователи, история, автоответы
├── handlers/
│   ├── admin.py            # Панель управления
│   ├── users.py            # Бизнес-чаты → ИИ ответы
│   └── support.py          # Тикеты
├── keyboards/
│   ├── inline.py
│   └── reply.py
├── middlewares/
│   ├── auth.py
│   └── antispam.py
└── utils/
    ├── ai.py               # Gemini: генерация с историей
    └── helpers.py          # Рассылка, форматирование
```
