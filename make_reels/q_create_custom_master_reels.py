import flame

"""Create a new Reel Group with 5 reels and a sequence reel under the selected Desktop."""

def get_media_panel_custom_ui_actions():
    """Return custom actions to execute on Media Panel objects."""

    def scope_desktop(selection):
        """Scope the custom action to Desktop objects only."""
        for item in selection:
            if isinstance(item, flame.PyDesktop):
                return True
        return False

    def create_reel_group_with_reels(selection):
        """Create a new Reel Group with 5 reels and a sequence reel."""
        for item in selection:
            if isinstance(item, flame.PyDesktop):
                # Create a new Reel Group under the selected Desktop
                reel_group = item.create_reel_group("Master Reel Group")
                
                # Create and add 5 reels to the new Reel Group
                reel_names = ["12ch", "6ch", "2ch", "Addl GFX", "IO"]
                for reel_name in reel_names:
                    reel_group.create_reel(reel_name)

                # Create and add a sequence reel with a specific color
                sequence_reel = reel_group.create_reel("MASTERS", sequence=True)
                sequence_reel.colour = (0.4, 0.0, 0.0)  # Set to a red shade

    return [
        {
            "name": "Create Reels",
            "actions": [
                {
                    "name": "Create Master Reel Group with Reels",
                    "isVisible": scope_desktop,
                    "execute": create_reel_group_with_reels
                }
            ]
        }
    ]
