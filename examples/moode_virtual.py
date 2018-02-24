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

from moode_common import gen_moode_status


def make_font(name, size):
    font_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'fonts', name))
    return ImageFont.truetype(font_path, size)

font = make_font("C&C Red Alert [INET].ttf", 12)
fontSong = make_font("code2000.ttf", 13)

Artwork = {}
Artwork['path'] = ''
Artwork['img'] = None

def renderArt(draw, artpath, pos, size):
    global Artwork
    if Artwork['path'] != artpath:
        Artwork['path'] = artpath
        response = requests.get(artpath)
        img =  Image.open(StringIO(response.content)) 
        hpercent = (size[1]/float(img.size[1]))
        wsize = int((float(img.size[0])*float(hpercent)))
        Artwork['img'] = img.resize(size) \
            .convert("L") \
            .convert(device.mode)
    draw.bitmap(pos, Artwork['img'], fill="white")
    return Artwork['img'].size[0]

# Renders text and returns the greater of width or rendered text width
def renderText( draw, pos, text, font, width ):
    draw.text( pos, text, font=font, fill="white" )
    w,h = draw.textsize(text, font)
    if w > width:
        width = w
    return width

fontSymbol = make_font("fontawesome-webfont.ttf", 12)
SYMBOL_PLAY = "\uf04b"
SYMBOL_PAUSE = "\uf04c"
SYMBOL_STOP = "\uf04d"
SYMBOL_EJECT = "\uf052"

STATES = {
        'pause': SYMBOL_PAUSE,
        'play': SYMBOL_PLAY,
        'stop': SYMBOL_STOP,
        'default': SYMBOL_EJECT,
        }

def renderState( draw, state, deviceSize ):
    try:
        text = STATES[state]
    except:
        text = STATES['default']

    w,h = draw.textsize(text, fontSymbol)
    draw.text( (deviceSize[0]-w,deviceSize[1]-h), text, 
            font=fontSymbol, fill="white" )

def renderSongInfo(virtual, margin, forceUpdate, deviceSize):
    textWidth = 0
    ypos = -1
    moodeStatus = gen_moode_status(forceUpdate)
    if moodeStatus['updated'] is True:
        with canvas(virtual) as draw:
            textWidth = renderText(draw, (margin, ypos), moodeStatus['title']+" ", fontSong, textWidth)
            ypos = 16
            for line in moodeStatus['details']:
                textWidth = renderText(draw, (margin, ypos), line, font, textWidth)
                ypos += 12
            renderState(draw, moodeStatus['state'], deviceSize)
            textWidth += margin
            if moodeStatus['artpath'] != '':
                # disable for now to prevent additional draws
                # textWidth += renderArt(draw, moodeStatus['artpath'], (textWidth,0), deviceSize)
                pass
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

        # Hack to prevent logic above from resulting in negative x value...
        # TODO: Fix logic above
        if x < 0:
            x = 0
        time.sleep(stepTime)
        sleep_since_update += stepTime 

if __name__ == "__main__":
    try:
        device = get_device()
        main()
    except KeyboardInterrupt:
        pass
