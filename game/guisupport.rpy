## Support shim for the stock Ren'Py GUI.
##
## The upstream template ships a `guisupport.rpy` that defines `gui.scale()`
## and, when running from the SDK, regenerates placeholder GUI images.  We
## keep the scale helper (the stock screens call it everywhere) but drop the
## image generator: every GUI image in this project is produced by
## `tools/build_assets.py` from the IWAD.

init -100 python in gui:

    def scale(n):
        return int(n)