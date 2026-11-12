################################################################################
## DOOM: Испытательный срок
##
## Точка входа. Пять глав, пять концовок и один очень уставший сержант.
################################################################################

label start:

    if _shots_enabled():
        jump shots

    $ kills = 0
    $ mercy = 0
    $ promises = 0
    $ hp = 100
    $ armor = 0
    $ ammo = 48
    $ chapter = 0
    $ persistent.runs += 1

    stop music fadeout 1.0
    play music mus("title") fadein 2.0

    scene black
    with Fade(0.5, 0.4, 0.8)

    card_title "DOOM"
    card_sub "ИСПЫТАТЕЛЬНЫЙ СРОК"

    card_body "Фанатская визуальная новелла.\nВсе изображения, звуки и шрифты извлечены из DOOM2.WAD.\n\nСвободный доступ к оружию массового поражения.\nНе является офертой, трудовым договором или приглашением на собеседование."

    call chapter(1, "Приёмная", "Первый рабочий день после конца света.", "map01")

    jump ch1_hr


## Interstitial helper ########################################################

label chapter(num, title, sub, mapname="map01"):

    $ chapter = num
    play sound sfx("door")

    call screen chapter_card(num, title, sub, mapname)

    return