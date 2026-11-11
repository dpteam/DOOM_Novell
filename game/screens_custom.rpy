################################################################################
## Custom screens: HUD, chapter cards, archive, bestiary, run summary
################################################################################

## HUD ########################################################################
##
## Drawn by the say screen, so it exists exactly as long as the dialogue box
## does and never bleeds into the menus.

screen hud():

    frame:
        background None
        xalign 1.0
        yalign 0.0
        xoffset -14
        yoffset 10

        hbox:
            spacing 20

            use hud_stat("images/items/medikit.png", "КРОВЬ", hp, "#ff8a58")
            use hud_stat("images/items/green_armor.png", "БРОНЯ", armor, "#8ab4ff")
            use hud_stat("images/items/pistol.png", "ПАТРОНЫ", ammo, "#ffd6a8")
            use hud_stat("images/ui/prop_skullpole.png", "ТРУПЫ", kills, "#c9b8a2")

screen hud_stat(icon, label, value, color):
    hbox:
        spacing 6
        yalign 0.5
        add icon zoom 0.40 yalign 0.5
        text label style "stat_key" yalign 0.5
        text "[value]" style "stat_value" color color yalign 0.5 yoffset -1


## Chapter card ###############################################################
##
## Full-screen interstitial with the actual floor plan of the map the chapter
## is named after.  Called with `call screen chapter_card(...)`.

screen chapter_card(num, title, sub, mapname="map01"):

    zorder 200

    add Solid("#050505")
    add "images/maps/%s.png" % mapname xalign 0.5 yalign 0.5 zoom 2.1 alpha 0.85

    add Solid("#00000055")

    vbox:
        xalign 0.5
        yalign 0.5
        spacing 10

        text "ГЛАВА [num]  /  [mapname!u]" style "chapter_kicker" xalign 0.5
        text "[title!u]" style "chapter_title" xalign 0.5 text_align 0.5
        null height 6
        text "[sub]" style "chapter_sub" xalign 0.5 text_align 0.5

    text "НАЖМИТЕ, ЧТОБЫ ПРОДОЛЖИТЬ" style "chapter_kicker" xalign 0.5 yalign 0.93

    key "dismiss" action Return()
    button:
        xfill True
        yfill True
        background None
        action Return()


## End of run summary #########################################################

screen run_summary(title, text_body, ending_key=None):

    modal True
    zorder 200

    add Solid("#050505")
    add "images/ui/map_hero.png" alpha 0.25 xalign 0.5 yalign 0.5 zoom 1.4

    vbox:
        xalign 0.5
        yalign 0.42
        spacing 14
        text "[title!u]" style "chapter_title" xalign 0.5
        null height 4
        text "[text_body]" style "chapter_sub" xalign 0.5 text_align 0.5 xmaximum 820

    frame:
        background None
        xalign 0.5
        yalign 0.72
        hbox:
            spacing 40
            use summary_stat("ТРУПОВ", kills)
            use summary_stat("ПРОЩЕНО", mercy)
            use summary_stat("ОБЕЩАНИЙ", promises)
            use summary_stat("HP", hp)

    textbutton "ПРОДОЛЖИТЬ" action Return() xalign 0.5 yalign 0.92

    key "dismiss" action Return()

screen summary_stat(key, value):
    vbox:
        spacing 0
        text key style "stat_key" xalign 0.5
        text "[value]" style "stat_value" xalign 0.5


## Archive ####################################################################

default gallery_tab = "endings"

screen archive():

    tag menu

    add "gui/game_menu.png"
    add "gui/overlay/game_menu.png"
    add "images/ui/scanlines.png" alpha 0.35

    frame:
        style "archive_header"
        xpos 30
        ypos 18
        hbox:
            spacing 26
            text "АРХИВ" style "game_menu_label_text"
            textbutton "КОНЦОВКИ" action SetVariable("gallery_tab", "endings")
            textbutton "БЕСТИАРИЙ" action SetVariable("gallery_tab", "bestiary")
            textbutton "УРОВНИ" action SetVariable("gallery_tab", "levels")

    if gallery_tab == "endings":
        use archive_endings
    elif gallery_tab == "bestiary":
        use archive_bestiary
    else:
        use archive_levels

    textbutton "НАЗАД" action Return() xpos 40 ypos 660

screen archive_header():
    pass

