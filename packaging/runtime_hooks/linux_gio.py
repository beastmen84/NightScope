import os
import sys


# Do not mix GIO modules from a newer host distribution with the Debian 12
# GLib libraries collected into the portable bundle.
os.environ["GIO_MODULE_DIR"] = os.path.join(sys._MEIPASS, "gio_modules")
