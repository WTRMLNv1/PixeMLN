# functions/json_manager.py
# Manages JSON file read/write and a few custom operations.

#───imports───#
import json
import os
import re
import sys
from pathlib import Path

try:
    from .dateUtils import check_date, convert_date_format
except ImportError:
    # Allow running this file directly: add project root to sys.path
    _project_root = Path(__file__).resolve().parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    from helpers.dateUtils import check_date, convert_date_format

#───constants───#
BASE_DIR = str(Path(__file__).resolve().parent.parent)

DEFAULT_GRAPH_COLOR = "green"

def _resolve_current_data_paths(file_path=None):
    if file_path:
        return [file_path]
    # Prefer capitalised 'Data' (canonical); fall back to lowercase for legacy setups
    for folder in ("Data", "data"):
        candidate = Path(BASE_DIR) / folder / "current_data.json"
        if candidate.exists():
            return [str(candidate)]
    # Default to canonical path even if not yet created
    return [str(Path(BASE_DIR) / "Data" / "current_data.json")]

#────────────generic functions────────────#
#───function <ensure_json_file>───#
def ensure_json_file(file_path, default_data=None):
    """Ensure the JSON file exists; if not, create it with an empty dict."""
    if default_data is None:
        default_data = {}
    try:
        with open(file_path, 'r') as f:
            json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(file_path, 'w') as f:
            json.dump(default_data, f)


#───function <read_json>───#
def read_json(file_path):
    """Read and return the contents of a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


#───function <write_json>───#
def write_json(file_path, data):
    """Write data to a JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


#──────────────────────────────────────────#

#────────────custom functions────────────#
#───data structure───#
"""
Data Structure for different files (current project layout):

1. creds.json
[
    {"username": "token"},
    {"otheruser": "token2"}
]

2. theme.json
{
    "accent_color": "#HEX",
    "hover_color": "#HEX",
    "text_color": "#HEX"
}

3. pixels.json
[
    {
        "username": [
            {
                "graph_id": "python",
                "graph_type": "int",
                "graph_color": "green",
                "pixels": [{"DDMMYYYY": 1}, {"DDMMYYYY": 2}]
            },
            {
                "graph_id": "sleep",
                "graph_type": "flt",
                "graph_color": "sky",
                "pixels": [{"DDMMYYYY": 7.5}]
            }
        ]
    }
]

All helper functions below read/write using the above shapes.
"""
#──────
def get_all_users(file_path=os.path.join(BASE_DIR, "Data", "creds.json")):
    """Get all usernames from creds.json (list of {username: token})."""
    ensure_json_file(file_path, [])
    data = read_json(file_path)
    users = []
    for user_entry in data:
        if isinstance(user_entry, dict):
            users.extend(user_entry.keys())
    return users

#──────
def get_current_user(file_path=os.path.join(BASE_DIR, "Data", "current_data.json")):
    ensure_json_file(file_path)
    data = read_json(file_path)
    current_user = data['current_user']
    return current_user

#──────
def get_token(username, file_path=os.path.join(BASE_DIR, "Data", "creds.json")):
    """Return token string for a username from creds.json, or None."""
    ensure_json_file(file_path, [])
    data = read_json(file_path)
    for user_entry in data:
        if isinstance(user_entry, dict) and username in user_entry:
            return user_entry.get(username)
    return None