style archive_header is frame:
    background None
    padding (16, 8, 16, 8)

screen archive_endings():

    viewport:
        xpos 60
        ypos 130
        xsize 1160
        ysize 500
        mousewheel True
        draggable True
        scrollbars "vertical"

        vbox:
            spacing 14
            for key, data in ENDINGS.items():
                frame:
                    xsize 1100
                    background Frame("gui/frame.png", 12, 12, 12, 12)
                    padding (20, 14, 20, 14)
                    vbox:
                        spacing 2
                        if ending_unlocked(key):
                            text data[0] style "gallery_title"
                            text data[1] style "gallery_item"
                        else:
                            text "???  /  ЗАКРЫТО" style "gallery_item_locked"
                            text "Ещё один способ уволиться." style "gallery_item_locked"

screen archive_bestiary():

    viewport:
        xpos 60
        ypos 130
        xsize 1160
        ysize 500
        mousewheel True
        draggable True
        scrollbars "vertical"

        vbox:
            spacing 10
            for entry in BESTIARY:
                frame:
                    xsize 1100
                    background Frame("gui/frame.png", 12, 12, 12, 12)
                    padding (16, 10, 16, 10)
                    hbox:
                        spacing 18
                        add entry["image"] zoom 0.30 yalign 0.5
                        vbox:
                            spacing 2
                            yalign 0.5
                            if entry["key"] in persistent.seen_bestiary:
                                text entry["name"] style "gallery_title" size 26
                                text entry["role"] style "gallery_item" color "#ffb27a"
                                text ("«" + entry["quote"] + "»") style "gallery_item" italic True
                            else:
                                text "???  /  НЕ ВСТРЕЧЕН" style "gallery_item_locked"
                                text "Собеседование ещё не назначено." style "gallery_item_locked"

screen archive_levels():

    viewport:
        xpos 60
        ypos 120
        xsize 1170
        ysize 520
        mousewheel True
        draggable True
        scrollbars "vertical"

        vpgrid:
            cols 6
            spacing 8

            for mapname in MAP_LIST:
                vbox:
                    spacing 2
                    imagebutton:
                        idle Transform("images/maps/%s.png" % mapname, zoom=0.20)
                        hover Transform("images/maps/%s.png" % mapname, zoom=0.21)
                        action Show("map_view", mapname=mapname)
                    text mapname style "map_label" size 28 xalign 0.5

screen map_view(mapname):

    modal True
    zorder 300

    add Solid("#000000cc")
    add "images/maps/%s.png" % mapname xalign 0.5 yalign 0.45 zoom 2.0
    text mapname style "map_label" xalign 0.5 yalign 0.055
    text "ЗАКРЫТЬ" style "chapter_kicker" xalign 0.5 yalign 0.93

    key "dismiss" action Hide("map_view")
    button:
        xfill True
        yfill True
        background None
        action Hide("map_view")


## Codex data ##################################################################

screen font_test(lines):
    add Solid("#101010")
    vbox:
        xpos 40
        ypos 40
        spacing 12
        for name, size, sample in lines:
            text sample font name size size color "#f2e0c8"

