#!/usr/bin/env python
"""
This file is about using getch to capture input and handle certain keys 
when the are pushed. The 'command_helper.py' was about parsing and calling functions.
This file is about capturing the user input so that you can mimic shell behavior.

"""
import os
import sys
import subprocess
import shutil
from time import sleep
from rich import print
from getch import Getch
from pathlib import Path

##################################################################################
##################################################################################

getch = Getch()  # create instance of our getch class

prompt = "$"  # set default prompt

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
 

def print_cmd(cmd):
    """This function "cleans" off the command line, then prints
    whatever cmd that is passed to it to the bottom of the terminal.
    """
    padding = " " * 80
    sys.stdout.write("\r" + padding)
    sys.stdout.write("\r" + prompt + cmd)
    sys.stdout.flush()

def ls(parts):
    flags = parts.get("flags", "") or ""
    params = parts.get("params") or []

    path = params[0] if params else "."

    if not os.path.exists(path):
        return {"output": None, "error": "Directory doesn't exist"}

    try:
        entries = os.listdir(path)
    except PermissionError:
        return {"output": None, "error": "Permission denied"}

    if 'a' not in flags:
        entries = [e for e in entries if not e.startswith('.')]

    entries.sort()
    output_lines = []

    if 'l' in flags:
        for e in entries:
            full_path = os.path.join(path, e)
            try:
                stats = os.stat(full_path)
            except Exception:
                continue
            mode = stats.st_mode
            perms = ""
            for shift in [6, 3, 0]:  # user, group, other
                perms += "r" if mode & (0o400 >> shift) else "-"
                perms += "w" if mode & (0o200 >> shift) else "-"
                perms += "x" if mode & (0o100 >> shift) else "-"

            size = stats.st_size
            if 'h' in flags:
                s = size
                for unit in ['B', 'K', 'M', 'G', 'T']:
                    if s < 1024:
                        size_str = f"{int(s)}{unit}"
                        break
                    s /= 1024
            else:
                size_str = str(size)
            mtime = int(stats.st_mtime)
            output_lines.append(f"{perms} {size_str} {mtime} {e}")
    else:
        output_lines = entries

    output = "\n".join(output_lines)
    return {"output": output, "error": None}

def rm(parts):
    params = parts.get("params") or []
    flags = parts.get("flags") or ""
    output, error = None, None

    def remove_path(path):
        if os.path.isfile(path) or os.path.islink(path):
            try:
                os.remove(path)
            except Exception as e:
                return f"rm: cannot remove '{path}': {e}"
        elif os.path.isdir(path):
            if "r" not in flags:
                return f"rm: cannot remove '{path}': Is a directory"
            try:
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
        if not os.path.exists(path):
            if "f" not in flags:
                error = f"rm: cannot remove '{path}': No such file or directory"
            continue
        err = remove_path(path)
        if err:
            error = err

    return {"output": output, "error": error}


def cat(parts):
    params = parts.get("params", [])
    input_data = parts.get("input", None)
    redirect_file = parts.get("redirect", None)

    if not params and not input_data:
        return {"output": None, "error": "cat: missing operand"}

    contents = []
    errors = []

    if input_data:
        contents.append(input_data)

    for file in params:
        try:
            with open(file, "r") as f:
                contents.append(f.read())
        except Exception as e:
            errors.append(f"cat: {file}: {e}")

    output = "\n".join(contents)
    error = "\n".join(errors) if errors else None
    if redirect_file:
        try:
            with open(redirect_file, "w") as f:
                f.write(output)
            output = None
        except Exception as e:
            error = f"cat: cannot write to {redirect_file}: {e}"

    return {"output": output, "error": error}


