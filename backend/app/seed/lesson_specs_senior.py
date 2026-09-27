from __future__ import annotations


def _example(first: str, second: str, third: str) -> list[dict]:
    return [
        {"title": "Разбираем условие", "text": first},
        {"title": "Выполняем по шагам", "text": second},
        {"title": "Проверяем результат", "text": third},
    ]


def _code(
    *,
    title: str,
    objective: str,
    explanation: str,
    key_points: list[str],
    example_steps: list[dict],
    practice_title: str,
    practice_prompt: str,
    starter_code: str,
    tests: list[dict],
    hints: list[str],
) -> dict:
    return {
        "title": title,
        "objective": objective,
        "explanation": explanation,
        "key_points": key_points,
        "example_steps": example_steps,
        "practice": {
            "kind": "code",
            "title": practice_title,
            "prompt": practice_prompt,
            "language": "javascript",
            "starter_code": starter_code,
            "tests": tests,
            "hints": hints,
        },
    }


def _text(
    *,
    title: str,
    objective: str,
    explanation: str,
    key_points: list[str],
    example_steps: list[dict],
    practice_title: str,
    practice_prompt: str,
    keywords: list[str],
    hints: list[str],
) -> dict:
    return {
        "title": title,
        "objective": objective,
        "explanation": explanation,
        "key_points": key_points,
        "example_steps": example_steps,
        "practice": {
            "kind": "text",
            "title": practice_title,
            "prompt": practice_prompt,
            "keywords": keywords,
            "hints": hints,
        },
    }


