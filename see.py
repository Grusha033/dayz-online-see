import curses
import json
import math
import os
import threading
import time
from datetime import datetime
import a2s

HISTORY_FILE = "history.json"
SETTINGS_FILE = "settings.json"
STATS_FILE = "stats.json"

DIGITS_TTY = {
    "0": [
        "███████",
        "██   ██",
        "██   ██",
        "██   ██",
        "███████",
    ],
    "1": [
        "     ██",
        "     ██",
        "     ██",
        "     ██",
        "     ██",
    ],
    "2": [
        "███████",
        "     ██",
        "███████",
        "██     ",
        "███████",
    ],
    "3": [
        "███████",
        "     ██",
        " ██████",
        "     ██",
        "███████",
    ],
    "4": [
        "██   ██",
        "██   ██",
        "███████",
        "     ██",
        "     ██",
    ],
    "5": [
        "███████",
        "██     ",
        "███████",
        "     ██",
        "███████",
    ],
    "6": [
        "███████",
        "██     ",
        "███████",
        "██   ██",
        "███████",
    ],
    "7": [
        "███████",
        "     ██",
        "   ██  ",
        "  ██   ",
        "  ██   ",
    ],
    "8": [
        "███████",
        "██   ██",
        "███████",
        "██   ██",
        "███████",
    ],
    "9": [
        "███████",
        "██   ██",
        "███████",
        "     ██",
        "███████",
    ],
    "/": [
        "    ██",
        "   ██ ",
        "  ██  ",
        " ██   ",
        "██    ",
    ],
    "|": [
        "    ██",
        "   ██ ",
        "  ██  ",
        " ██   ",
        "██    ",
    ],
    "-": [
        "       ",
        "       ",
        "███████",
        "       ",
        "       ",
    ],
    " ": [
        "  ",
        "  ",
        "  ",
        "  ",
        "  ",
    ],
}

state = {
    "history": [],
    "selected_idx": 0,
    "active_server": None,
    "mode": "nav",
    "input_buf": "",
    "server_name": "SELECT A SERVER",
    "online_str": "-/-",
    "meta_map": "",
    "meta_ping": "",
    "meta_address": "",
    "meta_status": "READY",
    "is_loading": False,
    "is_refreshing_current": False,
    "auto_refresh": False,
    "last_refresh_time": 0.0,
    "stats": {},
    "day_offset": 0,
    "chart_cursor_idx": -1,
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"auto_refresh": False}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"auto_refresh": False}

