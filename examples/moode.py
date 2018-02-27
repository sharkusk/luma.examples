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
        Artwork['img'] = img.resize(size) \
            .convert("L") \
            .convert(device.mode)
    draw.bitmap(pos, Artwork['img'], fill="white")
    return Artwork['img'].size[0]

# Renders text and returns the greater of width or rendered text width
def renderText( draw, pos, text, font ):
    draw.text( pos, text, font=font, fill="white" )
    w,h = draw.textsize(text, font)
    return w

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

class LineScroller():
    PAUSED = 1
    SCROLL_FOR = 2
    SCROLL_BACK = 3
    PAUSE_TICKS = 3

    def __init__(self, displayWidth):
        self.displayWidth = displayWidth
        self.reset()

    def tick(self, textWidth):
        if self.state == self.PAUSED:
            if self.delay == 0:
                if textWidth > self.displayWidth:
                    self.state = self.SCROLL_FOR
                elif self.offset > 0:
                    self.state = self.SCROLL_BACK
            else:
                self.delay -= 1
        elif self.state == self.SCROLL_FOR:
            if textWidth <= self.displayWidth:
                self.state = self.PAUSED
                self.delay = self.PAUSE_TICKS
            else:
                self.offset += 1
        elif self.state == self.SCROLL_BACK:
            if self.offset == 0:
                self.state = self.PAUSED
                self.delay = self.PAUSE_TICKS
            else:
                self.offset -= 1

    def getOffset(self):
        return self.offset

    def reset(self):
        self.delay = self.PAUSE_TICKS 
        self.offset = 0
        self.state = self.PAUSED

def renderLine(draw, pos, line, font):
    offset = line['scroller'].getOffset()
    textWidth = renderText(draw, pos, line['text'][offset:]+" ", font)
    line['scroller'].tick(textWidth)
    return textWidth

gTitle = {
        'text': '',
        'scroller': None,
        }

gDetails = []

INFO_CYCLES = 10
ART_CYCLES = 5

DISPLAY_INFO = 1
DISPLAY_ART = 2

gSongCycleCount = 0
gSongDisplayState = DISPLAY_INFO

def renderSongInfo(device, margin, forceUpdate):
    global gTitle, gDetails
    global gSongCycleCount, gSongDisplayState

    if gTitle['scroller'] == None:
        gTitle['scroller'] = LineScroller(device.width)

    textWidth = 0
    ypos = -1
    moodeStatus = gen_moode_status(forceUpdate)

    if gSongCycleCount >= INFO_CYCLES:
        if gSongCycleCount >= INFO_CYCLES+ART_CYCLES:
            gSongCycleCount = 0
            gSongDisplayState = DISPLAY_INFO
        elif gSongCycleCount == INFO_CYCLES:
            gSongDisplayState = DISPLAY_ART
    gSongCycleCount += 1

    if moodeStatus['updated'] is True:
        if moodeStatus['title'] != gTitle['text']:
            gTitle['text'] = moodeStatus['title']
            gTitle['scroller'].reset()

        for i in range(len(moodeStatus['details'])):
            if len(gDetails) == i:
                gDetails.append({
                    'text': moodeStatus['details'][i],
                    'scroller': LineScroller(device.width)
                    })
            else:
                if moodeStatus['details'][i] != gDetails[i]['text']:
                    if len(gDetails[i]['text']) != len(moodeStatus['details'][i]):
                        gDetails[i]['scroller'].reset()
                    gDetails[i]['text'] = moodeStatus['details'][i]

    if forceUpdate or moodeStatus['updated']:
        with canvas(device) as draw:
            if gSongDisplayState == DISPLAY_INFO or moodeStatus['artpath'] == '':
                textWidth = renderLine(draw, (margin, ypos), gTitle, fontSong)
                ypos = 16
                for line in gDetails:
                    textWidth = renderLine(draw, (margin, ypos), line, font)
                    ypos += 12
                renderState(draw, moodeStatus['state'], (device.width, device.height))
                textWidth += margin
            else:
                if moodeStatus['artpath'] != '':
                    textWidth += renderArt(draw, moodeStatus['artpath'], (textWidth,0), (device.width,device.height))
    return textWidth

def main():
    margin = 3
    pauseTime = 0.5

    while True:
        updatedTextWidth = renderSongInfo(device, margin, True)
        time.sleep(pauseTime)

if __name__ == "__main__":
    try:
        device = get_device()
        main()
    except KeyboardInterrupt:
        pass
