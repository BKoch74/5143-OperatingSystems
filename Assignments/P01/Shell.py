#!/usr/bin/env python
"""
This file is about using getch to capture input and handle certain keys 
when the are pushed. The 'command_helper.py' was about parsing and calling functions.
This file is about capturing the user input so that you can mimic shell behavior.

"""
import os
import random
import sys
import subprocess
import shutil
import time
import pwd
import grp
import readline
import stat
from rich import print
from getch import Getch
from pathlib import Path

##################################################################################
##################################################################################
SAVED_HISTORY = os.path.expanduser('~/.Shell_History') #create file to store history of typed commands

getch = Getch()  # create instance of our getch class

prompt = "$"  # set default prompt

#search for history file, then use readline to load previous commands into the shell
HISTORY_FILE = os.path.expanduser("~/.myshell_history")

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return [line.rstrip("\n") for line in f]
    return []

def save_history(cmd_history):
    try:
        with open(HISTORY_FILE, "w") as f:
            for cmd in cmd_history:
                f.write(cmd + "\n")
    except Exception as e:
        print(f"Error saving history: {e}", file=sys.stderr)

def parse_cmd(cmd_input):
    command_list = []
    cmds = [c.strip() for c in cmd_input.split("|")]

    for cmd in cmds:
        d = {"input": None, "cmd": None, "params": [], "flags": None, "redirect": None}
        parts = cmd.split()
        i = 0
        while i < len(parts):
            part = parts[i]
            if i == 0:
                d["cmd"] = part
            elif part.startswith("-") and len(part) > 1:
                if part[1:] in ["n"]:  # flags that take an argument
                    if i + 1 < len(parts):
                        d["flags"] = f"{part[1:]}{parts[i + 1]}"
                        i += 1
                    else:
                        d["flags"] = part[1:]
                else:
                    d["flags"] = part[1:]
            elif part == ">":
                if i + 1 < len(parts):
                    d["redirect"] = parts[i + 1]
                    i += 1
                else:
                    d["redirect"] = None
            else:
                d["params"].append(part)
            i += 1
        command_list.append(d)
    return command_list
 

def print_cmd(cmd, cursor_pos=None):
    """Cleans the line, prints the cmd with prompt,
    and repositions the cursor if needed."""
    padding = " " * 80
    sys.stdout.write("\r" + padding)        # clear line
    sys.stdout.write("\r" + prompt + cmd)   # reprint line

    if cursor_pos is not None:
        # Move cursor back from the end to correct position
        back_moves = len(cmd) - cursor_pos
        if back_moves > 0:
            sys.stdout.write("\b" * back_moves)

    sys.stdout.flush()

