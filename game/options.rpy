################################################################################
## Configuration for DOOM: Испытательный срок
##
## A visual novel built on Ren'Py 8.  Every image, sound and font in here is
## generated from an IWAD at build time (see tools/build_assets.py).
################################################################################

## Basics ######################################################################

define config.name = _("DOOM: Испытательный срок")

## Show the game name on the main menu.
define gui.show_name = True

define config.version = "1.0.0"

define gui.about = _p("""
Визуальная новелла по мотивам DOOM II, целиком собранная из ресурсов IWAD.

Все фоны, спрайты, элементы интерфейса, шрифты и звуки извлечены из DOOM2.WAD
(или FreeDOOM2.WAD) скриптами из каталога tools/. Ничего не скачано, ничего
не нарисовано мышкой: палитра, патчи, флэты, текстуры, спрайты, MUS-музыка и
карты уровней взяты из оригинального файла.

Код и скрипты игры распространяются по лицензии MIT. Графические и звуковые
ресурсы являются собственностью id Software / ZeniMax и используются здесь
исключительно как фанатская переработка для личного некоммерческого
использования. Подробности — в LICENSE и docs/ASSETS.md.
""")

define build.name = "DOOM_Novell"


## Sounds and music ############################################################

define config.has_sound = True
define config.has_music = True
define config.has_voice = False

init python:

    ## Point the main menu at whichever music format the build produced.
    for _ext in (".ogg", ".wav"):
        _candidate = "audio/music/title" + _ext
        if renpy.loadable(_candidate):
            config.main_menu_music = _candidate
            break


## Transitions #################################################################

define config.enter_transition = Dissolve(0.25)
define config.exit_transition = Dissolve(0.25)
define config.intra_transition = Dissolve(0.15)
define config.after_load_transition = Dissolve(0.3)
define config.end_game_transition = Fade(0.4, 0.2, 0.6)

define config.window = "auto"
define config.window_show_transition = Dissolve(0.15)
define config.window_hide_transition = Dissolve(0.15)


## Text ########################################################################

## Say things a bit faster than the default; the box holds four lines.
default preferences.text_cps = 48
default preferences.afm_time = 18


## Save directory ##############################################################

define config.save_directory = "DOOM_Novell-1755000000"

## Window icon (Windows / Linux task bar).
define config.window_icon = "gui/window_icon.png"



## Developer ###################################################################

default preferences.gl_powersave = True


## Packaging ###################################################################

init python:

    build.classify("**~", None)
    build.classify("**.bak", None)
    build.classify("**/.**", None)
    build.classify("**/#**", None)
    build.classify("**/thumbs.db", None)
    build.classify("**/*.psd", None)
    build.classify("**/*.wad", None)
    build.classify("**/*.WAD", None)
    build.classify("tools/**", None)
    build.classify("docs/**", "documentation")
    build.classify("refs/**", None)
    build.classify("game/**.rpy", "archive")
    build.classify("game/**.rpyc", "archive")
    build.classify("game/**.png", "archive")
    build.classify("game/**.wav", "archive")
    build.classify("game/**.ogg", "archive")
    build.classify("game/**.fnt", "archive")
    build.classify("game/**.json", "archive")

    build.documentation("*.md")
    build.documentation("LICENSE")