import os
import sys
import time
import errno
import signal
import webbrowser
from datetime import datetime

FILE_MODE = 0o777
TIME_STR_MAX_LEN = 32
MAX_PATHNAME_LEN = 50
INPUT_MAX_LENGTH = 2048
MAX_TOKEN_NUM = 128
MAX_CHILD_NUM = 20

# Define LOG_FILE constant
LOG_FILE = "logs/Hist.log"

block_mask = None
orig_mask = None
signal_received = False

def check_usage():
    if len(sys.argv) != 1:
        sys.stderr.write("Program is used incorrectly.\n"
                         "The usage is ./StK\n"
                         "This program does not take any argument\n")
        sys.exit(errno.EINVAL)


def set_signal_handlers():
    global block_mask, orig_mask
    sa_clean = None
    sa_clean = signal_handler
    sa_clean.sa_handler = cleaner_signal_handler
    signal.signal(signal.SIGINT, sa_clean)
    signal.signal(signal.SIGTSTP, sa_clean)
    signal.signal(signal.SIGQUIT, sa_clean)


def add_mask():
    global orig_mask
    orig_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [signal.SIGCHLD])

def add_additional_mask():
    global orig_mask
    signal.pthread_sigmask(signal.SIG_UNBLOCK, orig_mask)


def remove_mask():
    global orig_mask
    signal.pthread_sigmask(signal.SIG_SETMASK, orig_mask)


def prompt():
    current_path = os.getcwd()
    print("\x1B[32m\nStK-shell(BASH):\x1B[0m", "\x1B[34m" + current_path + "\x1B[0m", "$ ", end="")


def prompt_help():
    print("\nStK Shell, version 1.1\n"
          "Supported internal commands are: 'cd', ':q', 'help'\n"
          "Pipes are supported but at most there can be 19 pipe(20 processes)\n"
          "Ex. 'ls -la | grep file'\n"
          "Redirections are supported\n"
          "Ex. 'ls > file'\n"
          "Redirections and pipes can be mixed\n"
          "Ex. 'ls -la | grep file > results.txt'\n")


def get_input(buffer_size):
    try:
        input_buffer = input()
        return input_buffer
    except EOFError:
        print("Exiting...")
        return None  # Returning None to indicate an exit condition


def parse_buffer(buf, c):
    tokens = buf.split(c)
    tokens = [token.strip() for token in tokens]
    return tokens


def remove_space(buf):
    buf = buf.strip()
    return buf


def execute_pipeline(commands, number_of_token):
    global signal_received
    fd = []
    for i in range(number_of_token):
        fd.append([None, None])

    if not check_process_num(number_of_token):
        return

    for i in range(number_of_token):
        create_pipe(fd, number_of_token, i)
        child_pid = os.fork()

        if child_pid == 0:
            remove_mask()
            handle_child_pipeline(fd, number_of_token, i)
            if '<' in commands[i]:
                argv = parse_buffer(commands[i], '<')
                if not check_incorrect_redirect(len(argv)):
                    sys.exit(errno.EINVAL)
                execute_redirect(argv, number_of_token, '<')
            elif '>' in commands[i]:
                argv = parse_buffer(commands[i], '>')
                if not check_incorrect_redirect(len(argv)):
                    sys.exit(errno.EINVAL)
                execute_redirect(argv, number_of_token, '>')
            else:
                argv = parse_buffer(commands[i], ' ')
                os.execvp(argv[0], argv)
                sys.stderr.write("Incorrect input\n")
                sys.exit(errno.EINVAL)

        elif child_pid == -1:
            sys.stderr.write("fork failed\n")
            sys.exit(errno.EINVAL)

        else:
            add_additional_mask()
            handle_parent_pipeline(fd, i)
            os.wait()
            logger_command(commands[i], child_pid)

        remove_mask()


def check_process_num(num):
    if num > MAX_CHILD_NUM:
        sys.stderr.write("The program does not support that many processes in a pipe!\n")
        return False
    return True


def check_open_file(fd):
    if fd == -1:
        sys.stderr.write("cannot open file\n")
        return False
    return True


def check_incorrect_redirect(number_of_token):
    if number_of_token != 2:
        sys.stderr.write("Incorrect input redirection!"
                         "(has to be in this form: command < file or command > file)\n")
        return False
    return True


