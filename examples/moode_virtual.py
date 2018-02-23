#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2014-18 Richard Hull and contributors
# See LICENSE.rst for details.
from __future__ import unicode_literals

import sys
import subprocess
import requests
import time
import os.path, os
from StringIO import StringIO
from PIL import Image, ImageFont
from demo_opts import get_device
from luma.core.virtual import viewport
from luma.core.render import canvas

from moode_common import gen_song_lines

curArtUrl = ""
background = ""

def make_font(name, size):
    font_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'fonts', name))
    return ImageFont.truetype(font_path, size)

font = make_font("C&C Red Alert [INET].ttf", 12)
fontSong = make_font("code2000.ttf", 13)
fontSymbol = make_font("fontawesome-webfont.ttf", 16)

SYMBOL_PLAY = "\uf001"
SYMBOL_PLAY = "\uf04b"

# Not working  :(
def cover_art(mode):

    deviceMode = mode

    def render(draw, width, height):
        # We don't want to reload the same image multiple times...
        global curArtUrl
        global background

        song = moodeCurrentSong()

        if url != curArtUrl:
            import os

            response = requests.get(url)
            img = Image.open(StringIO(response.content)).convert("RGBA")
            img.resize((width, height), Image.ANTIALIAS)
            img = img.convert(deviceMode)

            background = Image.new("RGBA", (width, height), "white")
            background.paste(img)
            curArtUrl = url
        draw.bitmap(background)

    return render

# Renders text and returns the greater of width or rendered text width
def renderText( draw, pos, text, font, width ):
    draw.text( pos, text, font=font, fill="white" )
    w,h = draw.textsize(text, font)
    if w > width:
        width = w
    return width

def renderSongInfo(virtual, margin, forceUpdate, deviceSize):
    textWidth = 0
    ypos = -1
    lines = gen_song_lines(forceUpdate)
    if len(lines):
        with canvas(virtual) as draw:
            textWidth = renderText(draw, (margin, ypos), lines[0]+" ", fontSong, textWidth)
            ypos = 16
            for line in lines[1:]:
                textWidth = renderText(draw, (margin, ypos), line, font, textWidth)
                ypos += 12
        textWidth += margin
    return textWidth

def main():
    # logo = Image.open(img_path)

    virtual = viewport(device, width=device.width * 2, height=device.height)

    margin = 3
    x = 0
    stepTime = 0.05
    pauseTime = 0.5
    scrollSpeed = 0
    scrollDirection = scrollSpeed
    sleep_since_update = 0
    textWidth = 0

    while True:
        if sleep_since_update >= 1:
            modified_time = 0
            sleep_since_update = 0

        updatedTextWidth = renderSongInfo(virtual, margin, sleep_since_update is 0, (device.width,device.height))
        if updatedTextWidth != 0:
            textWidth = updatedTextWidth

        if textWidth > device.width * 2:
            textWidth = device.width * 2

        virtual.set_position((x, 0))
        

        # Pause at zero and max width
        if x+device.width == textWidth:
            scrollDirection = -1 * scrollSpeed
            time.sleep(pauseTime)
            sleep_since_update += pauseTime
        elif x == 0:
            scrollDirection = 1 * scrollSpeed
            time.sleep(pauseTime)
            sleep_since_update += pauseTime
        elif x+device.width+scrollDirection > textWidth:
            x = textWidth-device.width-scrollDirection
        elif x+scrollDirection < 0:
            x = 0-scrollDirection
        
        x += scrollDirection
        time.sleep(stepTime)
        sleep_since_update += stepTime 

if __name__ == "__main__":
    try:
        device = get_device()
        main()
    except KeyboardInterrupt:
        pass