def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"auto_refresh": state["auto_refresh"]}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_stats():
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_stats():
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(state["stats"], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def append_online_stat(ip, port, count):
    key = f"{ip}:{port}"
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    if key not in state["stats"]:
        state["stats"][key] = {}
    if date_str not in state["stats"][key]:
        state["stats"][key][date_str] = []

    day_list = state["stats"][key][date_str]

    if day_list:
        last = day_list[-1]
        if isinstance(last, list) and len(last) == 3:
            if last[2] == count:
                last[1] = time_str
                save_stats()
                return
        elif isinstance(last, dict) and "val" in last:
            if last["val"] == count:
                day_list[-1] = [last.get("time", time_str), time_str, count]
                save_stats()
                return

    day_list.append([time_str, time_str, count])
    save_stats()

def unpack_day_records(raw_records):
    points = []
    for item in raw_records:
        if isinstance(item, list) and len(item) == 3:
            start_t, end_t, val = item
            if start_t == end_t:
                points.append({"time": start_t, "val": val})
            else:
                points.append({"time": start_t, "val": val})
                points.append({"time": end_t, "val": val})
        elif isinstance(item, dict):
            points.append({"time": item.get("time", "00:00:00"), "val": item.get("val", 0)})
    return points

def get_server_days_data(ip, port):
    key = f"{ip}:{port}"
    srv_dict = state["stats"].get(key, {})
    today_str = datetime.now().strftime("%Y-%m-%d")

    dates = sorted(srv_dict.keys())
    if today_str not in dates:
        dates.append(today_str)
        dates.sort()

    total_days = len(dates)
    if state["day_offset"] >= total_days:
        state["day_offset"] = max(0, total_days - 1)
    elif state["day_offset"] < 0:
        state["day_offset"] = 0

    cur_date = dates[total_days - 1 - state["day_offset"]]
    raw_data = srv_dict.get(cur_date, [])
    points = unpack_day_records(raw_data)
    return cur_date, points, total_days

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history_list(items):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    state["history"] = items

def add_to_history(name, ip, port, reset_cursor=False):
    items = load_history()
    items = [i for i in items if not (i["ip"] == ip and i["port"] == port)]
    items.insert(0, {"name": name, "ip": ip, "port": port})
    items = items[:30]
    save_history_list(items)
    if reset_cursor:
        state["selected_idx"] = 0

def delete_current_server():
    if not state["history"]:
        return
    idx = state["selected_idx"]
    items = list(state["history"])
    if 0 <= idx < len(items):
        del_item = items.pop(idx)
        save_history_list(items)
        if state["selected_idx"] >= len(items):
            state["selected_idx"] = max(0, len(items) - 1)
        state["day_offset"] = 0
        state["chart_cursor_idx"] = -1
        state["auto_refresh"] = False
        save_settings()
        if items:
            cur = items[0]
            state["selected_idx"] = 0
            state["active_server"] = {"ip": cur["ip"], "port": cur["port"]}
            start_query(cur["ip"], cur["port"], is_switch=True)
        else:
            state["active_server"] = None
            state["server_name"] = "NO SERVERS"
            state["online_str"] = "-/-"
            state["meta_map"] = ""
            state["meta_ping"] = ""
            state["meta_address"] = ""
            state["meta_status"] = "LIST EMPTY"

def query_worker(ip, game_port, is_switch):
    if is_switch:
        state["is_loading"] = True
        state["is_refreshing_current"] = False
        state["meta_status"] = f"CONNECTING TO {ip}:{game_port}..."
    else:
        state["is_refreshing_current"] = True
        state["meta_status"] = "STATUS: UPDATING INFO..."

    state["meta_address"] = f"ADDRESS: {ip}:{game_port}"
    
    ports = [game_port + 1, game_port, 27016, 27015]
    found = None

    for p in ports:
        try:
            found = a2s.info((ip, p), timeout=1.8)
            break
        except Exception:
            continue

    if found:
        state["server_name"] = found.server_name.upper()
        state["online_str"] = f"{found.player_count}/{found.max_players}"
        state["meta_map"] = f"MAP: {found.map_name.upper()}"
        state["meta_ping"] = f"PING: {round(found.ping * 1000)} MS"
        state["meta_status"] = "STATUS: ONLINE"
        add_to_history(found.server_name, ip, game_port, reset_cursor=is_switch)
        append_online_stat(ip, game_port, found.player_count)
    else:
        if is_switch:
            state["server_name"] = f"{ip}:{game_port}"
            state["online_str"] = "OFF"
            state["meta_map"] = "MAP: UNKNOWN"
        state["meta_ping"] = "PING: TIMEOUT"
        state["meta_status"] = "STATUS: NO RESPONSE"

    state["is_loading"] = False
    state["is_refreshing_current"] = False
    state["last_refresh_time"] = time.time()

def start_query(ip, port, is_switch=False):
    t = threading.Thread(target=query_worker, args=(ip, port, is_switch), daemon=True)
    t.start()

def draw_round_box(stdscr, y, x, h, w, attr):
    if h < 2 or w < 2:
        return
    try:
        stdscr.addstr(y, x, "╭", attr)
        stdscr.addstr(y, x + w - 1, "╮", attr)
        stdscr.addstr(y + h - 1, x, "╰", attr)
        stdscr.addstr(y + h - 1, x + w - 1, "╯", attr)
        
        for col in range(x + 1, x + w - 1):
            stdscr.addstr(y, col, "─", attr)
            stdscr.addstr(y + h - 1, col, "─", attr)
            
        for row in range(y + 1, y + h - 1):
            stdscr.addstr(row, x, "│", attr)
            stdscr.addstr(row, x + w - 1, "│", attr)
    except curses.error:
        pass

def main(stdscr):
    curses.use_default_colors()
    curses.curs_set(0)
    curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
    stdscr.nodelay(True)
    stdscr.timeout(100)

    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)
    curses.init_pair(7, curses.COLOR_BLUE, -1)

    C_WHITE = curses.color_pair(1) | curses.A_BOLD
    C_TEXT = curses.color_pair(1)
    C_BORDER = curses.color_pair(1)
    C_ACTIVE = curses.color_pair(2) | curses.A_BOLD
    C_HINT = curses.color_pair(3)
    C_STAT = curses.color_pair(4) | curses.A_BOLD
    C_DEL = curses.color_pair(5)
    C_ON = curses.color_pair(3) | curses.A_BOLD
    C_OFF = curses.color_pair(5) | curses.A_BOLD
    C_SCOPE_TRACE = curses.color_pair(3) | curses.A_BOLD
    C_SCOPE_GRID = curses.color_pair(7)
    C_HIGHLIGHT = curses.color_pair(4) | curses.A_BOLD

    cfg = load_settings()
    state["auto_refresh"] = cfg.get("auto_refresh", False)
    state["stats"] = load_stats()
    state["history"] = load_history()
    state["last_refresh_time"] = time.time()

    if state["history"]:
        first = state["history"][0]
        state["selected_idx"] = 0
        state["active_server"] = {"ip": first["ip"], "port": first["port"]}
        start_query(first["ip"], first["port"], is_switch=True)

    click_points = []

    while True:
        now_ts = time.time()
        if (
            state["auto_refresh"]
            and not state["is_loading"]
            and not state["is_refreshing_current"]
            and state["active_server"]
            and (now_ts - state["last_refresh_time"] >= 10.0)
        ):
            start_query(state["active_server"]["ip"], state["active_server"]["port"], is_switch=False)

        max_y, max_x = stdscr.getmaxyx()
        stdscr.erase()

        if max_x < 70 or max_y < 26:
            stdscr.addstr(0, 0, "Terminal window too small.", C_WHITE)
            stdscr.refresh()
            time.sleep(0.1)
            continue

        split_x = max(28, int(max_x * 0.32))

        for y in range(max_y):
            try:
                stdscr.addstr(y, split_x + 1, "│", C_BORDER)
            except curses.error:
                pass

        sidebar_w = split_x - 1
        finder_h = 3
        recent_h = max_y - finder_h - 3
        recent_w = sidebar_w

        draw_round_box(stdscr, 1, 1, recent_h, recent_w, C_BORDER)
        try:
            stdscr.addstr(1, 3, " Recent ", C_WHITE)
        except curses.error:
            pass

        del_hint = "[del] remove"
        if recent_w > len(del_hint) + 4:
            try:
                stdscr.addstr(recent_h, recent_w - len(del_hint) - 2, f" {del_hint} ", C_DEL)
            except curses.error:
                pass

        max_history_rows = recent_h - 2
        for idx, item in enumerate(state["history"][:max_history_rows]):
            y = 2 + idx
            name_cut = item["name"][: recent_w - 5]
            if idx == state["selected_idx"] and state["mode"] == "nav":
                attr = C_ACTIVE
                prefix = "▸ "
            else:
                attr = C_TEXT
                prefix = "  "

            try:
                stdscr.addstr(y, 2, (prefix + name_cut)[: recent_w - 3], attr)
            except curses.error:
                pass

        finder_y = recent_h + 2
        draw_round_box(stdscr, 1 + finder_y - 1, 1, finder_h, recent_w, C_BORDER)

        if state["mode"] == "search":
            prompt = f" {state['input_buf']}█"
            p_attr = C_WHITE
        else:
            prompt = " [press /]"
            p_attr = C_TEXT

        try:
            stdscr.addstr(1 + finder_y - 1, 3, " finder ", C_WHITE)
            stdscr.addstr(1 + finder_y, 2, prompt[: recent_w - 3], p_attr)
        except curses.error:
            pass

        content_w = max_x - split_x - 3
        center_x = split_x + 2 + (content_w // 2)

        if state["is_loading"]:
            loading_msg = state["meta_status"]
            l_x = max(split_x + 3, center_x - (len(loading_msg) // 2))
            l_y = max_y // 3
            try:
                stdscr.addstr(l_y, l_x, loading_msg[: content_w - 2], C_STAT)
            except curses.error:
                pass
            click_points = []
        else:
            title = state["server_name"][: content_w - 4]
            title_x = max(split_x + 3, center_x - (len(title) // 2))
            try:
                stdscr.addstr(2, title_x, title, C_WHITE)
            except curses.error:
                pass

            clock_lines = ["", "", "", "", ""]
            clean_str = state["online_str"].replace(" ", "")
            for char in clean_str:
                glyph = DIGITS_TTY.get(char, DIGITS_TTY["-"])
                for i in range(5):
                    clock_lines[i] += glyph[i] + " "

            clock_w = len(clock_lines[0])
            clock_start_x = max(split_x + 3, center_x - (clock_w // 2))
            clock_start_y = 4

            for i in range(5):
                try:
                    stdscr.addstr(clock_start_y + i, clock_start_x, clock_lines[i], C_WHITE)
                except curses.error:
                    pass

            meta_y = clock_start_y + 6
            meta_items = [
                state["meta_map"],
                state["meta_ping"],
                state["meta_address"],
                state["meta_status"],
            ]

            for line in meta_items:
                if not line:
                    continue
                line_x = max(split_x + 3, center_x - (len(line) // 2))
                attr = C_STAT if ("CONNECTING" in line or "UPDATING" in line) else C_TEXT
                try:
                    stdscr.addstr(meta_y, line_x, line[: content_w - 2], attr)
                except curses.error:
                    pass
                meta_y += 1

            btn_y = meta_y + 1
            part_ref = "[r] refresh"
            part_sep = "   "
            part_auto_lbl = "[a] auto: "
            part_status = "ON (10s)" if state["auto_refresh"] else "OFF"
            total_len = len(part_ref) + len(part_sep) + len(part_auto_lbl) + len(part_status)
            start_x = max(split_x + 3, center_x - (total_len // 2))

            try:
                stdscr.addstr(btn_y, start_x, part_ref, C_HINT)
                cx = start_x + len(part_ref)
                stdscr.addstr(btn_y, cx, part_sep, C_TEXT)
                cx += len(part_sep)
                stdscr.addstr(btn_y, cx, part_auto_lbl, C_TEXT)
                cx += len(part_auto_lbl)
                stdscr.addstr(btn_y, cx, part_status, C_ON if state["auto_refresh"] else C_OFF)
            except curses.error:
                pass

            if state["active_server"]:
                cur_date, day_records, total_days = get_server_days_data(
                    state["active_server"]["ip"], state["active_server"]["port"]
                )
            else:
                cur_date = datetime.now().strftime("%Y-%m-%d")
                day_records, total_days = [], 1

            is_today = (state["day_offset"] == 0)
            nav_arrow_l = "◄ " if state["day_offset"] < total_days - 1 else "  "
            nav_arrow_r = " ►" if state["day_offset"] > 0 else "  "
            date_tag = "TODAY" if is_today else "PAST"
            hdr_date = f"{nav_arrow_l}{cur_date} ({date_tag}){nav_arrow_r}"

            chart_margin_top = btn_y + 2
            bottom_limit = max_y - 2
            plot_avail_h = max(5, min(10, bottom_limit - chart_margin_top - 2))

            chart_w = max(18, min(content_w - 6, 56))
            plot_w = chart_w
            chart_x = max(split_x + 3, center_x - (chart_w // 2))

            h_x = max(split_x + 3, center_x - (len(hdr_date) // 2))
            try:
                stdscr.addstr(chart_margin_top, h_x, hdr_date[:content_w - 2], C_WHITE)
            except curses.error:
                pass

            plot_top_y = chart_margin_top + 1
            plot_records = day_records[-plot_w:] if day_records else []

            if plot_records:
                vals = [r["val"] for r in plot_records]
                v_max = max(vals)
                v_min = min(vals)
                if v_max == v_min:
                    top_val = v_max + 5
                    bot_val = max(0, v_min - 5)
                else:
                    top_val = v_max + max(1, int((v_max - v_min) * 0.1))
                    bot_val = max(0, v_min - max(1, int((v_max - v_min) * 0.1)))
            else:
                top_val, bot_val = 10, 0

            val_range = max(1, top_val - bot_val)

            for row in range(plot_avail_h):
                cy = plot_top_y + row
                for col in range(plot_w):
                    grid_char = "·" if (col % 6 == 0 and row % 2 == 0) else " "
                    try:
                        stdscr.addstr(cy, chart_x + col, grid_char, C_SCOPE_GRID)
                    except curses.error:
                        pass

            click_points = []
            cur_pt = None

            if plot_records:
                if state["chart_cursor_idx"] >= len(plot_records):
                    state["chart_cursor_idx"] = len(plot_records) - 1

                pt_cols = []
                for i, r in enumerate(plot_records):
                    cx = chart_x + (plot_w - len(plot_records)) + i
                    norm = (r["val"] - bot_val) / val_range
                    norm = max(0.0, min(1.0, norm))
                    cy = plot_top_y + int(round((1.0 - norm) * (plot_avail_h - 1)))
                    pt_cols.append((cx, cy))
                    click_points.append((cx, cy, i))

                for i in range(len(pt_cols)):
                    cx, cy = pt_cols[i]
                    is_selected = (i == state["chart_cursor_idx"])
                    dot_char = "◈" if is_selected else "●"
                    dot_color = C_HIGHLIGHT if is_selected else C_SCOPE_TRACE

                    try:
                        stdscr.addstr(cy, cx, dot_char, dot_color)
                    except curses.error:
                        pass

                    if i < len(pt_cols) - 1:
                        nx, ny = pt_cols[i + 1]
                        if nx - cx == 1 and abs(ny - cy) > 1:
                            step = 1 if ny > cy else -1
                            for mid_y in range(cy + step, ny, step):
                                try:
                                    stdscr.addstr(mid_y, cx, "·", C_SCOPE_TRACE)
                                except curses.error:
                                    pass

                if 0 <= state["chart_cursor_idx"] < len(plot_records):
                    cur_pt = (plot_records[state["chart_cursor_idx"]], pt_cols[state["chart_cursor_idx"]])
            else:
                state["chart_cursor_idx"] = -1
                empty_msg = "[ NO RECORDS FOR THIS DAY ]"
                try:
                    stdscr.addstr(
                        plot_top_y + plot_avail_h // 2,
                        chart_x + max(0, (plot_w - len(empty_msg)) // 2),
                        empty_msg,
                        C_TEXT,
                    )
                except curses.error:
                    pass

            if cur_pt:
                rec, (px, py) = cur_pt
                time_part = rec['time'][:5]
                val_part = f"{rec['val']} "
                total_tip_len = len(time_part) + 1 + len(val_part) + 1
                tip_y = py - 1 if py - 1 >= plot_top_y else py + 1
                tip_x = max(chart_x, min(px - (total_tip_len // 2), chart_x + chart_w - total_tip_len))
                try:
                    stdscr.addstr(tip_y, tip_x, f"{time_part} {val_part}", C_WHITE)
                    stdscr.addstr(tip_y, tip_x + len(time_part) + 1 + len(val_part), "", C_ON)
                except curses.error:
                    pass

            time_line_y = plot_top_y + plot_avail_h
            if plot_records:
                t_first = plot_records[0]["time"][:5]
                t_last = plot_records[-1]["time"][:5]
                start_pos = chart_x + (plot_w - len(plot_records))
                end_pos = chart_x + plot_w - len(t_last)
                try:
                    stdscr.addstr(time_line_y, start_pos, t_first, C_TEXT)
                    if end_pos > start_pos + len(t_first) + 1:
                        stdscr.addstr(time_line_y, end_pos, t_last, C_TEXT)
                except curses.error:
                    pass
            else:
                try:
                    stdscr.addstr(time_line_y, chart_x, "00:00", C_TEXT)
                    stdscr.addstr(time_line_y, chart_x + plot_w - 5, "23:59", C_TEXT)
                except curses.error:
                    pass

        stdscr.refresh()

        try:
            key_raw = stdscr.get_wch()
        except Exception:
            key_raw = None

        if key_raw is None:
            continue

        if isinstance(key_raw, str):
            ch = key_raw
            code = ord(key_raw)
        else:
            code = key_raw
            ch = chr(code) if 0 <= code <= 0x10FFFF else ""

        if code == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED | curses.BUTTON1_DOUBLE_CLICKED):
                    hit = None
                    for cx, cy, idx in click_points:
                        if abs(mx - cx) <= 1 and abs(my - cy) <= 1:
                            hit = idx
                            break
                    if hit is not None:
                        state["chart_cursor_idx"] = hit
                    else:
                        state["chart_cursor_idx"] = -1
            except curses.error:
                pass
            continue

        if state["mode"] == "nav":
            if ch in ("q", "Q", "й", "Й"):
                break
            elif ch in ("/", ".", "ю", "Ю"):
                state["mode"] = "search"
                state["input_buf"] = ""
            elif code in (curses.KEY_UP,) or ch in ("k", "K", "л", "Л"):
                if state["history"]:
                    if state["selected_idx"] > 0:
                        state["selected_idx"] -= 1
                    else:
                        state["selected_idx"] = len(state["history"]) - 1
            elif code in (curses.KEY_DOWN,) or ch in ("j", "J", "о", "О"):
                if state["history"]:
                    if state["selected_idx"] < len(state["history"]) - 1:
                        state["selected_idx"] += 1
                    else:
                        state["selected_idx"] = 0
            elif code in (curses.KEY_LEFT,) or ch in ("h", "H", "р", "Р"):
                state["day_offset"] += 1
                state["chart_cursor_idx"] = -1
            elif code in (curses.KEY_RIGHT,) or ch in ("l", "L", "д", "Д"):
                if state["day_offset"] > 0:
                    state["day_offset"] -= 1
                    state["chart_cursor_idx"] = -1
            elif code in (curses.KEY_DC, 330) or ch in ("d", "D", "в", "В"):
                delete_current_server()
            elif code in (curses.KEY_ENTER, 10, 13):
                if state["history"] and not state["is_loading"]:
                    item = state["history"][state["selected_idx"]]
                    cur_active = state["active_server"]
                    is_new_server = not cur_active or not (cur_active["ip"] == item["ip"] and cur_active["port"] == item["port"])
                    if is_new_server:
                        state["auto_refresh"] = False
                        save_settings()
                    state["selected_idx"] = 0
                    state["active_server"] = {"ip": item["ip"], "port": item["port"]}
                    state["day_offset"] = 0
                    state["chart_cursor_idx"] = -1
                    start_query(item["ip"], item["port"], is_switch=is_new_server)
            elif ch in ("r", "R", "к", "К"):
                if state["active_server"] and not state["is_loading"] and not state["is_refreshing_current"]:
                    start_query(state["active_server"]["ip"], state["active_server"]["port"], is_switch=False)
            elif ch in ("a", "A", "ф", "Ф"):
                state["auto_refresh"] = not state["auto_refresh"]
                save_settings()
                if state["auto_refresh"]:
                    state["last_refresh_time"] = time.time()
            elif ch in ("[", "х", "Х"):
                if plot_records:
                    if state["chart_cursor_idx"] == -1:
                        state["chart_cursor_idx"] = len(plot_records) - 1
                    elif state["chart_cursor_idx"] > 0:
                        state["chart_cursor_idx"] -= 1
            elif ch in ("]", "ъ", "Ъ"):
                if plot_records:
                    if state["chart_cursor_idx"] == -1:
                        state["chart_cursor_idx"] = 0
                    elif state["chart_cursor_idx"] < len(plot_records) - 1:
                        state["chart_cursor_idx"] += 1

        elif state["mode"] == "search":
            if code == 27:
                state["mode"] = "nav"
                state["input_buf"] = ""
            elif code in (curses.KEY_BACKSPACE, 127, 8) or ch == "\b":
                state["input_buf"] = state["input_buf"][:-1]
            elif code in (curses.KEY_ENTER, 10, 13):
                raw = state["input_buf"].strip()
                if raw:
                    if ":" in raw:
                        parts = raw.split(":")
                        ip = parts[0].strip()
                        port = int(parts[1].strip()) if parts[1].strip().isdigit() else 2302
                    else:
                        ip = raw
                        port = 2302
                    state["auto_refresh"] = False
                    save_settings()
                    state["selected_idx"] = 0
                    state["active_server"] = {"ip": ip, "port": port}
                    state["day_offset"] = 0
                    state["chart_cursor_idx"] = -1
                    start_query(ip, port, is_switch=True)
                state["mode"] = "nav"
                state["input_buf"] = ""
            elif ch and ch.isprintable():
                state["input_buf"] += ch

if __name__ == "__main__":
    curses.wrapper(main)