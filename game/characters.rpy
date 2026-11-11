################################################################################
## Characters, images and the little "shooter" bookkeeping
################################################################################

## The player is a first-person camera in DOOM, so the sergeant never has a
## sprite - which is perfect for a visual novel, because it makes every other
## character look like they are talking to a shotgun.
define me = Character("СЕРЖАНТ", color="#ffcf9f")
define narr = Character(None, what_color="#d9c9b2")

define boris = Character("БОРИС", color="#a8e0a8")
define imp = Character("ИГНАТ", color="#f0a040")
define caco = Character("АЛЕКСЕЙ", color="#ef6a5a")
define baron = Character("БАРОН", color="#d79a63")
define rev = Character("РОМАН", color="#a8c8f0")
define vile = Character("ВИКА", color="#dc9cf0")
define cyber = Character("КИБЕРДЕМОН", color="#ff7a4a")
define lost = Character("ДУША", color="#f2e29a")
define pain = Character("БОЛЬ", color="#e8b0b0")
define cook = Character("ПОВАР", color="#cdb387")
define archn = Character("АРАХНА", color="#94d2c2")
define spider = Character("ПАУЧИХА", color="#c0a0f0")
define guard = Character("ОХРАННИК", color="#9aa0ea")
define dog = Character("ПЁС", color="#c08080")
define compsys = Character("СИСТЕМА UAC", color="#8ad8e0", what_prefix="> ", what_suffix="")

## ---------------------------------------------------------------- state

default hp = 100
default armor = 0
default ammo = 48
default kills = 0
default mercy = 0
default promises = 0
default chapter = 0
default callsign = "Сержант"
default music_on = True
default has_chainsaw = False

default persistent.endings = [ ]
default persistent.seen_bestiary = [ ]
default persistent.runs = 0

init python:

    MUSIC_FALLBACK = ".ogg"

    def mus(name):
        """Resolve a music track to whichever format the build produced."""
        for ext in (".ogg", ".wav"):
            path = "audio/music/" + name + ext
            if renpy.loadable(path):
                return path
        return "audio/music/" + name + MUSIC_FALLBACK

    def sfx(name):
        return "audio/sfx/" + name + ".wav"

    def unlock_ending(key):
        if key not in persistent.endings:
            persistent.endings.append(key)

    def ending_unlocked(key):
        return key in persistent.endings

    def add_kill(n=1, sound="squish"):
        store.kills += n
        if sound:
            renpy.sound.play(sfx(sound))
        renpy.notify("ФРАГ: +%d" % n)

    def add_mercy(n=1):
        store.mercy += n

    def take_damage(amount, sound="pain"):
        store.hp = max(0, store.hp - amount)
        if sound:
            renpy.sound.play(sfx(sound))
        renpy.with_statement(hpunch)

    def spend_ammo(amount=1):
        store.ammo = max(0, store.ammo - amount)

    def give_ammo(amount):
        store.ammo += amount
        renpy.sound.play(sfx("item"))

    def status_line():
        return "HP %d   ARMOR %d   AMMO %d   KILLS %d" % (store.hp, store.armor, store.ammo, store.kills)