SENIOR_LESSON_SPECS: dict[str, dict] = {
    "senior-js-core-lesson-1": _code(
        title="let и const",
        objective="Ученик сможет выбрать let или const для трёх переменных и безопасно изменить значение счётчика.",
        explanation=(
            "Переменная связывает имя со значением. const используют, когда самой переменной не будут присваивать "
            "другое значение, а let — когда значение должно изменяться. Объект внутри const можно изменять, но "
            "переназначить саму переменную нельзя. Такой выбор сразу показывает читателю намерение программы."
        ),
        key_points=[
            "По умолчанию выбирай const.",
            "Используй let только для запланированного переназначения.",
            "Не применяй var в новом коде из-за неочевидной области видимости.",
        ],
        example_steps=_example(
            "В корзине цена товара постоянна, а количество может меняться: const price = 120; let quantity = 2.",
            "После добавления товара выполняем quantity += 1 и считаем total = price * quantity.",
            "При price = 120 и quantity = 3 итог равен 360; price при этом не изменился.",
        ),
        practice_title="Обнови число билетов",
        practice_prompt="Считай количество билетов, увеличь его на 2 и выведи новое значение.",
        starter_code=(
            "const fs = require('fs');\n"
            "let tickets = Number(fs.readFileSync(0, 'utf8').trim());\n"
            "// TODO: увеличь tickets на 2\n"
            "console.log(tickets);\n"
        ),
        tests=[
            {"label": "Один билет", "input": "1\n", "expected": "3\n"},
            {"label": "Пять билетов", "input": "5\n", "expected": "7\n"},
        ],
        hints=[
            "Значение tickets должно измениться, поэтому оно объявлено через let.",
            "Используй оператор +=.",
            "Выводи только итоговое число.",
        ],
    ),
    "senior-js-core-lesson-2": _code(
        title="Функция форматирования",
        objective="Ученик сможет написать функцию с двумя параметрами, которая возвращает строку в заданном формате.",
        explanation=(
            "Функция получает данные через параметры, выполняет одно понятное действие и возвращает результат через "
            "return. Форматирование лучше держать внутри отдельной функции: тогда одинаковое правило не дублируется "
            "в интерфейсе. Контракт функции заранее описывает порядок параметров и вид результата."
        ),
        key_points=[
            "Параметры — входные данные функции.",
            "return передаёт результат вызывающему коду.",
            "Шаблонная строка помогает явно собрать формат.",
        ],
        example_steps=_example(
            "Нужно оформить номер заказа: formatOrder('A7', 3) должен вернуть «Заказ A7 · 3 товара».",
            "Создаём function formatOrder(id, count) и возвращаем шаблонную строку с обоими параметрами.",
            "Проверяем значения A7 и 3, затем B2 и 1: функция сохраняет один формат для разных данных.",
        ),
        practice_title="Сформируй бейдж игрока",
        practice_prompt="Считай имя и число очков с двух строк. Реализуй formatBadge(name, score), возвращающую «<имя> — <очки> очков», и выведи результат.",
        starter_code=(
            "const fs = require('fs');\n"
            "const [name, score] = fs.readFileSync(0, 'utf8').trim().split('\\n');\n"
            "function formatBadge(name, score) {\n"
            "  // TODO: верни строку нужного формата\n"
            "}\n"
            "console.log(formatBadge(name, score));\n"
        ),
        tests=[
            {"label": "Новый игрок", "input": "Мира\n15\n", "expected": "Мира — 15 очков\n"},
            {"label": "Опытный игрок", "input": "Лев\n240\n", "expected": "Лев — 240 очков\n"},
        ],
        hints=[
            "Используй оба параметра функции.",
            "Собери ответ шаблонной строкой в обратных кавычках.",
            "Не забудь return.",
        ],
    ),
    "senior-js-core-lesson-3": _code(
        title="Условный статус",
        objective="Ученик сможет реализовать три взаимоисключающих статуса с корректными граничными значениями.",
        explanation=(
            "Условие выбирает одну ветку программы по данным. Когда диапазонов несколько, проверки располагают от "
            "самой строгой к более общей и связывают через if, else if и else. Граница должна принадлежать ровно "
            "одному диапазону, иначе на ней появится ошибка."
        ),
        key_points=[
            "Проверяй диапазоны в логичном порядке.",
            "Границы задавай операторами >=, <=, > и < явно.",
            "else покрывает все оставшиеся случаи.",
        ],
        example_steps=_example(
            "Доставка: от 3000 рублей — free, от 1000 — standard, иначе small.",
            "Сначала проверяем amount >= 3000, затем amount >= 1000, после этого используем else.",
            "Для 3000 получаем free, для 1000 — standard, для 999 — small: границы не пересекаются.",
        ),
        practice_title="Определи уровень температуры",
        practice_prompt="Считай температуру. Выведи hot при значении от 30, warm при значении от 15 до 29 включительно, иначе cold.",
        starter_code=(
            "const fs = require('fs');\n"
            "const temperature = Number(fs.readFileSync(0, 'utf8').trim());\n"
            "let status;\n"
            "// TODO: выбери hot, warm или cold\n"
            "console.log(status);\n"
        ),
        tests=[
            {"label": "Граница жары", "input": "30\n", "expected": "hot\n"},
            {"label": "Тёплая погода", "input": "18\n", "expected": "warm\n"},
            {"label": "Холод", "input": "4\n", "expected": "cold\n"},
        ],
        hints=[
            "Начни с проверки самого высокого порога.",
            "Для второго диапазона достаточно temperature >= 15 после первой проверки.",
            "Последний вариант оформи через else.",
        ],
    ),
    "senior-js-core-lesson-4": _code(
        title="Стрелочная функция",
        objective="Ученик сможет записать одновыраженную стрелочную функцию и применить её к каждому элементу массива.",
        explanation=(
            "Стрелочная функция — компактная запись функции. Если тело состоит из одного выражения, фигурные скобки "
            "и return можно опустить: value => value * 2. Такая форма удобна для коротких преобразований в map, но "
            "для сложной логики лучше оставить блок и явный return."
        ),
        key_points=[
            "Один параметр можно писать без круглых скобок.",
            "Выражение после стрелки возвращается автоматически.",
            "Короткая запись должна оставаться читаемой.",
        ],
        example_steps=_example(
            "Есть цены [100, 250]; нужно получить цены со скидкой 10 процентов.",
            "Пишем const discount = price => price * 0.9 и вызываем prices.map(discount).",
            "Получаем [90, 225], а исходный массив [100, 250] остаётся прежним.",
        ),
        practice_title="Переведи минуты в секунды",
        practice_prompt="Считай минуты через пробел. Создай стрелочную функцию toSeconds и выведи преобразованные значения через пробел.",
        starter_code=(
            "const fs = require('fs');\n"
            "const minutes = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "// TODO: объяви стрелочную функцию toSeconds\n"
            "const seconds = minutes.map(value => value);\n"
            "console.log(seconds.join(' '));\n"
        ),
        tests=[
            {"label": "Несколько значений", "input": "1 2 5\n", "expected": "60 120 300\n"},
            {"label": "Ноль минут", "input": "0 10\n", "expected": "0 600\n"},
        ],
        hints=[
            "Одна минута содержит 60 секунд.",
            "Передай toSeconds в map вместо временной функции.",
            "Исходный массив изменять не нужно.",
        ],
    ),
    "senior-js-core-lesson-5": _code(
        title="Контракт функции",
        objective="Ученик сможет реализовать функцию с явным входом, предсказуемым выходом и обработкой значений вне диапазона.",
        explanation=(
            "Контракт отвечает на три вопроса: какие данные принимает функция, что возвращает и как ведёт себя на "
            "крайних случаях. Чем точнее контракт, тем проще использовать и тестировать функцию. В этой задаче "
            "результат всегда должен быть числом от 0 до 100, даже если вход выходит за диапазон."
        ),
        key_points=[
            "Тип и смысл входа должны быть однозначны.",
            "Функция должна возвращать результат во всех ветках.",
            "Граничные случаи являются частью контракта.",
        ],
        example_steps=_example(
            "Функция clampVolume получает громкость и должна вернуть число от 0 до 10.",
            "Значения меньше 0 заменяем на 0, больше 10 — на 10, остальные возвращаем без изменения.",
            "clampVolume(-2) даёт 0, clampVolume(7) — 7, clampVolume(14) — 10.",
        ),
        practice_title="Нормализуй прогресс",
        practice_prompt="Считай число и реализуй normalizeProgress: меньше 0 вернуть 0, больше 100 вернуть 100, иначе вернуть исходное число.",
        starter_code=(
            "const fs = require('fs');\n"
            "const value = Number(fs.readFileSync(0, 'utf8').trim());\n"
            "function normalizeProgress(value) {\n"
            "  // TODO: реализуй контракт диапазона 0..100\n"
            "}\n"
            "console.log(normalizeProgress(value));\n"
        ),
        tests=[
            {"label": "Ниже диапазона", "input": "-8\n", "expected": "0\n"},
            {"label": "Внутри диапазона", "input": "64\n", "expected": "64\n"},
            {"label": "Выше диапазона", "input": "140\n", "expected": "100\n"},
        ],
        hints=[
            "Сначала обработай значение меньше нуля.",
            "Затем обработай значение больше ста.",
            "В последней ветке верни value.",
        ],
    ),
    "senior-js-dom-events-lesson-1": _code(
        title="Модель кнопки",
        objective="Ученик сможет вычислить подпись и доступность кнопки из состояния интерфейса.",
        explanation=(
            "DOM-кнопка должна отражать состояние приложения, а не хранить бизнес-правила внутри обработчика клика. "
            "Удобно сначала построить модель вида {label, disabled}, а затем применить её к элементу. Тогда логику "
            "можно проверить без браузера и одинаково использовать при первом рендере и после события."
        ),
        key_points=[
            "Интерфейс является отображением состояния.",
            "disabled блокирует действие, пока оно недоступно.",
            "Чистую модель кнопки легко тестировать.",
        ],
        example_steps=_example(
            "Для кнопки сохранения состояние saving определяет модель: при true — «Сохраняем…» и disabled.",
            "Функция saveButtonModel(saving) возвращает объект, после чего UI устанавливает textContent и disabled.",
            "Проверяем оба состояния: false даёт «Сохранить|enabled», true — «Сохраняем…|disabled».",
        ),
        practice_title="Построй модель кнопки отправки",
        practice_prompt="Считай количество заполненных обязательных полей. Для 3 и более выведи «Отправить|enabled», иначе «Заполните поля|disabled».",
        starter_code=(
            "const fs = require('fs');\n"
            "const filled = Number(fs.readFileSync(0, 'utf8').trim());\n"
            "function submitButtonModel(filled) {\n"
            "  // TODO: верни объект { label, disabled }\n"
            "  return { label: '', disabled: true };\n"
            "}\n"
            "const model = submitButtonModel(filled);\n"
            "console.log(`${model.label}|${model.disabled ? 'disabled' : 'enabled'}`);\n"
        ),
        tests=[
            {"label": "Не все поля", "input": "2\n", "expected": "Заполните поля|disabled\n"},
            {"label": "Форма готова", "input": "3\n", "expected": "Отправить|enabled\n"},
        ],
        hints=[
            "Сравни filled с числом 3.",
            "В объекте должны быть и label, и disabled.",
            "Для готовой формы disabled равен false.",
        ],
    ),
    "senior-js-dom-events-lesson-2": _code(
        title="Состояние темы",
        objective="Ученик сможет реализовать предсказуемое переключение темы без прямой зависимости от DOM.",
        explanation=(
            "Тема интерфейса — часть состояния, обычно light или dark. Обработчик события должен получить текущее "
            "значение, вычислить следующее и только потом обновить DOM или хранилище. Отдельная функция nextTheme "
            "делает переход явным и не допускает накопления противоречивых CSS-классов."
        ),
        key_points=[
            "Состояние темы имеет ограниченный набор значений.",
            "Событие запускает переход, но не определяет разметку.",
            "Одна функция должна отвечать за одно переключение.",
        ],
        example_steps=_example(
            "Переключатель компактного режима меняет состояние normal на compact и обратно.",
            "Функция nextDensity(current) использует тернарный оператор и возвращает только новое значение.",
            "Два последовательных вызова для normal дают compact, затем снова normal.",
        ),
        practice_title="Переключи светлую и тёмную тему",
        practice_prompt="Считай текущую тему light или dark. Реализуй nextTheme и выведи следующее значение.",
        starter_code=(
            "const fs = require('fs');\n"
            "const current = fs.readFileSync(0, 'utf8').trim();\n"
            "function nextTheme(current) {\n"
            "  // TODO: верни противоположную тему\n"
            "}\n"
            "console.log(nextTheme(current));\n"
        ),
        tests=[
            {"label": "Из светлой в тёмную", "input": "light\n", "expected": "dark\n"},
            {"label": "Из тёмной в светлую", "input": "dark\n", "expected": "light\n"},
        ],
        hints=[
            "У функции только два допустимых результата.",
            "Сравни current со строкой light.",
            "Верни строку, не выводи её внутри функции.",
        ],
    ),
    "senior-js-dom-events-lesson-3": _code(
        title="Счётчик кликов",
        objective="Ученик сможет обновлять счётчик события и не превышать установленный интерфейсом лимит.",
        explanation=(
            "Каждый клик — событие, которое переводит состояние из текущего значения в следующее. Вместо изменения "
            "глобальной переменной полезно описать reducer: он получает count и возвращает новый count. Ограничение "
            "нужно применять в той же функции, чтобы все кнопки и тесты соблюдали одно правило."
        ),
        key_points=[
            "Новое состояние вычисляется из предыдущего.",
            "Ограничение проверяется при каждом событии.",
            "Чистый reducer не обращается к DOM.",
        ],
        example_steps=_example(
            "Кнопка лайка увеличивает число от 0 до максимума 10.",
            "Функция addLike(count) возвращает Math.min(count + 1, 10).",
            "Для 8 получаем 9, для 10 остаётся 10 — состояние не выходит за лимит.",
        ),
        practice_title="Обработай серию кликов",
        practice_prompt="Считай начальный счётчик и число кликов. Увеличивай счётчик за каждый клик, но не выше 5, затем выведи итог.",
        starter_code=(
            "const fs = require('fs');\n"
            "const [start, clicks] = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "function applyClicks(count, clicks) {\n"
            "  // TODO: вычисли итог с лимитом 5\n"
            "  return count;\n"
            "}\n"
            "console.log(applyClicks(start, clicks));\n"
        ),
        tests=[
            {"label": "Лимит не достигнут", "input": "1 3\n", "expected": "4\n"},
            {"label": "Лишние клики", "input": "4 8\n", "expected": "5\n"},
        ],
        hints=[
            "Без лимита итог равен count + clicks.",
            "Math.min выбирает меньшее из двух значений.",
            "Сравни вычисленный итог с 5.",
        ],
    ),
    "senior-js-dom-events-lesson-4": _code(
        title="Сообщение об ошибке",
        objective="Ученик сможет преобразовать технический код ошибки в понятное пользователю сообщение с запасным вариантом.",
        explanation=(
            "Пользователю не нужно показывать stack trace или внутренний код сервера. UI сопоставляет известный код "
            "с коротким сообщением и использует нейтральный fallback для неизвестной ошибки. Такое отображение держат "
            "отдельно от запроса, чтобы формулировки можно было менять без изменения сетевой логики."
        ),
        key_points=[
            "Техническая ошибка и пользовательское сообщение — разные данные.",
            "Каждый известный код получает конкретную подсказку.",
            "Неизвестный код должен иметь безопасный fallback.",
        ],
        example_steps=_example(
            "Коды EMPTY_NAME и NAME_TAKEN превращаем в «Введите имя» и «Это имя уже занято».",
            "Создаём объект messages и возвращаем messages[code] ?? 'Не удалось сохранить'.",
            "Проверяем известный NAME_TAKEN и неизвестный TIMEOUT: интерфейс всегда получает понятный текст.",
        ),
        practice_title="Покажи ошибку входа",
        practice_prompt="Считай код EMPTY_EMAIL, WRONG_PASSWORD или другой. Выведи соответственно «Введите email», «Неверный пароль» или «Не удалось войти».",
        starter_code=(
            "const fs = require('fs');\n"
            "const code = fs.readFileSync(0, 'utf8').trim();\n"
            "function loginErrorMessage(code) {\n"
            "  // TODO: сопоставь код с безопасным сообщением\n"
            "}\n"
            "console.log(loginErrorMessage(code));\n"
        ),
        tests=[
            {"label": "Пустой email", "input": "EMPTY_EMAIL\n", "expected": "Введите email\n"},
            {"label": "Неверный пароль", "input": "WRONG_PASSWORD\n", "expected": "Неверный пароль\n"},
            {"label": "Неизвестная ошибка", "input": "SERVER_DOWN\n", "expected": "Не удалось войти\n"},
        ],
        hints=[
            "Удобно создать объект code → message.",
            "Получи значение по ключу code.",
            "Для отсутствующего ключа используй оператор ??.",
        ],
    ),
    "senior-js-dom-events-lesson-5": _code(
        title="Композиция UI-логики",
        objective="Ученик сможет собрать проверку, преобразование и отображение данных в последовательный UI-конвейер.",
        explanation=(
            "Сложный обработчик проще понять, если разделить его на маленькие функции: нормализация ввода, проверка и "
            "построение модели отображения. Композиция передаёт результат одного шага следующему. Тогда каждый шаг "
            "можно проверить отдельно, а обработчик события только связывает их."
        ),
        key_points=[
            "Каждый этап решает одну задачу.",
            "Результат этапа становится входом следующего.",
            "Ошибка проверки останавливает дальнейшее действие.",
        ],
        example_steps=_example(
            "Форма поиска сначала trim-ит запрос, затем проверяет минимум 2 символа и строит заголовок результатов.",
            "Функции normalizeQuery, isValidQuery и makeSearchTitle вызываются по порядку.",
            "Ввод «  js  » даёт «Результаты: js», а « x » останавливается на проверке длины.",
        ),
        practice_title="Собери модель имени профиля",
        practice_prompt="Считай строку. Удали пробелы по краям; если осталось меньше 3 символов, выведи «Ошибка», иначе выведи «Профиль: <ИМЯ>» в верхнем регистре.",
        starter_code=(
            "const fs = require('fs');\n"
            "const raw = fs.readFileSync(0, 'utf8');\n"
            "const normalize = value => value.trim();\n"
            "const isValid = value => value.length >= 3;\n"
            "// TODO: скомпонуй шаги и сформируй result\n"
            "let result = '';\n"
            "console.log(result);\n"
        ),
        tests=[
            {"label": "Корректное имя", "input": "  mira  \n", "expected": "Профиль: MIRA\n"},
            {"label": "Слишком коротко", "input": " ab \n", "expected": "Ошибка\n"},
        ],
        hints=[
            "Сначала вызови normalize(raw).",
            "Перед toUpperCase проверь isValid.",
            "В каждой ветке присвой result готовую строку.",
        ],
    ),
    "senior-js-arrays-objects-lesson-1": _code(
        title="map для карточек",
        objective="Ученик сможет преобразовать массив объектов в массив строк для карточек, не изменяя исходные данные.",
        explanation=(
            "map проходит по каждому элементу и создаёт новый массив той же длины. Он подходит, когда каждому исходному "
            "объекту соответствует один новый результат: например, товару — подпись карточки. Callback получает "
            "элемент и должен вернуть преобразованное значение."
        ),
        key_points=[
            "map всегда возвращает новый массив.",
            "Число элементов после map не меняется.",
            "Callback обязан вернуть значение для каждой карточки.",
        ],
        example_steps=_example(
            "Из [{title: 'Книга', price: 500}] нужно получить ['Книга — 500 ₽'].",
            "Вызываем products.map(product => `${product.title} — ${product.price} ₽`).",
            "Длина сохраняется, объекты products не меняются, а результат готов для textContent.",
        ),
        practice_title="Подготовь карточки курсов",
        practice_prompt="Считай JSON-массив объектов с name и lessons. Через map создай строки «<name>: <lessons> уроков» и выведи их через |.",
        starter_code=(
            "const fs = require('fs');\n"
            "const courses = JSON.parse(fs.readFileSync(0, 'utf8'));\n"
            "// TODO: преобразуй каждый курс в подпись карточки\n"
            "const cards = courses;\n"
            "console.log(cards.join('|'));\n"
        ),
        tests=[
            {"label": "Два курса", "input": "[{\"name\":\"JS\",\"lessons\":8},{\"name\":\"CSS\",\"lessons\":5}]\n", "expected": "JS: 8 уроков|CSS: 5 уроков\n"},
            {"label": "Один курс", "input": "[{\"name\":\"Git\",\"lessons\":3}]\n", "expected": "Git: 3 уроков\n"},
        ],
        hints=[
            "Вызови courses.map(...).",
            "Callback получает один объект course.",
            "Верни из callback шаблонную строку.",
        ],
    ),
    "senior-js-arrays-objects-lesson-2": _code(
        title="filter для задач",
        objective="Ученик сможет отобрать объекты по булевому условию и сохранить порядок подходящих элементов.",
        explanation=(
            "filter создаёт новый массив только из элементов, для которых callback вернул true. Он не изменяет "
            "исходный массив и сохраняет относительный порядок. Условие фильтра должно прямо выражать критерий, "
            "например задача не завершена и имеет нужный приоритет."
        ),
        key_points=[
            "true оставляет элемент, false исключает.",
            "Исходный массив остаётся неизменным.",
            "Несколько требований объединяются логическими операторами.",
        ],
        example_steps=_example(
            "Из списка писем выбираем непрочитанные: messages.filter(message => !message.read).",
            "Для важности добавляем второе условие: !message.read && message.priority === 'high'.",
            "Проверяем, что прочитанные и low-письма исключены, а порядок оставшихся не изменился.",
        ),
        practice_title="Отбери активные задачи",
        practice_prompt="Считай JSON-массив задач с title и done. Оставь задачи, где done равно false, и выведи их title через запятую.",
        starter_code=(
            "const fs = require('fs');\n"
            "const tasks = JSON.parse(fs.readFileSync(0, 'utf8'));\n"
            "// TODO: оставь только незавершённые задачи\n"
            "const activeTitles = [];\n"
            "console.log(activeTitles.join(','));\n"
        ),
        tests=[
            {"label": "Смешанный список", "input": "[{\"title\":\"Макет\",\"done\":false},{\"title\":\"API\",\"done\":true},{\"title\":\"Тесты\",\"done\":false}]\n", "expected": "Макет,Тесты\n"},
            {"label": "Нет активных", "input": "[{\"title\":\"Релиз\",\"done\":true}]\n", "expected": "\n"},
        ],
        hints=[
            "Сначала примени filter к tasks.",
            "Проверяй task.done === false.",
            "После фильтра используй map, чтобы получить title.",
        ],
    ),
    "senior-js-arrays-objects-lesson-3": _code(
        title="reduce для суммы",
        objective="Ученик сможет накопить итоговую стоимость массива позиций с помощью reduce и правильного начального значения.",
        explanation=(
            "reduce сворачивает массив в одно значение. Аккумулятор хранит промежуточный итог, а callback добавляет "
            "к нему вклад текущего элемента. Начальное значение 0 делает поведение понятным и позволяет корректно "
            "обработать пустой массив."
        ),
        key_points=[
            "Аккумулятор переносит результат между шагами.",
            "Начальное значение задаётся вторым аргументом reduce.",
            "Для позиции вклад равен цене, умноженной на количество.",
        ],
        example_steps=_example(
            "Баллы [4, 7, 2] нужно сложить в общий результат.",
            "Вызываем scores.reduce((total, score) => total + score, 0).",
            "Аккумулятор последовательно равен 0, 4, 11 и 13; итог — 13.",
        ),
        practice_title="Посчитай стоимость корзины",
        practice_prompt="Считай JSON-массив позиций с price и quantity. Через reduce вычисли сумму price * quantity и выведи её.",
        starter_code=(
            "const fs = require('fs');\n"
            "const items = JSON.parse(fs.readFileSync(0, 'utf8'));\n"
            "// TODO: накопи общую стоимость\n"
            "const total = 0;\n"
            "console.log(total);\n"
        ),
        tests=[
            {"label": "Две позиции", "input": "[{\"price\":120,\"quantity\":2},{\"price\":50,\"quantity\":3}]\n", "expected": "390\n"},
            {"label": "Пустая корзина", "input": "[]\n", "expected": "0\n"},
        ],
        hints=[
            "Начальное значение аккумулятора — 0.",
            "Вклад item равен item.price * item.quantity.",
            "Присвой результат вызова reduce переменной total.",
        ],
    ),
    "senior-js-arrays-objects-lesson-4": _code(
        title="Объект профиля",
        objective="Ученик сможет собрать новый объект профиля из входных данных и вычисляемого поля, не мутируя источник.",
        explanation=(
            "Объект объединяет связанные свойства под одним именем. При подготовке профиля полезно создать новый "
            "объект через spread и добавить вычисляемые поля, а не менять ответ API. Это сохраняет исходные данные "
            "и отделяет серверную модель от модели интерфейса."
        ),
        key_points=[
            "Свойства читаются по имени через точку.",
            "Spread копирует перечисляемые свойства в новый объект.",
            "Вычисляемое поле можно добавить после spread.",
        ],
        example_steps=_example(
            "API вернул {firstName: 'Ира', lastName: 'Ли'}; интерфейсу нужен fullName.",
            "Создаём const view = {...user, fullName: `${user.firstName} ${user.lastName}`}.",
            "У view есть три поля, а объект user по-прежнему содержит только исходные два.",
        ),
        practice_title="Подготовь публичный профиль",
        practice_prompt="Считай JSON-объект с name и score. Создай новый профиль с этими полями и level: advanced при score >= 100, иначе starter. Выведи JSON.",
        starter_code=(
            "const fs = require('fs');\n"
            "const source = JSON.parse(fs.readFileSync(0, 'utf8'));\n"
            "// TODO: создай новый объект profile, не изменяя source\n"
            "const profile = {};\n"
            "console.log(JSON.stringify(profile));\n"
        ),
        tests=[
            {"label": "Начальный уровень", "input": "{\"name\":\"Аня\",\"score\":40}\n", "expected": "{\"name\":\"Аня\",\"score\":40,\"level\":\"starter\"}\n"},
            {"label": "Продвинутый уровень", "input": "{\"name\":\"Рома\",\"score\":100}\n", "expected": "{\"name\":\"Рома\",\"score\":100,\"level\":\"advanced\"}\n"},
        ],
        hints=[
            "Скопируй source через ...source.",
            "Сравни source.score со 100.",
            "Добавь level после spread, чтобы поле было частью нового объекта.",
        ],
    ),
    "senior-js-arrays-objects-lesson-5": _code(
        title="Группировка статуса",
        objective="Ученик сможет сгруппировать элементы по статусу и посчитать количество в каждой группе.",
        explanation=(
            "Группировка превращает плоский массив в сводку по ключу. Аккумулятор reduce может быть объектом, где "
            "каждому статусу соответствует счётчик. Перед увеличением отсутствующий счётчик заменяют нулём, поэтому "
            "алгоритм работает с любым набором статусов."
        ),
        key_points=[
            "Значение свойства может служить ключом группы.",
            "Для новой группы начальный счётчик равен нулю.",
            "reduce подходит для построения объекта-сводки.",
        ],
        example_steps=_example(
            "Заказы имеют status new или sent; нужно получить {new: 2, sent: 1}.",
            "В reduce выполняем totals[order.status] = (totals[order.status] ?? 0) + 1.",
            "После каждого заказа растёт только его группа; сумма счётчиков равна числу заказов.",
        ),
        practice_title="Посчитай статусы задач",
        practice_prompt="Считай JSON-массив задач со status todo, doing или done. Выведи количества строго в формате «todo=<n>;doing=<n>;done=<n>».",
        starter_code=(
            "const fs = require('fs');\n"
            "const tasks = JSON.parse(fs.readFileSync(0, 'utf8'));\n"
            "const counts = { todo: 0, doing: 0, done: 0 };\n"
            "// TODO: увеличь нужный счётчик для каждой задачи\n"
            "console.log(`todo=${counts.todo};doing=${counts.doing};done=${counts.done}`);\n"
        ),
        tests=[
            {"label": "Все группы", "input": "[{\"status\":\"todo\"},{\"status\":\"done\"},{\"status\":\"doing\"},{\"status\":\"done\"}]\n", "expected": "todo=1;doing=1;done=2\n"},
            {"label": "Одна группа", "input": "[{\"status\":\"todo\"},{\"status\":\"todo\"}]\n", "expected": "todo=2;doing=0;done=0\n"},
        ],
        hints=[
            "Перебери tasks через forEach или reduce.",
            "Статус доступен как task.status.",
            "Нужный счётчик можно выбрать через counts[task.status].",
        ],
    ),
    "senior-js-async-api-lesson-1": _code(
        title="Promise как будущий результат",
        objective="Ученик сможет создать Promise-цепочку и преобразовать полученное асинхронное значение.",
        explanation=(
            "Promise представляет результат, который появится позже: pending переходит в fulfilled или rejected. "
            "Метод then получает успешное значение и возвращает новый Promise, поэтому преобразования можно соединять "
            "в цепочку. Вывод нужно выполнять после разрешения Promise, а не сразу после его создания."
        ),
        key_points=[
            "Promise хранит будущий результат, а не само готовое значение.",
            "then выполняется после успешного завершения.",
            "Каждый then может передать преобразованное значение дальше.",
        ],
        example_steps=_example(
            "Promise.resolve(5) имитирует будущий ответ со значением 5.",
            "Первый then умножает число на 2, второй превращает его в строку «Итог: 10».",
            "console.log внутри последнего then срабатывает после вычислений и выводит готовый результат.",
        ),
        practice_title="Преобразуй будущую цену",
        practice_prompt="Считай цену. Создай Promise.resolve(price), в then добавь 20 процентов и выведи целое значение через Math.round.",
        starter_code=(
            "const fs = require('fs');\n"
            "const price = Number(fs.readFileSync(0, 'utf8').trim());\n"
            "Promise.resolve(price)\n"
            "  // TODO: добавь преобразование цены\n"
            "  .then(result => console.log(result));\n"
        ),
        tests=[
            {"label": "Цена 100", "input": "100\n", "expected": "120\n"},
            {"label": "Цена с округлением", "input": "83\n", "expected": "100\n"},
        ],
        hints=[
            "Добавь .then(value => Math.round(value * 1.2)).",
            "Не вызывай console.log до завершения цепочки.",
            "Последний then уже получает преобразованный result.",
        ],
    ),
    "senior-js-async-api-lesson-2": _code(
        title="async/await",
        objective="Ученик сможет дождаться результата асинхронной функции и использовать его внутри async-функции.",
        explanation=(
            "Ключевое слово async делает функцию возвращающей Promise. await приостанавливает только эту функцию до "
            "готовности Promise и позволяет читать асинхронный код сверху вниз. await можно использовать лишь внутри "
            "async-контекста, а полученное значение затем обрабатывается как обычные данные."
        ),
        key_points=[
            "async-функция всегда возвращает Promise.",
            "await извлекает успешное значение Promise.",
            "Зависимые шаги выполняются после await.",
        ],
        example_steps=_example(
            "Функция loadCity возвращает Promise.resolve({name: 'Казань'}).",
            "В async showCity вызываем const city = await loadCity(), затем строим строку с city.name.",
            "showCity выводит «Город: Казань» только после получения объекта.",
        ),
        practice_title="Загрузи название заказа",
        practice_prompt="Считай id заказа. Дождись fakeFetchOrder(id), которая возвращает объект с title «Заказ #<id>», и выведи title.",
        starter_code=(
            "const fs = require('fs');\n"
            "const id = fs.readFileSync(0, 'utf8').trim();\n"
            "const fakeFetchOrder = id => Promise.resolve({ title: `Заказ #${id}` });\n"
            "async function main() {\n"
            "  // TODO: дождись заказа и выведи его title\n"
            "}\n"
            "main();\n"
        ),
        tests=[
            {"label": "Первый заказ", "input": "17\n", "expected": "Заказ #17\n"},
            {"label": "Другой id", "input": "204\n", "expected": "Заказ #204\n"},
        ],
        hints=[
            "Вызови await fakeFetchOrder(id).",
            "Сохрани полученный объект в переменную.",
            "Выведи свойство title после await.",
        ],
    ),
    "senior-js-async-api-lesson-3": _code(
        title="Обработка ошибки",
        objective="Ученик сможет перехватить отклонённый Promise и вернуть понятный запасной результат.",
        explanation=(
            "Сетевой запрос может завершиться ошибкой, поэтому await помещают в try/catch. В try находится успешный "
            "сценарий, а catch получает исключение и формирует контролируемый ответ. Пользователь не должен видеть "
            "необработанный Promise rejection или внутренние детали."
        ),
        key_points=[
            "try описывает ожидаемый успешный путь.",
            "catch обрабатывает исключение из await.",
            "Ошибка должна превращаться в предсказуемое состояние интерфейса.",
        ],
        example_steps=_example(
            "loadWeather отклоняет Promise, если город пустой.",
            "В try ждём данные и возвращаем температуру, в catch возвращаем «Погода недоступна».",
            "Для «Омск» видим температуру, для пустого города — контролируемый fallback без падения.",
        ),
        practice_title="Обработай отсутствующего пользователя",
        practice_prompt="Считай id. fakeLoadUser отклоняет Promise для id 0. Выведи «Пользователь <id>» при успехе или «Пользователь не найден» при ошибке.",
        starter_code=(
            "const fs = require('fs');\n"
            "const id = Number(fs.readFileSync(0, 'utf8').trim());\n"
            "const fakeLoadUser = id => id === 0\n"
            "  ? Promise.reject(new Error('not found'))\n"
            "  : Promise.resolve({ name: `Пользователь ${id}` });\n"
            "async function main() {\n"
            "  // TODO: добавь try/catch вокруг await\n"
            "}\n"
            "main();\n"
        ),
        tests=[
            {"label": "Успешная загрузка", "input": "7\n", "expected": "Пользователь 7\n"},
            {"label": "Ошибка загрузки", "input": "0\n", "expected": "Пользователь не найден\n"},
        ],
        hints=[
            "В try дождись fakeLoadUser(id).",
            "При успехе выведи user.name.",
            "В catch выведи только безопасное сообщение.",
        ],
    ),
    "senior-js-async-api-lesson-4": _code(
        title="Нормализация ответа API",
        objective="Ученик сможет преобразовать неполный ответ API в стабильную модель с типами и значениями по умолчанию.",
        explanation=(
            "API может прислать лишние поля, строки вместо чисел или null. Нормализатор выбирает только нужные данные, "
            "приводит типы и задаёт defaults. После этого остальной интерфейс работает с одним стабильным контрактом "
            "и не повторяет проверки на каждой странице."
        ),
        key_points=[
            "Нормализация происходит на границе приложения.",
            "Number и Boolean явно приводят типы.",
            "Оператор ?? задаёт значение только для null и undefined.",
        ],
        example_steps=_example(
            "Ответ {user_name: 'Лена', points: '42'} нужно превратить в {name: 'Лена', score: 42}.",
            "Функция normalizeUser берёт user_name, вызывает Number(points) и не копирует служебные поля.",
            "Компонент получает предсказуемые name и score независимо от формы серверного ответа.",
        ),
        practice_title="Нормализуй карточку товара",
        practice_prompt="Считай JSON с title, price и необязательным available. Выведи JSON {name, price, available}, где name берётся из title, price — число, а available по умолчанию false.",
        starter_code=(
            "const fs = require('fs');\n"
            "const raw = JSON.parse(fs.readFileSync(0, 'utf8'));\n"
            "function normalizeProduct(raw) {\n"
            "  // TODO: верни стабильную модель товара\n"
            "  return {};\n"
            "}\n"
            "console.log(JSON.stringify(normalizeProduct(raw)));\n"
        ),
        tests=[
            {"label": "Все поля", "input": "{\"title\":\"Курс\",\"price\":\"900\",\"available\":true}\n", "expected": "{\"name\":\"Курс\",\"price\":900,\"available\":true}\n"},
            {"label": "Нет доступности", "input": "{\"title\":\"Практикум\",\"price\":\"450\"}\n", "expected": "{\"name\":\"Практикум\",\"price\":450,\"available\":false}\n"},
        ],
        hints=[
            "Создай новый объект с тремя полями.",
            "Для price вызови Number(raw.price).",
            "Для available используй raw.available ?? false.",
        ],
    ),
    "senior-js-async-api-lesson-5": _code(
        title="Кэш результата",
        objective="Ученик сможет кэшировать асинхронный результат по ключу и не выполнять повторную загрузку.",
        explanation=(
            "Кэш хранит уже полученный результат по ключу. Перед запросом функция проверяет Map: если id найден, "
            "возвращается сохранённое значение; иначе выполняется загрузка и результат записывается. Это уменьшает "
            "число одинаковых запросов, но ключ должен однозначно описывать данные."
        ),
        key_points=[
            "Проверка кэша выполняется до загрузки.",
            "Результат сохраняется под тем же ключом.",
            "Повторный ключ не увеличивает число запросов.",
        ],
        example_steps=_example(
            "loadCity('kzn') первый раз вызывает API и сохраняет город в Map.",
            "Второй вызов с 'kzn' находит cache.has('kzn') и сразу возвращает сохранённый объект.",
            "Два вызова дают одинаковые данные, но счётчик сетевых запросов равен одному.",
        ),
        practice_title="Кэшируй загрузку профиля",
        practice_prompt="Считай id через пробел. Для каждого вызови getProfile с Map-кэшем. Выведи имена через запятую и затем «requests=<n>», где n — число уникальных загрузок.",
        starter_code=(
            "const fs = require('fs');\n"
            "const ids = fs.readFileSync(0, 'utf8').trim().split(/\\s+/);\n"
            "const cache = new Map();\n"
            "let requests = 0;\n"
            "async function getProfile(id) {\n"
            "  // TODO: верни кэш или выполни имитацию загрузки\n"
            "  requests += 1;\n"
            "  return { name: `user-${id}` };\n"
            "}\n"
            "async function main() {\n"
            "  const profiles = [];\n"
            "  for (const id of ids) profiles.push(await getProfile(id));\n"
            "  console.log(profiles.map(profile => profile.name).join(','));\n"
            "  console.log(`requests=${requests}`);\n"
            "}\n"
            "main();\n"
        ),
        tests=[
            {"label": "Повторный id", "input": "1 2 1\n", "expected": "user-1,user-2,user-1\nrequests=2\n"},
            {"label": "Один профиль", "input": "8 8\n", "expected": "user-8,user-8\nrequests=1\n"},
        ],
        hints=[
            "Начни с if (cache.has(id)).",
            "После загрузки выполни cache.set(id, profile).",
            "Увеличивай requests только при отсутствии ключа.",
        ],
    ),
    "senior-algorithms-lesson-1": _code(
        title="Линейный поиск",
        objective="Ученик сможет найти индекс первого совпадения линейным проходом и вернуть -1 при отсутствии.",
        explanation=(
            "Линейный поиск проверяет элементы слева направо, пока не встретит цель. Он работает с любым массивом и "
            "не требует сортировки. В худшем случае приходится проверить каждый элемент, поэтому сложность равна "
            "O(n), а при первом совпадении цикл можно завершить сразу."
        ),
        key_points=[
            "Проверка начинается с индекса 0.",
            "Первое совпадение сразу завершает поиск.",
            "-1 явно означает, что элемента нет.",
        ],
        example_steps=_example(
            "В массиве ['red', 'blue', 'green'] ищем 'blue'.",
            "Сравниваем red — не подходит; затем blue — совпадение на индексе 1.",
            "Возвращаем 1 и не проверяем green; для yellow после полного прохода вернули бы -1.",
        ),
        practice_title="Найди первое число",
        practice_prompt="Первая строка содержит числа через пробел, вторая — цель. Реализуй linearSearch и выведи индекс первого совпадения или -1.",
        starter_code=(
            "const fs = require('fs');\n"
            "const [numbersLine, targetLine] = fs.readFileSync(0, 'utf8').trim().split('\\n');\n"
            "const numbers = numbersLine.split(/\\s+/).map(Number);\n"
            "const target = Number(targetLine);\n"
            "function linearSearch(items, target) {\n"
            "  // TODO: выполни линейный проход\n"
            "  return -1;\n"
            "}\n"
            "console.log(linearSearch(numbers, target));\n"
        ),
        tests=[
            {"label": "Есть повторы", "input": "4 9 2 9\n9\n", "expected": "1\n"},
            {"label": "Нет цели", "input": "3 6 8\n5\n", "expected": "-1\n"},
        ],
        hints=[
            "Используй цикл for с индексом.",
            "Сравнивай items[index] с target.",
            "При совпадении сразу return index.",
        ],
    ),
    "senior-algorithms-lesson-2": _code(
        title="Сортировка чисел",
        objective="Ученик сможет правильно отсортировать числа в JavaScript с числовым компаратором.",
        explanation=(
            "Метод sort без компаратора сравнивает элементы как строки: поэтому 10 может оказаться перед 2. Для "
            "возрастания чисел передают (a, b) => a - b. sort изменяет исходный массив, поэтому при необходимости "
            "сохранить данные сначала создают копию через spread."
        ),
        key_points=[
            "Числам нужен компаратор a - b.",
            "sort мутирует массив, на котором вызван.",
            "Spread позволяет сортировать копию.",
        ],
        example_steps=_example(
            "Рейтинги [20, 3, 11] нельзя надёжно сортировать вызовом ratings.sort().",
            "Создаём const ordered = [...ratings].sort((a, b) => b - a) для убывания.",
            "Получаем [20, 11, 3], а ratings остаётся [20, 3, 11].",
        ),
        practice_title="Отсортируй баллы по возрастанию",
        practice_prompt="Считай числа через пробел. Создай отсортированную копию по возрастанию и выведи её через пробел.",
        starter_code=(
            "const fs = require('fs');\n"
            "const scores = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "// TODO: скопируй и отсортируй scores как числа\n"
            "const ordered = scores;\n"
            "console.log(ordered.join(' '));\n"
        ),
        tests=[
            {"label": "Разный разряд", "input": "10 2 30 1\n", "expected": "1 2 10 30\n"},
            {"label": "Отрицательные", "input": "5 -2 0 -10\n", "expected": "-10 -2 0 5\n"},
        ],
        hints=[
            "Начни с [...scores].",
            "Передай sort функцию (a, b) => a - b.",
            "Не используй sort без аргумента.",
        ],
    ),
    "senior-algorithms-lesson-3": _code(
        title="Стек действий",
        objective="Ученик сможет моделировать undo с помощью стека и принципа LIFO.",
        explanation=(
            "Стек работает по правилу last in, first out: последним добавили — первым извлекли. push кладёт действие "
            "на вершину, pop снимает последнее. Такой порядок используют для отмены команд, истории переходов и "
            "разбора вложенных конструкций."
        ),
        key_points=[
            "push добавляет элемент на вершину.",
            "pop возвращает и удаляет последний элемент.",
            "Пустой стек нужно обрабатывать отдельно.",
        ],
        example_steps=_example(
            "Пользователь выполнил draw, move, color — кладём команды в стек в этом порядке.",
            "Первая отмена через pop возвращает color, вторая — move.",
            "В стеке остаётся draw: отмена идёт в обратном порядке выполнения.",
        ),
        practice_title="Отмени последние команды",
        practice_prompt="Первая строка содержит команды через пробел, вторая — число отмен. Удали указанное число последних команд и выведи оставшиеся через пробел.",
        starter_code=(
            "const fs = require('fs');\n"
            "const [commandsLine, undoLine] = fs.readFileSync(0, 'utf8').trim().split('\\n');\n"
            "const stack = commandsLine.split(/\\s+/);\n"
            "const undoCount = Number(undoLine);\n"
            "// TODO: выполни undoCount операций pop\n"
            "console.log(stack.join(' '));\n"
        ),
        tests=[
            {"label": "Две отмены", "input": "open edit save publish\n2\n", "expected": "open edit\n"},
            {"label": "Одна отмена", "input": "add move\n1\n", "expected": "add\n"},
        ],
        hints=[
            "Повтори действие undoCount раз.",
            "На каждом шаге вызывай stack.pop().",
            "Не удаляй элементы с начала массива.",
        ],
    ),
    "senior-algorithms-lesson-4": _code(
        title="Очередь задач",
        objective="Ученик сможет обработать задачи в порядке FIFO и ограничить число обработанных элементов.",
        explanation=(
            "Очередь работает по правилу first in, first out: первая поступившая задача выполняется первой. В массиве "
            "новые элементы добавляют push, а извлекают с начала через shift. Очереди применяют для фоновых задач, "
            "печати и последовательной обработки событий."
        ),
        key_points=[
            "Первый добавленный элемент обслуживается первым.",
            "shift извлекает начало очереди.",
            "Оставшиеся задачи сохраняют исходный порядок.",
        ],
        example_steps=_example(
            "В печать поступили report, photo, ticket именно в таком порядке.",
            "Первый вызов shift отдаёт report, второй — photo.",
            "После двух обработок в очереди остаётся ticket, а порядок не менялся.",
        ),
        practice_title="Обработай очередь запросов",
        practice_prompt="Первая строка содержит id запросов через пробел, вторая — лимит обработки. Выведи обработанные id через запятую, затем оставшиеся через запятую.",
        starter_code=(
            "const fs = require('fs');\n"
            "const [idsLine, limitLine] = fs.readFileSync(0, 'utf8').trim().split('\\n');\n"
            "const queue = idsLine.split(/\\s+/);\n"
            "const limit = Number(limitLine);\n"
            "const processed = [];\n"
            "// TODO: перенеси не более limit элементов из queue в processed\n"
            "console.log(processed.join(','));\n"
            "console.log(queue.join(','));\n"
        ),
        tests=[
            {"label": "Часть очереди", "input": "a b c d\n2\n", "expected": "a,b\nc,d\n"},
            {"label": "Вся очередь", "input": "x y\n5\n", "expected": "x,y\n\n"},
        ],
        hints=[
            "Цикл должен учитывать и limit, и queue.length.",
            "Извлекай элемент через queue.shift().",
            "Добавляй извлечённое значение в processed.",
        ],
    ),
    "senior-algorithms-lesson-5": _code(
        title="Оценка сложности",
        objective="Ученик сможет измерить число проверок линейного алгоритма и связать его с размером входа.",
        explanation=(
            "Сложность описывает, как растёт объём работы при увеличении данных. Один проход по n элементам — O(n), "
            "даже если конкретный поиск иногда завершается раньше. Счётчик операций помогает увидеть разницу между "
            "лучшим и худшим случаем, не заменяя асимптотическую оценку."
        ),
        key_points=[
            "O(n) означает линейный рост работы.",
            "Ранний выход улучшает конкретный случай.",
            "Считают значимые операции, а не миллисекунды одного запуска.",
        ],
        example_steps=_example(
            "Ищем 7 в [7, 4, 1]: совпадение находится на первой проверке.",
            "Для отсутствующего 9 проверяем все три элемента.",
            "Оба случая относятся к линейному поиску O(n), но счётчик равен соответственно 1 и 3.",
        ),
        practice_title="Посчитай проверки поиска",
        practice_prompt="Первая строка содержит числа, вторая — цель. Иди слева направо до первого совпадения или конца и выведи количество выполненных сравнений.",
        starter_code=(
            "const fs = require('fs');\n"
            "const [line, targetLine] = fs.readFileSync(0, 'utf8').trim().split('\\n');\n"
            "const values = line.split(/\\s+/).map(Number);\n"
            "const target = Number(targetLine);\n"
            "let checks = 0;\n"
            "// TODO: выполни поиск и увеличивай checks при каждом сравнении\n"
            "console.log(checks);\n"
        ),
        tests=[
            {"label": "Цель в середине", "input": "4 8 2 6\n2\n", "expected": "3\n"},
            {"label": "Цели нет", "input": "1 3 5\n9\n", "expected": "3\n"},
        ],
        hints=[
            "В цикле сначала увеличь checks.",
            "После сравнения с target можно использовать break.",
            "Если цели нет, цикл проверит весь массив.",
        ],
    ),
    "senior-security-privacy-lesson-1": _code(
        title="Проверка пароля",
        objective="Ученик сможет проверить пароль по длине, наличию буквы и цифры без хранения самого пароля.",
        explanation=(
            "Клиентская проверка помогает сразу показать требования, но не заменяет серверную. Валидация пароля "
            "проверяет свойства строки, а не сравнивает её с заранее заданным секретом. Пароль нельзя выводить в лог "
            "или включать в сообщение об ошибке."
        ),
        key_points=[
            "Каждое требование проверяется отдельно.",
            "Регулярные выражения находят нужные классы символов.",
            "Та же политика обязательно повторяется на сервере.",
        ],
        example_steps=_example(
            "Для PIN-кода проверяем ровно 4 символа и только цифры, не сохраняя введённое значение.",
            "Условия объединяем: pin.length === 4 && /^\\d+$/.test(pin).",
            "1234 проходит, 12a4 и 12345 не проходят; сообщение говорит о правиле, а не показывает PIN.",
        ),
        practice_title="Проверь надёжность пароля",
        practice_prompt="Считай пароль. Выведи strong, если длина не меньше 8 и есть хотя бы одна латинская буква и одна цифра; иначе weak.",
        starter_code=(
            "const fs = require('fs');\n"
            "const password = fs.readFileSync(0, 'utf8').trim();\n"
            "function passwordStatus(password) {\n"
            "  // TODO: проверь три требования\n"
            "  return 'weak';\n"
            "}\n"
            "console.log(passwordStatus(password));\n"
        ),
        tests=[
            {"label": "Надёжный пароль", "input": "alpha2026\n", "expected": "strong\n"},
            {"label": "Нет цифры", "input": "onlyletters\n", "expected": "weak\n"},
            {"label": "Слишком короткий", "input": "a7bc\n", "expected": "weak\n"},
        ],
        hints=[
            "Проверь password.length >= 8.",
            "Букву можно найти выражением /[a-z]/i.",
            "Цифру можно найти выражением /\\d/.",
        ],
    ),
    "senior-security-privacy-lesson-2": _code(
        title="Маскирование email",
        objective="Ученик сможет скрыть локальную часть email и сохранить домен для безопасного отображения.",
        explanation=(
            "Маскирование уменьшает объём персональных данных на экране и в сообщениях. Для email обычно оставляют "
            "первый символ локальной части, заменяют остальные звёздочками и сохраняют домен. Это не шифрование: "
            "исходный адрес всё равно нужно защищать и не записывать в лишние логи."
        ),
        key_points=[
            "Локальная часть находится до символа @.",
            "Количество звёздочек не должно раскрывать лишние символы.",
            "Маскирование не заменяет контроль доступа.",
        ],
        example_steps=_example(
            "Телефон +79991234567 отображаем как +7******4567.",
            "Сохраняем код страны и последние четыре цифры, середину заменяем фиксированными звёздочками.",
            "Пользователь узнаёт номер, но большая часть идентификатора не раскрывается.",
        ),
        practice_title="Скрой адрес почты",
        practice_prompt="Считай корректный email. Оставь первый символ имени, добавь три звёздочки и исходный домен: alex@example.com → a***@example.com.",
        starter_code=(
            "const fs = require('fs');\n"
            "const email = fs.readFileSync(0, 'utf8').trim();\n"
            "function maskEmail(email) {\n"
            "  // TODO: раздели адрес и собери маску\n"
            "}\n"
            "console.log(maskEmail(email));\n"
        ),
        tests=[
            {"label": "Обычный адрес", "input": "alex@example.com\n", "expected": "a***@example.com\n"},
            {"label": "Короткое имя", "input": "x@school.ru\n", "expected": "x***@school.ru\n"},
        ],
        hints=[
            "Раздели email через split('@').",
            "Возьми local[0].",
            "Домен добавь после строки ***@.",
        ],
    ),
    "senior-security-privacy-lesson-3": _code(
        title="Санитизация текста",
        objective="Ученик сможет безопасно экранировать HTML-символы перед вставкой пользовательского текста в разметку.",
        explanation=(
            "Если вставить пользовательскую строку через innerHTML, браузер может воспринять теги как разметку. "
            "Экранирование заменяет &, <, >, двойные и одинарные кавычки HTML-сущностями. Ещё безопаснее использовать "
            "textContent, но функция escapeHtml нужна там, где строка действительно собирается как HTML."
        ),
        key_points=[
            "Недоверенный ввод нельзя напрямую передавать в innerHTML.",
            "Символ & экранируют первым.",
            "Санитизация зависит от контекста вывода.",
        ],
        example_steps=_example(
            "Комментарий «<b>привет</b>» должен отобразиться как текст, а не жирный HTML.",
            "При присваивании element.textContent браузер сам показывает угловые скобки безопасно.",
            "В DOM появляется буквальная строка <b>привет</b>, тег не исполняется.",
        ),
        practice_title="Экранируй HTML",
        practice_prompt="Считай строку и реализуй escapeHtml, заменив &, <, >, \" и ' на &amp;, &lt;, &gt;, &quot; и &#39;.",
        starter_code=(
            "const fs = require('fs');\n"
            "const text = fs.readFileSync(0, 'utf8').trim();\n"
            "function escapeHtml(text) {\n"
            "  // TODO: экранируй пять специальных символов\n"
            "  return text;\n"
            "}\n"
            "console.log(escapeHtml(text));\n"
        ),
        tests=[
            {"label": "Тег", "input": "<script>alert(1)</script>\n", "expected": "&lt;script&gt;alert(1)&lt;/script&gt;\n"},
            {"label": "Кавычки и амперсанд", "input": "Tom & \"Bob's\"\n", "expected": "Tom &amp; &quot;Bob&#39;s&quot;\n"},
        ],
        hints=[
            "Начни с замены /&/g, иначе испортишь созданные сущности.",
            "Используй последовательные replace с флагом g.",
            "Одинарную кавычку замени на &#39;.",
        ],
    ),
    "senior-security-privacy-lesson-4": _code(
        title="Права доступа",
        objective="Ученик сможет реализовать allowlist-проверку действия по роли и запретить неизвестные роли.",
        explanation=(
            "Авторизация отвечает не на вопрос «кто вошёл», а «может ли этот пользователь выполнить действие над "
            "ресурсом». Безопаснее перечислить разрешённые действия для каждой роли и по умолчанию запрещать всё "
            "остальное. Проверка должна выполняться на сервере, даже если кнопка скрыта в интерфейсе."
        ),
        key_points=[
            "Аутентификация и авторизация решают разные задачи.",
            "Allowlist безопаснее списка запретов.",
            "Неизвестная роль получает отказ по умолчанию.",
        ],
        example_steps=_example(
            "В редакторе viewer может read, editor — read и update.",
            "Создаём permissions и проверяем permissions[role]?.includes(action) ?? false.",
            "viewer/update и guest/read возвращают false, editor/update — true.",
        ),
        practice_title="Проверь действие в курсе",
        practice_prompt="Считай роль и действие через пробел. student может view, teacher — view и edit, admin — view, edit и delete. Выведи allow или deny.",
        starter_code=(
            "const fs = require('fs');\n"
            "const [role, action] = fs.readFileSync(0, 'utf8').trim().split(/\\s+/);\n"
            "function can(role, action) {\n"
            "  // TODO: создай allowlist и проверь действие\n"
            "  return false;\n"
            "}\n"
            "console.log(can(role, action) ? 'allow' : 'deny');\n"
        ),
        tests=[
            {"label": "Учитель редактирует", "input": "teacher edit\n", "expected": "allow\n"},
            {"label": "Ученик удаляет", "input": "student delete\n", "expected": "deny\n"},
            {"label": "Неизвестная роль", "input": "guest view\n", "expected": "deny\n"},
        ],
        hints=[
            "Задай объект role → массив разрешённых действий.",
            "Для известной роли используй includes(action).",
            "При отсутствии роли возвращай false.",
        ],
    ),
    "senior-security-privacy-lesson-5": _code(
        title="Лог события без секрета",
        objective="Ученик сможет построить безопасную запись события, исключив пароль и токен из входных данных.",
        explanation=(
            "Лог должен помогать расследовать событие, но не становиться копией секретных данных. Вместо записи всего "
            "объекта выбирают allowlist безопасных полей: тип события, id пользователя и результат. Пароли, токены, "
            "cookie и полное тело запроса исключаются независимо от уровня логирования."
        ),
        key_points=[
            "Логируй только поля, нужные для диагностики.",
            "Секрет нельзя маскировать частично — его лучше не записывать.",
            "Структурированный лог проще проверять и фильтровать.",
        ],
        example_steps=_example(
            "Запрос оплаты содержит orderId, cardNumber и status.",
            "Для аудита создаём {event: 'payment', orderId, status}, не копируя cardNumber.",
            "JSON лога позволяет найти заказ и исход, но не раскрывает платёжные данные.",
        ),
        practice_title="Сформируй безопасный лог входа",
        practice_prompt="Считай JSON с userId, password, token и success. Выведи JSON только с event: «login», userId и success в этом порядке.",
        starter_code=(
            "const fs = require('fs');\n"
            "const request = JSON.parse(fs.readFileSync(0, 'utf8'));\n"
            "function safeLoginLog(request) {\n"
            "  // TODO: выбери только безопасные поля\n"
            "  return {};\n"
            "}\n"
            "console.log(JSON.stringify(safeLoginLog(request)));\n"
        ),
        tests=[
            {"label": "Успешный вход", "input": "{\"userId\":12,\"password\":\"qwerty\",\"token\":\"abc\",\"success\":true}\n", "expected": "{\"event\":\"login\",\"userId\":12,\"success\":true}\n"},
            {"label": "Ошибка входа", "input": "{\"userId\":5,\"password\":\"secret\",\"token\":null,\"success\":false}\n", "expected": "{\"event\":\"login\",\"userId\":5,\"success\":false}\n"},
        ],
        hints=[
            "Не используй spread request.",
            "Создай новый объект только из трёх разрешённых полей.",
            "Порядок свойств важен для ожидаемого JSON.",
        ],
    ),
    "senior-ai-dev-lesson-1": _text(
        title="Промпт как структура",
        objective="Ученик сможет составить промпт для разработки, содержащий цель, контекст, ограничения и формат результата.",
        explanation=(
            "Хороший промпт похож на техническое задание: он объясняет ожидаемый результат, даёт нужный контекст, "
            "фиксирует ограничения и определяет форму ответа. Просьба «сделай форму» оставляет слишком много догадок. "
            "Структура не гарантирует правильность ответа ИИ, но делает результат проверяемым."
        ),
        key_points=[
            "Цель описывает конкретный результат.",
            "Контекст содержит только сведения, влияющие на решение.",
            "Ограничения и формат превращаются в критерии проверки.",
        ],
        example_steps=_example(
            "Команде нужен SQL-запрос для отчёта о заказах за неделю.",
            "В промпте указываем PostgreSQL, таблицы, часовой пояс, запрет изменения данных и формат ответа «SQL + пояснение».",
            "Проверяем, что ответ содержит только SELECT, учитывает даты и может быть протестирован на копии базы.",
        ),
        practice_title="Составь промпт для компонента",
        practice_prompt=(
            "Напиши промпт для ИИ, который должен создать React-компонент списка уведомлений. Явно используй слова: "
            "цель, контекст, ограничения, формат. Укажи TypeScript, состояния загрузки/ошибки и запрет внешних библиотек."
        ),
        keywords=["цель", "контекст", "ограничения", "формат"],
        hints=[
            "Начни с результата, который должен получить разработчик.",
            "Перечисли входные данные и обязательные состояния.",
            "Заверши точным форматом ответа ИИ.",
        ],
    ),
    "senior-ai-dev-lesson-2": _text(
        title="Чек-лист ревью",
        objective="Ученик сможет проверить AI-сгенерированный патч минимум по четырём категориям до принятия.",
        explanation=(
            "Ответ ИИ — неподтверждённое предложение, а не готовое изменение. Ревью проверяет соответствие задаче, "
            "корректность, безопасность, тесты и понятность кода. Чек-лист снижает риск принять правдоподобный, но "
            "ошибочный патч и оставляет человеку ответственность за результат."
        ),
        key_points=[
            "Сначала сравни патч с исходной задачей.",
            "Безопасность и крайние случаи проверяются отдельно.",
            "Тесты должны подтверждать новое поведение, а не только запускаться.",
        ],
        example_steps=_example(
            "ИИ предложил endpoint удаления заметки по id.",
            "Ревьюер проверяет авторизацию владельца, ответ для отсутствующего id, транзакцию и тест запрета чужого удаления.",
            "Патч принимают только после исправления пропущенной проверки владельца и прохождения негативного теста.",
        ),
        practice_title="Проведи ревью AI-патча",
        practice_prompt=(
            "Опиши проверку AI-патча, который добавляет загрузку аватара. Обязательно используй слова: задача, "
            "безопасность, тесты, решение. Назови конкретные проверки типа файла, размера и прав пользователя."
        ),
        keywords=["задача", "безопасность", "тесты", "решение"],
        hints=[
            "Сначала сформулируй, что патч обязан делать.",
            "Добавь негативные сценарии для файла и доступа.",
            "Заверши решением: принять, доработать или отклонить.",
        ],
    ),
    "senior-ai-dev-lesson-3": _code(
        title="Фильтр опасного запроса",
        objective="Ученик сможет классифицировать запрос по нескольким риск-маркерам без выполнения содержащихся в нём инструкций.",
        explanation=(
            "Перед передачей запроса автоматизации полезно выделить очевидные маркеры риска: просьбы показать токен, "
            "удалить данные или отключить защиту. Простой фильтр не заменяет модель угроз и ручное ревью, но может "
            "направить запрос в безопасный процесс подтверждения."
        ),
        key_points=[
            "Классификация не должна выполнять текст запроса.",
            "Сравнение выполняют после нормализации регистра.",
            "Совпадение риск-маркера означает review, а не автоматический запуск.",
        ],
        example_steps=_example(
            "Система проверяет запросы на слова «export secret» и «disable audit».",
            "Текст приводится к нижнему регистру, затем маркеры ищутся через some и includes.",
            "«Disable audit for test» получает review, а «Explain audit log» — safe.",
        ),
        practice_title="Классифицируй запрос автоматизации",
        practice_prompt="Считай текст. Выведи review, если он содержит delete database, show token или bypass auth без учёта регистра; иначе safe.",
        starter_code=(
            "const fs = require('fs');\n"
            "const request = fs.readFileSync(0, 'utf8').trim();\n"
            "function riskStatus(request) {\n"
            "  const markers = ['delete database', 'show token', 'bypass auth'];\n"
            "  // TODO: проверь нормализованный текст по всем markers\n"
            "  return 'safe';\n"
            "}\n"
            "console.log(riskStatus(request));\n"
        ),
        tests=[
            {"label": "Опасная команда", "input": "Please DELETE DATABASE now\n", "expected": "review\n"},
            {"label": "Запрос токена", "input": "show token for debug\n", "expected": "review\n"},
            {"label": "Безопасный вопрос", "input": "explain database indexes\n", "expected": "safe\n"},
        ],
        hints=[
            "Создай lower через request.toLowerCase().",
            "Метод some проверит наличие хотя бы одного маркера.",
            "Для каждого marker используй lower.includes(marker).",
        ],
    ),
    "senior-ai-dev-lesson-4": _text(
        title="Human-in-the-loop",
        objective="Ученик сможет спроектировать процесс, где рискованное AI-действие требует явного человеческого решения.",
        explanation=(
            "Human-in-the-loop означает, что ИИ готовит предложение, но критическое действие выполняется только после "
            "проверки человеком. Точка подтверждения особенно нужна перед удалением, публикацией, платежом и изменением "
            "прав. Проверяющему показывают понятный diff, риск и возможность отклонить действие."
        ),
        key_points=[
            "ИИ предлагает, а уполномоченный человек решает.",
            "Подтверждение ставят перед необратимым действием.",
            "Решение и автор проверяющего фиксируются в аудите.",
        ],
        example_steps=_example(
            "ИИ подготовил ответы на 40 обращений поддержки.",
            "Низкорисковые черновики остаются в очереди, оператор читает каждый и нажимает «Отправить» или «Отклонить».",
            "Система отправляет только подтверждённые ответы и записывает автора решения.",
        ),
        practice_title="Спроектируй подтверждение публикации",
        practice_prompt=(
            "Опиши процесс публикации AI-сгенерированного урока. Обязательно используй слова: черновик, проверка, "
            "подтверждение, аудит. Укажи, кто принимает решение и что происходит при отклонении."
        ),
        keywords=["черновик", "проверка", "подтверждение", "аудит"],
        hints=[
            "Раздели генерацию и публикацию на разные этапы.",
            "Назови роль человека, имеющего право подтверждения.",
            "Сохрани отклонённый результат как исправляемый черновик.",
        ],
    ),
    "senior-ai-dev-lesson-5": _text(
        title="AI changelog",
        objective="Ученик сможет записать происхождение AI-изменения, выполненную проверку и итоговое человеческое решение.",
        explanation=(
            "AI changelog объясняет, где ИИ участвовал в работе и как результат был проверен. В записи указывают цель, "
            "область изменения, использованный результат, тесты и одобрившего человека, но не секретные промпты или "
            "персональные данные. Это облегчает аудит и последующее исправление."
        ),
        key_points=[
            "Запись связывает изменение с проверяемой целью.",
            "Нужно перечислить фактически выполненные проверки.",
            "Ответственность фиксируется за человеком, принявшим изменение.",
        ],
        example_steps=_example(
            "ИИ предложил рефакторинг функции расчёта скидки.",
            "В changelog записывают файлы, причину, добавленные граничные тесты и ручное сравнение результатов.",
            "После ревью указывают имя ответственного и статус accepted; исходный токен или приватный контекст не сохраняют.",
        ),
        practice_title="Запиши изменение документации",
        practice_prompt=(
            "Составь AI changelog для обновления инструкции по восстановлению пароля. Обязательно используй слова: "
            "цель, изменения, проверка, ответственный. Укажи, что ссылки и шаги проверены вручную."
        ),
        keywords=["цель", "изменения", "проверка", "ответственный"],
        hints=[
            "Одной строкой опиши, зачем понадобилось изменение.",
            "Перечисли изменённые разделы и способ проверки.",
            "Заверши именем роли, принявшей результат.",
        ],
    ),
    "senior-product-workflow-lesson-1": _text(
        title="User story",
        objective="Ученик сможет сформулировать user story с ролью, потребностью, ценностью и двумя критериями приёмки.",
        explanation=(
            "User story описывает проблему с точки зрения пользователя: «Как <роль>, я хочу <действие>, чтобы "
            "<ценность>». Она не диктует интерфейс заранее, а объясняет желаемый результат. Проверяемость добавляют "
            "конкретные критерии приёмки с наблюдаемым поведением."
        ),
        key_points=[
            "Роль должна быть реальным типом пользователя.",
            "Потребность описывает результат, а не кнопку.",
            "Критерии приёмки можно однозначно проверить.",
        ],
        example_steps=_example(
            "Библиотекарь хочет быстро видеть просроченные книги, чтобы связываться с читателями.",
            "История: «Как библиотекарь, я хочу фильтровать выдачи по просрочке, чтобы вовремя напоминать о возврате».",
            "Критерии: фильтр показывает только просроченные записи; сброс возвращает полный список.",
        ),
        practice_title="Опиши историю ученика",
        practice_prompt=(
            "Напиши user story для ученика, который хочет продолжать урок с последнего шага. Обязательно используй "
            "слова: роль, потребность, ценность, критерии. Добавь два измеримых критерия приёмки."
        ),
        keywords=["роль", "потребность", "ценность", "критерии"],
        hints=[
            "Назови пользователя и его ситуацию.",
            "Объясни пользу сохранения прогресса.",
            "Критерии должны описывать поведение после выхода и возврата.",
        ],
    ),
    "senior-product-workflow-lesson-2": _text(
        title="Definition of Done",
        objective="Ученик сможет составить общий Definition of Done из пяти проверяемых требований для задачи команды.",
        explanation=(
            "Definition of Done — единый минимум качества для всех задач команды. Он отличается от критериев конкретной "
            "user story: включает ревью, тесты, документацию, безопасность и готовность к развёртыванию. Формулировки "
            "должны проверяться ответом да или нет."
        ),
        key_points=[
            "DoD одинаков для задач одного рабочего процесса.",
            "Каждый пункт подтверждается артефактом или проверкой.",
            "«Код написан» недостаточно для завершения.",
        ],
        example_steps=_example(
            "Команда выпускает backend endpoint для заметок.",
            "DoD требует code review, позитивные и негативные тесты, обновлённый API-контракт и отсутствие ошибок линтера.",
            "Задача переходит в done только когда подтверждены все пункты, даже если endpoint уже работает локально.",
        ),
        practice_title="Определи готовность формы",
        practice_prompt=(
            "Составь Definition of Done для формы регистрации. Обязательно используй слова: ревью, тесты, "
            "доступность, документация, безопасность. Каждый пункт сформулируй как проверяемое условие."
        ),
        keywords=["ревью", "тесты", "доступность", "документация", "безопасность"],
        hints=[
            "Учти успешный и ошибочный сценарии.",
            "Добавь проверку клавиатурой и сообщений об ошибках.",
            "Не используй расплывчатые слова вроде «качественно».",
        ],
    ),
    "senior-product-workflow-lesson-3": _text(
        title="Канбан-статус",
        objective="Ученик сможет выбрать корректный канбан-статус по фактическому состоянию работы и назвать условие перехода.",
        explanation=(
            "Канбан-доска показывает поток работы, а не список желаний. Статус отражает наблюдаемое состояние: задача "
            "ожидает, выполняется, проверяется или завершена. Ограничение work in progress помогает не начинать новые "
            "задачи, пока текущие застряли."
        ),
        key_points=[
            "Статус меняется только после реального события.",
            "Review — отдельная работа, а не формальность.",
            "WIP-лимит выявляет узкие места потока.",
        ],
        example_steps=_example(
            "Разработчик завершил код, но тестировщик ещё не проверил задачу.",
            "Карточка переходит из In progress в Review, а не сразу в Done.",
            "После успешной проверки и выполнения DoD карточка становится Done; при ошибке возвращается в In progress.",
        ),
        practice_title="Разложи задачу по потоку",
        practice_prompt=(
            "Опиши статусы задачи добавления поиска: требования согласованы, код пишется, затем найден баг на ревью. "
            "Обязательно используй слова: очередь, работа, ревью, возврат. Для каждого перехода назови событие."
        ),
        keywords=["очередь", "работа", "ревью", "возврат"],
        hints=[
            "Начни со статуса до начала разработки.",
            "Не переносить карточку в Done при найденном баге.",
            "Свяжи каждый статус с конкретным фактом.",
        ],
    ),
    "senior-product-workflow-lesson-4": _text(
        title="Приоритет",
        objective="Ученик сможет назначить приоритет трём задачам по влиянию, срочности и стоимости задержки.",
        explanation=(
            "Приоритет показывает, что команда делает раньше при ограниченном времени. Решение опирается на влияние "
            "на пользователя, срочность, риск и стоимость задержки, а не на громкость просьбы. Критическая ошибка "
            "доступа обычно выше косметического улучшения, даже если последнее быстрее реализовать."
        ),
        key_points=[
            "Влияние оценивается по пользователям и бизнес-результату.",
            "Срочность учитывает последствия задержки.",
            "Обоснование приоритета важнее самого ярлыка.",
        ],
        example_steps=_example(
            "Есть падение оплаты, новый цвет кнопки и ускорение отчёта, которым пользуются раз в месяц.",
            "Падение оплаты получает P0 из-за потери транзакций; отчёт — P2; цвет — P3.",
            "Порядок подтверждается метриками: число затронутых пользователей и стоимость каждого часа простоя.",
        ),
        practice_title="Расставь приоритеты платформы",
        practice_prompt=(
            "Расставь P0–P2 для трёх задач: ученики видят чужие ответы, у заголовка опечатка, отчёт учителя грузится "
            "20 секунд. Обязательно используй слова: влияние, срочность, риск, порядок и кратко обоснуй решение."
        ),
        keywords=["влияние", "срочность", "риск", "порядок"],
        hints=[
            "Сначала оцени утечку чужих данных.",
            "Затем сравни рабочую задержку с косметической ошибкой.",
            "Для каждой задачи назови последствие ожидания.",
        ],
    ),
    "senior-product-workflow-lesson-5": _text(
        title="Релизная заметка",
        objective="Ученик сможет написать релизную заметку, которая объясняет изменение, пользу и действие пользователя.",
        explanation=(
            "Релизная заметка отвечает пользователю: что изменилось, зачем это полезно и нужно ли что-то сделать. Она "
            "не копирует названия коммитов и не перегружает внутренними деталями. Ограничения или изменение поведения "
            "указывают прямо, чтобы обновление не стало неожиданностью."
        ),
        key_points=[
            "Начинай с пользовательского результата.",
            "Избегай внутренних имён файлов и задач.",
            "Явно указывай необходимые действия и ограничения.",
        ],
        example_steps=_example(
            "В календаре появился экспорт событий в файл.",
            "Заметка сообщает: «Теперь расписание можно скачать в формате ICS и открыть в календаре».",
            "Добавляем действие «Откройте меню расписания → Экспорт» и ограничение: экспортирует выбранный месяц.",
        ),
        practice_title="Напиши заметку об автосохранении",
        practice_prompt=(
            "Напиши релизную заметку о появлении автосохранения черновика урока каждые 10 секунд. Обязательно используй "
            "слова: изменение, польза, действие, ограничение. Укажи, что офлайн-сохранение пока недоступно."
        ),
        keywords=["изменение", "польза", "действие", "ограничение"],
        hints=[
            "Первое предложение посвяти новому поведению.",
            "Объясни, как пользователь увидит статус сохранения.",
            "Честно назови офлайн-ограничение.",
        ],
    ),
    "senior-architecture-quality-lesson-1": _text(
        title="Слои приложения",
        objective="Ученик сможет распределить пять обязанностей между UI, бизнес-логикой и слоем данных.",
        explanation=(
            "Слои разделяют причины изменения. UI отображает состояние и принимает ввод, бизнес-слой применяет "
            "правила, слой данных общается с API или базой. Если компонент одновременно рисует форму, рассчитывает "
            "скидку и выполняет SQL, его трудно тестировать и безопасно изменять."
        ),
        key_points=[
            "UI не должен знать детали хранения данных.",
            "Бизнес-правила не зависят от конкретного интерфейса.",
            "Зависимости направляют от внешнего слоя к стабильным правилам.",
        ],
        example_steps=_example(
            "Экран заказа показывает позиции, рассчитывает доставку и загружает заказ.",
            "Компонент оставляет рендер; calculateDelivery переносим в domain; fetchOrder — в data service.",
            "Расчёт тестируется без браузера, а API можно заменить mock-реализацией.",
        ),
        practice_title="Раздели регистрацию по слоям",
        practice_prompt=(
            "Распредели обязанности регистрации: поля формы, проверка возраста, POST /users, показ ошибки и сохранение "
            "пользователя. Обязательно используй слова: интерфейс, логика, данные, граница."
        ),
        keywords=["интерфейс", "логика", "данные", "граница"],
        hints=[
            "Отображение и ввод оставь в интерфейсе.",
            "Правило возраста помести в бизнес-логику.",
            "HTTP-запрос относится к слою данных.",
        ],
    ),
    "senior-architecture-quality-lesson-2": _code(
        title="Чистая функция",
        objective="Ученик сможет переписать расчёт как чистую функцию без изменения аргумента и внешнего состояния.",
        explanation=(
            "Чистая функция при одинаковых аргументах возвращает одинаковый результат и не меняет данные снаружи. "
            "Она не читает глобальные переменные, не мутирует входной объект и не выполняет скрытый вывод. Такой код "
            "проще тестировать, переиспользовать и безопасно запускать в любом порядке."
        ),
        key_points=[
            "Результат зависит только от аргументов.",
            "Входные объекты и массивы не мутируются.",
            "Побочные эффекты выполняются за пределами вычисления.",
        ],
        example_steps=_example(
            "Функция addTax(price, rate) должна только вернуть price * (1 + rate).",
            "Убираем чтение globalTax и console.log из функции, передаём rate явно.",
            "Два вызова addTax(100, 0.2) дают 120 и не изменяют никакое внешнее состояние.",
        ),
        practice_title="Обнови пользователя без мутации",
        practice_prompt="Считай JSON-пользователя и новое число score с отдельной строки. Реализуй withScore, возвращающую новый объект с обновлённым score, и выведи JSON.",
        starter_code=(
            "const fs = require('fs');\n"
            "const [userLine, scoreLine] = fs.readFileSync(0, 'utf8').trim().split('\\n');\n"
            "const user = JSON.parse(userLine);\n"
            "const score = Number(scoreLine);\n"
            "function withScore(user, score) {\n"
            "  // TODO: верни новый объект и не меняй user\n"
            "  return user;\n"
            "}\n"
            "console.log(JSON.stringify(withScore(user, score)));\n"
        ),
        tests=[
            {"label": "Обновление баллов", "input": "{\"name\":\"Ира\",\"score\":10}\n35\n", "expected": "{\"name\":\"Ира\",\"score\":35}\n"},
            {"label": "Сохранение других полей", "input": "{\"name\":\"Макс\",\"score\":4,\"active\":true}\n9\n", "expected": "{\"name\":\"Макс\",\"score\":9,\"active\":true}\n"},
        ],
        hints=[
            "Используй объектный spread.",
            "Поле score добавь после ...user.",
            "Не присваивай user.score новое значение.",
        ],
    ),
    "senior-architecture-quality-lesson-3": _code(
        title="Тестовые данные",
        objective="Ученик сможет создать фабрику тестовых объектов с безопасными значениями по умолчанию и переопределениями.",
        explanation=(
            "Тестовые данные должны подчёркивать проверяемое условие, а не повторять большой production-объект. Фабрика "
            "задаёт валидные defaults и принимает overrides только для важного сценария. Это уменьшает шум теста и "
            "защищает его от несвязанных изменений модели."
        ),
        key_points=[
            "Defaults создают минимальный валидный объект.",
            "Overrides меняют только важные для теста поля.",
            "Каждый вызов фабрики возвращает новый объект.",
        ],
        example_steps=_example(
            "Для теста заказа фабрика makeOrder возвращает {id: 1, total: 100, status: 'new'}.",
            "Сценарий отмены вызывает makeOrder({status: 'cancelled'}), не дублируя остальные поля.",
            "Два вызова дают независимые объекты, поэтому изменение одного не влияет на другой.",
        ),
        practice_title="Создай фабрику пользователя",
        practice_prompt="Считай JSON overrides. Реализуй makeUser с defaults name: «Тест», role: «student», active: true и применением overrides. Выведи JSON.",
        starter_code=(
            "const fs = require('fs');\n"
            "const overrides = JSON.parse(fs.readFileSync(0, 'utf8'));\n"
            "function makeUser(overrides = {}) {\n"
            "  // TODO: объедини defaults и overrides\n"
            "  return {};\n"
            "}\n"
            "console.log(JSON.stringify(makeUser(overrides)));\n"
        ),
        tests=[
            {"label": "Без изменений", "input": "{}\n", "expected": "{\"name\":\"Тест\",\"role\":\"student\",\"active\":true}\n"},
            {"label": "Учитель", "input": "{\"name\":\"Анна\",\"role\":\"teacher\"}\n", "expected": "{\"name\":\"Анна\",\"role\":\"teacher\",\"active\":true}\n"},
        ],
        hints=[
            "Сначала перечисли поля defaults.",
            "Размести ...overrides после defaults.",
            "Не изменяй объект overrides.",
        ],
    ),
    "senior-architecture-quality-lesson-4": _text(
        title="Документация к функции",
        objective="Ученик сможет документировать назначение функции, параметры, результат и ошибочный случай без пересказа кода.",
        explanation=(
            "Полезная документация объясняет контракт и важные причины, а не переводит каждую строку кода на русский. "
            "Она указывает назначение, параметры, возвращаемое значение, возможные ошибки и короткий пример. Если "
            "поведение меняется, документация обновляется вместе с кодом."
        ),
        key_points=[
            "Описание начинается с результата для вызывающего кода.",
            "Параметры и return получают тип и смысл.",
            "Неочевидные ошибки и ограничения указываются явно.",
        ],
        example_steps=_example(
            "Функция parseDate(value) принимает ISO-строку и возвращает Date.",
            "JSDoc описывает формат value, возвращаемый тип и RangeError для некорректной даты.",
            "Пример parseDate('2026-07-30') подтверждает ожидаемый ввод, не повторяя реализацию.",
        ),
        practice_title="Документируй расчёт скидки",
        practice_prompt=(
            "Напиши JSDoc-описание для calculateDiscount(total, level), возвращающей сумму скидки и выбрасывающей "
            "ошибку при total < 0. Обязательно используй слова: назначение, параметры, результат, ошибка."
        ),
        keywords=["назначение", "параметры", "результат", "ошибка"],
        hints=[
            "Объясни бизнес-смысл функции одной фразой.",
            "Для каждого параметра укажи тип и допустимые значения.",
            "Добавь @returns и @throws.",
        ],
    ),
    "senior-architecture-quality-lesson-5": _text(
        title="Технический долг",
        objective="Ученик сможет оформить элемент технического долга с последствием, риском и ограниченным планом исправления.",
        explanation=(
            "Технический долг — осознанный компромисс, который увеличивает стоимость будущих изменений. Запись «плохой "
            "код» бесполезна: нужно назвать конкретную проблему, её влияние, риск ожидания и границы исправления. "
            "Приоритет долга сравнивают с продуктовой работой по реальным последствиям."
        ),
        key_points=[
            "Долг описывается через наблюдаемое последствие.",
            "Риск ожидания помогает определить приоритет.",
            "План исправления должен иметь ограниченный объём.",
        ],
        example_steps=_example(
            "Три страницы копируют одну проверку тарифного плана.",
            "Последствие: изменение правила требует трёх правок и уже вызвало расхождение; риск — неверный доступ.",
            "План: вынести canUseFeature в domain-модуль, добавить таблицу тестов и заменить три вызова.",
        ),
        practice_title="Оформи долг в модуле уведомлений",
        practice_prompt=(
            "Опиши технический долг: email и push по-разному определяют язык пользователя. Обязательно используй слова: "
            "проблема, последствие, риск, план. Предложи ограниченное исправление и проверку."
        ),
        keywords=["проблема", "последствие", "риск", "план"],
        hints=[
            "Назови конкретное расхождение поведения.",
            "Свяжи риск с получателем уведомления.",
            "План должен включать единое правило и тесты.",
        ],
    ),
    "senior-final-webapp-lesson-1": _text(
        title="Паспорт проекта",
        objective="Ученик сможет составить одностраничный паспорт проекта с пользователем, проблемой, границами и метрикой успеха.",
        explanation=(
            "Паспорт проекта удерживает команду в рамках решаемой проблемы. Он фиксирует целевого пользователя, его "
            "сценарий, ценность, минимальный объём первой версии и измеримый результат. Функции, не поддерживающие "
            "главный сценарий, явно остаются за границей MVP."
        ),
        key_points=[
            "Проект начинается с проблемы пользователя.",
            "MVP содержит минимальный законченный сценарий.",
            "Метрика показывает, решена ли проблема.",
        ],
        example_steps=_example(
            "Проект помогает тренеру собирать подтверждения участия в матче.",
            "MVP: тренер создаёт событие, игрок отвечает да/нет, тренер видит итог; чат и статистика вне первой версии.",
            "Метрика успеха: 80 процентов ответов получены за 24 часа без ручных сообщений.",
        ),
        practice_title="Создай паспорт сервиса заметок",
        practice_prompt=(
            "Составь паспорт веб-сервиса учебных заметок. Обязательно используй слова: пользователь, проблема, границы, "
            "метрика. Укажи один главный сценарий и функции, которые не войдут в MVP."
        ),
        keywords=["пользователь", "проблема", "границы", "метрика"],
        hints=[
            "Выбери одну конкретную группу пользователей.",
            "Опиши путь от создания заметки до её повторного открытия.",
            "Метрику сформулируй числом или долей.",
        ],
    ),
    "senior-final-webapp-lesson-2": _text(
        title="Модель данных",
        objective="Ученик сможет выделить три сущности проекта, их ключевые поля, идентификаторы и связи.",
        explanation=(
            "Модель данных описывает факты, которые приложение обязано хранить. Сущности получают стабильные id, поля "
            "с понятными типами и явные связи. Не следует копировать одно и то же имя во многие таблицы, если достаточно "
            "ссылки; при этом модель должна поддерживать главный пользовательский сценарий."
        ),
        key_points=[
            "Сущность представляет самостоятельный объект предметной области.",
            "Идентификатор отличает одну запись от другой.",
            "Связь показывает принадлежность или взаимодействие сущностей.",
        ],
        example_steps=_example(
            "Для бронирования переговорных выделяем User, Room и Booking.",
            "Booking хранит id, userId, roomId, startAt и endAt; связи указывают автора и комнату.",
            "Проверяем сценарий: по roomId можно найти занятость, по userId — бронирования пользователя.",
        ),
        practice_title="Спроектируй данные трекера задач",
        practice_prompt=(
            "Опиши сущности User, Project и Task для командного трекера. Обязательно используй слова: сущность, "
            "идентификатор, поле, связь. Укажи типы ключевых полей и кардинальность связей."
        ),
        keywords=["сущность", "идентификатор", "поле", "связь"],
        hints=[
            "Начни с данных, необходимых для создания задачи.",
            "Свяжи Task с Project и ответственным User по id.",
            "Укажи, где связь один-ко-многим.",
        ],
    ),
    "senior-final-webapp-lesson-3": _code(
        title="Бизнес-правило",
        objective="Ученик сможет реализовать бизнес-правило как чистую функцию с положительным и отрицательными сценариями.",
        explanation=(
            "Бизнес-правило определяет допустимое действие предметной области и не должно прятаться в обработчике "
            "кнопки. Чистая функция получает все необходимые факты и возвращает решение. Сервер использует то же "
            "правило перед изменением данных, а тесты покрывают границы."
        ),
        key_points=[
            "Правило формулируется до написания условия.",
            "Все влияющие данные передаются явно.",
            "Отказ является ожидаемым результатом, а не сбоем программы.",
        ],
        example_steps=_example(
            "Билет можно вернуть, если событие ещё не началось и билет не использован.",
            "Функция canRefund({started, used}) возвращает !started && !used.",
            "Неиспользованный будущий билет даёт true; начавшийся или использованный — false.",
        ),
        practice_title="Проверь публикацию проекта",
        practice_prompt="Считай JSON с testsPassed, hasDescription и openCriticalBugs. Выведи publish, только если тесты прошли, описание есть и критических багов 0; иначе block.",
        starter_code=(
            "const fs = require('fs');\n"
            "const project = JSON.parse(fs.readFileSync(0, 'utf8'));\n"
            "function canPublish(project) {\n"
            "  // TODO: объедини три условия бизнес-правила\n"
            "  return false;\n"
            "}\n"
            "console.log(canPublish(project) ? 'publish' : 'block');\n"
        ),
        tests=[
            {"label": "Готово к публикации", "input": "{\"testsPassed\":true,\"hasDescription\":true,\"openCriticalBugs\":0}\n", "expected": "publish\n"},
            {"label": "Есть критический баг", "input": "{\"testsPassed\":true,\"hasDescription\":true,\"openCriticalBugs\":1}\n", "expected": "block\n"},
            {"label": "Нет описания", "input": "{\"testsPassed\":true,\"hasDescription\":false,\"openCriticalBugs\":0}\n", "expected": "block\n"},
        ],
        hints=[
            "Все три требования должны выполняться одновременно.",
            "Используй оператор &&.",
            "Сравни openCriticalBugs строго с нулём.",
        ],
    ),
    "senior-final-webapp-lesson-4": _text(
        title="Проверка перед демо",
        objective="Ученик сможет составить воспроизводимый pre-demo checklist для главного сценария и резервного плана.",
        explanation=(
            "Демо проверяет пользовательскую ценность, поэтому перед показом проходят главный сценарий на чистых "
            "данных, проверяют окружение и готовят восстановление. Список должен содержать конкретные действия и "
            "ожидаемый результат. Запись экрана или подготовленный набор данных помогает при внешнем сбое."
        ),
        key_points=[
            "Главный сценарий проверяется от начала до конца.",
            "Демо-данные не содержат персональной информации.",
            "Резервный план готовится до презентации.",
        ],
        example_steps=_example(
            "Перед демо календаря создаём тестового пользователя и два безопасных события.",
            "Проверяем вход, создание, перенос и удаление события в том же окружении, где будет показ.",
            "Сохраняем короткую запись успешного сценария и ссылку на стабильную резервную сборку.",
        ),
        practice_title="Подготовь демо трекера задач",
        practice_prompt=(
            "Составь pre-demo checklist для создания, назначения и завершения задачи. Обязательно используй слова: "
            "сценарий, данные, окружение, резерв. Для каждого шага укажи ожидаемый результат."
        ),
        keywords=["сценарий", "данные", "окружение", "резерв"],
        hints=[
            "Начни с проверки версии и доступности приложения.",
            "Используй отдельные неперсональные демо-данные.",
            "Добавь действие на случай потери сети.",
        ],
    ),
    "senior-final-webapp-lesson-5": _text(
        title="Финальный питч",
        objective="Ученик сможет подготовить двухминутный питч проекта с проблемой, демонстрацией решения и измеримым следующим шагом.",
        explanation=(
            "Питч не перечисляет все технологии, а быстро связывает проблему пользователя с работающим решением. "
            "Сначала даётся контекст, затем показывается один главный сценарий, после — доказательство пользы и "
            "следующий шаг. Ограничения лучше назвать честно, чем скрывать за общими обещаниями."
        ),
        key_points=[
            "Проблема и аудитория звучат в начале.",
            "Демонстрация показывает один законченный сценарий.",
            "Следующий шаг опирается на обратную связь или метрику.",
        ],
        example_steps=_example(
            "Команда представляет сервис очереди школьной столовой для учеников и персонала.",
            "За минуту показывает заказ и номер в очереди, затем сообщает результат теста: ожидание снизилось с 12 до 7 минут.",
            "Питч завершается планом проверить оплату на одной точке, не обещая немедленный запуск во всех школах.",
        ),
        practice_title="Подготовь питч учебного проекта",
        practice_prompt=(
            "Напиши структуру двухминутного питча своего веб-проекта. Обязательно используй слова: проблема, решение, "
            "демонстрация, метрика, шаг. Добавь одно честное ограничение текущей версии."
        ),
        keywords=["проблема", "решение", "демонстрация", "метрика", "шаг"],
        hints=[
            "Уложи проблему и аудиторию в первые два предложения.",
            "Выбери для демонстрации одно ключевое действие.",
            "Заверши измеримым следующим экспериментом.",
        ],
    ),
}
