"""
export_resolution_v1.2.py — Flame Python Export Hook
======================================================
v1.2 — Auto-destination from project path
  Reads the current Flame project name and derives the export destination
  automatically:  <project_root>/06_EXPORTS
  The Flame browser still opens pre-navigated to that folder so the user
  can confirm or override the destination before exporting.

Parses a resolution token from each selected clip's name and exports each
one independently as a QuickTime ProRes 422 HQ movie at that resolution,
with no audio mixdown.

WHY PyExporter INSTEAD OF presetPath IN HOOKS
---------------------------------------------
Flame's export hook system locks in the preset once — during preCustomExport —
and uses it for the entire batch.  Setting info['presetPath'] in
preExportSequence is ignored by Flame; it is not an editable key at that stage.

The only way to give each clip its own preset (and therefore its own resolution)
is to drive each export explicitly using flame.PyExporter, one clip at a time.
preCustomExport intercepts the selection, runs all exports via PyExporter, then
sets info['abort'] = True to prevent Flame from also running its own (wrong)
export pass at native resolution.

HOW THE PROJECT PATH IS DERIVED
---------------------------------
flame.projects.current_project.project_folder returns a path nested inside
the larger project directory, e.g.:
    /Volumes/Media/NETFLIX_PROJECTS/MY_PROJECT/05_FLAME/MY_PROJECT_flame01

The script locates the project name component in that path, truncates
everything after it, then appends 06_EXPORTS:
    /Volumes/Media/CLIENT/MY_PROJECT/06_EXPORTS

If the project name cannot be found in the path, the browser falls back
to BROWSE_START_PATH so the user can still pick a folder manually.

HOOK PLACEMENT
--------------
Copy this file to your Flame hooks directory, e.g.:
    /opt/Autodesk/shared/python/   (system-wide)
  or add its folder to $DL_PYTHON_HOOK_PATH.

PRESET REQUIREMENT
------------------
Save a Flame export preset named exactly:
    "MASTER_SAME-AS-SOURCE_422HQ"
via the Flame Export dialog (Movie / QuickTime / ProRes 422 HQ / VBR /
<n> filename token / No Mixdown), then confirm it exists at PRESET_BASE_DIR.

RESOLUTION NAMING CONVENTIONS SUPPORTED
----------------------------------------
    MySpot_1920x1080_v01
    PROJ_3840x2160_v003_OUTPUT
    en_US_<show>_Spot_<spot name>_30_1920x1080_PRHQ_2CH_post_...
    Sequence_2048_1556
    spot_1920_1080_final

USAGE
-----
Select one or more clips/sequences in the Media Panel.
Right-click → "Export by Resolution in Name".
The Flame browser opens pre-set to <project_root>/06_EXPORTS.
Confirm or change the destination, then each clip is exported at the
resolution found in its own name.
"""

import re
import os
import xml.etree.ElementTree as ET
import tempfile
import shutil

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# Base directory for Flame shared export presets.
# Update the version string (e.g. 2027.pr239) when upgrading Flame.
PRESET_BASE_DIR = "/opt/Autodesk/shared/python/EXPORT-FILENAME-RESOLUTION/EXPORT_PRESET"

# The exact filename (without .xml) of your ProRes 422 HQ preset.
PRORES_PRESET_NAME = "MASTER_SAME-AS-SOURCE_422HQ"

# Starting directory shown in the browse-for-folder dialog.
# BROWSE_START_PATH = "/Volumes/Media/NETFLIX_PROJECTS/"

# Name shown in Flame's right-click contextual menu.
MENU_LABEL = "Export by Resolution in Name"

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

# Regex: WxH (e.g. 1920x1080) tried first, then _W_H_ (e.g. _1920_1080_)
_RES_PATTERNS = [
    re.compile(r'(\d{3,5})[xX](\d{3,5})'),
    re.compile(r'_(\d{3,5})_(\d{3,5})(?:[_.]|$)'),
]

_NAMED_PRESETS = {
    (640,  480):  "640 x 480",
    (720,  486):  "NTSC 720 x 486",
    (720,  576):  "PAL 720 x 576",
    (1280, 720):  "HD 1280 x 720",
    (1920, 1080): "HD 1920 x 1080",
    (2048, 1080): "2K 2048 x 1080",
    (2048, 1556): "2K 2048 x 1556",
    (3840, 2160): "UHD 3840 x 2160",
    (4096, 2160): "4K 4096 x 2160",
    (4096, 2304): "4K 4096 x 2304",
}


