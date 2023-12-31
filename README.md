# alsh-py
A custom UNIX shell written in Python, originally written in C as [alsh](https://github.com/AlanLuu/alsh).

**NOTE**: alsh-py only works on Unix-like systems such as Linux and macOS. It requires Python 3.8 or higher on the aforementioned systems. It will **not** work on Windows as it uses several functions from the `os` module that are not available on Windows.

# Features
- Execute commands (e.g. `ls`)
- Execute commands with arguments and flags (e.g. `ls -la /`)
- Execute commands with redirection `<` `>` `>>`
- Execute commands with pipes `|`
- Execute multiple commands separated by `;` on the same line
    - Given the statement `cmd1; cmd2`, `cmd1` and `cmd2` are executed sequentially
- Other operators
    - `&&`: Given the statement `cmd1 && cmd2`, `cmd2` is executed if and only if `cmd1` returns an exit status of 0, which indicates success
    - `||`: Given the statement `cmd1 || cmd2`, `cmd2` is executed if and only if `cmd1` returns a non-zero exit status, which indicates failure
- View command history with `history` and execute previous commands with `!n`, where `n` is the command number in the history list (e.g. `!3` will execute the third command in the history list)
    - To execute the previous command, use `!!`
    - To execute the command `n` lines back in the history list, use `!-n` (e.g. `!-2` will execute the command 2 lines back in the history list)
    - To clear the history list, use `history -c`
    - To write the history list to a file, use `history -w`, which will write the list to `~/.alsh_history`

# Run
(Requires Python 3.8+)
```
git clone https://github.com/AlanLuu/alsh-py.git
cd alsh-py
python3 alsh.py
```

# License
alsh-py is distributed under the terms of the [MIT License](https://github.com/AlanLuu/alsh-py/blob/main/LICENSE).
