# StK Shell (Python Implementation)

# WARNING!!! You Cannot Use StK On Windows Or Any OS That Doesn't Use Bash

# StK 1.1!!! Log:
- All Issues fixed
- Doesn't crash after typing one command
- First Solid Issueless Version

## Linux Usage
- Python 3.8 or higher
- webbrowser library (`pip3 install webbrowser`)

## Opening StK
- Clone It With Git:
```shell
git clone https:/github.com/SFYMMIK/StK.git
```
- Go To StK's Directory:
```shell
cd ~/StK
```
- Open It:
```shell
python3 StK.py
```

## Signal Handling
- The program sets up signal handlers for `SIGINT`, `SIGTSTP`, and `SIGQUIT` to handle interruptions and termination gracefully.

## Input Processing
- The `prompt()` function displays the current working directory and a prompt for user input.
- The `get_input(buffer_size)` function reads user input, with a maximum length defined by `INPUT_MAX_LENGTH`.

## Command Parsing
- The program parses user input into tokens using the `parse_buffer(buf, c)` function, where `c` is the delimiter.

## Pipeline Execution
- The program supports pipelines using the `execute_pipeline(commands, number_of_token)` function.
- It forks child processes for each command in the pipeline, setting up pipes for communication between them.

## Redirection
- The program supports input and output redirection using `<` and `>` operators.

## Internal Commands
- Internal commands include `cd`, `:q` (to exit), and `help`.
- The `run_cd(argv, number_of_argv)` function handles changing the current working directory.

## Logging
- The program logs executed commands and their associated process IDs (PIDs) to a file specified by the `LOG_FILE` constant.

## Error Handling
- The program includes error handling for various scenarios, such as incorrect input redirection and file-related errors.

## Cleanup and Exit
- The `clean_up()` function resets variables and buffers when necessary.
- The program exits when the user enters `:q`.

## User Interface
- The main loop continuously prompts the user for input and executes commands until the user exits.