def parse_resolution(name):
    """Return (width, height) ints parsed from *name*, or (None, None)."""
    for pattern in _RES_PATTERNS:
        m = pattern.search(name)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
            if 64 <= w <= 16384 and 64 <= h <= 16384:
                return w, h
    return None, None


def build_preset_path(preset_name, base_dir=PRESET_BASE_DIR):
    """Return the full path to a named preset XML file."""
    return os.path.join(base_dir, preset_name + ".xml")


def patch_preset_xml(source_xml_path, width, height):
    """
    Copy the preset XML to a fresh temp file with <width>, <height>,
    <resolutionName>, and <mixdown> patched for this clip's resolution.
    Returns the path to the temp file.
    """
    tree = ET.parse(source_xml_path)
    root = tree.getroot()

    video_el = root.find(".//video")
    search_root = video_el if video_el is not None else root

    for tag in ("width", "frameWidth", "Width"):
        el = search_root.find(tag) or root.find(".//" + tag)
        if el is not None:
            el.text = str(width)
            break

    for tag in ("height", "frameHeight", "Height"):
        el = search_root.find(tag) or root.find(".//" + tag)
        if el is not None:
            el.text = str(height)
            break

    res_label = _NAMED_PRESETS.get(
        (width, height), "Custom {:d} x {:d}".format(width, height)
    )
    for tag in ("resolutionName", "ResolutionPreset", "resolution"):
        el = root.find(".//" + tag)
        if el is not None:
            el.text = res_label
            break

    audio_el = root.find(".//audio")
    if audio_el is not None:
        for tag in ("mixdown", "Mixdown", "audioMixdown"):
            el = audio_el.find(tag)
            if el is not None:
                el.text = "No"
                break
        else:
            ET.SubElement(audio_el, "mixdown").text = "No"

    tmp_dir = tempfile.mkdtemp(prefix="flame_export_preset_")
    tmp_path = os.path.join(
        tmp_dir,
        "prores_{:d}x{:d}.xml".format(width, height)
    )
    tree.write(tmp_path, encoding="utf-8", xml_declaration=True)
    return tmp_path


def get_project_export_path():
    """
    Derive the export destination from the current Flame project.

    flame.projects.current_project.project_folder returns a path that is
    nested *inside* the larger project directory, e.g.:
        /Volumes/Media/CLIENT/MY_PROJECT/05_FLAME/MY_PROJECT_flame01

    To reach 06_EXPORTS we need to:
      1. Split the path into components.
      2. Find the component that matches the project name (e.g. "MY_PROJECT").
      3. Truncate everything after it.
      4. Append "06_EXPORTS".

    Result:
        /Volumes/Media/CLIENT/MY_PROJECT/06_EXPORTS

    Returns the derived path string, or None if the project name cannot be
    located in the folder path (caller falls back to BROWSE_START_PATH).
    """
    import flame

    try:
        project        = flame.projects.current_project
        project_name   = str(project.name)
        project_folder = str(project.project_folder)

        if not project_name:
            print("[exportHook] Project name is missing.")
            return None
        if not project_folder:
            print("[exportHook] Project folder is missing.")
            return None

        # Split path and locate the project name component
        parts = project_folder.replace("\\", "/").split("/")

        try:
            idx = parts.index(project_name)
        except ValueError:
            print(
                "[exportHook] Project name '{}' not found in path '{}'. "
                "Cannot truncate.".format(project_name, project_folder)
            )
            return None

        # Rebuild path up to and including the project name, then add 06_EXPORTS
        project_root = "/".join(parts[:idx + 1])
        export_path  = os.path.join(project_root, "06_EXPORTS")

        print(
            "[exportHook] Project: '{}' | Root: '{}' | Export path: {}".format(
                project_name, project_root, export_path
            )
        )
        return export_path

    except Exception as exc:
        print("[exportHook] Could not derive project path: {}".format(exc))
        return None


def browse_for_destination(default_path=BROWSE_START_PATH):
    """
    Open the native Flame folder browser.
    Returns the chosen path string, or None if the user cancelled.
    """
    import flame

    flame.browser.show(
        title="Choose Export Destination",
        default_path=default_path,
        select_directory=True,
        multi_selection=False,
    )

    selection = flame.browser.selection
    if selection:
        return str(selection[0])
    return None


