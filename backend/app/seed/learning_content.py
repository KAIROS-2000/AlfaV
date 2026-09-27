
from __future__ import annotations

from typing import Callable


JUNIOR_MODULES = [
    ("junior-digital-start", "Компьютер и цифровая безопасность", "Устройство компьютера, файлы, пароли, личные данные и цифровой этикет.", "monitor", "#4A90D9",
     ["Компьютер как помощник", "Файлы и папки", "Пароли и личные данные", "Точные команды", "Цифровой этикет"]),
    ("junior-algorithms-life", "Алгоритмы в жизни", "Алгоритмы, исполнители, псевдокод, проверка и правила мини-игры.", "route", "#2ECC71",
     ["Что такое алгоритм", "Исполнитель и команды", "Псевдокод на карточках", "Проверка алгоритма", "Алгоритм для игры"]),
    ("junior-patterns", "Последовательности и шаблоны", "Закономерности, порядок команд, шаблоны историй, ритм и кодирование узоров.", "sparkles", "#F59E0B",
     ["Находим закономерность", "Команды по порядку", "Шаблоны в историях", "Ритм и повтор", "Секретный код узора"]),
    ("junior-events", "События и реакции", "События, клики, реакции персонажа, сообщения пользователю и сценарии интерактивных сцен.", "mouse-pointer-click", "#EC4899",
     ["Что такое событие", "Кнопка и действие", "Герой реагирует", "Сообщения пользователю", "Сценарий интерактивной сцены"]),
    ("junior-loops", "Циклы и повторения", "Повтор команд, цикл с количеством, цикл до условия, остановка и игровой цикл.", "repeat", "#10B981",
     ["Повторяем команды", "Цикл с количеством", "Цикл до условия", "Опасный бесконечный повтор", "Цикл в игре"]),
    ("junior-conditions", "Условия и выбор", "Если-то, иначе, несколько условий, дерево решений и правила победы в игре.", "git-branch", "#8B5CF6",
     ["Если — то", "Иначе", "Несколько условий", "Дерево решений", "Условия в правилах игры"]),
    ("junior-data", "Данные без кода", "Факты, таблицы, сортировка, диаграммы и честная работа с информацией.", "database", "#06B6D4",
     ["Что такое данные", "Сортировка", "Таблица", "Диаграмма", "Честные данные"]),
    ("junior-game-design", "Игровой дизайн", "Цель игры, правила, уровни сложности, награды и тестирование игрового опыта.", "gamepad-2", "#F97316",
     ["Цель игры", "Правила и ограничения", "Уровни сложности", "Награды и очки", "Тестируем игру"]),
    ("junior-ai-literacy", "ИИ-помощник и правила", "Первые навыки безопасной работы с ИИ: вопросы, проверка, приватность, идеи и ответственность.", "bot", "#6366F1",
     ["ИИ не волшебник", "Хороший вопрос", "Безопасность с ИИ", "ИИ для идей", "Человек принимает решение"]),
    ("junior-final-story", "Финальный проект: интерактивная история", "Финальный творческий проект: идея, сцены, выборы, тестирование и презентация.", "trophy", "#EF4444",
     ["Идея проекта", "Карта сцен", "Правила выбора", "Тестирование истории", "Презентация проекта"]),
]

