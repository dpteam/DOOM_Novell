"""Translate the stock Ren'Py GUI strings that the player actually sees."""

from pathlib import Path

PATH = Path("game/screens.rpy")

TRANSLATIONS = {
    "About": "О ПРОЕКТЕ",
    "Accesses the game menu.": "Открывает игровое меню.",
    "Advances dialogue and activates the interface.": "Продвигает диалог и активирует интерфейс.",
    "Advances dialogue without selecting choices.": "Продвигает диалог, не выбирая варианты.",
    "After Choices": "После выборов",
    "Arrow Keys": "Стрелки",
    "Auto": "АВТО",
    "Auto-Forward Time": "Время автопрокрутки",
    "Automatic saves": "Автосохранения",
    "Back": "НАЗАД",
    "Calibrate": "Калибровка",
    "Display": "Экран",
    "Download Sync": "Скачать синхронизацию",
    "D-Pad, Sticks": "Крестовина, стики",
    "empty slot": "пустой слот",
    "Fullscreen": "Полный экран",
    "Gamepad": "Геймпад",
    "Help": "УПРАВЛЕНИЕ",
    "History": "ИСТОРИЯ",
    "Hides the user interface.": "Скрывает интерфейс.",
    "Keyboard": "КЛАВИАТУРА",
    "Left Click": "ЛКМ",
    "Left Trigger\\nLeft Shoulder": "Левый триггер\\nЛевый бампер",
    "Load": "ЗАГРУЗКА",
    "Main Menu": "ГЛАВНОЕ МЕНЮ",
    "Menu": "МЕНЮ",
    "Middle Click": "СКМ",
    "Mouse": "МЫШЬ",
    "Mouse Wheel Down": "Колесо вниз",
    "Mouse Wheel Up": "Колесо вверх",
    "Music Volume": "Громкость музыки",
    "Mute All": "Выключить всё",
    "Navigate the interface.": "Навигация по интерфейсу.",
    "No": "НЕТ",
    "Opens the accessibility menu.": "Открывает меню доступности.",
    "Page {}": "Стр. {}",
    "Preferences": "НАСТРОЙКИ",
    "Quick saves": "Быстрые сохранения",
    "Quit": "ВЫХОД",
    "Return": "НАЗАД",
    "Right Click": "ПКМ",
    "Right Shoulder": "Правый бампер",
    "Right Trigger\\nA/Bottom Button": "Правый триггер\\nКнопка A",
    "Rolls back to earlier dialogue.": "Возврат к предыдущим репликам.",
    "Rolls forward to later dialogue.": "Прокрутка вперёд по репликам.",
    "Save": "СОХРАНЕНИЕ",
    "Skip": "ПРОПУСК",
    "Skipping": "ПРОПУСК",
    "Skips dialogue while held down.": "Пропускает диалог, пока зажато.",
    "Sound Volume": "Громкость звуков",
    "Start": "НАЧАТЬ",
    "Start, Guide, B/Right Button": "Start, Guide, кнопка B",
    "Takes a screenshot.": "Делает скриншот.",
    "Test": "ТЕСТ",
    "Text Speed": "Скорость текста",
    "The dialogue history is empty.": "История пуста.",
    "Toggles dialogue skipping.": "Включает пропуск диалога.",
    "Transitions": "Переходы",
    "Unseen Text": "Непрочитанный текст",
    "Upload Sync": "Выгрузить синхронизацию",
    "Version [config.version!t]\\n": "Версия [config.version!t]\\n",
    "Voice Volume": "Громкость голоса",
    "Window": "В окне",
    "Y/Top Button": "Кнопка Y",
    "Yes": "ДА",
}

path = PATH
text = path.read_text(encoding="utf-8")
replaced = 0
for old, new in TRANSLATIONS.items():
    needle = '_("%s")' % old
    if needle in text:
        text = text.replace(needle, '_("%s")' % new)
        replaced += 1
path.write_text(text, encoding="utf-8")
print(f"translated {replaced} of {len(TRANSLATIONS)} strings")