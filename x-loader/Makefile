# Pure-X11 startup splash spike (see main.c's top comment for why).
# Needs libx11-dev + libxinerama-dev (apt install ...). No Qt, no uv/venv,
# no CMake -- deliberately as few moving parts as possible.
CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra
LDLIBS := -lX11 -lXinerama -lm

x-loader: main.c effects.c spinner.c effects.h spinner.h assets.h
	$(CC) $(CFLAGS) -o $@ main.c effects.c spinner.c $(LDLIBS)

assets.h: generate_assets.sh ../resources/loader-assets/background_light.png ../resources/loader-assets/background_dark.png
	./generate_assets.sh

.PHONY: clean
clean:
	rm -f x-loader