MIDDLE_MODULES = [
    ("middle-python-start", "Python: уверенный старт", "Синтаксис, вывод, ввод, переменные и форматирование.", "code", "#8B5CF6",
     ["Первая программа", "Переменные и значения", "Ввод от пользователя", "Числа и сложение", "Форматированный ответ"]),
    ("middle-python-logic", "Условия и логика", "if/elif/else, сравнения, and/or и ветвление в программах.", "git-branch", "#EC4899",
     ["Проверка возраста", "Чётное или нечётное", "Три категории", "Логика and", "Логика or"]),
    ("middle-python-loops", "Циклы", "for, while, счётчики, накопление результата и повторяемые действия.", "repeat", "#10B981",
     ["Повтор через for", "Сумма чисел", "Обратный отсчёт", "while до цели", "Счётчик совпадений"]),
    ("middle-python-collections", "Списки и строки", "Списки, индексы, методы строк, фильтрация и простая обработка текста.", "list", "#06B6D4",
     ["Список задач", "Добавление элемента", "Максимум в списке", "Фильтр слов", "Подсчёт символов"]),
    ("middle-python-functions", "Функции", "def, параметры, return, декомпозиция и повторное использование кода.", "function-square", "#14B8A6",
     ["Функция приветствия", "Функция суммы", "Функция категории", "Среднее значение", "Мини-проект заметки"]),
    ("middle-data-projects", "Данные и мини-аналитика", "Опросы, словари, очистка данных, текстовые диаграммы и выводы.", "bar-chart-3", "#0EA5E9",
     ["Опрос класса", "Мини-таблица", "Чистка данных", "Простая диаграмма", "Вывод из данных"]),
    ("middle-ai-prompts", "ИИ и промптинг", "Промпты, приватность, классификация запросов, оценка ответов и human-in-the-loop.", "bot", "#6366F1",
     ["Шаблон промпта", "Проверка личных данных", "Классификатор темы", "Оценка ответа", "Человек в цикле"]),
    ("middle-web-basics", "Веб-основы через Python", "HTML как структура, текстовые шаблоны, состояние интерфейса и мини-лендинг.", "globe", "#F97316",
     ["HTML-карточка", "Список HTML", "CSS-класс как состояние", "Навигация", "Мини-лендинг"]),
    ("middle-debug-testing", "Отладка и тестирование", "Ошибки, тест-кейсы, граничные значения, debug-вывод и рефакторинг.", "bug", "#EF4444",
     ["Читаем ошибку", "Проверка примеров", "Граничный случай", "Логирование шагов", "Рефакторинг"]),
    ("middle-final-python", "Финальный Python-проект", "Проектирование консольного приложения: идея, меню, todo, критерии и питч.", "trophy", "#F59E0B",
     ["Идея приложения", "Меню приложения", "Список задач проекта", "Итоговая оценка", "Питч проекта"]),
]

SENIOR_MODULES = [
    ("senior-js-core", "JavaScript Core", "let/const, функции, условия, стрелочные функции и контракты.", "code-2", "#0EA5E9",
     ["let и const", "Функция форматирования", "Условный статус", "Стрелочная функция", "Контракт функции"]),
    ("senior-js-dom-events", "DOM-логика и события", "Модель интерфейса, обработчики, состояние, сообщения и композиция UI-логики.", "mouse-pointer-click", "#EC4899",
     ["Модель кнопки", "Состояние темы", "Счётчик кликов", "Сообщение об ошибке", "Композиция UI-логики"]),
    ("senior-js-arrays-objects", "Массивы и объекты", "map, filter, reduce, объекты профиля и статус по данным.", "database", "#10B981",
     ["map для карточек", "filter для задач", "reduce для суммы", "Объект профиля", "Группировка статуса"]),
    ("senior-js-async-api", "API и асинхронность", "Promise, async/await, ошибки, нормализация ответа и кэш.", "cloud", "#6366F1",
     ["Promise как будущий результат", "async/await", "Обработка ошибки", "Нормализация ответа API", "Кэш результата"]),
    ("senior-algorithms", "Алгоритмы и структуры", "Поиск, сортировка, стек, очередь и оценка сложности.", "network", "#F59E0B",
     ["Линейный поиск", "Сортировка чисел", "Стек действий", "Очередь задач", "Оценка сложности"]),
    ("senior-security-privacy", "Кибербезопасность и приватность", "Валидация, маскирование данных, санитизация, права и безопасные логи.", "shield", "#EF4444",
     ["Проверка пароля", "Маскирование email", "Санитизация текста", "Права доступа", "Лог события без секрета"]),
    ("senior-ai-dev", "ИИ в разработке", "AI-assisted coding: промпты, ревью, фильтр рисков, утверждение и changelog.", "bot", "#8B5CF6",
     ["Промпт как структура", "Чек-лист ревью", "Фильтр опасного запроса", "Human-in-the-loop", "AI changelog"]),
    ("senior-product-workflow", "Проектная разработка", "User story, Definition of Done, канбан, приоритет и релизные заметки.", "kanban", "#14B8A6",
     ["User story", "Definition of Done", "Канбан-статус", "Приоритет", "Релизная заметка"]),
    ("senior-architecture-quality", "Архитектура и качество", "Разделение слоёв, чистые функции, тестовые данные, документация и технический долг.", "layers", "#64748B",
     ["Слои приложения", "Чистая функция", "Тестовые данные", "Документация к функции", "Технический долг"]),
    ("senior-final-webapp", "Финальный веб-проект", "От идеи до демо: модель данных, бизнес-правило, проверка, метрики и питч.", "trophy", "#F97316",
     ["Паспорт проекта", "Модель данных", "Бизнес-правило", "Проверка перед демо", "Финальный питч"]),
]


