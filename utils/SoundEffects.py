#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame


class SoundEffects:
    #TODO: have volume control in settings section
    def play(file):
        if file:
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(file)
                pygame.mixer.music.play()
                pygame.mixer.music.set_volume(0.25)

            except Exception as e:
                print(f'sound effect failed {e} {file}')