def head(parts):
    params = parts.get("params", [])
    flags = parts.get("flags", "")
    n = 10  # default

    if flags:
        for flag in flags.split():
            if flag.startswith("n"):
                try:
                    n = int(flag[1:])
                except:
                    return {"output": None, "error": f"head: invalid number in flag '{flag}'"}

    if not params:
        return {"output": None, "error": "head: missing operand"}

    output = []
    for file in params:
        try:
            with open(file, "r") as f:
                lines = f.readlines()
                output.append("".join(lines[:n]))
        except Exception as e:
            return {"output": None, "error": f"head: {e}"}

    return {"output": "\n".join(output), "error": None}


def tail(parts):
    params = parts.get("params", [])
    flags = parts.get("flags", "")
    n = 10

    if flags:
        for flag in flags.split():
            if flag.startswith("n"):
                try:
                    n = int(flag[1:])
                except:
                    return {"output": None, "error": f"tail: invalid number in flag '{flag}'"}

    if not params:
        return {"output": None, "error": "tail: missing operand"}

    output = []
    for file in params:
        try:
            with open(file, "r") as f:
                lines = f.readlines()
                output.append("".join(lines[-n:]))
        except Exception as e:
            return {"output": None, "error": f"tail: {e}"}

    return {"output": "\n".join(output), "error": None}


def less(parts):
    params = parts.get("params") or []
    if not params:
        return {"output": None, "error": "less: missing operand"}

    file_path = params[0]

    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        return {"output": None, "error": f"less: {e}"}

    page_size = 20
    pos = 0

    while True:
        os.system("clear")
        page = lines[pos:pos + page_size]
        print("".join(page), end="")
        print(f"\n--Lines {pos+1}-{min(pos+page_size,len(lines))} of {len(lines)}--", end="", flush=True)

        char = getch()

        if char in ("q", "\x03"):
            break
        elif char in ("\r", "\n", "j", "\x1b[B"):
            if pos + page_size < len(lines):
                pos += 1
        elif char in ("k", "\x1b[A"):
            if pos > 0:
                pos -= 1
        elif char == " ":
            if pos + page_size < len(lines):
                pos += page_size
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
    params = parts.get("params", [])
    redirect_file = parts.get("redirect", None)
    input_data = parts.get("input")  # from a pipe
    errors = []

    if not params:
        return {"output": None, "error": "grep: missing search string"}

    pattern = params[0]
    files = params[1:]

    matches = []

    if input_data:
        for line in input_data.splitlines():
            if pattern in line:
                matches.append(line.rstrip("\n"))

    elif files:
        for fname in files:
            try:
                with open(fname, "r") as f:
                    for line in f:
                        if pattern in line:
                            matches.append(line.rstrip("\n"))
            except FileNotFoundError:
                errors.append(f"grep: {fname}: No such file")
            except Exception as e:
                errors.append(f"grep: {fname}: {e}")

    else:
        return {"output": None, "error": "grep: no input provided"}

    output = "\n".join(matches) if matches else ""

    if redirect_file and output:
        try:
            with open(redirect_file, "w") as f:
                f.write(output)
            output = None
        except Exception as e:
            errors.append(f"grep: {e}")

    error = "\n".join(errors) if errors else None
    return {"output": output, "error": error}


def wc(parts):
    params = parts.get ("params", [])
    input_data = parts.get ("input", None)
    redirect_file = parts.get("redirect", None)
    errors = []
    output = None 
    
    if not params and not input_data:
        return {"output": None, "error": " wc: operand is missing"}
        
    try:
        if params:
            file = params[0]
            with open(file, "r") as f:
                text = f.read()
            output = str(len(text.split()))
            
        else:
            output = str(len(input_data.split()))
    except Exception as err:
        errors.append(f"wc: {err}")
        output = None
        
    if redirect_file and output:
        try:
            with open(redirect_file, "w") as f:
                f.write(output)
            output = None
        except Exception as err:
            errors.append(f"wc: cannot write to {redirect_file}: {err}")
            
    error = "\n".join(errors) if errors else None
    return {"output": output, "error": error}

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


