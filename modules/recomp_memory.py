"""Read-only MHGURecomp adapter for the user's overlay v1.1.1.

Runtime reference: morerokk/MHGURecomp, commit
34e753a2d37ed3d10969471a004e2355021a620b.
Guest host base: cpu.h; heap bounds: rt.h; enemy manager: net/emsync.c.
The overlay's original monster signature and relative field offsets are retained.
"""

import numpy as np
import pymem
import pymem.memory
import scanmodule

from modules.mhgu_xx import Monsters


def get_base_address(process_name):
    if process_name.lower() != 'mhgurecomp.exe':
        return None
    # This is an explicit runtime ABI constant, not an address from a session.
    return 0x10000000000


def get_data(pid, base_address, only_large_monsters, workers=2):
    import ctypes
    import logging
    import math
    import struct
    import time
    from ctypes import wintypes

    def report(message):
        print(message, flush=True)
        logging.info(message)

    empty = {'monsters': [], 'total': [0, 0]}
    guest_base = base_address
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x410, False, pid)
    if not handle:
        if time.monotonic() >= getattr(get_data, '_error_at', 0):
            report('[Recomp] Cannot read process: Windows error %s' % ctypes.get_last_error())
            get_data._error_at = time.monotonic() + 15
        return empty

    def read(address, size):
        return pymem.memory.read_bytes(handle, address, size)

    def integer(address, size=2):
        return int.from_bytes(read(address, size), 'little')

    def floating(address):
        return struct.unpack('<f', read(address, 4))[0]

    def guest_pointer(address):
        value = integer(guest_base + address, 4)
        return value if 0x08000000 <= value < 0xA8000000 and value % 4 == 0 else 0

    def readable_ranges(start, end):
        class Region(ctypes.Structure):
            _fields_ = [('BaseAddress', ctypes.c_void_p),
                        ('AllocationBase', ctypes.c_void_p),
                        ('AllocationProtect', wintypes.DWORD),
                        ('RegionSize', ctypes.c_size_t),
                        ('State', wintypes.DWORD),
                        ('Protect', wintypes.DWORD),
                        ('Type', wintypes.DWORD)]
        query = kernel.VirtualQueryEx
        query.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                          ctypes.POINTER(Region), ctypes.c_size_t]
        query.restype = ctypes.c_size_t
        info = Region()
        address = start
        while address < end and query(handle, address, ctypes.byref(info), ctypes.sizeof(info)):
            region_base = info.BaseAddress or 0
            next_address = region_base + info.RegionSize
            if next_address <= address:
                break
            if (info.State == 0x1000 and not info.Protect & 0x100
                    and info.Protect & 0xFF in (2, 4, 8, 0x20, 0x40, 0x80)):
                yield max(start, region_base), min(end, next_address)
            address = next_address

    # A unique live-data signature from the original overlay. Only fixed bytes
    # are compared; it does not depend on Switch guest pointers retaining values.
    pattern_bytes = bytes([0, 0, 1, 0, 0, 0x18, 0, 0] + [0]*12 + [0x20] + [0]*7)
    mask_bytes = bytes([0, 0, 255, 0, 0, 255, 255, 255] + [0]*12 + [255]*8)

    def valid_signature(address):
        data = read(address, 28)
        return all((b & m) == p for b, m, p in zip(data, mask_bytes, pattern_bytes))

    def valid_monster(address):
        hp_address = address + 0x17A4
        species = integer(hp_address + 0x5EA0)
        if species not in Monsters.large_monsters and species not in Monsters.small_monsters:
            return False
        hp, maximum = integer(hp_address), integer(hp_address + 4)
        return 5 < maximum <= 65535 and 0 <= hp <= maximum

    try:
        # The singleton and ten slots are cheap change detectors. They let new
        # spawns / zone transitions refresh the scan without scanning every poll.
        manager = guest_pointer(0x1A51FE0)
        slots = read(guest_base + manager + 0x1C, 40) if manager else b''
        quest = guest_pointer(0x1A8AD90)
        quest_data = guest_pointer(quest + 0xA4) if quest else 0
        quest_number = integer(guest_base + quest_data + 8, 4) if quest_data else 0
        key = (pid, manager, quest_data, quest_number)
        state = getattr(get_data, '_state', None)
        if not state or state['key'] != key:
            state = {'key': key, 'slots': slots, 'candidates': [], 'next_scan': 0,
                     'last_scan': -100, 'selected': None}
            get_data._state = state
        now = time.monotonic()
        changed = slots != state['slots']
        # Allow no more than one whole heap pass per five seconds. A full
        # periodic refresh also catches spawns outside the ten loaded slots.
        if now >= state['next_scan'] or (changed and now - state['last_scan'] >= 5):
            state['slots'] = slots
            state['last_scan'] = now
            if not manager or not any(slots):
                state['candidates'] = []
                state['next_scan'] = now + 5
                return empty
            pattern = np.frombuffer(pattern_bytes, dtype=np.uint8)
            mask = np.frombuffer(mask_bytes, dtype=np.uint8)
            candidates = set()
            scanned = 0
            chunk_size = 4 * 1024 * 1024
            # Do not query or read reserved pages: Recomp commits its guest heap
            # lazily, and a single reserved page would abort the original scan.
            for begin, end in readable_ranges(guest_base + 0x08000000, guest_base + 0xA8000000):
                for address in range(begin, end, chunk_size):
                    try:
                        data = read(address, min(chunk_size + 27, end - address))
                    except Exception:
                        continue  # mappings can change during a zone transition
                    scanned += len(data)
                    for result in scanmodule.scan_chunk(data, pattern, mask, address, 0):
                        candidate = result[1] - 0x17A4
                        try:
                            if valid_monster(candidate):
                                candidates.add(candidate)
                        except Exception:
                            continue
            state['candidates'] = sorted(candidates)
            state['next_scan'] = time.monotonic() + (30 if candidates else 5)
            report('[Recomp] Scanned %s MiB of committed heap; %s monster candidate(s).'
                   % (scanned // (1024*1024), len(candidates)))

        large, small = [], []
        for candidate in state['candidates']:
            try:
                if not valid_signature(candidate) or not valid_monster(candidate):
                    state['next_scan'] = min(state['next_scan'], now + 5)
                    continue
                pointer = candidate + 0x17A4
                species = integer(pointer + 0x5EA0)
                hp, maximum = integer(pointer), integer(pointer + 4)
                visible = integer(pointer - 0x17A0, 1) != 7 or hp != 0
                if not visible:
                    continue
                if species in Monsters.large_monsters:
                    size = floating(pointer - 0x1C0)
                    if not math.isfinite(size) or not 0.1 <= size <= 10:
                        continue
                    status = {}
                    for label, first, second in (
                            ('Poison', 0x5924, 0x5930), ('Sleep', 0x5928, 0x5926),
                            ('Paralysis', 0x593E, 0x593C), ('Dizzy', 0x5A06, 0x5A08),
                            ('Exhaust', 0x5A12, 0x5A14), ('Jump', 0x5A2A, 0x5A2C),
                            ('Blast', 0x5A3A, 0x5A38)):
                        try:
                            values = [integer(pointer + first), integer(pointer + second)]
                            if values[1] != 0xFFFF:
                                status[label] = values
                        except Exception:
                            pass  # an unreadable optional status must not hide HP
                    try:
                        rage = floating(pointer + 0x1A4)
                        if math.isfinite(rage) and 0 <= rage < 360000:
                            status['Rage'] = math.ceil(rage / 60)
                    except Exception:
                        pass
                    large.append([species, hp, maximum, int(round(size * 100, 2)), status, pointer])
                elif only_large_monsters and species in Monsters.small_monsters:
                    # Despite its v1.1.1 argument name, this flag means show small monsters.
                    small.append([species, hp, maximum])
            except Exception:
                state['next_scan'] = min(state['next_scan'], now + 5)
        large.sort(key=lambda m: m[5])
        return {'monsters': large + small, 'total': [len(large), len(small)]}
    except Exception as error:
        if time.monotonic() >= getattr(get_data, '_error_at', 0):
            report('[Recomp] Read failed (game may still be loading): %s' % error)
            get_data._error_at = time.monotonic() + 15
        return empty
    finally:
        kernel.CloseHandle(handle)


def get_monster_selected(pid, start_address, num_chunks=400, max_workers=2):
    # The emulator's selection AOB has not been validated for the native runtime.
    # The separate Recomp config shows statuses for all monsters instead.
    return 0