init python:

    ENDINGS = {
        "bfg": (
            "КРАСНЫЙ ПРОТОКОЛ",
            "Вы применили BFG-9000 к переговорной. Квартальный отчёт сгорел вместе с кварталом. "
            "Совет директоров признал подход «энергичным».",
        ),
        "union": (
            "КОЛЛЕКТИВНЫЙ ДОГОВОР",
            "Вы вступили в профсоюз демонов. Через год у вас появились выходные, "
            "медицинская страховка и вежливые пытки.",
        ),
        "hr": (
            "КАРЬЕРНЫЙ РОСТ",
            "Вы согласились на должность директора по урегулированию. "
            "Первое решение: сократить себя. Второе: премия.",
        ),
        "quiet": (
            "ТИХИЙ УХОД",
            "Вы просто вышли из офиса. Демоны не заметили. Никто не заметил. "
            "Через месяц вам всё равно написали про переработки.",
        ),
        "dead": (
            "НЕ ДОЖИЛ",
            "Вы умерли до финального решения. В отчёте это отмечено как «прервал встречу "
            "по собственному желанию», а в графе «причина» стоит «он сам».",
        ),
        "chainsaw": (
            "ПИЛА И ПОКОЙ",
            "Секретная концовка. Вы отказались от переговоров, от отчёта и от оружия дальнего боя. "
            "Осталась только пила. Пила справилась.",
        ),
    }

    BESTIARY = [
        {
            "key": "boris",
            "image": "images/chars/boris_neutral.png",
            "name": "БОРИС",
            "role": "Зомби-сотрудник, 14 смертей, 0 выговоров",
            "quote": "Я не мёртвый, я на удалёнке.",
        },
        {
            "key": "imp",
            "image": "images/chars/imp_neutral.png",
            "name": "ИГНАТ",
            "role": "Стажёр. Бросает огонь в принтер «для скорости»",
            "quote": "А можно я не буду проходить онбординг?",
        },
        {
            "key": "caco",
            "image": "images/chars/caco_neutral.png",
            "name": "АЛЕКСЕЙ",
            "role": "Эйчар. Парит над проблемой, а не решает её",
            "quote": "Давайте выпьем кофе и забудем про ужас.",
        },
        {
            "key": "baron",
            "image": "images/chars/baron_neutral.png",
            "name": "БАРОН",
            "role": "Мидл-менеджер. Легенда по KPI, угроза по этике",
            "quote": "Результат важнее средств. Средства — тоже результат.",
        },
        {
            "key": "rev",
            "image": "images/chars/revenant_neutral.png",
            "name": "РОМАН",
            "role": "Айти. Ракетница вместо тикетницы",
            "quote": "У меня всё работает. Остальное — не моя зона.",
        },
        {
            "key": "vile",
            "image": "images/chars/archvile_neutral.png",
            "name": "ВИКА",
            "role": "Коуч по выгоранию. Сжигает стажёров для мотивации",
            "quote": "Ты не устал, ты просто недостаточно веришь в миссию.",
        },
        {
            "key": "cyber",
            "image": "images/chars/cyber_neutral.png",
            "name": "КИБЕРДЕМОН",
            "role": "Генеральный директор. Ракета вместо ответа",
            "quote": "Я не кричу. Это моя нормальная громкость.",
        },
        {
            "key": "lost",
            "image": "images/chars/lost_neutral.png",
            "name": "ДУША",
            "role": "Корпоративная культура. Горит энтузиазмом",
            "quote": "Всё к лучшему! Даже это. Особенно это.",
        },
        {
            "key": "pain",
            "image": "images/chars/pain_neutral.png",
            "name": "БОЛЬ",
            "role": "Ребёнок директора. Выдыхает мелких демонов",
            "quote": "Папа сказал, что я тоже акционер.",
        },
        {
            "key": "cook",
            "image": "images/chars/mancubus_neutral.png",
            "name": "ПОВАР",
            "role": "Столовая. Готовит из того, что не дожило",
            "quote": "Белковый день. Опять.",
        },
        {
            "key": "arachno",
            "image": "images/chars/arachno_neutral.png",
            "name": "АРАХНА",
            "role": "QA. Находит баги, о которых вы не знали",
            "quote": "Я завела задачу. На тебя.",
        },
        {
            "key": "spider",
            "image": "images/chars/spider_neutral.png",
            "name": "ПАУЧИХА",
            "role": "CTO. Смотрит в будущее, видит бэклог",
            "quote": "Архитектура — это просто нити. Тяните.",
        },
        {
            "key": "guard",
            "image": "images/chars/chaingunner_neutral.png",
            "name": "ОХРАННИК",
            "role": "Пропускной режим. Очередь из стрельбы",
            "quote": "Пропуск? Не смешите мою пушку.",
        },
        {
            "key": "shotgunner",
            "image": "images/chars/shotgunner_neutral.png",
            "name": "КОНВОИР",
            "role": "Сопровождение до кабинета. И после",
            "quote": "Один выстрел — и ты в отпуске.",
        },
        {
            "key": "dog",
            "image": "images/chars/demon_neutral.png",
            "name": "ПЁС",
            "role": "Корпоративный питомец, 900 кг, кусается",
            "quote": "Гав.",
        },
    ]

    MAP_LIST = [
        "map%02d" % i for i in range(1, 33)
    ]

init python:

    def remember(key):
        """Record that the player has met a bestiary entry."""
        if key not in persistent.seen_bestiary:
            persistent.seen_bestiary.append(key)