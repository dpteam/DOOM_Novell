# Сборка и запуск

## Что нужно

- **Ren'Py 8.2+** — для запуска и упаковки игры.
- **Python 3.10+**, `Pillow`, `numpy` — только если вы пересобираете ассеты.
- **IWAD** — `DOOM2.WAD` (или `freedoom2.wad`, `doom.wad`, `freedoom1.wad`).
- **ffmpeg** (необязательно) — сожмёт синтезированную музыку в OGG.

Игра запускается и без Python с Pillow: готовые ассеты уже лежат в репозитории.

## Запуск из SDK

```bash
# Windows
"C:\path\to\renpy-8.2.0-sdk\renpy.exe" "C:\path\to\DOOM_Novell"

# Linux / macOS
/path/to/renpy-8.2.0-sdk/renpy.sh /path/to/DOOM_Novell
```

Или откройте лаунчер Ren'Py, добавьте папку проекта в список и нажмите
«Запустить».

## Проверка проекта

```bash
renpy.exe "C:\path\to\DOOM_Novell" lint
```

Ожидаемый результат — отчёт без единой ошибки:

```
The game contains 373 dialogue blocks, containing 3,178 words ...
The game contains 7 menus, 148 images, and 36 screens.
```

Есть и автоматический прогон по сценарию (меню → главы → концовка):

```bash
renpy.exe "C:\path\to\DOOM_Novell" test smoke
```

Он требует настоящего GPU/OpenGL: в виртуальных машинах без ускорения Ren'Py
уходит в software-рендерер и падает на создании окна. Поэтому основной
проверкой остаются `lint` и запуск вручную.

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
| `Could not find font 'fonts/cyr26.fnt'` | шрифт не зарегистрирован под этим размером | используйте размер из `game/fonts/fonts.json` |
| Текст выглядит как сплошные прямоугольники | маска глифа записана только в альфу, а Ren'Py читает красный канал | пересоберите шрифты: `build_assets.py` пишет маску в RGB и в альфу |
| Пустые прямоугольники вместо букв | в `.fnt` указан неверный путь к атласу | пересоберите шрифты конвейером |
| Тексты «плывут» в меню | стиль переопределён после `theme.rpy` | поднимите `init offset` в `theme.rpy` |
| Нет музыки | не установлен ffmpeg и треки остались `.wav` | это нормально, `mus()` найдёт `.wav` |
| `audio/music/*.ogg is not loadable` в lint | музыка не синтезирована | `--music-only` или полная сборка |
| Латиница DOOM-шрифта слипается | `STCFN` — это 8×7 пикселей | не увеличивайте больше 2–3×, для текста используйте cyr-шрифты |

## Заметки для разработчика

- Все тексты — в `game/story/*.rpy`; правка сценария не требует пересборки
  ассетов.
- Стили — только в `game/theme.rpy`, чтобы не спорить с шаблоном Ren'Py.
- HUD рисуется внутри экрана `say`, поэтому не нужно вручную скрывать его
  перед меню.
- Если добавляете новый размер шрифта, помните: bitmap-шрифты не масштабируются.