#──────
def get_user_graphs(username, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Get all graphs for a given username from pixels.json.
    Returns a list of dicts like [{graph_id: [date_quantity, ...]}, ...]."""
    ensure_json_file(file_path, [])
    data = read_json(file_path)
    for user_entry in data:
        if isinstance(user_entry, dict) and user_entry.get(username):
            return user_entry[username]
    return []

#──────
def get_user_graph_names(username, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Return list of graph IDs for a username from pixels.json."""
    data = get_user_graphs(username, file_path)
    graph_names = []
    for graph in data:
        if isinstance(graph, dict):
            gid = graph.get('graph_id')
            if gid:
                graph_names.append(gid)
    return graph_names

#──────
def get_all_graph_names(file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Return list of graph IDs for the current user."""
    try:
        current_user = get_current_user()
    except Exception:
        return []
    if not current_user:
        return []
    return get_user_graph_names(current_user, file_path)

#──────
def get_graph_type(username, graph_id, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Return the declared graph_type for a user's graph from pixels.json.
    Returns the string value (e.g. 'int' or 'flt'), or None if not found."""
    graphs = get_user_graphs(username, file_path)
    for graph in graphs:
        if not isinstance(graph, dict):
            continue
        if graph.get('graph_id') == graph_id:
            return graph.get('graph_type')
    return None

#──────
def get_graph_color(username, graph_id, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Return the graph_color for a user's graph from pixels.json.
    Falls back to DEFAULT_GRAPH_COLOR if the field is missing (existing graphs)."""
    graphs = get_user_graphs(username, file_path)
    for graph in graphs:
        if not isinstance(graph, dict):
            continue
        if graph.get('graph_id') == graph_id:
            return graph.get('graph_color', DEFAULT_GRAPH_COLOR)
    return DEFAULT_GRAPH_COLOR

#──────
def get_theme(file_path=os.path.join(BASE_DIR, "Data", "themes.json")):
    """Gets a dictionary with accent color, hover color, and text color from theme.json."""
    default_theme = {
        "accent_color": "#5BF69F",
        "hover_color": "#48C47F",
        "text_color": "#FFFFFF"
    }
    ensure_json_file(file_path, default_theme)
    return read_json(file_path)

#──────
def get_pixel_dict(username, graph_id, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Get pixel data for a specific user and graph as {'YYYYMMDD': quantity}."""
    ensure_json_file(file_path, [])
    data = read_json(file_path)
    pixel_dict = {}

    for user_entry in data:
        if not (isinstance(user_entry, dict) and user_entry.get(username)):
            continue

        for graph in user_entry[username]:
            if not (isinstance(graph, dict) and graph.get('graph_id') == graph_id):
                continue

            for p in graph.get('pixels', []):
                try:
                    # New format: {"DDMMYYYY": quantity}
                    if isinstance(p, dict):
                        for date_str, quant in p.items():
                            normal_date = convert_date_format(str(date_str))
                            if normal_date is not None:
                                pixel_dict[normal_date] = quant
                        continue

                    # Backward compatibility: "DDMMYYYY_quantity"
                    if isinstance(p, str):
                        date_str, quant = p.split("_", 1)
                        normal_date = convert_date_format(date_str)
                        if normal_date is not None:
                            pixel_dict[normal_date] = quant
                        continue
                except Exception as e:
                    print("pixel parse failed:", p, e)
                    continue

            return pixel_dict

    return pixel_dict

#──────
def _num_pixels(username, graph_id, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Return the number of pixel entries for a specific user and graph."""
    ensure_json_file(file_path, [])
    data = read_json(file_path)
    for user_entry in data:
        if isinstance(user_entry, dict) and user_entry.get(username):
            for graph in user_entry[username]:
                if isinstance(graph, dict) and graph.get('graph_id') == graph_id:
                    return len(graph.get('pixels', []))
    return 0

#──────
def check_pixel_conflict(username, graph_id, date_str, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Check whether a pixel already exists for username+graph_id+date_str (DDMMYYYY).

    Returns:
        {"ok": True}
        {"ok": False, "date": date_str, "value": existing_value}
    """
    ensure_json_file(file_path, [])
    data = read_json(file_path)

    for user_entry in data:
        if not (isinstance(user_entry, dict) and username in user_entry):
            continue
        for graph in user_entry[username]:
            if not (isinstance(graph, dict) and graph.get("graph_id") == graph_id):
                continue
            for p in graph.get("pixels", []):
                # New format: {"DDMMYYYY": value}
                if isinstance(p, dict) and date_str in p:
                    return {"ok": False, "date": date_str, "value": p.get(date_str)}

                # Backward compatibility: "DDMMYYYY_value"
                if isinstance(p, str):
                    try:
                        d, v = p.split("_", 1)
                        if d == date_str:
                            return {"ok": False, "date": date_str, "value": v}
                    except Exception:
                        continue
            return {"ok": True}
    return {"ok": True}

# ──────
def _coerce_number(value):
    """Best-effort numeric coercion preserving ints when possible."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        if "." in s:
            f = float(s)
            return int(f) if f.is_integer() else f
        return int(s)
    except Exception:
        return None

# ──────
def resolve_pixel_conflict(username, graph_id, date_str, quantity, action, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Resolve an existing pixel conflict for a date using action in {'combine','replace'}."""
    if action not in {"combine", "replace"}:
        return False

    ensure_json_file(file_path, [])
    data = read_json(file_path)

    for user_entry in data:
        if not (isinstance(user_entry, dict) and username in user_entry):
            continue
        for graph in user_entry[username]:
            if not (isinstance(graph, dict) and graph.get("graph_id") == graph_id):
                continue
            pixels = graph.setdefault("pixels", [])
            for i, p in enumerate(pixels):
                # New format
                if isinstance(p, dict) and date_str in p:
                    old_value = p.get(date_str)
                    if action == "replace":
                        p[date_str] = quantity
                    else:
                        old_num = _coerce_number(old_value)
                        new_num = _coerce_number(quantity)
                        if old_num is None or new_num is None:
                            return False
                        combined = old_num + new_num
                        p[date_str] = int(combined) if isinstance(combined, float) and combined.is_integer() else combined
                    write_json(file_path, data)
                    return True

                # Backward compatibility input
                if isinstance(p, str):
                    try:
                        d, v = p.split("_", 1)
                    except Exception:
                        continue
                    if d != date_str:
                        continue
                    if action == "replace":
                        pixels[i] = {date_str: quantity}
                    else:
                        old_num = _coerce_number(v)
                        new_num = _coerce_number(quantity)
                        if old_num is None or new_num is None:
                            return False
                        combined = old_num + new_num
                        combined = int(combined) if isinstance(combined, float) and combined.is_integer() else combined
                        pixels[i] = {date_str: combined}
                    write_json(file_path, data)
                    return True
            return False
    return False

def get_current_graph(file=None):
    paths = _resolve_current_data_paths(file)
    ensure_json_file(file_path=paths[0])
    data = read_json(paths[0])
    current_graph = data["display_graph"]
    current_type = data["display_type"]
    return {"graph": current_graph, "type": current_type}

#────────────────────────────── edit functions ──────────────────────────────#
# The below functions modify the JSON files based on user actions. They typically read the current data, update the relevant fields, and write it back.

# ──────
def change_graph_type(display_type, file_path=None):
    """Update display_type in current_data.json."""
    paths = _resolve_current_data_paths(file_path)
    for p in paths:
        ensure_json_file(file_path=p)
        data = read_json(p)
        data["display_type"] = display_type
        write_json(p, data)

# ──────
def change_display_graph(graph_id, file_path=None):
    """Update display_graph in current_data.json."""
    paths = _resolve_current_data_paths(file_path)
    for p in paths:
        ensure_json_file(file_path=p)
        data = read_json(p)
        data["display_graph"] = graph_id
        write_json(p, data)

# ──────
def change_current_user(username, file_path=None):
    """Update current_user in current_data.json."""
    paths = _resolve_current_data_paths(file_path)
    for p in paths:
        ensure_json_file(file_path=p)
        data = read_json(p)
        data["current_user"] = username
        write_json(p, data)

# ──────
def create_account(username, token="", file_path=os.path.join(BASE_DIR, "Data", "creds.json")):
    """Create a new account in creds.json.

    Returns:
        (ok, message): tuple[bool, str]
    """
    name = str(username or "").strip()
    if not name:
        return False, "Username cannot be empty"
    if not re.fullmatch(r"[A-Za-z.0-9_-]+", name):
        return False, "Only letters, numbers, '-', '_', '.'"

    ensure_json_file(file_path, [])
    data = read_json(file_path)
    if not isinstance(data, list):
        data = []

    for entry in data:
        if isinstance(entry, dict) and name in entry:
            return False, "Username already exists"

    data.append({name: str(token or "")})
    write_json(file_path, data)
    return True, "Account created"

# ——————
def rename_account(
    old_username,
    new_username,
    creds_file=os.path.join(BASE_DIR, "Data", "creds.json"),
    pixels_file=os.path.join(BASE_DIR, "Data", "pixels.json"),
    current_data_file=None,
):
    """Rename an existing account and propagate references."""
    old_name = str(old_username or "").strip()
    new_name = str(new_username or "").strip()

    if not old_name:
        return False, "Select an account first"
    if not new_name:
        return False, "Username cannot be empty"
    if not re.fullmatch(r"[A-Za-z.0-9_-]+", new_name):
        return False, "Only letters, numbers, '-', '_', '.'"
    if old_name == new_name:
        return False, "No changes to save"

    ensure_json_file(creds_file, [])
    creds = read_json(creds_file)
    if not isinstance(creds, list):
        creds = []

    old_idx = None
    old_token = ""
    for i, entry in enumerate(creds):
        if not isinstance(entry, dict):
            continue
        if old_name in entry:
            old_idx = i
            old_token = str(entry.get(old_name, ""))
        if new_name in entry:
            return False, "Username already exists"

    if old_idx is None:
        return False, "Selected account not found"

    creds[old_idx] = {new_name: old_token}
    write_json(creds_file, creds)

    ensure_json_file(pixels_file, [])
    pixels = read_json(pixels_file)
    if not isinstance(pixels, list):
        pixels = []
    for i, entry in enumerate(pixels):
        if not isinstance(entry, dict) or old_name not in entry:
            continue
        pixels[i] = {new_name: entry.get(old_name, [])}
        break
    write_json(pixels_file, pixels)

    paths = _resolve_current_data_paths(current_data_file)
    for p in paths:
        ensure_json_file(file_path=p)
        current_data = read_json(p)
        if current_data.get("current_user") == old_name:
            current_data["current_user"] = new_name
            write_json(p, current_data)

    return True, "Account renamed"

# ——————
def delete_account(
    username,
    creds_file=os.path.join(BASE_DIR, "Data", "creds.json"),
    pixels_file=os.path.join(BASE_DIR, "Data", "pixels.json"),
    current_data_file=None,
):
    """Delete an account and update current user if needed."""
    name = str(username or "").strip()
    if not name:
        return False, "Select an account first"

    ensure_json_file(creds_file, [])
    creds = read_json(creds_file)
    if not isinstance(creds, list):
        creds = []

    existing_users = []
    for entry in creds:
        if isinstance(entry, dict):
            existing_users.extend(entry.keys())

    if name not in existing_users:
        return False, "Selected account not found"
    if len(existing_users) <= 1:
        return False, "Cannot delete the last account"

    updated_creds = []
    for entry in creds:
        if isinstance(entry, dict) and name in entry:
            continue
        updated_creds.append(entry)
    write_json(creds_file, updated_creds)

    remaining_users = []
    for entry in updated_creds:
        if isinstance(entry, dict):
            remaining_users.extend(entry.keys())

    ensure_json_file(pixels_file, [])
    pixels = read_json(pixels_file)
    if not isinstance(pixels, list):
        pixels = []
    updated_pixels = []
    for entry in pixels:
        if isinstance(entry, dict) and name in entry:
            continue
        updated_pixels.append(entry)
    write_json(pixels_file, updated_pixels)

    fallback_user = remaining_users[0] if remaining_users else None
    paths = _resolve_current_data_paths(current_data_file)
    for p in paths:
        ensure_json_file(file_path=p)
        current_data = read_json(p)
        if current_data.get("current_user") == name:
            current_data["current_user"] = fallback_user
            write_json(p, current_data)

    return True, "Account deleted"

# ──────
def add_pixel_entry(username, graph_id, date_str, quantity, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Add a pixel entry for a specific user and graph in pixels.json."""
    if not check_date(date_str):
        return False  # or just return

    ensure_json_file(file_path, [])
    data = read_json(file_path)

    user_found = False
    graph_found = False

    for user_entry in data:
        if isinstance(user_entry, dict) and username in user_entry:
            user_found = True
            for graph in user_entry[username]:
                if isinstance(graph, dict) and graph.get('graph_id') == graph_id:
                    graph_found = True
                    graph.setdefault('pixels', []).append({date_str: quantity})
                    break
            if not graph_found:
                # infer graph_type from quantity
                gtype = 'flt' if (isinstance(quantity, float) or (isinstance(quantity, str) and '.' in str(quantity))) else 'int'
                user_entry[username].append({
                    "graph_id": graph_id,
                    "graph_type": gtype,
                    "graph_color": DEFAULT_GRAPH_COLOR,
                    "pixels": [{date_str: quantity}]
                })
            break

    if not user_found:
        gtype = 'flt' if (isinstance(quantity, float) or (isinstance(quantity, str) and '.' in str(quantity))) else 'int'
        data.append({username: [{
            "graph_id": graph_id,
            "graph_type": gtype,
            "graph_color": DEFAULT_GRAPH_COLOR,
            "pixels": [{date_str: quantity}]
        }]})

    write_json(file_path, data)
    return True

# ──────
def set_theme(accent_color="#5BF69F", hover_color="#48C47F", text_color="#FFFFFF", file_path=os.path.join(BASE_DIR, "Data", "themes.json")):
    """Set the theme colors in themes.json."""
    theme = get_theme(file_path)
    if accent_color:
        theme['accent_color'] = accent_color
    if hover_color:
        theme['hover_color'] = hover_color
    if text_color:
        theme['text_color'] = text_color
    write_json(file_path, theme)

# ──────
def add_graph(username, graph_id, graph_type, graph_color=DEFAULT_GRAPH_COLOR, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Add a new graph for a user. graph_color defaults to 'green'."""
    ensure_json_file(file_path, [])
    data = read_json(file_path)

    for user_obj in data:
        if username in user_obj:
            user_obj[username].append({
                "graph_id": graph_id,
                "graph_type": graph_type,
                "graph_color": graph_color,
                "pixels": []
            })
            write_json(file_path, data)
            return

    # user not found → create new user
    data.append({
        username: [{
            "graph_id": graph_id,
            "graph_type": graph_type,
            "graph_color": graph_color,
            "pixels": []
        }]
    })
    write_json(file_path, data)

# ──────
def set_graph_color(username, graph_id, color, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Update the graph_color for a user's graph in pixels.json.

    Returns:
        (ok, message): tuple[bool, str]
    """
    ensure_json_file(file_path, [])
    data = read_json(file_path)

    for user_entry in data:
        if not (isinstance(user_entry, dict) and username in user_entry):
            continue
        for graph in user_entry[username]:
            if isinstance(graph, dict) and graph.get("graph_id") == graph_id:
                graph["graph_color"] = color
                write_json(file_path, data)
                return True, "Graph color updated"
        return False, "Graph not found"

    return False, "User not found"

# ──────
def rename_graph(username, old_graph_id, new_graph_id, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Rename a graph for a user in pixels.json.

    Returns:
        (ok, message): tuple[bool, str]
    """
    old_id = str(old_graph_id or "").strip()
    new_id = str(new_graph_id or "").strip()

    if not old_id:
        return False, "Select a graph first"
    if not new_id:
        return False, "Graph name cannot be empty"
    if old_id == new_id:
        return False, "No changes to save"

    ensure_json_file(file_path, [])
    data = read_json(file_path)

    for user_entry in data:
        if not (isinstance(user_entry, dict) and username in user_entry):
            continue
        graphs = user_entry[username]

        # Check new name doesn't already exist
        for g in graphs:
            if isinstance(g, dict) and g.get("graph_id") == new_id:
                return False, "A graph with that name already exists"

        # Find and rename
        for g in graphs:
            if isinstance(g, dict) and g.get("graph_id") == old_id:
                g["graph_id"] = new_id
                write_json(file_path, data)
                return True, "Graph renamed"

        return False, "Graph not found"

    return False, "User not found"


# ──────
def delete_graph(username, graph_id, file_path=os.path.join(BASE_DIR, "Data", "pixels.json")):
    """Delete a graph and all its pixels for a user in pixels.json.

    Returns:
        (ok, message): tuple[bool, str]
    """
    gid = str(graph_id or "").strip()
    if not gid:
        return False, "Select a graph first"

    ensure_json_file(file_path, [])
    data = read_json(file_path)

    for user_entry in data:
        if not (isinstance(user_entry, dict) and username in user_entry):
            continue
        graphs = user_entry[username]
        original_len = len(graphs)
        user_entry[username] = [
            g for g in graphs
            if not (isinstance(g, dict) and g.get("graph_id") == gid)
        ]
        if len(user_entry[username]) == original_len:
            return False, "Graph not found"
        write_json(file_path, data)
        return True, "Graph deleted"

    return False, "User not found"

if __name__ == "__main__":
    # print(get_all_users())
    # print(get_user_graphs("meaowasaurusthethird"))
    # print(get_user_graph_names("meaowasaurusthethird"))
    # print(get_graph_type("meaowasaurusthethird", "sleep"))
    # print(get_theme())
    print(get_pixel_dict("meaowasaurusthethird", "sleep"))
    # add_graph("meaowasaurusthethird", "meaows", "int")
    # print(get_current_graph())
    # add_pixel_entry("meaowasaurusthethird", "meaowasaurusthethird", "01012025", 8)
    # set_theme()