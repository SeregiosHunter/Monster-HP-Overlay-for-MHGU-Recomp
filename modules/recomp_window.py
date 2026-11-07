"""Window adapters for the separate MHGURecomp overlay build."""

import win32gui

from modules.utils import log_timer


def get_window(self, ahk, target_window_title, not_responding_title, yuzu_target_window_title):
    self.is_xx = False
    win = ahk.find_window(title='ahk_exe mhgurecomp.exe')
    if win and win.process_name.lower() == 'mhgurecomp.exe':
        return win
    return None


def update_position(self, ahk, layout, target_window_title, not_responding_title, yuzu_target_window_title):
    try:
        win = self.get_window(ahk, target_window_title, not_responding_title, yuzu_target_window_title)
        if win is None:
            self.is_open_window = False
            return
        # SDL has no emulator menu/tool/status bars. Anchor to its client area.
        left, top, right, bottom = win32gui.GetClientRect(win.id)
        screen_x, screen_y = win32gui.ClientToScreen(win.id, (left, top))
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0 or win32gui.IsIconic(win.id):
            self.is_open_window = False
            return
        process_changed = self.pid is not None and self.pid != win.pid
        self.process_name = win.process_name
        self.pid = win.pid
        self.is_ryujinx = False
        if process_changed:
            self.base_address = None
            self.is_open_window = False
            return
        monitor = win.get_monitor()
        scale = monitor.scale_factor
        self.is_borderless = width >= monitor.size[0] and height >= monitor.size[1] - 1
        margin = round(6 * scale)
        layout.setContentsMargins(margin, margin, margin, margin)
        self.resize(self.minimumSizeHint())
        offset_x = screen_x + (width - self.geometry().width()) * self.x / 100 + self.fix_offset['x']
        offset_y = screen_y + (height - self.geometry().height()) * self.y / 100 + self.fix_offset['y']
        self.move(round(offset_x), round(offset_y))
        self.is_open_window = True
    except Exception as error:
        self.is_open_window = False
        if self.debugger:
            log_timer(self.pt, [dict(type='error', msg='Recomp window error: %s' % error)])
