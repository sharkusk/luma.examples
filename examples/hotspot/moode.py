#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2014-18 Richard Hull and contributors
# See LICENSE.rst for details.

import psutil
from hotspot.common import bytes2human, right_text, title_text, tiny_font

import subprocess
from PIL import Image, ImageFont
import requests
from StringIO import StringIO

import os

curArtUrl = ""
background = ""

def make_font(name, size):
    font_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../fonts', name))
    return ImageFont.truetype(font_path, size)

font = make_font("ProggyTiny.ttf", 15)
fontSong = make_font("code2000.ttf", 13)

"""
Reads moode audio's current song text file and return as a dictionary.

Sample:
~~~~~~~
file=SDCARD/Stereo Test/LRMonoPhase4.flac
artist=Koz
album=Stereo Test
title=LR Channel And Phase
coverurl=/coverart.php/SDCARD%2FStereo%20Test%2FLRMonoPhase4.flac
track=1
date=1997
composer=
encoded=16/48k FLAC
bitrate=409 kbps
volume=19
mute=0
state=play
"""
def moodeCurrentSong():
    with open('/var/local/www/currentsong.txt', 'r') as f:
        info = f.read()

    song = dict([t.split('=') for t in info.strip().split('\n')])

    # Special case for radio stations, as the artist and song end up being
    # combined in the song title.
    if song['artist'].strip() == "Radio station":
        try:
            song['artist'], song['title'] = song['title'].split(' - ')
        except:
            pass

    # Url's from moode can have the following forms:
    # http://.../image/path...
    # image/path...
    # /image/path...
    # 
    # The last two should be mapped to http://localhost/image/path
    if not song['coverurl'].startswith('http'):
        if song['coverurl'][0] == '/':
            song['coverurl'] = "http://localhost" + song['coverurl']
        else:
            song['coverurl'] = "http://localhost/" + song['coverurl']

    return song

"""
Reads mpd's status function and return as a dictionary
"""
def mpdStatus():
    status = subprocess.check_output(['mpc'])
    d = {}
    d['Song'] = status.split('\n')[0]
    # [playing] #3/3   0:05/0:39 (12%)
    state = status.split('\n')[1]
    d['Play State'] = state.split()[0][1:-1]
    d['Track Number'] = state.split()[1].split('/')[0][1:] 
    d['Playlist Length'] = state.split()[1].split('/')[1]
    d['Current Time'] = state.split()[2].split('/')[0]
    d['Total Time'] = state.split()[2].split('/')[1]
    return d

def render(draw, width, height):
    margin = 3

    # Don't crash if files are mis-formed
    try:
        song = moodeCurrentSong()
        status = mpdStatus()
    except:
        return

    draw.text((margin, 0), text=song['title'], font=fontSong, fill="white")
    #title_text(draw, margin, width, text=song['title'])
    draw.text((margin, 18), text=song['artist'], font=font, fill="white")
    draw.text((margin, 18+15), text=song['album'], font=font, fill="white")
    draw.text((margin, 18+15+15), text="{} {}/{} {}/{} {}".format(
        song['date'], status['Track Number'], status['Playlist Length'],
        status['Current Time'], status['Total Time'], song['encoded']).strip(), 
        font=font, fill="white")

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