def ls(parts):
    """
    ls-like command supporting:
    -a : show hidden files
    -l : long format with permissions, owner, group, size, mtime
    -h : human-readable sizes (with -l)
    Supports multiple paths like real ls.
    """
    flags = parts.get("flags", "") or ""
    params = parts.get("params") or ["."]
    results = []

    def human_readable_size(size):
        units = ["B", "K", "M", "G", "T", "P"]
        s = float(size)
        for unit in units:
            if s < 1024:
                return f"{s:.1f}{unit}" if unit != "B" else f"{int(s)}{unit}"
            s /= 1024
        return f"{s:.1f}E"

    def format_entry(full_path, stats, name_override=None):
        e = name_override or os.path.basename(full_path)
        if "l" not in flags:
            return e

        # Permissions and type
        perms = stat.filemode(stats.st_mode)

        # Links
        nlink = stats.st_nlink

        # Owner and group
        try:
            owner = pwd.getpwuid(stats.st_uid).pw_name
        except KeyError:
            owner = str(stats.st_uid)
        try:
            group = grp.getgrgid(stats.st_gid).gr_name
        except KeyError:
            group = str(stats.st_gid)

        # Size
        size = stats.st_size
        size_str = human_readable_size(size) if "h" in flags else str(size)

        # Modification time
        mtime = time.strftime("%b %d %H:%M", time.localtime(stats.st_mtime))

        # Symlink handling
        if stat.S_ISLNK(stats.st_mode):
            try:
                target = os.readlink(full_path)
                e_display = f"{e} -> {target}"
            except OSError:
                e_display = e
        else:
            e_display = e

        return f"{perms} {nlink:3} {owner:8} {group:8} {size_str:>8} {mtime} {e_display}"

    def format_columns(entries):
        cols, _ = shutil.get_terminal_size(fallback=(80, 20))
        if not entries:
            return ""
        max_len = max(len(e) for e in entries) + 2
        per_line = max(1, cols // max_len)
        lines = []
        for i in range(0, len(entries), per_line):
            row = "".join(e.ljust(max_len) for e in entries[i:i + per_line])
            lines.append(row.rstrip())
        return "\n".join(lines)

    for path in params:
        if not os.path.exists(path):
            results.append(f"ls: cannot access '{path}': No such file or directory")
            continue

        # File or symlink
        if os.path.isfile(path) or os.path.islink(path):
            try:
                stats = os.lstat(path)
                results.append(format_entry(path, stats))
            except Exception as e:
                results.append(f"ls: cannot access '{path}': {e}")
            continue

        # Directory
        try:
            entries = os.listdir(path)
        except PermissionError:
            results.append(f"ls: cannot open directory '{path}': Permission denied")
            continue

        if "a" not in flags:
            entries = [e for e in entries if not e.startswith(".")]

        entries.sort()

        if len(params) > 1:
            results.append(f"{path}:")

        if "l" in flags:
            lines = []
            for e in entries:
                full_path = os.path.join(path, e)
                try:
                    stats = os.lstat(full_path)
                except Exception:
                    continue
                lines.append(format_entry(full_path, stats, e))
            results.append("\n".join(lines))
        else:
            results.append(format_columns(entries))

    return {"output": "\n".join(results), "error": None}

def rm(parts):
    params = parts.get("params") or []
    flags = parts.get("flags") or ""
    output, error = None, None

    help_text = (
        "Usage: rm [OPTION]... FILE...\n"
        "Remove (unlink) the FILE(s).\n\n"
        "  -r, --recursive  remove directories and their contents recursively\n"
        "  -f, --force      ignore nonexistent files, never prompt, ignore write-only permissions\n"
        "  -h, --help       display this help message\n"
    )

    # Handle help
    if "h" in flags or "--help" in params:
        return {"output": help_text, "error": None}

    force = "f" in flags or "--force" in params
    recursive = "r" in flags or "--recursive" in params

    def remove_path(path):
        if not os.path.exists(path):
            if not force:
                return f"rm: cannot remove '{path}': No such file or directory"
            return None

        if os.path.isfile(path) or os.path.islink(path):
            try:
                if not force:
                    if not os.access(path, os.W_OK):
                        confirm = input(f"rm: remove write-protected file '{path}'? [y/N] ")
                        if confirm.lower() != "y":
                            return None
                if force:
                    os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
                os.remove(path)
            except Exception as e:
                return f"rm: cannot remove '{path}': {e}"

        elif os.path.isdir(path):
            if not recursive:
                return f"rm: cannot remove '{path}': Is a directory"
            try:
                # Recursively delete contents
                for entry in os.listdir(path):
                    entry_path = os.path.join(path, entry)
                    err = remove_path(entry_path)
                    if err:
                        return err
                os.rmdir(path)
            except Exception as e:
                return f"rm: cannot remove '{path}': {e}"

        return None
    for path in params:
        err = remove_path(path)
        if err:
            error = err

    return {"output": output, "error": error}


def cat(parts):
    params = parts.get("params", [])
    input_data = parts.get("input", None)
    redirect_file = parts.get("redirect", None)
    flags = parts.get("flags", "") or ""

    if "h" in flags or "--help" in params:
        help_text = (
            "Usage: cat [FILE]...\n"
            "Concatenate FILE(s) to standard output.\n"
            "If no FILE is given, reads from stdin (piped input).\n"
        )
        return {"output": help_text, "error": None}
    contents = []
    errors = []

    if input_data:
        contents.append(input_data)
    for file in params:
        if file == "-":
            if input_data:
                contents.append(input_data)
            continue
        try:
            with open(file, "r") as f:
                contents.append(f.read())
        except FileNotFoundError:
            errors.append(f"cat: {file}: No such file or directory")
        except PermissionError:
            errors.append(f"cat: {file}: Permission denied")
        except Exception as e:
            errors.append(f"cat: {file}: {e}")

    output = "\n".join(contents) if contents else None
    error = "\n".join(errors) if errors else None

    if redirect_file and output is not None:
        try:
            with open(redirect_file, "w") as f:
                f.write(output)
            output = None
        except Exception as e:
            error = f"cat: cannot write to {redirect_file}: {e}"

    return {"output": output, "error": error}


def head(parts):
    params = parts.get("params", [])
    flags = parts.get("flags", "") or ""
    input_data = parts.get("input", None)
    redirect_file = parts.get("redirect", None)

    if "h" in flags or "--help" in params:
        help_text = (
            "Usage: head [OPTION]... [FILE]...\n"
            "Print the first 10 lines of each FILE to standard output.\n"
            "With more than one FILE, precede each with a header.\n"
            "Options:\n"
            "  -n NUM       print the first NUM lines instead of the first 10\n"
            "  -h, --help   display this help text\n"
        )
        return {"output": help_text, "error": None}

    n = 10
    if "n" in flags:
        try:
            n = int(flags.replace("n", ""))
        except ValueError:
            return {"output": None, "error": f"head: invalid number in flag '{flags}'"}

    output_lines = []
    errors = []

    def process_content(name, content):
        lines = content.splitlines()
        if len(params) > 1:
            header = f"==> {name} <=="
            output_lines.append(header)
        output_lines.extend(lines[:n])

    if input_data:
        process_content("stdin", input_data)

    for file in params:
        try:
            with open(file, "r") as f:
                content = f.read()
            process_content(file, content)
        except FileNotFoundError:
            errors.append(f"head: cannot open '{file}' for reading: No such file or directory")
        except PermissionError:
            errors.append(f"head: cannot open '{file}' for reading: Permission denied")
        except Exception as e:
            errors.append(f"head: {file}: {e}")

    output = "\n".join(output_lines) if output_lines else None
    error = "\n".join(errors) if errors else None

    if redirect_file and output is not None:
        try:
            with open(redirect_file, "w") as f:
                f.write(output)
            output = None
        except Exception as e:
            error = f"head: cannot write to {redirect_file}: {e}"

    return {"output": output, "error": error}


def tail(parts):
    flags_str = str(parts.get("flags") or "")
    flag_values = parts.get("flag_values") or {}
    params = list(parts.get("params") or [])
    input_data = parts.get("input")
    redirect_file = parts.get("redirect") or None

    if "h" in flags_str or "--help" in params:
        help_text = (
            "tail: print the last 10 lines of each FILE to standard output.\n\n"
            "Usage:\n"
            "  tail [OPTION]... [FILE]...\n\n"
            "Options:\n"
            "  -n NUM      output the last NUM lines, instead of the last 10\n"
            "  -h          display this help and exit\n\n"
            "If no FILE is given, or when FILE is '-', read standard input."
        )
        return {"output": help_text, "error": None}

    def parse_int(s):
        try:
            return int(s)
        except Exception:
            return None

    n = 10

    if "n" in flag_values:
        val = parse_int(flag_values["n"])
        if val is None or val < 0:
            return {"output": None, "error": f"tail: invalid number of lines: {flag_values['n']}"}
        n = val
    else:
        found_num = None
        s = flags_str
        idx = s.find("n")
        if idx != -1:
            j = idx + 1
            digits = ""
            while j < len(s) and s[j].isdigit():
                digits += s[j]
                j += 1
            if digits:
                val = parse_int(digits)
                if val is None or val < 0:
                    return {"output": None, "error": f"tail: invalid number of lines: {digits}"}
                n = val
                found_num = True

        if not found_num and "n" in s:
            for i, tok in enumerate(params):
                if isinstance(tok, str) and tok.lstrip("+-").isdigit():
                    val = parse_int(tok)
                    if val is not None:
                        n = val
                        params.pop(i)
                        found_num = True
                        break
            if not found_num:
                return {"output": None, "error": f"tail: option requires an argument -- 'n'"}

    if n < 0:
        return {"output": None, "error": f"tail: invalid number of lines: {n}"}

    output_lines = []
    errors = []

    if input_data is not None:
        lines = input_data.splitlines()
        output_lines.extend(lines[-n:] if n > 0 else [])
    elif params:
        for fname in params:
            try:
                if fname == "-":
                    if input_data is not None:
                        lines = input_data.splitlines()
                    else:
                        errors.append(f"tail: cannot open '{fname}' for reading: No such file")
                        continue
                else:
                    with open(fname, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.read().splitlines()
                if len(params) > 1:
                    output_lines.append(f"==> {fname} <==")
                output_lines.extend(lines[-n:] if n > 0 else [])
            except FileNotFoundError:
                errors.append(f"tail: cannot open '{fname}' for reading: No such file")
            except PermissionError:
                errors.append(f"tail: cannot open '{fname}' for reading: Permission denied")
            except Exception as e:
                errors.append(f"tail: {fname}: {e}")
    else:
        return {"output": None, "error": "tail: missing input"}

    output = "\n".join(output_lines)

    if redirect_file and output:
        try:
            with open(redirect_file, "w", encoding="utf-8") as f:
                f.write(output)
            output = None
        except Exception as e:
            errors.append(f"tail: cannot write to {redirect_file}: {e}")

    error = "\n".join(errors) if errors else None
    return {"output": output, "error": error}


def less(parts):
    params = parts.get("params") or []
    input_data = parts.get("input") or None
    redirect_file = parts.get("redirect") or None
    flags = str(parts.get("flags") or "")

    if "h" in flags:
        help_text = (
            "less: view file or input one screen at a time.\n\n"
            "Usage:\n"
            "  less [FILE]\n\n"
            "Controls:\n"
            "  j or DOWN arrow   scroll down one line\n"
            "  k or UP arrow     scroll up one line\n"
            "  SPACE             scroll down one page\n"
            "  b                 scroll up one page\n"
            "  q or Ctrl-C       quit less"
        )
        return {"output": help_text, "error": None}

    lines = []
    errors = []

    if input_data:
        lines = input_data.splitlines()
    elif params:
        file_path = params[0]
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
        except Exception as e:
            return {"output": None, "error": f"less: {e}"}
    else:
        return {"output": None, "error": "less: missing input"}

    if redirect_file:
        try:
            with open(redirect_file, "w") as f:
                f.write("".join(lines))
            return {"output": None, "error": None}
        except Exception as e:
            return {"output": None, "error": f"less: cannot write to {redirect_file}: {e}"}

    page_size = 20
    pos = 0
    total_lines = len(lines)

    while True:
        os.system("clear")
        page = lines[pos:pos + page_size]
        print("".join(page), end="")
        print(f"\n--Lines {pos+1}-{min(pos+page_size,total_lines)} of {total_lines}--", end="", flush=True)

        char = getch()

        if char in ("q", "\x03"):
            break
        elif char in ("j", "\x1b[B", "\r", "\n"):
            if pos + 1 < total_lines:
                pos += 1
        elif char in ("k", "\x1b[A"):
            if pos > 0:
                pos -= 1
        elif char == " ":
            if pos + page_size < total_lines:
                pos += page_size
            else:
                pos = total_lines - 1
        elif char == "b":
            pos = max(0, pos - page_size)

    return {"output": None, "error": None}

def cp(parts):
    params = parts.get ("params" , [])
    redirect_file = parts.get ("redirect", None)
    errors = []
    if len(params) < 2:
        return {"output": None, "error" : "cp command requires a source and destination to operate."}
    
    s,d = params [:2]
    try:
        content = Path(s).read_bytes()
        Path(d).write_bytes(content)
        output = f"file has been copied {s} to {d}"
    
    except Exception as err:
        errors.append(f" cp: {err}")
        output = None
    error = "\n".join(errors) if errors else None
    return {"output" : output, "error": error}

def grep(parts):
    """
    Grep-like command for CLI.
    Flags supported:
        -i : ignore case
        -v : invert match
        -c : count matches
        -l : list only file names with matches
    Accepts piped input via 'input' key.
    Redirects output if 'redirect' is specified.
    """
    params = parts.get("params", [])
    flags = parts.get("flags", "") or ""
    input_data = parts.get("input", None)
    redirect_file = parts.get("redirect", None)
    errors = []

    if not params and not input_data:
        return {"output": None, "error": "grep: missing search pattern"}

    # First param is always the pattern
    pattern = params[0]
    files = params[1:] if len(params) > 1 else []

    ignore_case = 'i' in flags
    invert = 'v' in flags
    count_only = 'c' in flags
    list_files = 'l' in flags

    matches = []
    matched_files = set()

    # Helper to test if a line matches
    def line_matches(line):
        test_line = line.lower() if ignore_case else line
        test_pattern = pattern.lower() if ignore_case else pattern
        matched = test_pattern in test_line
        return not matched if invert else matched

    # If piped input exists
    if input_data:
        for line in input_data.splitlines():
            if line_matches(line):
                matches.append(line)

    # If files are specified
    for fname in files:
        try:
            with open(fname, "r") as f:
                file_lines = f.readlines()
                file_match_count = 0
                for line in file_lines:
                    if line_matches(line):
                        file_match_count += 1
                        if not count_only and not list_files:
                            matches.append(line.rstrip("\n"))
                if count_only:
                    matches.append(f"{file_match_count}")
                if list_files and file_match_count > 0:
                    matched_files.add(fname)
        except FileNotFoundError:
            errors.append(f"grep: {fname}: No such file")
        except Exception as e:
            errors.append(f"grep: {fname}: {e}")

    # For list_files flag
    if list_files:
        matches = list(matched_files)

    output = "\n".join(matches) if matches else ""

    # Redirect output if needed
    if redirect_file and output:
        try:
            with open(redirect_file, "w") as f:
                f.write(output)
            output = None
        except Exception as e:
            errors.append(f"grep: {e}")

    error = "\n".join(errors) if errors else None
    return {"output": output, "error": error}

def clear(parts=None):
    try:
        # Cross-platform clear
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        return {"output": None, "error": None}
    except Exception as e:
        return {"output": None, "error": f"clear: {e}"}

def wc(parts):
    params = parts.get ("params", [])
    flags = parts.get("flags",set()) or set()
    input_data = parts.get ("input", None)
    redirect_file = parts.get("redirect", None)
    errors = []
    output = None 
    
    if not params and not input_data:
        return {"output": None, "error": " wc: operand is missing"}
        
    try:
        text = ""
        if params:
            results = []
            for filename in params:
                try:
                    with open(filename, "r") as f:
                        text = f.read()
                    counts = get_counts(text, flags)
                    results.append(f"{counts} {filename}")
                except FileNotFoundError:
                    errors.append(f"wc: {filename}: file not found")
                except Exception as e:
                    errors.append(f"wc: {filename}: {e}")
            output= "\n".join(results)
        else:
            counts = get_counts(input_data, flags)
            output = str(counts)
    except Exception as err:
        errors.append(f"wc: {err}")
        output = None
    error = "\n".join(errors) if errors else None
    return {"output": output, "error": error}


def get_counts(text, flags):
    lines = text.splitlines()
    words = text.split()
    chars = text
    
    if not flags:
        return str(len(words))
        
    results = []
    if "w" in flags:
        results.append(str(len(words)))
    if "l" in flags:
        results.append(str(len(lines)))
    if "c" in flags:
        results.append(str(len(chars)))
    return " ".join(results)

def history(parts):
    params = parts.get("params", [])
    redirect_file = parts.get("redirect", None)
    errors = []
    output = None
    
    try: 
        result = subprocess.run("history",shell = True, capture_output = True, text = True)
        output = result.stdout.strip()
        if result.stderr:
            errors.append(result.stderr.strip())
    except Exception as err:
        errors.append(f"history: {err}")
        output = None
            
    if redirect_file and output:
        try:
            with open(redirect_file, "w") as f:
                    f.write(output)
            output = None
        except Exception as err:
            errors.append(f"history: cannot write to {redirect_file}: {err}")
                
    error = "\n".join(errors) if errors else None
    return {"output": output, "error" : error}

def chmod(parts):
    params = parts.get("params", [])
    redirect_file = parts.get("redirect",None)
    errors = []
    output = None
        
    if not params or len(params) <2:
       return {"output": None, "error": "chmod: missing mode/file"}
            
    m,f = params[:2]
    try:
        subprocess.run(["chmod", m, f])
        output = f"permissions for {f} are set to {m}"
    except Exception as err:
        errors.append(f"chmod: {err}")
        output = None
            
    if redirect_file and output:
       try:
         with open(redirect_file, "w") as f:
            f.write(output)
            output = None
       except Exception as err:
            errors.append(f"chmod: cannot write to {redirect_file}: {err}")
                
    error = "\n".join(errors) if errors else None
    return {"output": output, "error" : error}


def sorting(parts):
    params = parts.get("params", [])
    input_data = parts.get("input", None)
    redirect_file = parts.get("redirect",None)
    errors = []
    contents = []
    output = None
        
    if input_data:
            contents.extend(input_data.splitlines())
    for file in params:
        try:
           with open(file, "r") as f:
                    contents.extend(f.readlines())
        except Exception as err:
            errors.append(f"sort:{file}: {err}")
                
    try:
            output = "\n".join(sorted([line.strip() for line in contents]))
    except Exception as err:
        errors.append(f"sort: {err}")
        output = None
                
    if redirect_file and output:
      try:
          with open(redirect_file, "w") as f:
              f.write(output)
          output = None
      except Exception as err:
          errors.append(f"sort: cannot write to {redirect_file}: {err}")
                    
    error = "\n".join(errors) if errors else None
    return {"output": output, "error" : error} 
       
        
def history_expansion(parts, cmd_history):
    if not parts.get("params"):
        return {"output": None, "error": "No history index specified"}

    try:
        index = int(parts["params"][0]) - 1  # 1-based indexing
        if 0 <= index < len(cmd_history):
            prev_cmd = cmd_history[index]
            command_list = parse_cmd(prev_cmd)
            return {"output": prev_cmd, "error": None, "execute": command_list}
        else:
            return {"output": None, "error": "History index out of range"}
    except ValueError:
        return {"output": None, "error": "Invalid history index"}


def pwd_cmd(parts):
    output = None
    error = None
    flags = parts.get("flags", "") or ""
    params = parts.get("params") or []
    
    #current working directory
    try:
        output = os.getcwd()
    except Exception as err:
        error = f"pwd:{err}"

    return {"output": output, "error" : error}


def mv(parts):
    output = None
    error = None
    #Doesn't handle flags but handles params
    flags = parts.get("flags")
    params = parts.get("params")

    if flags:
        return "This function does not accept flags."

    if not params or len(params) < 2:
        return "Usage: mv <source> <destination>"

    source_path = params[0]
    dest_path = params[1]

    #Extracting file and directory names to keep tne path logic
    source_parts = source_path.split('/')
    source_file = source_parts[-1]

    dest_parts = dest_path.split('/')
    dest_file = dest_parts[-1]

    #Checking if the src file exists
    if not os.path.exists(source_path):
        return f"Source file does not exist: {source_path}"

    try:
        #Moving the file from src to dest
        shutil.move(source_path, dest_path) #It automatically overwrites the file if destination is an existing 
                                         #file or if destination is a directory it moves the file to the directory 
        output = f"Moved '{source_file}' to '{dest_path}'."
    except Exception as e:
        error = f"Error moving file: {str(e)}"
    return {"output": output, "error": error}
    

def cd(parts):
    """
    Change directory. Supports:
    - cd (no args) → home directory
    - cd ..        → parent directory
    - cd /         → root directory
    - cd <path>    → specific path
    """
    params = parts.get("params") or []

    # If no param → go to home
    if not params:
        target = os.path.expanduser("~")
    else:
        target = params[0]

        if target == "/":  # go root
            target = "/"
        elif target == "..":  # go parent
            target = os.path.dirname(os.getcwd())
        elif not os.path.isabs(target):  # relative path
            target = os.path.join(os.getcwd(), target)

    if os.path.isdir(target):
        try:
            os.chdir(target)
            return {"output": f"Changed directory to: {target}", "error": None}
        except Exception as err:
            return {"output": None, "error": f"cd: {err}"}
    else:
        return {"output": None, "error": f"cd: no such directory: {target}"}



def mkdir(parts):
    output = None
    error = None
    params = parts.get("params")

    if not params or not params[0]:
        error = "No directory name specified."
    dicty_name = params[0]

    try:
        os.mkdir(dicty_name)
        output = f"Directory '{dicty_name}' created successfully."
    except FileExistsError:
        error = f"Directory '{dicty_name}' already exists."
    return {"output": output, "error": error}


def randomline(parts):
    """
    randomline - prints one or more random lines from a file or piped input
    Usage:
        randomline <file1> [file2 ...]      # print 1 random line per file
        randomline -n 5 <file>              # print 5 random lines
    Accepts piped input as well.
    """
    params = parts.get("params", [])
    input_data = parts.get("input", None)
    flags = parts.get("flags", "") or ""

    num_lines = 1  # default
    if 'n' in flags:
        try:
            # expect flags like "n5"
            num_lines = int(flags.replace("n", ""))
        except ValueError:
            return {"output": None, "error": f"randomline: invalid number in flag '{flags}'"}

    lines = []

    # Collect input
    if input_data:
        lines.extend(input_data.splitlines())
    for file in params:
        try:
            with open(file, "r") as f:
                lines.extend(f.read().splitlines())
        except Exception as e:
            return {"output": None, "error": f"randomline: {file}: {e}"}

    if not lines:
        return {"output": None, "error": "randomline: no input provided"}

    # Pick random lines
    if num_lines > len(lines):
        num_lines = len(lines)

    output_lines = random.sample(lines, num_lines)
    output = "\n".join(output_lines)

    return {"output": output, "error": None}

if __name__ == "__main__":
    cmd_history = load_history()
    history_index = len(cmd_history)
    cmd = ""
    cursor_pos = 0

    print_cmd(cmd, cursor_pos)

    while True:
        char = getch()

        # Ctrl-C or 'exit'
        if char == "\x03" or cmd.strip() == "exit":
            save_history(cmd_history)  # save history before leaving
            raise SystemExit("Bye.")

        # Backspace
        elif char == "\x7f":
            if cursor_pos > 0:
                cmd = cmd[:cursor_pos-1] + cmd[cursor_pos:]
                cursor_pos -= 1
            print_cmd(cmd, cursor_pos)

        # Arrow keys
        elif char == "\x1b":
            getch()
            direction = getch()
            if direction == "A":  # Up
                if cmd_history and history_index > 0:
                    history_index -= 1
                    cmd = cmd_history[history_index]
                    cursor_pos = len(cmd)
                    print_cmd(cmd, cursor_pos)
            elif direction == "B":  # Down
                if cmd_history and history_index < len(cmd_history) - 1:
                    history_index += 1
                    cmd = cmd_history[history_index]
                else:
                    history_index = len(cmd_history)
                    cmd = ""
                cursor_pos = len(cmd)
                print_cmd(cmd, cursor_pos)
            elif direction == "C":  # Right
                if cursor_pos < len(cmd):
                    cursor_pos += 1
                print_cmd(cmd, cursor_pos)
            elif direction == "D":  # Left
                if cursor_pos > 0:
                    cursor_pos -= 1
                print_cmd(cmd, cursor_pos)

        # Enter pressed
        elif char == "\r":
            print()  # newline
            if not cmd.strip():
                cmd = ""
                cursor_pos = 0
                print_cmd(cmd, cursor_pos)
                continue

            if cmd.startswith("!"):
                try:
                    num = int(cmd[1:])
                    if num <= 0 or num > len(cmd_history):
                        print(f"bash: !{num}: event not found")
                        cmd, cursor_pos = "", 0
                        print_cmd(cmd, cursor_pos)
                        continue
                    cmd = cmd_history[num - 1]
                    print(cmd)  # echo command
                except ValueError:
                    print(f"bash: {cmd}: event not found")
                    cmd, cursor_pos = "", 0
                    print_cmd(cmd, cursor_pos)
                    continue

            cmd_history.append(cmd)
            history_index = len(cmd_history)
            save_history(cmd_history)

            # run commands
            command_list = parse_cmd(cmd)
            piped_input = None
            final_output = None

            for command in command_list:
                if piped_input is not None:
                    command["input"] = piped_input

                c = command['cmd']
                try:
                    if c == "ls":
                        output = ls(command)
                    elif c == "cat":
                        output = cat(command)
                    elif c == "grep":
                        output = grep(command)
                    elif c == "tail":
                        output = tail(command)
                    elif c == "head":
                        output = head(command)
                    elif c == "less":
                        output = less(command)
                    elif c == "rm":
                        output = rm(command)
                    elif c == "cp":
                        output = cp(command)
                    elif c == "pwd":
                        output = pwd_cmd(command)
                    elif c == "mv":
                        output = mv(command)
                    elif c == "cd":
                        output = cd(command)
                    elif c == "mkdir":
                        output = mkdir(command)
                    elif c == "clear":
                        output = clear(command)
                    elif c == "history":
                        hist_out = "\n".join(f"{i + 1} {c}" for i, c in enumerate(cmd_history))
                        output = {"output": hist_out, "error": None}
                    elif c == "chmod":
                        output = chmod(command)
                    elif c == "sort":
                        output = sorting(command)
                    elif c == "wc":
                        output = wc(command)
                    elif c == "randomline":
                        output = randomline(command)
                    else:
                        output = {"output": None, "error": f"{c}: command not found"}
                except Exception as e:
                    output = {"output": None, "error": str(e)}

                if output["error"]:
                    print(output["error"])
                    piped_input = None
                    final_output = None
                else:
                    piped_input = output["output"]
                    final_output = output

            redirect_file = command_list[-1].get("redirect")
            if redirect_file and final_output and final_output.get("output"):
                try:
                    with open(redirect_file, "w") as f:
                        f.write(final_output["output"])
                    final_output["output"] = None
                except Exception as e:
                    print(f"Error writing to file {redirect_file}: {e}")

            if final_output and final_output.get("output"):
                print(final_output["output"])

            cmd = ""
            cursor_pos = 0
            print_cmd(cmd, cursor_pos)
        else:
            cmd = cmd[:cursor_pos] + char + cmd[cursor_pos:]
            cursor_pos += 1
            print_cmd(cmd, cursor_pos)