def create_pipe(fd, limit, i):
    if i != limit - 1:
        if i < 0 or i >= MAX_CHILD_NUM:
            sys.stderr.write("invalid index for fd array\n")
            sys.exit(errno.EINVAL)

        try:
            fd[i][0], fd[i][1] = os.pipe()
        except OSError:
            sys.stderr.write("pipe creating was not successful\n")
            sys.exit(errno.EINVAL)


def handle_child_pipeline(fd, limit, i):
    if i != limit - 1:
        os.dup2(fd[i][1], 1)
        os.close(fd[i][0])
        os.close(fd[i][1])

    if i != 0:
        os.dup2(fd[i - 1][0], 0)
        os.close(fd[i - 1][1])
        os.close(fd[i - 1][0])


def handle_parent_pipeline(fd, i):
    if i != 0:
        os.close(fd[i - 1][0])
        os.close(fd[i - 1][1])


def execute_redirect(commands, number_of_token, c):
    fd = None
    remove_space(commands[1])
    argv = parse_buffer(commands[0], ' ')

    if c == '<':
        fd = os.open(commands[1], os.O_RDONLY | os.O_CREAT, FILE_MODE)
        if not check_open_file(fd):
            sys.exit(errno.EINVAL)
        os.dup2(fd, 0)
        os.close(fd)

    elif c == '>':
        fd = os.open(commands[1], os.O_WRONLY | os.O_CREAT, FILE_MODE)
        if not check_open_file(fd):
            sys.exit(errno.EINVAL)
        os.dup2(fd, 1)
        os.close(fd)

    os.execvp(argv[0], argv)
    sys.stderr.write("Incorrect input\n")
    sys.exit(errno.EINVAL)


def execute_single_redirect(commands, number_of_token, c):
    fd = None
    remove_space(commands[1])
    argv = parse_buffer(commands[0], ' ')
    child_pid = os.fork()

    if child_pid == 0:
        remove_mask()
        if c == '<':
            fd = os.open(commands[1], os.O_RDONLY, FILE_MODE)
            if not check_open_file(fd):
                sys.exit(errno.EINVAL)
            os.dup2(fd, 0)
            os.close(fd)
        elif c == '>':
            fd = os.open(commands[1], os.O_WRONLY, FILE_MODE)
            if not check_open_file(fd):
                sys.exit(errno.EINVAL)
            os.dup2(fd, 1)
            os.close(fd)
        else:
            sys.exit(errno.EINVAL)
        os.execvp(argv[0], argv)
        sys.stderr.write("Incorrect input\n")
        sys.exit(errno.EINVAL)

    elif child_pid == -1:
        sys.stderr.write("fork failed\n")
        sys.exit(errno.EINVAL)

    else:
        add_additional_mask()
        os.wait()
        logger_command(' '.join(commands), child_pid)

    remove_mask()


def execute_single(commands, number_of_token):
    child_pid = os.fork()

    if child_pid == 0:
        remove_mask()
        os.execvp(commands[0], commands)
        sys.stderr.write("Incorrect input\n")
        sys.exit(errno.EINVAL)

    elif child_pid == -1:
        sys.stderr.write("fork failed\n")
        sys.exit(errno.EINVAL)

    else:
        add_additional_mask()
        os.wait()
        logger_command(' '.join(commands), child_pid)

    remove_mask()


def run_cd(argv, number_of_argv):
    if number_of_argv > 2:
        sys.stderr.write("\ncd: too many arguments\n")
        return
    elif not argv[1]:
        os.chdir("/")
    else:
        try:
            os.chdir(argv[1])
        except FileNotFoundError:
            sys.stderr.write(f" {argv[1]}: no such directory\n")


def clean_up(input_buffer, tokens, argv, sub_argv, single_command, number_of_token):
    global signal_received
    signal_received = False
    input_buffer = ""  # clear input buffer
    single_command = ""  # clear single_command
    number_of_token = 0  # reset number of tokens
    clean_tokens(tokens)
    clean_tokens(argv)
    clean_tokens(sub_argv)


def clean_tokens(tokens):
    for i in range(min(MAX_TOKEN_NUM, len(tokens))):
        if tokens[i] is not None:
            tokens[i] = None

