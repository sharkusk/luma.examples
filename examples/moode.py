#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import requests
import time
import os.path, os
from StringIO import StringIO
from PIL import Image, ImageFont
from demo_opts import get_device
from luma.core.render import canvas

from moode_common import gen_moode_status, mpdToggle

def make_font(name, size):
    font_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'fonts', name))
    return ImageFont.truetype(font_path, size)

font = make_font("C&C Red Alert [INET].ttf", 12)
fontSong = make_font("code2000.ttf", 13)

Artwork = {}
Artwork['path'] = ''
Artwork['img'] = None

# set pos[x] = -1 to center
def renderArt(draw, artpath, pos, size):
    global Artwork

    if Artwork['path'] != artpath:
        print (device.mode)
        Artwork['path'] = artpath
        response = requests.get(artpath)
        img =  Image.open(StringIO(response.content))
        aspectRatio = float(img.height)/float(img.width)
        newSize = (int(size[1]*aspectRatio), size[1])
        # Work around for 1.5" OLED.  Fails due to mode being RGB, but draw requires RGBA
        if device.mode == "1":
            Artwork['img'] = img.resize(newSize).convert("L").convert(device.mode)
        else:
            # RGBA shows blank screen, L shows properly
            Artwork['img'] = img.resize(newSize).convert("L")
    x = pos[0]
    y = pos[1]
    if x == -1:
        x = (size[0]-Artwork['img'].width)/2
    if y == -1:
        y = (size[1]-Artwork['img'].height)/2
    draw.bitmap((x,y), Artwork['img'], fill="white")
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

    def __init__(self, displayWidth, scrollBack=True):
        self.displayWidth = displayWidth
        self.scrollBack = scrollBack
        self.reset()

    def tick(self, textWidth):
        if self.state == self.PAUSED:
            if self.delay == 0:
                if textWidth > self.displayWidth:
                    self.state = self.SCROLL_FOR
                elif self.offset > 0:
                    if self.scrollBack:
                        self.state = self.SCROLL_BACK
                    else:
                        self.offset = 0
                        self.state = self.PAUSED
                        self.delay = self.PAUSE_TICKS
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

INFO_CYCLES = 15
ART_CYCLES = 8 # Disable art by setting to 0

DISPLAY_INFO = 1
DISPLAY_ART = 2

gSongCycleCount = 0
gSongDisplayState = DISPLAY_INFO

def renderSongInfo(device, margin, forceUpdate):
    global gTitle, gDetails
    global gSongCycleCount, gSongDisplayState

    if gTitle['scroller'] == None:
        gTitle['scroller'] = LineScroller(device.width, False)

    textWidth = 0
    ypos = -1

    num_lines = 5
    if device.height > 64:
        num_lines = 10

    moodeStatus = gen_moode_status(forceUpdate, num_lines)

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
                    'scroller': LineScroller(device.width, False)
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
                    textWidth += renderArt(draw, moodeStatus['artpath'], (-1,-1), (device.width,device.height))
    return textWidth

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def main():
    margin = 3
    pauseTime = 0.2

    while True:
        input_state = GPIO.input(4)
        if input_state == False:
            print("Button pressed!")
            mpdToggle()

        updatedTextWidth = renderSongInfo(device, margin, True)
        time.sleep(pauseTime)

if __name__ == "__main__":
    try:
        device = get_device()
        main()
    except KeyboardInterrupt:
        pass
