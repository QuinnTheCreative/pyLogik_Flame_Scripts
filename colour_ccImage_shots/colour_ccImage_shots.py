"""
Script Name: Color Image-Colour Correct Shots
Script Version: 2.3.1
Flame Version: 2022.3
Written by: Michael Vaglienty - modified & cleaned by QuinnR
Creation Date: 08.08.2025
Update Date: 08.08.2025

Custom Action Type: Media Panel Sequence Clips / Selected Timeline Segments

Description:
    Colors segments in sequence/timeline that have an Image node applied.

Menu:
    Flame 2023.2+:
        Right-click on selected sequences in media panel -> Color Image Colour Corrected Segments
        Right-click on selected segments in timeline -> Color Image Colour Corrected Segments
"""

# ---------------------------------------- #
# Imports

import flame
from pyflame_lib_colour_ccImage_shots import *

# ---------------------------------------- #
# Constants

SCRIPT_NAME = 'Color Image CC Shots'
SCRIPT_VERSION = 'v2.3.1'

SEGMENT_COLOR = (0.0, 0.24, 0.446)  # RGB float values

# ---------------------------------------- #
# Core Function

def color_segments_with_image(segments):
    """Color any segment that contains an Image effect."""
    colored_count = 0

    for segment in segments:
        if isinstance(segment, flame.PySegment):
            if any("image" in tlfx.type.lower() for tlfx in segment.effects):
                segment.colour = SEGMENT_COLOR
                colored_count += 1

    # Print to console
    print(f"{colored_count} segment(s) colored.")

    # Show in Flame message panel
    pyflame.message_print(
        message=f'{colored_count} segment(s) colored.',
        script_name=SCRIPT_NAME,
    )

# ---------------------------------------- #
# Sequence Handler

def color_ccImage_sequence(selection):
    """Handle sequence selection in media panel."""
    print(f"\n{'>'*10} {SCRIPT_NAME} {SCRIPT_VERSION} {'<'*10}\n")
    segments = []
    for shot in selection:
        for version in shot.versions:
            for track in version.tracks:
                segments.extend(track.segments)
    color_segments_with_image(segments)

# ---------------------------------------- #
# Segment Handler

def color_ccImage_segment_selection(selection):
    """Handle direct segment selection in timeline."""
    print(f"\n{'>'*10} {SCRIPT_NAME} {SCRIPT_VERSION} {'<'*10}\n")
    color_segments_with_image(selection)

# ---------------------------------------- #
# Scopes

def scope_segment(selection):
    return any(isinstance(item, flame.PySegment) for item in selection)

def scope_seq(selection):
    return any(isinstance(item, flame.PySequence) for item in selection)

# ---------------------------------------- #
# Flame Menus

def get_media_panel_custom_ui_actions():
    return [
        {
            'name': 'Color Segments...',
            'hierarchy': [],
            'actions': [
                {
                    'name': 'Color Image Segments',
                    'isVisible': scope_seq,
                    'execute': color_ccImage_sequence,
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
                    'name': 'Color Image Segments',
                    'isVisible': scope_segment,
                    'execute': color_ccImage_segment_selection,
                    'minimumVersion': '2020',
                }
            ]
        }
    ]
