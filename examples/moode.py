 #!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2014-18 Richard Hull and contributors
# See LICENSE.rst for details.
# PYTHON_ARGCOMPLETE_OK

"""
Scrolling artist + song and play/pause indicator
"""

import os
import time
from PIL import ImageFont, Image, ImageDraw
from demo_opts import get_device
from luma.core.render import canvas
from luma.core.image_composition import ImageComposition, ComposableImage

import subprocess

"""
Reads moode audio's current song text file and return as a dictionary.
"""
def moodeCurrentSong():
    info = ""

    while info == "":
        f = open('/var/local/www/currentsong.txt', 'r')
        info = f.read()
        f.close()

    return dict([t.split('=') for t in info.strip().split('\n')])

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

class TextImage():
    def __init__(self, device, text, font):
        with canvas(device) as draw:
            w, h = draw.textsize(text, font)
        self.image = Image.new(device.mode, (w, h))
        draw = ImageDraw.Draw(self.image)
        draw.text((0, 0), text, font=font, fill="white")
        del draw
        self.width = w
        self.height = h


class Synchroniser():
    def __init__(self):
        self.synchronised = {}

    def busy(self, task):
        self.synchronised[id(task)] = False

    def ready(self, task):
        self.synchronised[id(task)] = True

    def is_synchronised(self):
        for task in self.synchronised.iteritems():
            if task[1] is False:
                return False
        return True


class Scroller():
    WAIT_SCROLL = 1
    SCROLLING = 2
    WAIT_REWIND = 3
    WAIT_SYNC = 4

    def __init__(self, image_composition, rendered_image, scroll_delay, synchroniser):
        self.image_composition = image_composition
        self.speed = 1
        self.image_x_pos = 0
        self.rendered_image = rendered_image
        self.image_composition.add_image(rendered_image)
        self.max_pos = rendered_image.width - image_composition().width
        self.delay = scroll_delay
        self.ticks = 0
        self.state = self.WAIT_SCROLL
        self.synchroniser = synchroniser
        self.render()
        self.synchroniser.busy(self)
        self.cycles = 0
        self.must_scroll = self.max_pos > 0

    def __del__(self):
        self.image_composition.remove_image(self.rendered_image)

    def tick(self):

        # Repeats the following sequence:
        #  wait - scroll - wait - rewind -> sync with other scrollers -> wait
        if self.state == self.WAIT_SCROLL:
            if not self.is_waiting():
                self.cycles += 1
                self.state = self.SCROLLING
                self.synchroniser.busy(self)

        elif self.state == self.WAIT_REWIND:
            if not self.is_waiting():
                self.synchroniser.ready(self)
                self.state = self.WAIT_SYNC

        elif self.state == self.WAIT_SYNC:
            if self.synchroniser.is_synchronised():
                if self.must_scroll:
                    self.image_x_pos = 0
                    self.render()
                self.state = self.WAIT_SCROLL

        elif self.state == self.SCROLLING:
            if self.image_x_pos < self.max_pos:
                if self.must_scroll:
                    self.render()
                    self.image_x_pos += self.speed
            else:
                self.state = self.WAIT_REWIND

    def render(self):
        self.rendered_image.offset = (self.image_x_pos, 0)

    def is_waiting(self):
        self.ticks += 1
        if self.ticks > self.delay:
            self.ticks = 0
            return False
        return True

    def get_cycles(self):
        return self.cycles


def make_font(name, size):
    font_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'fonts', name))
    return ImageFont.truetype(font_path, size)

# ------- main

device = get_device()

TICK_TIME    = 0.100
SCROLL_DELAY = 1
MARGIN       = 2

if device.height >= 16:
    font = make_font("code2000.ttf", 12)
    fontSong = make_font("code2000.ttf", 14)
else:
    font = make_font("pixelmix.ttf", 8)

image_composition = ImageComposition(device)

modified_time = 0
status_time = 1.0 

try:

    synchroniser = Synchroniser()
    while True:
        new_time = os.stat('/var/local/www/currentsong.txt').st_mtime
        if modified_time != new_time:
            msong = moodeCurrentSong()
            ci_song = ComposableImage(TextImage(device, msong['title'], fontSong).image, position=(MARGIN, -2))
            ci_artist = ComposableImage(TextImage(device, msong['artist'], font).image, position=(MARGIN, 15))
            ci_album = ComposableImage(TextImage(device, msong['album'], font).image, position=(MARGIN, 30))

            song = Scroller(image_composition, ci_song, SCROLL_DELAY/TICK_TIME, synchroniser)
            artist = Scroller(image_composition, ci_artist, SCROLL_DELAY/TICK_TIME, synchroniser)
            album = Scroller(image_composition, ci_album, SCROLL_DELAY/TICK_TIME, synchroniser)
            modified_time = new_time

        artist.tick()
        song.tick()
        album.tick()
        time.sleep(TICK_TIME)

        status_time += TICK_TIME
        if status_time >= 1.0-TICK_TIME:
            status = mpdStatus()
            status_time = 0

        with canvas(device, background=image_composition()) as draw:
            draw.text((MARGIN, 45), "{}of{}  {}/{} ".format(
                status['Track Number'], status['Playlist Length'],
                status['Current Time'], status['Total Time']), font=font, fill="white")
            image_composition.refresh()
            # draw.rectangle(device.bounding_box, outline="white")


except KeyboardInterrupt:
    pass
