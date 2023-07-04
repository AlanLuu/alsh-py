#!/usr/bin/env python3

import os
import platform
import sys
from typing import Union

class History:
    def __init__(self):
        self._elements: list[str] = []
        self._count: int = 0
    
    def add(self, element: str) -> None:
        self._elements.append(element)
        self._count += 1
    
    def clear(self) -> None:
        self._elements.clear()
        self._count = 0
    
    def first(self) -> Union[str, None]:
        return None if self._count == 0 else self._elements[0]
    
    def last(self) -> Union[str, None]:
        return None if self._count == 0 else self._elements[-1]
    
    def pop(self, index: int = None) -> Union[str, None]:
        return self.remove(-1 if index is None else index)
    
    def remove(self, index: int) -> Union[str, None]:
        if self._count > 0:
            item = self._elements.pop(index)
            self._count -= 1
            return item
        return None
    
    def __getitem__(self, index: int) -> Union[str, None]:
        try:
            return self._elements[index]
        except IndexError:
            return None
    
    def __iter__(self):
        return iter(self._elements)
    
    def __len__(self) -> int:
        return self._count

COMMENT_CHAR = "#"
EXIT_COMMAND = "exit"
HISTORY_COMMAND = "history"
HISTORY_FILE_NAME = ".alsh_history"
SHELL_NAME = "alsh"

cwd = ""
history = History()

# Print to stderr
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def handle_redirect_stdout(cmd: str, cmd_tokens: list[str]) -> tuple[bool, Union[int, None]]:
    stdout_redirect_chr = cmd.find(">")
    if stdout_redirect_chr != -1:
        file_name = cmd[stdout_redirect_chr + 1:].strip()
        if file_name.startswith(">"):
            while ">" in file_name:
                file_name = file_name[1:].strip()
            open_mode = "a"
        else:
            open_mode = "w"
        
        if not file_name:
            eprint(f"{SHELL_NAME}: {'>>' if open_mode == 'a' else '>'}: Missing file name")
            status = (-1, None)
        else:
            old_stdout = os.dup(sys.stdout.fileno())
            status = (1, old_stdout)
            cmd_tokens.remove(file_name)
            with open(file_name, open_mode) as f:
                os.dup2(f.fileno(), sys.stdout.fileno())
    else:
        status = (0, None)
    
    return status

def handle_redirect_stdin(cmd: str, cmd_tokens: list[str]) -> tuple[int, Union[int, None]]:
    stdin_redirect_chr = cmd.find("<")
    if stdin_redirect_chr != -1:
        file_name = cmd[stdin_redirect_chr + 1:].strip()
        if ">" in file_name:
            file_name = file_name[:file_name.index(">")].strip()
        
        try:
            with open(file_name, "r") as f:
                old_stdin = os.dup(sys.stdin.fileno())
                os.dup2(f.fileno(), sys.stdin.fileno())
                status = (1, old_stdin)
        except FileNotFoundError:
            eprint(f"{SHELL_NAME}: {file_name}: No such file or directory")
            status = (-1, None)
    else:
        status = (0, None)
    
    return status

def execute_command(cmd: str) -> None:
    temp_cmd = ""
    cmd_index = 0
    cmd_len = len(cmd)
    special_chrs = ("<", ">")
    while cmd_index < cmd_len:
        c = cmd[cmd_index]
        if (
            cmd_index > 0
            and c in special_chrs
            and (
                cmd[cmd_index - 1] != " "
                or (cmd[cmd_index + 1] != " " and cmd[cmd_index + 1] != ">")
            )
        ):
            temp_cmd += " "
            temp_cmd += c
            cmd_index += 1
            if c == ">" and cmd[cmd_index] == ">":
                temp_cmd += cmd[cmd_index]
                cmd_index += 1
            temp_cmd += " "
        else:
            temp_cmd += c
            cmd_index += 1
    
    # Remove extra spaces, leaving only one space between tokens
    temp_cmd = " ".join(temp_cmd.split())
    
    cmd = temp_cmd
    tokens = cmd.split(" ")

    if tokens[0] == "ls":
        tokens.append("--color=auto")
    
    tokens_len = len(tokens)
    if tokens[0] == "cd":
        if tokens_len > 1:
            arg = tokens[1]
            if arg == "..":
                global cwd
                last_slash_pos = cwd.rfind("/")
                cwd = cwd[:last_slash_pos + 1]
                try:
                    os.chdir(cwd)
                except OSError:
                    eprint(f"{SHELL_NAME}: cd: Failed to go up one directory")
            else:
                try:
                    os.chdir(arg)
                except OSError:
                    eprint(f"{SHELL_NAME}: cd: {arg}: No such file or directory")
        else:
            try:
                os.chdir(os.path.expanduser("~"))
            except OSError:
                eprint(f"{SHELL_NAME}: cd: Failed to change to home directory")
        return
    
    if tokens[0] == HISTORY_COMMAND:
        if tokens_len > 1:
            flag = tokens[1]
            if flag == "-c":
                history.clear()
            elif flag == "-w":
                history_file = f"{os.getenv('HOME')}/{HISTORY_FILE_NAME}"
                with open(history_file, "w") as f:
                    for cmd in history:
                        f.write(f"{cmd}\n")
            else:
                eprint(f"{SHELL_NAME}: {HISTORY_COMMAND}: {flag}: invalid option")
        else:
            for i, cmd in enumerate(history):
                print(f"    {i + 1}. {cmd}")
        return
    
    stdin_status = handle_redirect_stdin(cmd, tokens)
    if stdin_status[0] == -1:
        return
    stdout_status = handle_redirect_stdout(cmd, tokens)
    if stdout_status[0] == -1:
        return

    cid = os.fork()
    if cid == 0:
        strs_to_remove = ("<", ">", ">>")
        for str in strs_to_remove:
            while str in tokens:
                tokens.remove(str)
        
        try:
            os.execvp(tokens[0], tokens)
        except OSError:
            eprint(f"{SHELL_NAME}: {tokens[0]}: command not found")
            sys.exit(1)
    
    os.wait()
    if stdin_status[0]:
        os.dup2(stdin_status[1], sys.stdin.fileno())
    if stdout_status[0]:
        os.dup2(stdout_status[1], sys.stdout.fileno())

