################################################################################
## Automated smoke test.
##
##   renpy.exe . test smoke
##
## It walks the menus, then plays the game from the prologue to the BFG ending,
## clicking through dialogue and picking options by caption.  Any missing image,
## broken screen or unknown font stops it with a traceback, which is the point.
################################################################################

testcase smoke:

    pause 0.8

    ## --- archive ---------------------------------------------------------
    "АРХИВ"
    pause 0.4
    "БЕСТИАРИЙ"
    pause 0.3
    "УРОВНИ"
    pause 0.3
    "КОНЦОВКИ"
    pause 0.3
    "НАЗАД"
    pause 0.4

    ## --- about / prefs / help --------------------------------------------
    "О ПРОЕКТЕ"
    pause 0.3
    "НАЗАД"
    pause 0.3

    "НАСТРОЙКИ"
    pause 0.3
    "НАЗАД"
    pause 0.3

    "УПРАВЛЕНИЕ"
    pause 0.3
    "НАЗАД"
    pause 0.4

    ## --- start ------------------------------------------------------------
    "УСТРОИТЬСЯ"
    pause 0.8

    ## Prologue + chapter card.
    click until "Ты опоздал на девять минут."
    click until "Спросить про профсоюз."
    "Спросить про профсоюз."

    ## Chapter 2.
    click until "Потушить огонь."
    "Потушить огонь."

    ## Chapter 3: take the chainsaw so the secret path exists.
    click until "Снять со стены бензопилу."
    "Снять со стены бензопилу."

    ## Chapter 4: two choices.
    click until "Извиниться перед ребёнком."
    "Извиниться перед ребёнком."
    click until "Спросить Арахну, что она думает."
    "Спросить Арахну, что она думает."

    ## Chapter 5: dodge, then BFG.
    click until "Уклониться и не провоцировать."
    "Уклониться и не провоцировать."
    click until "Достать BFG-9000."
    "Достать BFG-9000."

    ## Ending summary.
    click until "ПРОДОЛЖИТЬ"
    "ПРОДОЛЖИТЬ"

    ## Credits roll, the game returns to the main menu.
    pause 3.0
    click until "УСТРОИТЬСЯ"

    run Quit(confirm=False)