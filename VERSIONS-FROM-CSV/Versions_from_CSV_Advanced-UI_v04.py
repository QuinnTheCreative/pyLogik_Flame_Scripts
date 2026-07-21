# -*- coding: utf-8 -*-
"""
Script Name: CSV Sequence Duplicator (Flame UI Style) with Color Support
             and Automatic Track Visibility
Author: Quinn Richardson + Claude

Creation Date: 09.22.2025
Last Updated: 07.21.2026

Script Version: 1.3
Flame Version: 2025+ (PySide6)

Description:
    Enhanced UI version for duplicating sequences from CSV file using
    Flame-style UI components. Creates multiple duplicates of selected
    sequences with names from CSV file. Automatically colors clips
    containing "_post_" in their name, using a color you choose in the
    UI (defaults to #565B79).

    After each duplicate is created and renamed, its final name is
    checked against TRACK_VISIBILITY_RULES and matching tracks are
    hidden automatically:
        name contains "NoBug"    -> hides track "bug"
        name contains "NoSub"    -> hides track "sub"
        name contains "Textless" -> hides tracks "bug", "sub", "gfx"
    (matching is case-insensitive and ignores spaces/underscores).
    Edit TRACK_VISIBILITY_RULES below to change these mappings.

Usage: 

    First- for each sequence you need to create, make or save a CSV file 
    with one entry per line each sequence you need to create.

    -In Flame-
    Right-click selected sequence on the desktop or desktop reel --> 
    "Choose Duplicate from CSV" --> Advanced UI
    Select the Browse button to locate your CSV file.
    The window above the browse button shows you the sequence to be duplicated
    The window below the browse button shows you the named sequences to be created
    from the source sequence.
    Click the color swatch to choose the color used for "_post_" clips
    (defaults to #565B79). If everything appears correct, click Create
    Duplicates.

    The window will remain in case you need to make duplicates of other sequences.

    Clips whose final name matches a track-visibility rule (see above)
    will have the corresponding track(s) hidden automatically.

To Install:

    For all users, copy this file to:
    /opt/Autodesk/shared/python

    For a specific user on Linux, copy this file to:
    ~/flame/python

    For a specific user on Mac, copy this file to:
    /User/user_name/Library/Preferences/Autodesk/flame/python

"""

import flame
import csv
import os
import time
from PySide6 import QtCore, QtGui, QtWidgets
from functools import partial


TITLE = 'CSV Sequence Duplicator'
VERSION = '1.3'
TITLE_VERSION = f'{TITLE} v{VERSION}'
MESSAGE_PREFIX = '[CSV DUPLICATOR]'

# Default color configuration - hex color "565B79" converted to RGB (0-1 range).
# This is only the *default* shown in the UI; each window instance stores
# its own chosen color in self.post_color_rgb / self.post_color_hex, which
# is what's actually used when coloring "_post_" clips.
POST_COLOR_HEX = "565B79"
POST_COLOR_RGB = (86/255.0, 91/255.0, 121/255.0)  # Normalized to 0.0-1.0 range


# ---------------- UTILITY FUNCTIONS ---------------- #