def execute_commands_and_pipes(cmd: str) -> None:
    pipe_chr_pos = cmd.find("|")
    if pipe_chr_pos != -1:
        tokens = [token.strip() for token in cmd.split("|")]
        terminal_stdin = os.dup(sys.stdin.fileno())
        terminal_stdout = os.dup(sys.stdout.fileno())

        tokens_len = len(tokens)
        i = 0
        while i < tokens_len - 1:
            fd = os.pipe()
            cid = os.fork()
            if cid == 0:
                os.dup2(fd[1], sys.stdout.fileno())
                os.close(fd[0])
                execute_command(tokens[i])
                sys.exit(0)
            os.wait()
            os.dup2(fd[0], sys.stdin.fileno())
            os.close(fd[1])
            i += 1

        execute_command(tokens[i])
        os.dup2(terminal_stdout, sys.stdout.fileno())
        os.dup2(terminal_stdin, sys.stdin.fileno())
        return
    
    execute_command(cmd)

def process_command(cmd: str) -> None:
    comment_chr_pos = cmd.find(COMMENT_CHAR)
    if comment_chr_pos != -1:
        cmd = cmd[:comment_chr_pos]
    
    semicolon_chr_pos = cmd.find(";")
    if semicolon_chr_pos != -1:
        for token in cmd.split(";"):
            token = token.strip()
            if token:
                execute_commands_and_pipes(token)
        return
    
    execute_commands_and_pipes(cmd)

def print_intro() -> None:
    print(f"Welcome to {SHELL_NAME}! (Python version)")
    print(f"Type '{EXIT_COMMAND}' to exit.\n")

def print_prompt() -> None:
    global cwd
    cwd = os.getcwd()
    is_root = os.getuid() == 0
    if is_root:
        print(f"\033[1;31m%s-root:\033[1;34m%s\033[0m# " % (SHELL_NAME, cwd), end="")
    else:
        print(f"%s:\033[1;34m%s\033[0m$ " % (SHELL_NAME, cwd), end="")

def main(argc: int, argv: list[str]) -> int:
    if platform.system() == "Windows":
        eprint(f"""It looks like you are using Windows.
{SHELL_NAME} is not supported on Windows and only works on Unix-like systems such as Linux and macOS.""")
        return 1

    if argc > 1:
        try:
            with open(argv[1], "r") as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith(COMMENT_CHAR):
                        process_command(line)
        except FileNotFoundError:
            eprint(f"{SHELL_NAME}: {argv[1]}: No such file or directory")
            return 1
    else:
        history_file = f"{os.getenv('HOME')}/{HISTORY_FILE_NAME}"
        try:
            with open(history_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith(COMMENT_CHAR):
                        history.add(line)
        except FileNotFoundError:
            pass

        stdin_from_terminal = os.isatty(sys.stdin.fileno())
        if stdin_from_terminal:
            print_intro()
            print_prompt()

        while True:
            try:
                try:
                    cmd = input().strip()
                except EOFError:
                    print(f"\n{EXIT_COMMAND}")
                    break

                if cmd.startswith("!"):
                    cmd_len = len(cmd)
                    if cmd_len <= 1:
                        print_prompt()
                        continue

                    index = 1
                    is_negative = False
                    if cmd[index] == "-":
                        is_negative = True
                        index += 1

                    if cmd[index] == "!":
                        if len(history) == 0:
                            eprint(f"{SHELL_NAME}: !!: event not found")
                            print_prompt()
                            continue
                        cmd = history.last() + cmd[2:]
                    elif cmd[index].isdigit():
                        history_number = 0
                        while index < cmd_len and cmd[index].isdigit():
                            history_number = history_number * 10 + int(cmd[index])
                            index += 1
                        
                        if is_negative:
                            history_index = len(history) - history_number
                            if history_index < 0:
                                eprint(f"{SHELL_NAME}: !-{history_number}: event not found")
                                print_prompt()
                                continue
                        else:
                            if history_number <= 0 or history_number > len(history):
                                eprint(f"{SHELL_NAME}: !{history_number}: event not found")
                                print_prompt()
                                continue
                            history_index = history_number - 1
                        
                        history_cmd = history[history_index]
                        cmd = history_cmd + cmd[index:]
                    else:
                        eprint(f"{SHELL_NAME}: {cmd}: event not found")
                        print_prompt()
                        continue

                    print(cmd)
                
                if cmd and not cmd.startswith(COMMENT_CHAR):
                    if not history.last() == HISTORY_COMMAND or not cmd == HISTORY_COMMAND:
                        history.add(cmd)
                    if cmd == EXIT_COMMAND:
                        print(f"{EXIT_COMMAND}")
                        break
                    process_command(cmd)
                
                if stdin_from_terminal:
                    print_prompt()
            except KeyboardInterrupt:
                print()
                print_prompt()
    
    return 0

if __name__ == "__main__":
    sys.exit(main(len(sys.argv), sys.argv))
