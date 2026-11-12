################################################################################
## Automated smoke test (Ren'Py 8.5 testcase syntax).
##
##   renpy.exe . test smoke
##
## It walks every menu, then plays the whole game from the prologue to an
## ending, picking options by their caption.  A missing image, a broken screen
## or an unregistered font stops it with a traceback, which is the point.
##
## 8.5 changed this language: bare string literals are gone, use `click "..."`,
## `advance`, and `advance until <condition>` (see renpy/test/testparser.py).
################################################################################

testsuite global:
    teardown:
        exit


testcase smoke:

    $ _test.transition_timeout = 0.05
    ## Screenshots are evidence for the CI artifacts, not a golden-image test,
    ## so never compare against a previous run.
    $ _test.overwrite_screenshots = True

    pause 0.8
    screenshot "01-main-menu.png"

    ## --- archive ---------------------------------------------------------
    click "АРХИВ"
    pause 0.5
    screenshot "02-archive-endings.png"
    click "БЕСТИАРИЙ"
    pause 0.4
    screenshot "03-archive-bestiary.png"
    click "УРОВНИ"
    pause 0.4
    screenshot "04-archive-levels.png"
    click "КОНЦОВКИ"
    pause 0.3
    click "НАЗАД"
    pause 0.4

    ## --- about / preferences / help --------------------------------------
    click "О ПРОЕКТЕ"
    pause 0.3
    click "НАЗАД"
    pause 0.3

    click "НАСТРОЙКИ"
    pause 0.3
    click "НАЗАД"
    pause 0.3

    click "УПРАВЛЕНИЕ"
    pause 0.3
    click "НАЗАД"
    pause 0.4

    ## --- play ------------------------------------------------------------
    click "УСТРОИТЬСЯ"

    ## Chapter 1. The prologue fades in, then the chapter card appears; capture
    ## that card rather than a half-faded frame, then advance into the chapter.
    advance until screen "chapter_card" timeout 120
    pause 0.4
    screenshot "05-chapter-card.png"

    advance until screen "choice" timeout 120
    pause 0.3
    screenshot "06-first-choice.png"
    click "Спросить про профсоюз."

    ## Chapter 2.
    advance until screen "choice" timeout 120
    click "Потушить огонь."

    ## Chapter 3: take the chainsaw, it unlocks the secret ending.
    advance until screen "choice" timeout 120
    click "Снять со стены бензопилу."

    ## Chapter 4: two choices.
    advance until screen "choice" timeout 120
    click "Извиниться перед ребёнком."

    advance until screen "choice" timeout 120
    click "Спросить Арахну, что она думает."

    ## Chapter 5: dodge, then the BFG.
    advance until screen "choice" timeout 120
    click "Уклониться и не провоцировать."

    advance until screen "choice" timeout 120
    click "Достать BFG-9000."

    ## Ending summary, then the credits (which restart the game).  `advance
    ## until screen "main_menu"` is the real assertion here: it only succeeds
    ## if the restart actually lands back on the main menu.
    advance until screen "run_summary" timeout 120
    pause 0.3
    screenshot "07-ending.png"
    click "ПРОДОЛЖИТЬ"

    advance until screen "main_menu" timeout 90

    ## And the menu still responds after a full restart.
    click "АРХИВ"
    pause 0.6
    click "НАЗАД"
    pause 0.4