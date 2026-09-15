import curses
import json
import os
import threading
import time
import a2s

HISTORY_FILE = "history.json"

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
    "mode": "nav",
    "input_buf": "",
    "server_name": "SELECT A SERVER",
    "online_str": "-/-",
    "meta_map": "",
    "meta_ping": "",
    "meta_address": "",
    "meta_status": "READY",
    "is_loading": False,
}

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

def add_to_history(name, ip, port):
    items = load_history()
    items = [i for i in items if not (i["ip"] == ip and i["port"] == port)]
    items.insert(0, {"name": name, "ip": ip, "port": port})
    items = items[:30]
    save_history_list(items)
    state["selected_idx"] = 0

def delete_current_server():
    if not state["history"]:
        return
    idx = state["selected_idx"]
    items = list(state["history"])
    if 0 <= idx < len(items):
        items.pop(idx)
        save_history_list(items)
        if state["selected_idx"] >= len(items):
            state["selected_idx"] = max(0, len(items) - 1)
        if items:
            cur = items[state["selected_idx"]]
            start_query(cur["ip"], cur["port"])
        else:
            state["server_name"] = "NO SERVERS"
            state["online_str"] = "-/-"
            state["meta_map"] = ""
            state["meta_ping"] = ""
            state["meta_address"] = ""
            state["meta_status"] = "LIST EMPTY"

def query_worker(ip, game_port):
    state["is_loading"] = True
    state["meta_status"] = f"CONNECTING TO {ip}:{game_port}..."
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
        add_to_history(found.server_name, ip, game_port)
    else:
        state["server_name"] = f"{ip}:{game_port}"
        state["online_str"] = "OFF"
        state["meta_map"] = "MAP: UNKNOWN"
        state["meta_ping"] = "PING: TIMEOUT"
        state["meta_status"] = "STATUS: NO RESPONSE"

    state["is_loading"] = False

def start_query(ip, port):
    t = threading.Thread(target=query_worker, args=(ip, port), daemon=True)
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
    stdscr.nodelay(True)
    stdscr.timeout(100)

    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)

    C_WHITE = curses.color_pair(1) | curses.A_BOLD
    C_TEXT = curses.color_pair(1)
    C_BORDER = curses.color_pair(1)
    C_ACTIVE = curses.color_pair(2) | curses.A_BOLD
    C_HINT = curses.color_pair(3)
    C_STAT = curses.color_pair(4) | curses.A_BOLD
    C_DEL = curses.color_pair(5)

    state["history"] = load_history()
    if state["history"]:
        first = state["history"][0]
        start_query(first["ip"], first["port"])

    while True:
        max_y, max_x = stdscr.getmaxyx()
        stdscr.erase()

        if max_x < 70 or max_y < 20:
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
            prompt = " [press / to find]"
            p_attr = C_TEXT

        try:
            stdscr.addstr(1 + finder_y - 1, 3, " finder ", C_WHITE)
            stdscr.addstr(1 + finder_y, 2, prompt[: recent_w - 3], p_attr)
        except curses.error:
            pass

        content_w = max_x - split_x - 3
        center_x = split_x + 2 + (content_w // 2)

        title = state["server_name"][: content_w - 4]
        title_x = max(split_x + 3, center_x - (len(title) // 2))
        try:
            stdscr.addstr(max_y // 6, title_x, title, C_WHITE)
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
        clock_start_y = max_y // 6 + 3

        for i in range(5):
            try:
                stdscr.addstr(clock_start_y + i, clock_start_x, clock_lines[i], C_WHITE)
            except curses.error:
                pass

        meta_y = clock_start_y + 7
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
            attr = C_STAT if "CONNECTING" in line else C_TEXT
            try:
                stdscr.addstr(meta_y, line_x, line[: content_w - 2], attr)
            except curses.error:
                pass
            meta_y += 1

        refresh_hint = "[r] refresh"
        hint_x = max(split_x + 3, center_x - (len(refresh_hint) // 2))
        try:
            stdscr.addstr(max_y - 2, hint_x, refresh_hint, C_HINT)
        except curses.error:
            pass

        stdscr.refresh()

        try:
            key = stdscr.getch()
        except Exception:
            key = -1

        if key == -1:
            continue

        if state["mode"] == "nav":
            if key in (ord("q"), ord("Q")):
                break
            elif key == ord("/"):
                state["mode"] = "search"
                state["input_buf"] = ""
            elif key in (curses.KEY_UP, ord("k")):
                if state["history"]:
                    if state["selected_idx"] > 0:
                        state["selected_idx"] -= 1
                    else:
                        state["selected_idx"] = len(state["history"]) - 1
            elif key in (curses.KEY_DOWN, ord("j")):
                if state["history"]:
                    if state["selected_idx"] < len(state["history"]) - 1:
                        state["selected_idx"] += 1
                    else:
                        state["selected_idx"] = 0
            elif key in (curses.KEY_DC, ord("d"), ord("D"), 330):
                delete_current_server()
            elif key in (curses.KEY_ENTER, 10, 13):
                if state["history"] and not state["is_loading"]:
                    item = state["history"][state["selected_idx"]]
                    start_query(item["ip"], item["port"])
            elif key in (ord("r"), ord("R")):
                if state["history"] and not state["is_loading"]:
                    item = state["history"][state["selected_idx"]]
                    start_query(item["ip"], item["port"])

        elif state["mode"] == "search":
            if key == 27:
                state["mode"] = "nav"
                state["input_buf"] = ""
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                state["input_buf"] = state["input_buf"][:-1]
            elif key in (curses.KEY_ENTER, 10, 13):
                raw = state["input_buf"].strip()
                if raw:
                    if ":" in raw:
                        parts = raw.split(":")
                        ip = parts[0].strip()
                        port = int(parts[1].strip()) if parts[1].strip().isdigit() else 2302
                    else:
                        ip = raw
                        port = 2302
                    start_query(ip, port)
                state["mode"] = "nav"
                state["input_buf"] = ""
                state["selected_idx"] = 0
            elif 32 <= key <= 126:
                state["input_buf"] += chr(key)

if __name__ == "__main__":
    curses.wrapper(main)