def export_clip_with_preset(clip, preset_path, destination):
    """
    Export a single PyClip/PySequence using flame.PyExporter.

    PyExporter.export() takes (clip, preset_path, destination_path).
    foreground=True keeps the Flame progress bar visible.
    """
    import flame

    exporter = flame.PyExporter()
    exporter.foreground = True
    exporter.use_top_video_track = True
    exporter.export(clip, preset_path, destination)


# ---------------------------------------------------------------------------
# FLAME EXPORT HOOK INTERFACE
# ---------------------------------------------------------------------------

def getCustomExportProfiles(profiles):
    """Register the menu item in Flame's right-click export contextual menu."""
    profiles[MENU_LABEL] = {"exportType": "resolutionFromName"}


def preCustomExport(info, userData):
    """
    Intercepts the export and handles everything before Flame's own pass.

    Strategy
    --------
    1. Validate the base preset exists on disk.
    2. Prompt once for a destination folder.
    3. Read the current Media Panel selection.
    4. For each selected clip:
         a. Parse its resolution from its own name.
         b. Patch a fresh copy of the preset XML for that resolution.
         c. Export it via flame.PyExporter (one clip → one preset → correct res).
         d. Clean up the temp preset copy.
    5. Always set info['abort'] = True so Flame does NOT also run its own
       export pass (which would use the unpatched preset at native resolution).
    """
    if userData.get("exportType") != "resolutionFromName":
        return

    import flame

    # ------------------------------------------------------------------
    # 1. Validate the base preset file.
    # ------------------------------------------------------------------
    base_preset = build_preset_path(PRORES_PRESET_NAME)

    if not os.path.isfile(base_preset):
        info["abort"] = True
        info["abortMessage"] = (
            "Export by Resolution in Name:\n\n"
            "Cannot find the ProRes 422 HQ export preset at:\n"
            "  {}\n\n"
            "Save a preset named '{}' from the Flame Export dialog and "
            "place it in:\n  {}"
        ).format(base_preset, PRORES_PRESET_NAME, PRESET_BASE_DIR)
        return

    # ------------------------------------------------------------------
    # 2. Derive the export destination from the current project, then let
    #    the user confirm or override it in the Flame browser.
    # ------------------------------------------------------------------
    suggested = get_project_export_path() or BROWSE_START_PATH

    # Create the suggested folder now so the browser can navigate to it.
    os.makedirs(suggested, exist_ok=True)

    dest = browse_for_destination(default_path=suggested)

    if not dest:
        info["abort"] = True
        info["abortMessage"] = (
            "Export by Resolution in Name:\n\n"
            "No destination folder selected. Export cancelled."
        )
        return

    os.makedirs(dest, exist_ok=True)

    # ------------------------------------------------------------------
    # 3. Get the selected clips from the Media Panel.
    # ------------------------------------------------------------------
    selection = flame.media_panel.selected_entries

    if not selection:
        info["abort"] = True
        info["abortMessage"] = (
            "Export by Resolution in Name:\n\n"
            "No clips are selected in the Media Panel."
        )
        return

    # ------------------------------------------------------------------
    # 4. Export each clip individually with its own resolution-patched preset.
    # ------------------------------------------------------------------
    errors = []

    for clip in selection:
        clip_name = str(clip.name)
        tmp_preset = None

        try:
            width, height = parse_resolution(clip_name)

            if width is None:
                errors.append(
                    "'{}': no resolution token found "
                    "(expected e.g. 1920x1080 in the name)".format(clip_name)
                )
                continue

            # Each clip gets its own temp preset — completely independent.
            tmp_preset = patch_preset_xml(base_preset, width, height)

            print(
                "[exportHook] Exporting '{}' at {}x{} → {}".format(
                    clip_name, width, height, dest
                )
            )

            export_clip_with_preset(clip, tmp_preset, dest)

            print("[exportHook] Done: '{}'".format(clip_name))

        except Exception as exc:
            errors.append("'{}': {}".format(clip_name, str(exc)))

        finally:
            # Clean up the temp preset dir whether export succeeded or failed.
            if tmp_preset and os.path.isfile(tmp_preset):
                try:
                    shutil.rmtree(os.path.dirname(tmp_preset), ignore_errors=True)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # 5. Abort Flame's own export pass in all cases.
    #    A non-empty abortMessage shows an error dialog, so only set it
    #    when there were actual failures.
    # ------------------------------------------------------------------
    info["abort"] = True

    if errors:
        info["abortMessage"] = (
            "Export by Resolution in Name — completed with errors:\n\n"
            + "\n".join("• " + e for e in errors)
        )
    else:
        info["abortMessage"] = ""  # silent success — no dialog shown