def pwd(parts):
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

def count(parts):
    """
    Custom CLI command:
    count -l -> count lines
    count -w -> count words
    count -c -> count characters
    Can take piped input or file names in params
    """
    flags = parts.get("flags", "") or ""
    params = parts.get("params", [])
    input_data = parts.get("input")
    redirect_file = parts.get("redirect", None)
    errors = []

    count_lines = 'l' in flags
    count_words = 'w' in flags
    count_chars = 'c' in flags

    if not (count_lines or count_words or count_chars):
        count_lines = True

    text_data = ""
    if input_data:
        text_data = input_data
    elif params:
        for fname in params:
            try:
                with open(fname, "r") as f:
                    text_data += f.read() + "\n"
            except Exception as e:
                errors.append(f"count: {fname}: {e}")
    else:
        return {"output": None, "error": "count: no input provided"}
    output_parts = []
    if count_lines:
        output_parts.append(f"Lines: {len(text_data.splitlines())}")
    if count_words:
        output_parts.append(f"Words: {len(text_data.split().copy())}")
    if count_chars:
        output_parts.append(f"Chars: {len(text_data)}")

    output = " | ".join(output_parts)

    if redirect_file:
        try:
            with open(redirect_file, "w") as f:
                f.write(output)
            output = None
        except Exception as e:
            errors.append(f"count: {e}")

    error = "\n".join(errors) if errors else None
    return {"output": output, "error": error}


if __name__ == "__main__":
    cmd_history = []
    history_index = 0
    cmd = ""

    print_cmd(cmd)

    while True:
        char = getch()

        # Ctrl-C or 'exit'
        if char == "\x03" or cmd.strip() == "exit":
            raise SystemExit("Bye.")

        # Backspace
        elif char == "\x7f":
            cmd = cmd[:-1]
            print_cmd(cmd)

        # Arrow keys
        elif char == "\x1b":
            getch()  # skip '['
            direction = getch()
            if direction == "A":  # Up
                if cmd_history and history_index > 0:
                    history_index -= 1
                    cmd = cmd_history[history_index]
                    print_cmd(cmd)
            elif direction == "B":  # Down
                if cmd_history and history_index < len(cmd_history) - 1:
                    history_index += 1
                    cmd = cmd_history[history_index]
                else:
                    history_index = len(cmd_history)
                    cmd = ""
                print_cmd(cmd)
            # Left/Right arrows can be ignored for now

        # Enter pressed
        elif char == "\r":
            print()  # move to next line
            if not cmd.strip():
                cmd = ""
                print_cmd(cmd)
                continue

            # Save to history
            cmd_history.append(cmd)
            history_index = len(cmd_history)

            # Parse commands
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
                        output = pwd(command)
                    elif c == "mv":
                        output = mv(command)
                    elif c == "cd":
                        output = cd(command)
                    elif c == "mkdir":
                        output = mkdir(command)
                    elif c == "history":
                        hist_out = "\n".join(f"{i + 1} {c}" for i, c in enumerate(cmd_history))
                        output = {"output": hist_out, "error": None}
                    elif c == "!x":
                        output = history_expansion(command, cmd_history)
                        # If executing previous command
                        if output.get("execute"):
                            command_list = output["execute"] + command_list[1:]
                            piped_input = None
                            break
                    elif c == "chmod":
                        output = chmod(command)
                    elif c == "sort":
                        output = sorting(command)
                    elif c == 'wc':
                        output = wc(command)
                    elif c == 'count':
                        output = count(command)
                    else:
                        output = {"output": None, "error": f"{c}: command not found"}
                except Exception as e:
                    output = {"output": None, "error": str(e)}

                # Handle errors
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

            # Print final output if not redirected
            if final_output and final_output.get("output"):
                print(final_output["output"])

            cmd = ""
            print_cmd(cmd)

        # Regular character input
        else:
            cmd += char
            print_cmd(cmd)
