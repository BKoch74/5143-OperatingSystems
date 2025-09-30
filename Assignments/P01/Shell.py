#!/usr/bin/env python
"""
This file is about using getch to capture input and handle certain keys 
when the are pushed. The 'command_helper.py' was about parsing and calling functions.
This file is about capturing the user input so that you can mimic shell behavior.

"""
import os
import sys
import subprocess
from time import sleep
from rich import print
from getch import Getch

##################################################################################
##################################################################################

getch = Getch()  # create instance of our getch class

prompt = "$"  # set default prompt

def parse_cmd(cmd_input):
    command_list = []
    cmds = cmd_input.split("|")
    for cmd in cmds:
        d = {"input":None,"cmd":None,"params":[],"flags":None, "redirect":None}
        subparts = cmd.strip().split()
        d["cmd"]= subparts[0]
        for item in subparts[1:]:
            if "-" in item:
                d["flags"]=item[1:]
            elif ">" in item:
                d["redirect"]=item[1:]
            else:
                d['params'].append(item)
            
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

import os

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
        content = path(s).read_bytes()
        path(d).write_bytes(content)
        output = f"file has been copied {s} to {d}"
    
    except Exception as err:
        errors.append(f" cp: {err}")
        output = None
    error = "\n".join(errors) if errors else None
    return {"output" : output, "error": error}

def grep(parts):
    params = parts.get ("params" , [])
    redirect_file = parts.get ("redirect", None)
    errors = []
    output = None
    if not params or len(params) <2:
        return {"output": None , "error" : "grep requires a pattern to search for within the files"}
        
    pattern = params[0]
    files = params [1:]
        
    try:
        cmd = ["grep","-lic", pattern, *files]
        results = subprocess.run(cmd,capture_output = True, text = True)
        output = results.stdout.strip()
        if results.stderr:
            errors.append(results.stderr.strip())
                
    except Exception as err:
        errors.append(f"grep: {err}")
        output = None
                
    if redirect_file and output:
        try:
            with open(redirect_file, 'w') as f:
                f.write(output)
                output = None
        except Exception as err:
            errors.append(f"grep: {err}")
                
        error = "\n".join(errors) if errors else None
        return { "output": output, "error": error}


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








if __name__ == "__main__":
    cmd_list = parse_cmd("ls Assignments -lah | grep '.py' | wc -l > output")
    cmd = ""  # empty cmd variable

    print_cmd(cmd)  # print to terminal

    while True:  # loop forever

        char = getch()  # read a character (but don't print)

        if char == "\x03" or cmd == "exit":  # ctrl-c
            raise SystemExit("Bye.")

        elif char == "\x7f":  # back space pressed
            cmd = cmd[:-1]
            print_cmd(cmd)

        elif char == "\x1b":  # arrow key pressed
            null = getch()  # waste a character
            direction = getch()  # grab the direction

            if direction in "A":  # up arrow pressed
                # get the PREVIOUS command from your history (if there is one)
                # prints out 'up' then erases it (just to show something)
                cmd += "\u2191"
                print_cmd(cmd)
                sleep(0.3)
                # cmd = cmd[:-1]

            if direction in "B":  # down arrow pressed
                # get the NEXT command from history (if there is one)
                # prints out 'down' then erases it (just to show something)
                cmd += "\u2193"
                print_cmd(cmd)
                sleep(0.3)
                # cmd = cmd[:-1]

            if direction in "C":  # right arrow pressed
                # move the cursor to the right on your command prompt line
                # prints out 'right' then erases it (just to show something)
                cmd += "\u2192"
                print_cmd(cmd)
                sleep(0.3)
                # cmd = cmd[:-1]

            if direction in "D":  # left arrow pressed
                # moves the cursor to the left on your command prompt line
                # prints out 'left' then erases it (just to show something)
                cmd += "\u2190"
                print_cmd(cmd)
                sleep(0.3)
                # cmd = cmd[:-1]

        elif char in "\r":  # return pressed

            # This 'elif' simulates something "happening" after pressing return
            cmd_list.append(cmd)
            command_list = parse_cmd(cmd)
            cmd = "Executing command...."  #
            for command in command_list:
                print(command)
                if command['cmd'] == 'ls':
                    output = ls(command)
                elif command['cmd'] == 'cat':
                    output = cat(command)
                elif command['cmd'] == 'tail':
                    output = tail(command)
                elif command['cmd'] == 'head':
                    output = head(command)
                elif command['cmd'] == 'less':
                    output = less(command)
                elif command['cmd'] == 'rm':
                    output = rm(command)
                    if output["output"] is None:
                        output["output"] = ""
                elif command['cmd'] == 'cp':
                    output = cp (command)
                    if output["output"] is None:
                        output["output"] = ""
                elif command['cmd'] == 'grep':
                    output = grep (command)
                    if output["output"] is None:
                        output["output"] = ""
                elif command['cmd'] == 'wc':
                    output = wc (command)
                    if output["output"] is None:
                        output["output"] = ""
                elif command['cmd'] == 'history':
                    output = history (command)
                    if output["output"] is None:
                        output["output"] = ""
                elif command['cmd'] == 'chmod':
                    output = chmod (command)
                    if output["output"] is None:
                        output["output"] = ""
                
                else:
                    output['error'] = 'Invalid Command'
                if output['error']:
                    print(output['error'])
                else:
                    print(output['output'])
            sleep(1)

            ## YOUR CODE HERE
            ## Parse the command
            ## Figure out what your executing like finding pipes and redirects

            cmd = ""  # reset command to nothing (since we just executed it)

            print_cmd(cmd)  # now print empty cmd prompt
        else:
            cmd += char  # add typed character to our "cmd"
            print_cmd(cmd)  # print the cmd out
