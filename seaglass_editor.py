#!/usr/bin/env python3
"""
seaglass_editor.py -- GUI for Pokemon Emerald Seaglass saves.

Left panel:  a collapsible "Party" section and one collapsible grid per PC box.
             Click any Pokemon (party or box) to view/edit it in the right pane.
Right pane:  sprite, info (with gender + shiny), and editable party fields.

Party mons are editable (write path in seaglass_write.py). Box mons are
read-only for now (view + .pk3 export). Species and nature are read-only.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt, QSize, QRect, QPoint, QRectF
from PySide6.QtGui import QImage, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QToolButton,
    QComboBox, QLineEdit, QSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QHBoxLayout, QVBoxLayout, QGridLayout, QLayout, QFileDialog, QMessageBox,
    QSplitter, QScrollArea, QStatusBar, QSizePolicy,
)

from seaglass_inspect import Rom, Save, NATURES, STAT_KEYS
from seaglass_write import EditableMon, write_party_mon, save_to_file, export_pk3
import theme

STAT_LABELS = ["HP", "Atk", "Def", "Spe", "SpA", "SpD"]
GENDER_GLYPH = {"male": "\u2642", "female": "\u2640", "genderless": "\u2014"}


class FlowLayout(QLayout):
    """A layout that wraps its children into rows based on available width."""
    def __init__(self, parent=None, margin=0, hspacing=6, vspacing=6):
        super().__init__(parent)
        self._items = []
        self._h = hspacing
        self._v = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for it in self._items:
            size = size.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        eff = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_h = eff.x(), eff.y(), 0
        for it in self._items:
            w = it.sizeHint()
            if x + w.width() > eff.right() + 1 and line_h > 0:
                x = eff.x()
                y = y + line_h + self._v
                line_h = 0
            if not test_only:
                it.setGeometry(QRect(QPoint(x, y), w))
            x = x + w.width() + self._h
            line_h = max(line_h, w.height())
        return y + line_h - rect.y() + m.bottom()





def sprite_pixmap(rom: Rom, species: int, shiny: bool, size: int = 96) -> QPixmap:
    res = rom.sprite_rgba(species, shiny)
    if not res:
        return QPixmap()
    w, h, rgba = res
    img = QImage(rgba, w, h, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(img).scaled(size, size, Qt.KeepAspectRatio, Qt.FastTransformation)


class CollapsibleSection(QWidget):
    """A header button that shows/hides a body widget (collapsible section)."""

    def __init__(self, title: str, expanded: bool = True):
        super().__init__()
        self._title = title
        self._expanded = expanded
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(2)
        self.toggle = QToolButton()
        self.toggle.setText(self._label())
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.toggle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toggle.setStyleSheet(
            "QToolButton { text-align: left; font-weight: 600; padding: 6px 8px;"
            " border: 1px solid palette(mid); border-radius: 6px; }")
        self.toggle.clicked.connect(self._on_click)
        lay.addWidget(self.toggle)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(6, 4, 6, 4)
        lay.addWidget(self.body)
        self.body.setVisible(expanded)

    def _label(self) -> str:
        return ("\u25BC " if self._expanded else "\u25B6 ") + self._title

    def _on_click(self):
        self._expanded = self.toggle.isChecked()
        self.toggle.setText(self._label())
        self.body.setVisible(self._expanded)

    def set_title(self, title: str):
        self._title = title
        self.toggle.setText(self._label())

    def set_body(self, widget: QWidget):
        self.body_layout.addWidget(widget)


class Editor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.rom = None
        self.save = None
        self.save_path = None
        self.mons = []
        self.boxes = []
        self.sel_kind = None
        self.sel_index = None
        self._current_mon = None
        self.setWindowTitle("Emerald Seaglass \u2014 Save Editor")
        self.resize(1180, 760)
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(14, 8, 14, 8); outer.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Emerald Seaglass \u2014 Save Editor"); title.setObjectName("header")
        head.addWidget(title, 1)
        self.btn_rom = QPushButton("Open ROM\u2026")
        self.btn_open_save = QPushButton("Open Save\u2026")
        self.cb_only_shiny = QCheckBox("Show only shinies")
        self.cb_only_shiny.toggled.connect(self._on_only_shiny_toggle)
        head.addWidget(self.cb_only_shiny)
        self.btn_apply = QPushButton("Apply to Pok\u00e9mon"); self.btn_apply.setObjectName("primary")
        self.btn_save = QPushButton("Save")
        self.btn_saveas = QPushButton("Save As\u2026")
        self.btn_pk3 = QPushButton("Export .pk3\u2026")
        self.btn_rom.clicked.connect(self.open_rom)
        self.btn_open_save.clicked.connect(self.open_save)
        self.btn_apply.clicked.connect(self.apply_current)
        self.btn_save.clicked.connect(self.save_over)
        self.btn_saveas.clicked.connect(self.save_as)
        self.btn_pk3.clicked.connect(self.export_pk3_current)
        for b in (self.btn_rom, self.btn_open_save, self.btn_apply,
                  self.btn_save, self.btn_saveas, self.btn_pk3):
            head.addWidget(b)
        outer.addLayout(head)

        split = QSplitter(Qt.Horizontal)
        outer.addWidget(split, 1)

        left_scroll = QScrollArea(); left_scroll.setWidgetResizable(True)
        left_inner = QWidget(); self.left_layout = QVBoxLayout(left_inner)
        self.left_layout.setContentsMargins(0, 0, 0, 0); self.left_layout.setSpacing(8)
        left_scroll.setWidget(left_inner)
        split.addWidget(left_scroll)

        self.party_section = CollapsibleSection("Party", expanded=True)
        self.party_grid = FlowLayout(hspacing=6, vspacing=6)
        party_holder = QWidget(); party_holder.setLayout(self.party_grid)
        party_holder.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.party_section.set_body(party_holder)
        self.left_layout.addWidget(self.party_section)

        self.boxes_container = QWidget()
        self.boxes_layout = QVBoxLayout(self.boxes_container)
        self.boxes_layout.setContentsMargins(0, 0, 0, 0); self.boxes_layout.setSpacing(8)
        self.left_layout.addWidget(self.boxes_container)
        self.left_layout.addStretch(1)

        scroll = QScrollArea(); scroll.setObjectName("editorScroll"); scroll.setWidgetResizable(True)
        panel = QWidget(); self.form_outer = QVBoxLayout(panel); self.form_outer.setSpacing(12)
        scroll.setWidget(panel)
        split.addWidget(scroll)
        split.setSizes([430, 750])

        toprow = QHBoxLayout()
        self.sprite = QLabel(); self.sprite.setObjectName("sprite")
        self.sprite.setFixedSize(120, 120); self.sprite.setAlignment(Qt.AlignCenter)
        toprow.addWidget(self.sprite)
        self.info = QLabel("Open a ROM and a save to begin."); self.info.setObjectName("info")
        self.info.setAlignment(Qt.AlignTop)
        toprow.addWidget(self.info, 1)
        panel_wrap = QWidget(); panel_wrap.setLayout(toprow)
        self.form_outer.addWidget(panel_wrap)

        gb_basic = QGroupBox("Identity")
        f = QFormLayout(gb_basic)
        self.ed_nick = QLineEdit(); self.ed_nick.setMaxLength(10)
        self.sp_lvl = QSpinBox(); self.sp_lvl.setRange(1, 100)
        self.sp_exp = QSpinBox(); self.sp_exp.setRange(0, 0xFFFFF)
        self.cb_nature = QComboBox(); self.cb_nature.addItems(NATURES); self.cb_nature.setEnabled(False)
        self.lbl_gender = QLabel("\u2014")
        self.cb_shiny = QCheckBox("Shiny")
        self.cb_shiny.toggled.connect(self._on_shiny_toggle)
        self.sp_friend = QSpinBox(); self.sp_friend.setRange(0, 255)
        f.addRow("Nickname", self.ed_nick)
        f.addRow("Gender", self.lbl_gender)
        f.addRow("Level", self.sp_lvl)
        f.addRow("EXP", self.sp_exp)
        f.addRow("Nature (read-only)", self.cb_nature)
        f.addRow("Friendship", self.sp_friend)
        f.addRow("", self.cb_shiny)
        self.form_outer.addWidget(gb_basic)

        gb_abil = QGroupBox("Ability / Origin")
        fa = QFormLayout(gb_abil)
        self.cb_ability = QComboBox()
        self.cb_item = QComboBox()
        fa.addRow("Ability (slot)", self.cb_ability)
        fa.addRow("Held item", self.cb_item)
        self.form_outer.addWidget(gb_abil)

        gb_moves = QGroupBox("Moves")
        gm = QGridLayout(gb_moves)
        self.cb_moves = []
        for i in range(4):
            cb = QComboBox()
            gm.addWidget(QLabel(f"Move {i+1}"), i // 2, (i % 2) * 2)
            gm.addWidget(cb, i // 2, (i % 2) * 2 + 1)
            self.cb_moves.append(cb)
        self.form_outer.addWidget(gb_moves)

        gb_stats = QGroupBox("IVs / EVs")
        gs = QGridLayout(gb_stats)
        self.iv_spins = []; self.ev_spins = []
        gs.addWidget(QLabel("Stat"), 0, 0)
        gs.addWidget(QLabel("IV"), 0, 1)
        gs.addWidget(QLabel("EV"), 0, 2)
        for i, lab in enumerate(STAT_LABELS):
            gs.addWidget(QLabel(lab), i + 1, 0)
            iv = QSpinBox(); iv.setRange(0, 31)
            ev = QSpinBox(); ev.setRange(0, 255)
            gs.addWidget(iv, i + 1, 1); gs.addWidget(ev, i + 1, 2)
            self.iv_spins.append(iv); self.ev_spins.append(ev)
        self.form_outer.addWidget(gb_stats)
        self.form_outer.addStretch(1)

        self.setStatusBar(QStatusBar())
        self.status("Ready.")
        self._set_editor_enabled(False)

    # --------------------------------------------------------------- helpers
    def status(self, msg: str):
        self.statusBar().showMessage(msg)

    def _set_editor_enabled(self, on: bool):
        for w in (self.ed_nick, self.sp_lvl, self.sp_exp, self.sp_friend,
                  self.cb_ability, self.cb_item, self.cb_shiny, *self.cb_moves,
                  *self.iv_spins, *self.ev_spins, self.btn_apply,
                  self.btn_save, self.btn_saveas, self.btn_pk3):
            w.setEnabled(on)

    # ------------------------------------------------------------- file open
    def open_rom(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Seaglass ROM", "", "GBA ROM (*.gba);;All files (*)")
        if not path:
            return
        try:
            self.rom = Rom(path)
        except Exception as e:
            QMessageBox.critical(self, "ROM error", str(e)); return
        if not self.rom.ok():
            QMessageBox.warning(self, "ROM warning",
                                "ROM self-check failed; names may be wrong. Is this a Seaglass ROM?")
        self.status(f"ROM loaded: {os.path.basename(path)}")
        self._populate_dropdowns()
        self._rebuild_left()

    def _populate_dropdowns(self):
        rom = self.rom
        self.move_ids = [0]; move_names = ["\u2014"]
        for mv in range(1, 1200):
            nm = rom.move_name(mv)
            if nm and not nm.startswith("move") and any(c.isalnum() for c in nm):
                self.move_ids.append(mv); move_names.append(nm)
        for cb in self.cb_moves:
            cb.clear()
            for mid, nm in zip(self.move_ids, move_names):
                cb.addItem(nm, mid)
        self.item_ids = [0]; item_names = ["(none)"]
        for it in range(1, 1600):
            nm = rom.item_name(it)
            if nm and not nm.startswith("item") and any(c.isalnum() for c in nm):
                self.item_ids.append(it); item_names.append(nm)
        self.cb_item.clear()
        for iid, nm in zip(self.item_ids, item_names):
            self.cb_item.addItem(nm, iid)

    def open_save(self):
        if not self.rom:
            QMessageBox.information(self, "Load ROM first", "Please open the Seaglass ROM first."); return
        path, _ = QFileDialog.getOpenFileName(self, "Open Save", "", "Save (*.sav *.srm);;All files (*)")
        if not path:
            return
        try:
            self.save = Save(path)
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e)); return
        self.save_path = path
        bad = self.save.verify_checksums()
        if bad:
            QMessageBox.warning(self, "Checksum warning",
                                f"Some sectors have bad checksums: {[b[0] for b in bad]}. "
                                "Editing may be risky.")
        self._rebuild_left()
        self.status(f"Save loaded: {os.path.basename(path)}  (slot "
                    f"{'B' if self.save.active_slot else 'A'}, counter {self.save.counter})")

    # ----------------------------------------------------------- left panel
    def _rebuild_left(self):
        if not self.rom or not self.save:
            return
        _, self.mons = self.save.party(self.rom)
        self._build_party_grid()
        self.boxes = self.save.read_boxes(self.rom)
        self._build_boxes_grid()
        if self.mons:
            self._select_party(0)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _cell_button(self, mon):
        rom = self.rom
        btn = QPushButton()
        btn.setFixedSize(64, 64)
        btn.setFlat(True)
        btn.setStyleSheet("QPushButton { border: 1px solid palette(mid); border-radius: 6px;"
                          " background: transparent; }"
                          "QPushButton:hover { border: 1px solid palette(highlight); }")
        if mon is None:
            btn.setVisible(False)
            return btn
        only_shiny = getattr(self, "cb_only_shiny", None) and self.cb_only_shiny.isChecked()
        visible = (not only_shiny) or mon.is_shiny
        if not visible:
            btn.setVisible(False)
            return btn
        pm = sprite_pixmap(rom, mon.species, mon.is_shiny, size=54)
        if not pm.isNull():
            btn.setIcon(QIcon(pm)); btn.setIconSize(QSize(54, 54))
        tip = rom.species_name(mon.species)
        if mon.is_shiny:
            tip = "\u2605 " + tip
        btn.setToolTip(tip)
        return btn

    def _build_party_grid(self):
        self._clear_layout(self.party_grid)
        self.party_section.set_title(f"Party ({len(self.mons)})")
        for i, m in enumerate(self.mons):
            btn = self._cell_button(m)
            btn.clicked.connect(lambda _=False, idx=i: self._select_party(idx))
            self.party_grid.addWidget(btn)

    def _build_boxes_grid(self):
        self._clear_layout(self.boxes_layout)
        cur = self.save.current_box()
        for b, slots in enumerate(self.boxes):
            count = sum(1 for x in slots if x)
            title = f"Box {b + 1}" + (" (current)" if b == cur else "") + f"  \u2014 {count}"
            section = CollapsibleSection(title, expanded=(b == cur or (count > 0 and b < 3)))
            flow = FlowLayout(hspacing=4, vspacing=4)
            holder = QWidget(); holder.setLayout(flow)
            holder.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            for pos, mon in enumerate(slots):
                btn = self._cell_button(mon)
                if mon is not None:
                    btn.clicked.connect(lambda _=False, bb=b, pp=pos: self._select_box(bb, pp))
                flow.addWidget(btn)
            section.set_body(holder)
            self.boxes_layout.addWidget(section)

    def _on_only_shiny_toggle(self, _checked: bool):
        if self.rom and self.save:
            self._build_party_grid()
            self._build_boxes_grid()

    # ------------------------------------------------------------- selection
    def _select_party(self, idx: int):
        self.sel_kind = "party"; self.sel_index = idx
        m = self.mons[idx]
        self._current_mon = m
        self._load_into_editor(m, editable=True)

    def _select_box(self, box: int, pos: int):
        mon = self.boxes[box][pos]
        if mon is None:
            return
        self.sel_kind = "box"; self.sel_index = (box, pos)
        self._current_mon = mon
        self._load_into_editor(mon, editable=False)
        self.status(f"Box {box + 1} slot {pos + 1}: {self.rom.species_name(mon.species)} "
                    "(box view is read-only; .pk3 export available)")

    def _load_into_editor(self, m, editable: bool):
        rom = self.rom
        self._set_editor_enabled(editable)
        # PK3 export and Save are valid for box mons too (read-only view + export).
        self.btn_pk3.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.btn_saveas.setEnabled(True)
        self.ed_nick.setText(m.nickname)
        self.sp_lvl.setValue(m.level)
        self.sp_exp.setValue(m.experience)
        self.sp_friend.setValue(m.friendship)
        self.cb_nature.setCurrentText(m.nature)
        g = rom.gender(m.species, m.pid)
        self.lbl_gender.setText(f"{GENDER_GLYPH.get(g, '')} {g.capitalize()}")
        self.cb_ability.clear()
        ab = rom.species_abilities(m.species)
        for si, aid in enumerate(ab):
            if not aid:
                continue
            self.cb_ability.addItem(f"Slot {si}: {rom.ability_name(aid)}", si)
        self.cb_ability.setCurrentIndex(m.ability_slot if m.ability_slot < self.cb_ability.count() else 0)
        idx = self.cb_item.findData(m.held_item)
        self.cb_item.setCurrentIndex(idx if idx >= 0 else 0)
        for i, cb in enumerate(self.cb_moves):
            mid = m.moves[i] if i < len(m.moves) else 0
            j = cb.findData(mid); cb.setCurrentIndex(j if j >= 0 else 0)
        iv = m.ivs; ev = m.evs
        for i, k in enumerate(STAT_KEYS):
            self.iv_spins[i].setValue(iv[k]); self.ev_spins[i].setValue(ev[k])
        self.cb_shiny.setChecked(m.is_shiny)
        self._refresh_sprite_and_info(m)

    def _on_shiny_toggle(self, checked: bool):
        m = getattr(self, "_current_mon", None)
        if m is not None:
            self._refresh_sprite_and_info(m, force_shiny=checked)

    def _refresh_sprite_and_info(self, m, force_shiny=None):
        shiny = self.cb_shiny.isChecked() if force_shiny is None else force_shiny
        self.sprite.setPixmap(sprite_pixmap(self.rom, m.species, shiny, size=110))
        bst = self.rom.base_stats(m.species)
        g = self.rom.gender(m.species, m.pid)
        where = ""
        if self.sel_kind == "party":
            where = f"Party slot {self.sel_index + 1}"
        elif self.sel_kind == "box":
            where = f"Box {self.sel_index[0] + 1}, slot {self.sel_index[1] + 1}"
        self.info.setText(
            f"{where}\n"
            f"Species: {self.rom.species_name(m.species)} (#{m.species})\n"
            f"Gender: {GENDER_GLYPH.get(g,'')} {g.capitalize()}    "
            f"Shiny: {'YES' if shiny else 'no'}    Egg: {m.is_egg}\n"
            f"PID: 0x{m.pid:08X}    OTID: 0x{m.otid:08X}\n"
            f"Base: {bst[0]}/{bst[1]}/{bst[2]}/{bst[4]}/{bst[3]}/{bst[5]}  "
            f"(HP/Atk/Def/SpA/SpD/Spe)")

    # --------------------------------------------------------------- apply
    def apply_current(self):
        if self.sel_kind != "party" or not isinstance(self.sel_index, int):
            QMessageBox.information(self, "Party only",
                                    "Only party Pok\u00e9mon can be edited in this version. "
                                    "Box mons are read-only (use Export .pk3).")
            return
        idx = self.sel_index
        m = self.mons[idx]
        em = EditableMon(m.raw, self.rom)
        em.set_nickname(self.ed_nick.text())
        em.set_level(self.sp_lvl.value())
        em.set_experience(self.sp_exp.value())
        em.set_friendship(self.sp_friend.value())
        em.set_ability_slot(self.cb_ability.currentData() if self.cb_ability.currentData() is not None else 0)
        em.set_held_item(self.cb_item.currentData())
        em.set_moves([cb.currentData() for cb in self.cb_moves])
        em.set_ivs({STAT_KEYS[i]: self.iv_spins[i].value() for i in range(6)})
        em.set_evs({STAT_KEYS[i]: self.ev_spins[i].value() for i in range(6)})
        sid_changed = em.force_shiny(self.cb_shiny.isChecked())
        touched = write_party_mon(self.save, idx, em.to_raw())
        _, self.mons = self.save.party(self.rom)
        self._build_party_grid()
        if sid_changed:
            self.status("Applied. Note: adjusted Secret ID to make this Pok\u00e9mon non-shiny "
                        "(was shiny by PID; Trainer ID unchanged).")
        else:
            self.status(f"Applied to Pokemon {idx + 1}; sections touched: {touched}. "
                        "Use 'Save'/'Save As' to write a file.")

    def save_as(self):
        if not self.save:
            return
        default = os.path.splitext(self.save_path)[0] + "_edited.sav" if self.save_path else "edited.sav"
        path, _ = QFileDialog.getSaveFileName(self, "Save As", default, "Save (*.sav);;All files (*)")
        if not path:
            return
        try:
            save_to_file(self.save, path)
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e)); return
        bad = Save(path).verify_checksums()
        if bad:
            QMessageBox.warning(self, "Post-save check",
                                f"Wrote file but checksums look off: {[b[0] for b in bad]}")
        self.status(f"Saved to {os.path.basename(path)}")

    def save_over(self):
        if not self.save or not self.save_path:
            return
        r = QMessageBox.question(
            self, "Overwrite save?",
            f"Overwrite the original file?\n\n{self.save_path}\n\n"
            "This cannot be undone. Consider Save As\u2026 instead.",
            QMessageBox.Yes | QMessageBox.No)
        if r != QMessageBox.Yes:
            return
        try:
            save_to_file(self.save, self.save_path)
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e)); return
        self.status(f"Overwrote {os.path.basename(self.save_path)}")

    def export_pk3_current(self):
        if self._current_mon is None:
            return
        m = self._current_mon
        sp = self.rom.species_name(m.species)
        default = f"{m.nickname.strip() or sp}_{sp}.pk3".replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(self, "Export .pk3", default, "PK3 (*.pk3);;All files (*)")
        if not path:
            return
        try:
            export_pk3(m.raw, path, level=m.level, want_shiny=m.is_shiny)
        except Exception as e:
            QMessageBox.critical(self, "Export error", str(e)); return
        self.status(f"Exported {os.path.basename(path)} (100 bytes)")


def _resource_path(name: str) -> str:
    """Return the path to a bundled resource (works in source and in the
    PyInstaller one-file build, where files are unpacked to sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Window / taskbar icon (app.ico is generated from large.png+small.png).
    for icon_name in ("app.ico", "large.png"):
        icon_path = _resource_path(icon_name)
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            break
    win = Editor()
    theme.apply_theme(app, win)
    if not app.windowIcon().isNull():
        win.setWindowIcon(app.windowIcon())
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