def logger_command(command, child_pid):
    time_str = current_time_string()
    buffer = ""
    fd = None

    try:
        buffer = open_file(time_str, buffer)
        if buffer is not None:
            write_to_file(fd, time_str, buffer, child_pid, command)
    finally:
        if fd is not None:
            close_file(fd)


def current_time_string():
    ts = time.time()
    timeinfo = time.localtime(ts)
    buffer = time.strftime("log_%Y_%m_%d_%H.%M.%S", timeinfo)
    buffer += f".{ts % 1:.9f}"
    return buffer


def tidy_time_str(time_str):
    if time_str and time_str[-1] == '\n':
        return time_str[:-1]
    return time_str


def open_file(time_str, buffer):
    try:
        fd = os.open(LOG_FILE, os.O_CREAT | os.O_WRONLY | os.O_APPEND)
        if fd < 0:
            raise OSError("Failed to open file")
        bytes_written = os.write(fd, f"Time: {time_str}\nCommand: {buffer}\n".encode())
        return fd
    except OSError as e:
        print(f"Error opening file: {e}")
        sys.exit(1)

def write_to_file(fd, time_str, buffer, child_pid, command):
    try:
        if fd is not None:
            bytes_written = os.write(fd, f"PID: {child_pid}\nCommand: {command}\n".encode())
            if bytes_written < 0:
                sys.stderr.write("Error while formatting log message\n")
                sys.exit(errno.EINVAL)
    except OSError as e:
        sys.stderr.write(f"Error while writing to log file: {e}\n")
        sys.exit(errno.EINVAL)

def close_file(fd):
    try:
        os.close(fd)
    except OSError as e:
        sys.stderr.write(f"Error while closing log file: {e}\n")
        sys.exit(errno.EINVAL)


def signal_handler(signum, frame):
    global signal_received
    signal_received = True


def cleaner_signal_handler(s):
    if s == signal.SIGINT:
        signal_name = "SIGINT"
    elif s == signal.SIGTSTP:
        signal_name = "SIGTSTP"
    elif s == signal.SIGQUIT:
        signal_name = "SIGQUIT"
    else:
        signal_name = "UNKNOWN SIGNAL"

    sys.stdout.write("\n")
    sys.stdout.write(signal_name)
    sys.stdout.write(" signal is received\n")
    sys.stdout.flush()
    global signal_received
    signal_received = True


def main():
    check_usage()
    set_signal_handlers()
    print("StK TE Has Loaded")

    input_buffer = ""
    single_command = ""
    tokens = [None] * MAX_TOKEN_NUM
    argv = [None] * MAX_TOKEN_NUM
    sub_argv = [None] * MAX_TOKEN_NUM
    number_of_token = 0
    i = -1

    while True:
        add_mask()
        i += 1

        if i > 0:
            clean_up(input_buffer, tokens, argv, sub_argv, single_command, number_of_token)

        prompt()
        input_buffer = get_input(INPUT_MAX_LENGTH)

        if signal_received:
            continue

        if input_buffer == "\n":
            continue
        elif '|' in input_buffer:
            tokens = parse_buffer(input_buffer, '|')
            number_of_token = len(tokens)
            execute_pipeline(tokens, number_of_token)
        elif '>' in input_buffer:
            tokens = parse_buffer(input_buffer, '>')
            number_of_token = len(tokens)
            if check_incorrect_redirect(number_of_token):
                execute_single_redirect(tokens, number_of_token, '>')
        elif '<' in input_buffer:
            tokens = parse_buffer(input_buffer, '<')
            number_of_token = len(tokens)
            if check_incorrect_redirect(number_of_token):
                execute_single_redirect(tokens, number_of_token, '<')
        else:
            tokens = parse_buffer(input_buffer, ' ')
            number_of_token = len(tokens)
            if tokens[0] == ":q":
                break
            elif tokens[0] == "cd":
                run_cd(tokens, number_of_token)
            elif tokens[0] == "help":
                prompt_help()
            else:
                execute_single(tokens, number_of_token)

    clean_up(input_buffer, tokens, argv, sub_argv, single_command, number_of_token)
    print("\nBYE")

if __name__ == "__main__":
    main()
