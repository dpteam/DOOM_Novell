################################################################################
## DOOM_Novell theme
##
## The stock Ren'Py GUI is kept (it is a lot of well-tested screens), but every
## colour, font and panel here is replaced with something milled out of the
## WAD.  This file runs at a higher init offset than `screens.rpy`, so it wins.
################################################################################

init offset = 5

## Every text style below pairs a font with the exact pixel size it was
## rasterised at.  Bitmap fonts do not scale, so the pairs must not drift:
##   cyr20 / cyr26 / cyr32 / cyr44  - Russian body text, pixel-rasterised
##   doom1 (14) / doom2 (28) / doom3 (56) - the actual DOOM menu font


## Base styles ################################################################

style default:
    font "fonts/cyr26.fnt"
    size 26
    color "#f2e0c8"
    line_spacing 2

style input:
    color "#ffb27a"
    caret "#ff7346"

style hyperlink_text:
    font "fonts/cyr20.fnt"
    size 20
    color "#e05a34"
    hover_color "#ff8a58"
    hover_underline True

style gui_text:
    font "fonts/cyr20.fnt"
    size 20
    color "#e7d5bb"

style button_text:
    font "fonts/cyr20.fnt"
    size 20
    yalign 0.5

style label_text:
    font "fonts/cyr44.fnt"
    size 44
    color "#ffb27a"

style prompt_text:
    font "fonts/cyr20.fnt"
    size 20


## Dialogue ###################################################################

style window:
    background Image("gui/textbox.png")
    ysize 185

style namebox:
    background Frame("gui/namebox.png", 10, 10, 10, 10)
    padding (24, 6, 24, 8)
    xpos 64
    ypos -24

style say_label:
    font "fonts/cyr32.fnt"
    size 32
    color "#ffb27a"
    outlines [ (2, "#2a0d06", 0, 0) ]
    xalign 0.0
    yalign 0.5

style say_dialogue:
    font "fonts/cyr26.fnt"
    size 26
    color "#f6e6cf"
    outlines [ (1, "#140a08", 0, 0) ]
    line_spacing 4
    xpos 92
    ypos 46
    xsize 1100

style say_thought:
    font "fonts/cyr26.fnt"
    size 26
    color "#c9b8a2"
    italic False
    line_spacing 4

style namebox_label:
    font "fonts/cyr32.fnt"
    size 32
    color "#ffd6a8"


## Choices ####################################################################

style choice_vbox:
    xalign 0.5
    ypos 240
    spacing 18

style choice_button:
    xsize 790
    ysize 66
    background Frame("gui/choice/idle_background.png", 16, 10, 16, 10)
    hover_background Frame("gui/choice/hover_background.png", 16, 10, 16, 10)
    padding (26, 12, 26, 12)
    activate_sound "audio/sfx/shotgun.wav"
    hover_sound "audio/sfx/switch.wav"

style choice_button_text:
    font "fonts/cyr26.fnt"
    size 26
    color "#d8c3a8"
    hover_color "#fff0d6"
    insensitive_color "#6b5c4d"
    xalign 0.5
    text_align 0.5
    outlines [ (1, "#100a08", 0, 0) ]


## Buttons ####################################################################

style button:
    hover_sound "audio/sfx/switch.wav"
    activate_sound "audio/sfx/item.wav"

style navigation_button:
    xsize 300
    ysize 34

style navigation_button_text:
    font "fonts/cyr20.fnt"
    size 20
    xalign 0.0
    idle_color "#a08b78"
    hover_color "#ff9a6a"

style quick_button:
    hover_sound "audio/sfx/switch.wav"

style quick_button_text:
    font "fonts/cyr20.fnt"
    size 20
    idle_color "#8d7a66"
    hover_color "#ff9a6a"
    selected_color "#e05a34"


## Main menu ##################################################################

style main_menu_frame:
    xsize 380
    background "gui/overlay/main_menu.png"

style main_menu_vbox:
    xalign 1.0
    xoffset -30
    xmaximum 800
    yalign 1.0
    yoffset -24

style main_menu_text:
    font "fonts/cyr20.fnt"
    size 20
    color "#a08b78"

style main_menu_title:
    font "fonts/cyr44.fnt"
    size 44
    color "#ff9a6a"

style main_menu_version:
    font "fonts/cyr20.fnt"
    size 20
    color "#8d7a66"


## Game menu ##################################################################

style game_menu_label:
    ysize 96

style game_menu_label_text:
    font "fonts/cyr44.fnt"
    size 44
    color "#ffb27a"
    yalign 0.5
    outlines [ (2, "#2a0d06", 0, 0) ]

style return_button:
    xpos 0
    ypos -40

style page_label_text:
    font "fonts/cyr20.fnt"
    size 20

style page_button_text:
    font "fonts/cyr20.fnt"
    size 20

style slot_button_text:
    font "fonts/cyr20.fnt"
    size 20

style slot_time_text:
    font "fonts/cyr20.fnt"
    size 20

style slot_name_text:
    font "fonts/cyr20.fnt"
    size 20

style pref_label_text:
    font "fonts/cyr20.fnt"
    size 20
    color "#ffb27a"

