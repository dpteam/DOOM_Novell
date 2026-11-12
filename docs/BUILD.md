# Сборка и запуск

## Что нужно

- **Ren'Py 8.5+** — для запуска и упаковки игры.
- **Python 3.10+**, `Pillow`, `numpy` — только если вы пересобираете ассеты.
- **IWAD** — `DOOM2.WAD` (или `freedoom2.wad`, `doom.wad`, `freedoom1.wad`).
- **ffmpeg** (необязательно) — сожмёт синтезированную музыку в OGG.

Игра запускается и без Python с Pillow: готовые ассеты уже лежат в репозитории.

## Установка движка

```bash
scoop install renpy        # Windows, ставит 8.5.x в ~/scoop/apps/renpy
```

Или скачайте SDK с <https://www.renpy.org/latest.html> и распакуйте куда угодно.
Проект не зависит от места установки: путь к SDK нигде не захардкожен.

## Запуск

```bash
# через shim из Scoop
renpy "C:\path\to\DOOM_Novell"

# или напрямую из SDK
"C:\path\to\renpy-8.5.3-sdk\renpy.exe" "C:\path\to\DOOM_Novell"

# Linux / macOS
/path/to/renpy-8.5.3-sdk/renpy.sh /path/to/DOOM_Novell
```

Или откройте лаунчер Ren'Py, добавьте папку проекта в список и нажмите
«Запустить».

## Проверка проекта

```bash
renpy "C:\path\to\DOOM_Novell" lint
```

Ожидаемый результат — отчёт без единой ошибки:

```
The game contains 375 dialogue blocks, containing 3,178 words ...
The game contains 7 menus, 148 images, and 36 screens.
```

Есть и автоматический прогон: меню → архив → настройки → управление → вся игра
до концовки → возврат в главное меню после титров.

```bash
renpy "C:\path\to\DOOM_Novell" test smoke
# [rpytest] Status: PASSED
```

Тест настоящий, а не декоративный: он падает, если сломать шрифт, экран или
кнопку «НАЗАД». Именно так и были найдены два бага при переходе на 8.5 (см.
`docs/CHANGELOG.md`). Ему нужен настоящий GPU/OpenGL — в виртуальных машинах
без ускорения Ren'Py уходит в software-рендерер и падает на создании окна,
поэтому для таких сред основной проверкой остаётся `lint` и запуск вручную.

Если игра запускается с чёрным экраном или показывает диалог «Renderer» —
выберите **Force ANGLE2**: на удалённых сессиях без OpenGL это единственный
рабочий вариант.

## Пересборка ассетов

```bash
python -m pip install -r requirements.txt

# всё сразу
python tools/build_assets.py --iwad D:\games\doom2\DOOM2.WAD --out .

# только интерфейс и спрайты, без синтеза музыки (быстро)
python tools/build_assets.py --iwad DOOM2.WAD --out . --skip-music

# только пересобрать саундтрек
python tools/build_assets.py --iwad DOOM2.WAD --out . --music-only
```

После пересборки обновите список изображений:

```bash
python tools/gen_images_rpy.py
```

Если вы добавили сцены или персонажей — правьте `SCENES` / `CHARACTERS` в
`tools/build_assets.py`, а не файлы в `game/images`.

### FreeDoom вместо DOOM2

```bash
python tools/build_assets.py --iwad freedoom2.wad --out .
```

FreeDoom содержит те же имена ресурсов, но другие картинки и звуки, поэтому
игра получится другой по настроению — и её можно распространять. Никаких
правок кода для этого не нужно.

## Упаковка

Из лаунчера Ren'Py: «Собрать дистрибутивы». Из командной строки:

```bash
renpy.exe "C:\path\to\DOOM_Novell" distribute --destination dist
```

`build.classify` в `game/options.rpy` исключает из сборки `tools/`, `docs/`,
`refs/` и любые `*.wad`.

## Иконка

`icon.ico` в корне проекта используется Ren'Py при упаковке под Windows.
`game/gui/window_icon.png` — иконка окна. Оба файла генерируются конвейером
из `MARBLE1`, `CYBRA1`, `HEADB1` и логотипа `M_DOOM`.

## Типичные проблемы

| Симптом | Причина | Решение |
| --- | --- | --- |
| `FreetypeError: unknown file format` | где-то остался `{size=N}` (или `size N` в стиле) для bitmap-шрифта | у каждого размера должен быть свой `.fnt`; см. `card_*_text` в `theme.rpy` |
| `Could not find font 'fonts/cyr26.fnt'` | шрифт не зарегистрирован под этим размером | используйте размер из `game/fonts/fonts.json` |
| Текст выглядит как сплошные прямоугольники | маска глифа записана только в альфу, а Ren'Py читает красный канал | пересоберите шрифты: `build_assets.py` пишет маску в RGB и в альфу |
| Пустые прямоугольники вместо букв | в `.fnt` указан неверный путь к атласу | пересоберите шрифты конвейером |
| Кнопка «НАЗАД» не видна в меню | у `style return_button` задан `ypos` без `yalign` — уезжает за экран | держите `yalign 1.0` + `yoffset` |
| Текст в меню заезжает под колонку навигации | `navigation_button` шире, чем `game_menu_navigation_frame` | ширина кнопки ≤ 280 − `navigation_xpos` |
| Тексты «плывут» в меню | стиль переопределён после `theme.rpy` | поднимите `init offset` в `theme.rpy` |
| Нет музыки | не установлен ffmpeg и треки остались `.wav` | это нормально, `mus()` найдёт `.wav` |
| `audio/music/*.ogg is not loadable` в lint | музыка не синтезирована | `--music-only` или полная сборка |
| Латиница DOOM-шрифта слипается | `STCFN` — это 8×7 пикселей | не увеличивайте больше 2–3×, для текста используйте cyr-шрифты |
| Тест падает на `click "..."` с таймаутом | искомой кнопки нет на экране | это баг интерфейса, а не теста — проверьте скриншот из `tests/screenshots/` |

## Заметки для разработчика

- Все тексты — в `game/story/*.rpy`; правка сценария не требует пересборки
  ассетов.
- Стили — только в `game/theme.rpy`, чтобы не спорить с шаблоном Ren'Py.
- HUD рисуется внутри экрана `say`, поэтому не нужно вручную скрывать его
  перед меню.
- Если добавляете новый размер шрифта, помните: bitmap-шрифты не масштабируются.