def hex_to_rgb_normalized(hex_color):
    """Convert hex color to normalized RGB (0.0-1.0) tuple."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)


def rgb_normalized_to_hex(rgb_tuple):
    """Convert a normalized (0.0-1.0) RGB tuple to a hex string (no '#')."""
    r, g, b = rgb_tuple
    return "{:02X}{:02X}{:02X}".format(
        int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
    )


def set_clip_color(clip, rgb_tuple):
    """
    Set the color of a clip using RGB values.
    
    Args:
        clip: PyClip or PySequence object
        rgb_tuple: Tuple of (r, g, b) values between 0.0 and 1.0
    """
    try:
        clip.colour = rgb_tuple
        return True
    except Exception as e:
        message(f"Error setting color for {clip.name}: {e}")
        return False


# ---------------- FLAME UI COMPONENTS ---------------- #

class FlameButton(QtWidgets.QPushButton):
    """Custom Qt Flame Button Widget"""

    def __init__(self, button_name, connect, button_color='normal', button_width=150,
                 button_max_width=150):
        super().__init__()

        self.setText(button_name)
        self.setMinimumSize(QtCore.QSize(button_width, 28))
        self.setMaximumSize(QtCore.QSize(button_max_width, 28))
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.clicked.connect(connect)
        
        if button_color == 'normal':
            self.setStyleSheet("""
                QPushButton {
                    color: rgb(154, 154, 154);
                    background-color: rgb(58, 58, 58);
                    border: none;
                    font: 14px "Discreet"}
                QPushButton:hover {
                    border: 1px solid rgb(90, 90, 90)}
                QPushButton:pressed {
                    color: rgb(159, 159, 159);
                    background-color: rgb(66, 66, 66);
                    border: 1px solid rgb(90, 90, 90)}
                QPushButton:disabled {
                    color: rgb(116, 116, 116);
                    background-color: rgb(58, 58, 58);
                    border: none}""")
        elif button_color == 'blue':
            self.setStyleSheet("""
                QPushButton {
                    color: rgb(190, 190, 190);
                    background-color: rgb(0, 110, 175);
                    border: none;
                    font: 12px "Discreet"}
                QPushButton:hover {
                    border: 1px solid rgb(90, 90, 90)}
                QPushButton:pressed {
                    color: rgb(159, 159, 159);
                    border: 1px solid rgb(90, 90, 90)}
                QPushButton:disabled {
                    color: rgb(116, 116, 116);
                    background-color: rgb(58, 58, 58);
                    border: none}""")


class FlameLabel(QtWidgets.QLabel):
    """Custom Qt Flame Label Widget"""

    def __init__(self, label_name, label_type='normal', label_width=150):
        super().__init__()

        self.setText(label_name)
        self.setMinimumSize(label_width, 28)
        self.setMaximumHeight(28)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        if label_type == 'normal':
            self.setStyleSheet("""
                QLabel {
                    color: rgb(154, 154, 154);
                    font: 14px "Discreet"}
                QLabel:disabled {
                    color: rgb(106, 106, 106)}""")
        elif label_type == 'underline':
            self.setAlignment(QtCore.Qt.AlignCenter)
            self.setStyleSheet("""
                QLabel {
                    color: rgb(154, 154, 154);
                    border-bottom: 1px inset rgb(40, 40, 40);
                    font: 14px "Discreet"}
                QLabel:disabled {
                    color: rgb(106, 106, 106)}""")


class FlameLineEdit(QtWidgets.QLineEdit):
    """Custom Qt Flame Line Edit Widget"""

    def __init__(self, text, width=150, max_width=2000):
        super().__init__()

        self.setText(text)
        self.setMinimumHeight(28)
        self.setMinimumWidth(width)
        self.setMaximumWidth(max_width)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setStyleSheet("""
            QLineEdit {
                color: rgb(154, 154, 154);
                background-color: rgb(55, 65, 75);
                selection-color: rgb(38, 38, 38);
                selection-background-color: rgb(184, 177, 167);
                border: 1px solid rgb(55, 65, 75);
                padding-left: 5px;
                font: 14px "Discreet"}
            QLineEdit:focus {background-color: rgb(73, 86, 99)}
            QLineEdit:hover {border: 1px solid rgb(90, 90, 90)}
            QLineEdit:disabled {
                color: rgb(106, 106, 106);
                background-color: rgb(55, 55, 55);
                border: 1px solid rgb(55, 55, 55)}""")


class FlameListWidget(QtWidgets.QListWidget):
    """Custom Qt Flame List Widget"""

    def __init__(self, parent_window, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setMinimumSize(500, 250)
        self.setParent(parent_window)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setSpacing(3)
        self.setAlternatingRowColors(True)
        self.setUniformItemSizes(True)
        self.setStyleSheet("""
            QListWidget {
                color: #9a9a9a;
                background-color: #2a2a2a;
                alternate-background-color: #2d2d2d;
                outline: none;
                font: 14px "Discreet"}
            QListWidget::item:selected {
                color: #d9d9d9;
                background-color: #474747}""")


class FlameProgressBar(QtWidgets.QProgressBar):
    """Custom Qt Flame Progress Bar Widget"""

    def __init__(self):
        super().__init__()
        
        self.setMinimumHeight(20)
        self.setStyleSheet("""
            QProgressBar {
                color: rgb(154, 154, 154);
                background-color: rgb(55, 65, 75);
                border: 1px solid rgb(55, 65, 75);
                border-radius: 3px;
                text-align: center;
                font: 12px "Discreet"}
            QProgressBar::chunk {
                background-color: rgb(0, 110, 175);
                border-radius: 2px}""")


class FlameColorSwatch(QtWidgets.QFrame):
    """Small clickable swatch showing the currently chosen post-color."""

    clicked = QtCore.Signal()

    def __init__(self, rgb_tuple, width=40, height=28):
        super().__init__()
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)
        self.setFrameShape(QtWidgets.QFrame.Panel)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.set_color(rgb_tuple)

    def set_color(self, rgb_tuple):
        hex_color = rgb_normalized_to_hex(rgb_tuple)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #{hex_color};
                border: 1px solid rgb(90, 90, 90);
            }}""")

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


# ---------------- CSV READING ---------------- #

def get_csv_names(path):
    """Read CSV file and return a list of names."""
    names = []
    try:
        with open(path, newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row and row[0].strip():
                    names.append(row[0].strip())
    except Exception as e:
        message(f"Error reading CSV: {e}")
    return names


def message(string):
    """Print message to shell window."""
    print(' '.join([MESSAGE_PREFIX, string]))


# ---------------- TRACK VISIBILITY (from hide_tracks_by_sequence_name.py) ---------------- #
#
# After a duplicate is created and renamed, its name is checked against
# these rules and any matching tracks are hidden. Matching is
# case-insensitive and ignores spaces/underscores, so "NoBug", "No_Bug",
# "nobug" etc. all trigger the same rule.

TRACK_VISIBILITY_RULES = [
    ("nobug", ["bug"]),
    ("nosub", ["sub"]),
    ("textless", ["bug", "sub", "gfx"]),
]


def _normalize_for_track_rules(text):
    """Lowercase and strip spaces/underscores for loose matching."""
    return text.lower().replace(" ", "").replace("_", "")


def apply_track_visibility_rules(sequence):
    """
    Given a flame.PySequence, check its name against
    TRACK_VISIBILITY_RULES and hide any matching tracks across all of
    its versions. Returns a list of (track_name, hidden_bool) for
    tracks that were changed.
    """
    seq_name = sequence.name.get_value()
    normalized_seq_name = _normalize_for_track_rules(seq_name)

    tracks_to_hide = set()
    for trigger, track_names in TRACK_VISIBILITY_RULES:
        if trigger in normalized_seq_name:
            tracks_to_hide.update(track_names)

    if not tracks_to_hide:
        return []

    message(f"Track visibility: '{seq_name}' matched rule(s), target tracks = {sorted(tracks_to_hide)}")

    changed = []
    for version_index, version in enumerate(sequence.versions):
        remaining = {t.lower() for t in tracks_to_hide}
        all_track_names = []

        for track in version.tracks:
            track_name = track.name.get_value()
            all_track_names.append(track_name)
            if track_name.lower() in remaining:
                track.hidden = True
                changed.append((track_name, True))
                remaining.discard(track_name.lower())
                message(f"Track visibility: '{seq_name}' hid track '{track_name}'")

        if remaining:
            message(
                f"Track visibility: '{seq_name}' WARNING - could not find "
                f"track(s) {sorted(remaining)} on version index {version_index}. "
                f"Tracks present: {all_track_names}"
            )

    return changed


# ---------------- MAIN WINDOW CLASS ---------------- #

class CSVDuplicatorWindow(QtWidgets.QWidget):
    """Main window for CSV Sequence Duplicator"""
    
    def __init__(self, selection, parent_widget=None):
        super().__init__(parent=parent_widget)
        
        self.selection = selection
        self.csv_names = []
        self.csv_path = ""
        self.is_processing = False

        # Per-window color choice for "_post_" clips, defaults to the
        # module-level default until the user picks something else.
        self.post_color_rgb = POST_COLOR_RGB
        self.post_color_hex = POST_COLOR_HEX
        
        self.init_window()
        self.populate_selection_list()

    def init_window(self):
        """Create the UI window."""
        self.setMinimumSize(750, 680)
        self.setStyleSheet('background-color: #272727')
        self.setWindowTitle(TITLE_VERSION)

        # Mac needs this to close the window
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Keeps on top of Flame but not other windows
        self.setWindowFlags(QtCore.Qt.Tool)

        # Title
        self.title_label = FlameLabel(TITLE_VERSION, 'normal', 750)
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: rgb(154, 154, 154);
                font: 18px "Discreet";
                margin-bottom: 10px}""")

        # Selected Items Section
        self.selected_label = FlameLabel('Selected Items:', 'underline', 500)
        self.selection_list = FlameListWidget(self)
        self.selection_list.setMaximumHeight(120)

        # CSV File Section
        self.csv_label = FlameLabel('CSV File:', 'normal')
        self.csv_line_edit = FlameLineEdit('', width=400, max_width=500)
        self.csv_browse_button = FlameButton(
            'Browse...', self.browse_csv, button_width=100)
        
        # CSV Preview Section
        self.csv_preview_label = FlameLabel('CSV Names Preview:', 'underline', 500)
        self.csv_preview_list = FlameListWidget(self)
        self.csv_preview_list.setMaximumHeight(200)
        
        self.csv_count_label = FlameLabel('Names found: 0', 'normal', 200)
        self.csv_count_label.setStyleSheet("""
            QLabel {
                color: rgb(120, 120, 120);
                font: 12px "Discreet"}""")
        
        # Color info section - swatch + choose button + label
        self.color_swatch = FlameColorSwatch(self.post_color_rgb)
        self.color_swatch.clicked.connect(self.choose_post_color)

        self.color_choose_button = FlameButton(
            'Choose Color...', self.choose_post_color, button_width=120)

        self.color_info_label = FlameLabel(
            f'Clips with "_post_" will be colored: #{self.post_color_hex}',
            'normal', 350)
        self.color_info_label.setStyleSheet("""
            QLabel {
                color: rgb(154, 154, 154);
                font: 12px "Discreet";
                padding: 5px}""")
        
        # Summary Section
        self.summary_label = FlameLabel('', 'normal', 500)
        self.summary_label.setAlignment(QtCore.Qt.AlignCenter)
        self.summary_label.setStyleSheet("""
            QLabel {
                color: rgb(200, 150, 50);
                font: 14px "Discreet";
                padding: 20px}""")

        # Progress Section
        self.progress_bar = FlameProgressBar()
        self.progress_bar.setVisible(False)
        
        self.progress_label = FlameLabel('', 'normal', 500)
        self.progress_label.setStyleSheet("""
            QLabel {
                color: rgb(120, 120, 120);
                font: 12px "Discreet"}""")
        self.progress_label.setVisible(False)

        # Buttons
        self.duplicate_button = FlameButton(
            'Create Duplicates', self.start_duplication, 
            button_color='blue', button_width=150)
        self.duplicate_button.setEnabled(False)
        
        self.cancel_button = FlameButton(
            'Cancel', self.close, button_width=110)

        # Layout
        self.setup_layout()
        
        # Shortcuts
        self.shortcut_enter = QtGui.QShortcut(
            QtGui.QKeySequence('Enter'), self.duplicate_button, self.start_duplication)
        self.shortcut_escape = QtGui.QShortcut(
            QtGui.QKeySequence('Escape'), self.cancel_button, self.close)

        self.center_window()

    def setup_layout(self):
        """Setup the window layout."""
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        main_layout.addWidget(self.title_label)
        
        # Selected Items
        main_layout.addWidget(self.selected_label)
        main_layout.addWidget(self.selection_list)
        
        # CSV File Selection
        csv_layout = QtWidgets.QHBoxLayout()
        csv_layout.addWidget(self.csv_label)
        csv_layout.addWidget(self.csv_line_edit)
        csv_layout.addWidget(self.csv_browse_button)
        main_layout.addLayout(csv_layout)
        
        # CSV Preview
        main_layout.addWidget(self.csv_preview_label)
        main_layout.addWidget(self.csv_preview_list)
        main_layout.addWidget(self.csv_count_label)
        
        # Color picker row: swatch, choose button, info label
        color_layout = QtWidgets.QHBoxLayout()
        color_layout.addWidget(self.color_swatch)
        color_layout.addWidget(self.color_choose_button)
        color_layout.addWidget(self.color_info_label)
        color_layout.addStretch()
        main_layout.addLayout(color_layout)
        
        # Summary
        main_layout.addWidget(self.summary_label)
        
        # Progress
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.progress_label)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.duplicate_button)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)

    def center_window(self):
        """Center the window on screen."""
        resolution = QtGui.QGuiApplication.primaryScreen().screenGeometry()
        self.move(
            (resolution.width() / 2) - (self.frameSize().width() / 2),
            (resolution.height() / 2) - (self.frameSize().height() / 2))

    def choose_post_color(self):
        """Open a color picker to choose the "_post_" clip color."""
        if self.is_processing:
            return

        initial = QtGui.QColor(
            int(round(self.post_color_rgb[0] * 255)),
            int(round(self.post_color_rgb[1] * 255)),
            int(round(self.post_color_rgb[2] * 255)),
        )

        chosen = QtWidgets.QColorDialog.getColor(
            initial, self, "Choose _post_ Clip Color")

        if chosen.isValid():
            self.post_color_rgb = (
                chosen.redF(), chosen.greenF(), chosen.blueF())
            self.post_color_hex = rgb_normalized_to_hex(self.post_color_rgb)

            self.color_swatch.set_color(self.post_color_rgb)
            self.color_info_label.setText(
                f'Clips with "_post_" will be colored: #{self.post_color_hex}')

            message(f"Post color changed to #{self.post_color_hex}")

    def populate_selection_list(self):
        """Populate the selection list with selected items."""
        for item in self.selection:
            item_text = f"{item.name} ({type(item).__name__})"
            self.selection_list.addItem(item_text)

    def browse_csv(self):
        """Open file dialog to select CSV file."""
        if self.is_processing:
            return
            
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.csv_path = file_path
            self.csv_line_edit.setText(file_path)
            self.load_csv_preview()

    def load_csv_preview(self):
        """Load and display CSV preview."""
        if not self.csv_path:
            return
            
        self.csv_names = get_csv_names(self.csv_path)
        
        # Update preview list with color indicator
        self.csv_preview_list.clear()
        post_count = 0
        for i, name in enumerate(self.csv_names[:50]):  # Show first 50
            indicator = " [COLOR]" if "_post_" in name.lower() else ""
            self.csv_preview_list.addItem(f"{i+1:2d}. {name}{indicator}")
            if "_post_" in name.lower():
                post_count += 1
        
        if len(self.csv_names) > 50:
            self.csv_preview_list.addItem(f"... and {len(self.csv_names) - 50} more names")
        
        # Update count
        count_text = f"Names found: {len(self.csv_names)}"
        if post_count > 0:
            count_text += f" ({post_count} will be colored)"
        self.csv_count_label.setText(count_text)
        
        # Update summary
        sequence_count = len([s for s in self.selection if isinstance(s, flame.PySequence)])
        total_duplicates = sequence_count * len(self.csv_names)
        
        if self.csv_names and sequence_count > 0:
            self.summary_label.setText(
                f"This will create {sequence_count} × {len(self.csv_names)} = {total_duplicates} duplicates")
            self.duplicate_button.setEnabled(True)
        else:
            self.summary_label.setText("Please select a valid CSV file with names")
            self.duplicate_button.setEnabled(False)

    def start_duplication(self):
        """Start the duplication process."""
        if self.is_processing or not self.csv_names:
            return
            
        self.is_processing = True
        self.duplicate_button.setEnabled(False)
        self.csv_browse_button.setEnabled(False)
        self.color_choose_button.setEnabled(False)
        
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        
        # Start duplication
        self.duplicate_sequences()

    def duplicate_sequences(self):
        """Duplicate sequences with progress tracking and color application."""
        sequences = [s for s in self.selection if isinstance(s, flame.PySequence)]
        total_operations = len(sequences) * len(self.csv_names)
        current_operation = 0
        
        success_count = 0
        error_count = 0
        colored_count = 0
        hidden_track_total = 0
        
        for sequence in sequences:
            parent_reel = sequence.parent
            if not parent_reel:
                continue
                
            sequences_before = len([s for s in parent_reel.children if isinstance(s, flame.PySequence)])
            
            for name in self.csv_names:
                current_operation += 1
                progress = int((current_operation / total_operations) * 100)
                
                self.progress_bar.setValue(progress)
                self.progress_label.setText(f"Creating: {name[:40]}..." if len(name) > 40 else f"Creating: {name}")
                
                # Process events to update UI
                QtWidgets.QApplication.processEvents()
                
                try:
                    # Duplicate the sequence
                    flame.media_panel.copy(
                        source_entries=[sequence],
                        destination=parent_reel,
                        duplicate_action='add'
                    )
                    
                    time.sleep(0.1)
                    
                    # Find and rename the duplicate
                    current_sequences = [s for s in parent_reel.children if isinstance(s, flame.PySequence)]
                    if len(current_sequences) > sequences_before:
                        new_sequences = current_sequences[sequences_before:]
                        if new_sequences:
                            duplicate = new_sequences[-1]
                            duplicate.name = name

                            # Apply track visibility rules now that the
                            # duplicate has its final name (e.g. hides
                            # "bug"/"sub"/"gfx" tracks based on NoBug/
                            # NoSub/Textless in the name).
                            hidden_tracks = apply_track_visibility_rules(duplicate)
                            if hidden_tracks:
                                hidden_track_total += len(hidden_tracks)
                            
                            # Apply color if name contains "_post_"
                            if "_post_" in name.lower():
                                if set_clip_color(duplicate, self.post_color_rgb):
                                    colored_count += 1
                                    message(f"Created and colored (#{self.post_color_hex}): {name}")
                                else:
                                    message(f"Created (color failed): {name}")
                            else:
                                message(f"Created: {name}")
                            
                            success_count += 1
                            sequences_before += 1
                        else:
                            message(f"Failed to find duplicate for: {name}")
                            error_count += 1
                    else:
                        message(f"Duplication failed for: {name}")
                        error_count += 1
                        
                except Exception as e:
                    message(f"Error creating {name}: {str(e)}")
                    error_count += 1
        
        # Completion
        self.progress_bar.setValue(100)
        completion_msg = f"Complete! Created {success_count} duplicates"
        if colored_count > 0:
            completion_msg += f", colored {colored_count}"
        if hidden_track_total > 0:
            completion_msg += f", hid {hidden_track_total} track(s)"
        if error_count > 0:
            completion_msg += f", {error_count} errors"
        self.progress_label.setText(completion_msg)
        
        message(f"Duplication complete: {success_count} created, {colored_count} colored, "
                f"{hidden_track_total} tracks hidden, {error_count} errors")
        
        # Re-enable buttons after a delay
        QtCore.QTimer.singleShot(2000, self.reset_ui)

    def reset_ui(self):
        """Reset UI after completion."""
        self.is_processing = False
        self.duplicate_button.setEnabled(True)
        self.csv_browse_button.setEnabled(True)
        self.color_choose_button.setEnabled(True)
        self.duplicate_button.setText("Create More Duplicates")

    def closeEvent(self, event):
        """Handle window close event."""
        if self.is_processing:
            event.ignore()
        else:
            message("CSV Duplicator closed")
            event.accept()


# ---------------- MAIN EXECUTION FUNCTION ---------------- #

def duplicate_from_csv_advanced(selection):
    """Launch the advanced CSV duplicator window."""
    if not selection:
        message("No items selected.")
        return

    # Filter to only sequences
    sequences = [item for item in selection if isinstance(item, flame.PySequence)]
    if not sequences:
        message("No sequences selected.")
        return

    message(f"CSV Duplicator launched with {len(sequences)} sequence(s)")
    
    # Get Flame main window as parent
    parent_window = None
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.objectName() == 'CF Main Window':
            parent_window = widget
            break
    
    # Create and show the window
    window = CSVDuplicatorWindow(selection, parent_window)
    window.show()
    
    return window


# ---------------- FLAME HOOK ---------------- #

def get_media_panel_custom_ui_actions():
    return [
        {
            "name": "Duplicate from CSV",
            "actions": [
                {
                    "name": "Advanced UI",
                    "isVisible": lambda selection: all(
                        isinstance(item, (flame.PyClip, flame.PySequence)) for item in selection
                    ),
                    "execute": duplicate_from_csv_advanced,
                }
            ],
        }
    ]