def build_learning_modules(
    _lesson_payload: Callable,
    _question_single: Callable,
    _question_multiple: Callable,
    _question_order: Callable,
    _question_match: Callable,
    _stdio_validation: Callable,
) -> list[dict]:
    """Content-only roadmap: 3 возрастные группы × 10 модулей × 5 уроков."""

    from .lesson_specs import get_lesson_spec, validate_lesson_specs

    module_groups = (
        ("junior", JUNIOR_MODULES),
        ("middle", MIDDLE_MODULES),
        ("senior", SENIOR_MODULES),
    )
    expected_lessons = {
        f"{module_slug}-lesson-{lesson_index}": lesson_title
        for _age_group, modules in module_groups
        for module_slug, _module_title, _description, _icon, _color, lessons in modules
        for lesson_index, lesson_title in enumerate(lessons, start=1)
    }
    validate_lesson_specs(expected_lessons)

    def quiz_questions(
        prefix: str,
        title: str,
        key_points: list[str],
        example_steps: list[dict],
    ) -> list[dict]:
        step_titles = [step["title"] for step in example_steps]
        deterministic_seed = sum(
            index * ord(character)
            for index, character in enumerate(prefix, start=1)
        )
        single_correct_index = deterministic_seed % 4
        single_options = [
            "Результат можно не проверять.",
            "Достаточно запомнить название темы.",
            "Любой случайный ответ будет правильным.",
        ]
        single_options.insert(single_correct_index, key_points[0])

        multiple_distractor_index = (deterministic_seed // 4) % 4
        multiple_options = list(key_points)
        multiple_options.insert(
            multiple_distractor_index,
            "Пропустить разбор примера.",
        )
        multiple_correct = [
            index for index in range(4) if index != multiple_distractor_index
        ]

        order_shift = deterministic_seed % 2 + 1
        shuffled_step_titles = (
            step_titles[order_shift:] + step_titles[:order_shift]
        )
        return [
            _question_single(
                prefix + "a",
                f"Какое утверждение верно для темы «{title}»?",
                single_options,
                single_correct_index,
            ),
            _question_multiple(
                prefix + "b",
                f"Что важно учитывать в теме «{title}»?",
                multiple_options,
                multiple_correct,
            ),
            _question_order(
                prefix + "c",
                "Восстанови порядок разобранного примера.",
                shuffled_step_titles,
                step_titles,
            ),
        ]

    def lesson_payload(
        age_group: str,
        module_slug: str,
        lesson_index: int,
        title: str,
    ) -> dict:
        lesson_slug = f"{module_slug}-lesson-{lesson_index}"
        spec = get_lesson_spec(lesson_slug)
        practice = spec["practice"]
        is_code = practice["kind"] == "code"
        starter_code = practice.get("starter_code", "") if is_code else ""
        minimum_answer_length = {
            "junior": 80,
            "middle": 100,
            "senior": 120,
        }[age_group]
        practice_prompt = practice["prompt"]
        if not is_code:
            practice_prompt = (
                f"{practice_prompt} Ответ должен содержать не меньше "
                f"{minimum_answer_length} символов."
            )
        task_validation = (
            _stdio_validation(practice["language"], practice["tests"])
            if is_code
            else {
                "keywords": practice["keywords"],
                "require_all_keywords": True,
                "minimum_answer_length": minimum_answer_length,
            }
        )
        prefix = {
            "junior": "j",
            "middle": "m",
            "senior": "s",
        }[age_group]
        payload = _lesson_payload(
            title,
            spec["objective"],
            spec["key_points"],
            practice["title"],
            practice_prompt,
            practice.get("keywords", []),
            practice["hints"],
            quiz_questions(
                f"{prefix}{module_slug[-8:]}{lesson_index}",
                title,
                spec["key_points"],
                spec["example_steps"],
            ),
            starter_code,
            task_validation,
        )
        payload["theory_blocks"] = [
            {
                "type": "hero",
                "title": title,
                "text": spec["objective"],
            },
            {
                "type": "text",
                "title": "Объяснение темы",
                "text": spec["explanation"],
            },
            {
                "type": "list",
                "title": "Главное, что нужно запомнить",
                "items": spec["key_points"],
            },
        ]
        payload["interactive_steps"] = spec["example_steps"]
        return payload

    modules: list[dict] = []
    for age_group, module_group in module_groups:
        for slug, title, description, icon, color, lessons in module_group:
            modules.append(
                {
                    "slug": slug,
                    "title": title,
                    "description": description,
                    "age_group": age_group,
                    "icon": icon,
                    "color": color,
                    "lessons": [
                        lesson_payload(age_group, slug, lesson_index, lesson_title)
                        for lesson_index, lesson_title in enumerate(lessons, start=1)
                    ],
                }
            )

    return modules
