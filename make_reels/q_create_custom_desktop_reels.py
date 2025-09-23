
import os
import re
import flame

"""Create a reel that inherits the colour coding of the reel group it is added under."""

def get_media_panel_custom_ui_actions():
    """Return custom actions to execute on Media Panel objects."""

    def scope_reel(selection):
        """Scope the custom action to the Reel Groups."""
        import flame
        for item in selection:
            if isinstance(item, flame.PyReelGroup):
                return True
        return False

    def create_reel(selection):
        """Propagate the colour of the parent Reel Group to the newly created Reel."""
        import flame
        for item in selection:
            reel = item.create_reel("GFX")
            reel.colour = (0.478,0.478,0.271)

        for item in selection:
            reel = item.create_reel("INTROS-OUTROS")

        for item in selection:
            reel = item.create_reel("BUGS-AND-RATINGS")

        for item in selection:
            reel = item.create_reel("SUBTITLES")

        for item in selection:
            reel = item.create_reel("IO")

        for item in selection:
            reel = item.create_reel("APPROVAL-AUDIO")

        for item in selection:
            reel = item.create_reel("REFERENCE")

        for item in selection:
            reel = item.create_reel("SEQUENCES",sequence=True)
            reel.colour = (0.400,0.000,0.000)


    return [
        {
            "name": "Create Reels",
            "actions": [
                {
                    "name": "Create Custom Desktop Reels",
                    "isVisible": scope_reel,
                    "execute": create_reel
                }
            ]
        }
    ]
