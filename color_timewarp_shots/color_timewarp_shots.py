"""
Script Name: Color Timewarp Shots
Script Version: 2.2.0
Flame Version: 2022.3
Written by: Michael Vaglienty
Creation Date: 08.29.19
Update Date: 02.07.24

Custom Action Type: Media Panel Sequence Clips /  Selected Timeline Segments

Description:

    Colors segments in sequence/timeline that have timewarps in red

Menu:

    Flame 2022 - 2023.1:

        Right-click on selected sequences in media panel -> Color Segments... -> Color Timewarped Segments

        Right-click on selected segments in timeline -> Color Segments... -> Color Timewarped Segments

    Flame 2023.2+:

        Right-click on selected sequences in media panel -> Color Timewarped Segments

        Right-click on selected segments in timeline -> Color Timewarped Segments

To install:

    Copy script into /opt/Autodesk/shared/python/color_timewarp_shots

Updates:

    v2.2.0 02.07.24

        Updated PySide.

        Update to pyflame lib v2.

    v2.1 09.28.22

        Updated for Python 3.7.

        Added menu to timeline.

        Updated menus for Flame 2023.2+.
"""

# ---------------------------------------- #
# Imports

import flame
from pyflame_lib_color_timewarp_shots import *

# ---------------------------------------- #
# Main Script

SCRIPT_NAME = 'Color Timewarp Shots'
SCRIPT_VERSION = 'v2.2.0'

SEGMENT_COLOR = (0.147, 0.446, 0.707)

def color_timewarp_sequence(selection):

    print('\n')
    print('>' * 10, f'{SCRIPT_NAME} {SCRIPT_VERSION}', '<' * 10, '\n')

    for shot in selection:
        for version in shot.versions:
            for track in version.tracks:
                for segment in track.segments:
                    for tlfx in segment.effects:
                        if tlfx.type == 'Timewarp':

                            # Set color of clips on timeline

                            segment.colour = SEGMENT_COLOR

    pyflame.message_print(
        message='Timewarp segments colored.',
        script_name=SCRIPT_NAME,
        )

def color_timewarp_segment_selection(selection):

    print('\n')
    print('>' * 10, f'{SCRIPT_NAME} {SCRIPT_VERSION}', '<' * 10, '\n')

    for segment in selection:
        if isinstance(segment, flame.PySegment):
            for tlfx in segment.effects:
                if tlfx.type == 'Timewarp':

                    # Set color of clips on timeline

                    segment.colour = SEGMENT_COLOR

    pyflame.message_print(
        message='Timewarp segments colored.',
        script_name=SCRIPT_NAME,
        )

# ---------------------------------------- #
# Scopes

def scope_segment(selection):

    for item in selection:
        if isinstance(item, flame.PySegment):
            return True
    return False

def scope_seq(selection):

    for item in selection:
        if isinstance(item, flame.PySequence):
            return True
    return False

# ---------------------------------------- #
# Flame Menus

def get_media_panel_custom_ui_actions():
    return [
        {
            'name': 'Color Segments...',
            'hierarchy': [],
            'actions': [
                {
                    'name': 'Color Timewarped Segments',
                    'isVisible': scope_seq,
                    'execute': color_timewarp_sequence,
                    'minimumVersion': '2020',
                }
            ]
        }
    ]

def get_timeline_custom_ui_actions():
    return [
        {
            'name': 'Color Segments...',
            'hierarchy': [],
            'actions': [
                {
                    'name': 'Color Timewarped Segments',
                    'isVisible': scope_segment,
                    'execute': color_timewarp_segment_selection,
                    'minimumVersion': '2020',
                }
            ]
        }
    ]
