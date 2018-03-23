#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2018 Marcus Kellerman

import subprocess
import os
from datetime import datetime

try:
    import psutil
except ImportError:
    print("The psutil library was not found. Run 'sudo -H pip install psutil' to install it.")
    sys.exit()

def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9K'
    >>> bytes2human(100001221)
    '95M'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n

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

    try:
        song = dict([t.split('=') for t in info.strip().split('\n')])
    except:
        song = {}
        song['file']=""
        song['artist']=""
        song['album']=""
        song['title']=""
        song['coverurl']=""
        song['track']=""
        song['date']=""
        song['composer']=""
        song['encoded']=""
        song['bitrate']=""
        song['volume']=""
        song['mute']=""
        song['state']=""

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
    if not song['coverurl'].startswith('http') and not song['coverurl'] == '':
        if song['coverurl'][0] == '/':
            song['coverurl'] = "http://localhost" + song['coverurl']
        else:
            song['coverurl'] = "http://localhost/" + song['coverurl']

    return song

"""
Reads mpd's status function and return as a dictionary
"""
def mpdStatus():
    d = {}
    try:
        status = subprocess.check_output(['mpc'])
        d['Song'] = status.split('\n')[0]
        # [playing] #3/3   0:05/0:39 (12%)
        state = status.split('\n')[1]
        d['Play State'] = state.split()[0][1:-1]
        d['Track Number'] = state.split()[1].split('/')[0][1:] 
        d['Playlist Length'] = state.split()[1].split('/')[1]
        d['Current Time'] = state.split()[2].split('/')[0]
        d['Total Time'] = state.split()[2].split('/')[1]
    except:
        d['Song'] = ""
        d['Play State'] = "" 
        d['Track Number'] =  ""
        d['Playlist Length'] = ""
        d['Current Time'] = ""
        d['Total Time'] = ""
    return d

def mpdToggle():
    status = subprocess.check_output(['mpc', 'toggle'])

def song_update_required():
    SongModifiedTime = 0
    while True:
        updateRequired = False
        t = os.stat('/var/local/www/currentsong.txt').st_mtime
        if SongModifiedTime != t:
            SongModifiedTime = t
            updateRequired = True
        yield updateRequired
"""
This function returns an array of text strings, the first being the song title

It will return a blank array if the file has not been updated since the last call.
"""
def gen_moode_status(forceUpdate=False):
    moodeStatus = {}

    moodeStatus['updated'] = False
    if song_update_required() or forceUpdate:
        moodeStatus['updated'] = True
        song = moodeCurrentSong()
        status = mpdStatus()
        moodeStatus['details'] = []
        moodeStatus['artpath'] = ''
        moodeStatus['title'] = "{}".format(song['title'])
        moodeStatus['state'] = song['state']
        if song['state'] == "play":
            moodeStatus['artpath'] = song['coverurl']
            moodeStatus['details'].append("{}".format(song['artist']))
            moodeStatus['details'].append("{} {}".format(song['date'], song['album']).strip())
            moodeStatus['details'].append("{} {}".format(song['bitrate'], song['encoded']))
            moodeStatus['details'].append("{}/{} {}/{}".format(
                status['Track Number'], status['Playlist Length'],
                status['Current Time'], status['Total Time'],).strip())
        else:
            moodeStatus['details'].append(cpu_usage())
            moodeStatus['details'].append(mem_usage())
            moodeStatus['details'].append(gen_ip_addr('eth0'))
            moodeStatus['details'].append(gen_ip_addr('wlan0'))
    return moodeStatus


def cpu_usage():
    # load average, uptime
    uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    av1, av2, av3 = os.getloadavg()
    return "Ld:%.1f %.1f %.1f Up: %s" \
        % (av1, av2, av3, str(uptime).split('.')[0])


def mem_usage():
    usage = psutil.virtual_memory()
    return "Mem: %s %.0f%%" \
        % (bytes2human(usage.used), 100 - usage.percent)

def gen_ip_addr(iface):
    ip = ''
    try:
        ip = psutil.net_if_addrs()[iface][0].address
    except:
        pass

    return "{}: {}".format(iface, ip)