style radio_label_text:
    font "fonts/cyr20.fnt"
    size 20

style check_label_text:
    font "fonts/cyr20.fnt"
    size 20

style slider_label_text:
    font "fonts/cyr20.fnt"
    size 20

style history_name_text:
    font "fonts/cyr20.fnt"
    size 20
    color "#ffb27a"
    xalign 1.0

style history_text:
    font "fonts/cyr20.fnt"
    size 20
    line_spacing 2

style history_label_text:
    font "fonts/cyr32.fnt"
    size 32
    color "#ffb27a"

style about_label_text:
    font "fonts/cyr32.fnt"
    size 32
    color "#ffb27a"

style about_text:
    font "fonts/cyr20.fnt"
    size 20
    line_spacing 3

style help_label_text:
    font "fonts/cyr32.fnt"
    size 32
    color "#ffb27a"

style help_text:
    font "fonts/cyr20.fnt"
    size 20

style confirm_prompt_text:
    font "fonts/cyr26.fnt"
    size 26
    text_align 0.5

style skip_text:
    font "fonts/cyr20.fnt"
    size 20

style notify_text:
    font "fonts/cyr20.fnt"
    size 20


## NVL ########################################################################

style nvl_window:
    background Image("gui/nvl.png")

style nvl_dialogue:
    font "fonts/cyr26.fnt"
    size 26

style nvl_label:
    font "fonts/cyr32.fnt"
    size 32
    color "#ffb27a"

style nvl_button_text:
    font "fonts/cyr20.fnt"
    size 20


## Boxes / frames #############################################################

style frame:
    background Frame("gui/frame.png", 12, 12, 12, 12)
    padding (18, 14, 18, 14)

style confirm_frame:
    background Frame("gui/confirm_frame.png", 24, 24, 24, 24)
    padding (40, 32, 40, 32)

style skip_frame:
    background Frame("gui/skip.png", 16, 5, 40, 5)

style notify_frame:
    background Frame("gui/notify.png", 16, 5, 40, 5)


## Bars #######################################################################

style bar:
    ysize 25
    left_bar Frame("gui/bar/left.png", 4, 4, 4, 4)
    right_bar Frame("gui/bar/right.png", 4, 4, 4, 4)

style slider:
    ysize 25


## Custom game styles #########################################################

style hud_text:
    font "fonts/cyr32.fnt"
    size 32
    color "#ffd6a8"
    outlines [ (2, "#000000", 0, 0) ]

style hud_label:
    font "fonts/cyr32.fnt"
    size 32
    color "#e05a34"
    outlines [ (2, "#000000", 0, 0) ]

style hud_num:
    font "fonts/cyr20.fnt"
    size 20
    color "#f6e6cf"

style chapter_kicker:
    font "fonts/cyr20.fnt"
    size 20
    color "#e05a34"
    kerning 3

style chapter_title:
    font "fonts/cyr44.fnt"
    size 44
    color "#ffe8c4"
    outlines [ (3, "#3a1006", 0, 0) ]

style chapter_sub:
    font "fonts/cyr26.fnt"
    size 26
    color "#c9b8a2"

style map_label:
    font "fonts/cyr32.fnt"
    size 32
    color "#ffd6a8"
    outlines [ (2, "#000000", 0, 0) ]

style gallery_title:
    font "fonts/cyr32.fnt"
    size 32
    color "#ffb27a"

style gallery_item:
    font "fonts/cyr20.fnt"
    size 20
    color "#c9b8a2"

style gallery_item_locked:
    font "fonts/cyr20.fnt"
    size 20
    color "#4a423b"

style stat_value:
    font "fonts/cyr32.fnt"
    size 32
    color "#ffd6a8"

style stat_key:
    font "fonts/cyr20.fnt"
    size 20
    color "#a08b78"

style stamp:
    font "fonts/cyr20.fnt"
    size 20
    color "#8d7a66"
    kerning 1


## Transforms #################################################################

transform ch_in(x=0.5):
    xalign x
    yalign 1.0
    alpha 0.0
    yoffset 40
    easein 0.30 alpha 1.0 yoffset 0

transform ch_out:
    easeout 0.22 alpha 0.0

transform ch_breathe:
    block:
        easeout 1.6 yoffset -6
        easein 1.6 yoffset 0
        repeat

transform ch_shake:
    block:
        linear 0.02 xoffset 6
        linear 0.02 xoffset -6
        linear 0.02 xoffset 4
        linear 0.02 xoffset -4
        linear 0.02 xoffset 0
        pause 0.6
        repeat

transform stage_left:
    xalign 0.18
    yalign 1.0

transform stage_right:
    xalign 0.82
    yalign 1.0

transform stage_center:
    xalign 0.5
    yalign 1.0

transform stage_huge:
    xalign 0.5
    yalign 1.0
    zoom 1.0

transform title_drift:
    subpixel True
    zoom 1.04
    xalign 0.5
    yalign 0.4
    linear 30.0 zoom 1.0

define white_flash = Fade(0.04, 0.0, 0.55, color="#ffffff")
