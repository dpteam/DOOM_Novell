################################################################################
## Screenshot harness (developer tool)
##
## Run the game with DOOM_NOVELL_SHOTS=1 to make it pose for four stills,
## write them to docs/screenshots/ and quit.  It doubles as a smoke test: if
## the bitmap fonts, GUI images or screens are broken, this fails loudly.
##
## It hooks `splashscreen` because that runs before the main menu appears.
################################################################################

init python:
    import os

    def _shots_enabled():
        return bool(os.environ.get("DOOM_NOVELL_SHOTS"))

    def _shot(name):
        folder = os.path.join(config.basedir, "docs", "screenshots")
        if not os.path.isdir(folder):
            os.makedirs(folder)
        path = os.path.join(folder, name)
        renpy.screenshot(path)
        return path

    class _ShotItem(object):
        def __init__(self, caption):
            self.caption = caption
            self.action = None
            self.chosen = False
            self.args = tuple()
            self.kwargs = { }


label splashscreen:

    if not _shots_enabled():
        return

    jump shots


label shots:

    $ hp, armor, ammo, kills = 82, 40, 31, 7

    ## Instant text so the stills are not caught mid-typewriter.
    $ preferences.text_cps = 0

    scene bg landing
    show boris neutral at stage_left
    with None

    ## A real Character say (interact=False) so the dialogue picks up
    ## `say_dialogue` and `say_label` exactly like the game does.
    $ renpy.say(boris, "Ты опоздал на девять минут. Демоны уже захватили второй этаж, но это не повод нарушать график.", interact=False)
    $ renpy.pause(0.5, hard=True)
    $ _shot("01-dialogue.png")

    scene bg hellhall
    show baron angry at stage_right
    with None
    python:
        renpy.show_screen(
            "choice",
            items=[
                _ShotItem("Подписать квартальный план."),
                _ShotItem("Выстрелить в барона."),
                _ShotItem("Снять со стены бензопилу."),
            ],
        )
    $ renpy.pause(0.5, hard=True)
    $ _shot("02-choice.png")
    $ renpy.hide_screen("choice")

    scene black
    python:
        renpy.show_screen("chapter_card", num=1, title="Приёмная",
                          sub="Первый рабочий день после конца света.", mapname="map01")
    $ renpy.pause(0.5, hard=True)
    $ _shot("03-chapter.png")
    $ renpy.hide_screen("chapter_card")

    scene black
    python:
        renpy.show_screen(
            "font_test",
            lines=[
                ("fonts/doom1.fnt", 14, "RIP AND TEAR 1234567890"),
                ("fonts/doom2.fnt", 21, "RIP AND TEAR 1234567890"),
                ("fonts/doom3.fnt", 28, "DOOM II 1994"),
                ("fonts/cyr20.fnt", 20, "Тест 12345 КРОВЬ"),
                ("fonts/cyr26.fnt", 26, "Тест 12345 КРОВЬ"),
                ("fonts/cyr32.fnt", 32, "Тест 12345 КРОВЬ"),
                ("fonts/cyr44.fnt", 44, "АД 9000"),
            ],
        )
    $ renpy.pause(0.6, hard=True)
    $ _shot("05-fonts.png")
    $ renpy.hide_screen("font_test")

    ## The archive screen is a `tag menu` screen; it is exercised by lint and by
    ## normal play, but it cannot be posed from here without entering the menu
    ## context, so it is intentionally not part of this harness.

    $ renpy.quit()