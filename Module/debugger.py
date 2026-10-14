import inspect
from datetime import datetime
import functools
import os

DEBUG = True

def debug_state(state=False):
    global DEBUG
    DEBUG = state

# SINGLE TRUTH SOURCE FOR LOG PRINTING
def _execute_log_print(caller_frame, title_or_msg, msg, func=None, all_params=None, result=None):
    bold = "\033[1m"
    underline = "\033[4m"
    magenta_color = "\033[35m"
    blue_color = "\033[34m"
    cyan_color = "\033[36m"
    red_color = "\033[31m"
    yellow_color = "\033[33m"
    green_color = "\033[32m"
    normalize_color = "\033[0m"

    timestamp = f"🕒 {datetime.now().strftime('%H:%M:%S')} | "
    
    while caller_frame and caller_frame.f_code.co_name == 'wrapper':
        caller_frame = caller_frame.f_back
    if not caller_frame:
        return

    lineno = caller_frame.f_lineno
    filename = caller_frame.f_globals.get("__file__", "<stdin>").replace("\\", "/").split("/")[-1]
    func_name = caller_frame.f_code.co_name
    
    display_func_name = func.__name__ if func else func_name
    location_string = f"{blue_color}{display_func_name}({green_color}{all_params if all_params else ''}{blue_color}){normalize_color}" if display_func_name != '<module>' else '<module>'
    
    print("\n" + "~" * 100)
    print(f"[DEBUG @{filename} line:{lineno} inside {location_string}]")

    # Safe Title Print
    try:
        base_title = (
            f"{underline}{bold}{magenta_color}{title_or_msg}" if title_or_msg is not None 
            else f"Executing: {func.__name__ if func else 'Checkpoint'}"
        )
        print(timestamp + str(base_title) + normalize_color)
    except Exception as e:
        print(timestamp + red_color + f"[TITLE ERROR]: {yellow_color}Failed to convert title to string -> {e}" + normalize_color)

    # Safe Comments Print
    for comment in msg:
        try:
            print(" ➤ ", cyan_color + str(comment) + normalize_color)
        except Exception as e:
            # The singular, absolute place this error text exists now:
            print(timestamp + red_color + "[COMMENT ERROR]: " + yellow_color + f"Failed to print comment -> {e}" + normalize_color)

    # Safe Execution Context Print
    if func is not None:
        try:
            print(timestamp + f"↳ {yellow_color}Executed: {blue_color}{func.__name__}({green_color}{all_params}{blue_color}){normalize_color} | Returned: {green_color}{result}" + normalize_color)
        except Exception as e:
            print(timestamp + red_color + f"[FUNCTION PRINT ERROR]: {yellow_color}{e}" + normalize_color)
            try:
                print(f" ➤ {red_color}[FALLBACK FUNCTION NAME]: {blue_color}{func.__name__}" + normalize_color)
                print(f" ➤ {yellow_color}[FALLBACK PARAMS]: {cyan_color}{all_params}" + normalize_color)
                print(f" ➤ {red_color}[FALLBACK RETURN TYPE]: {yellow_color}{type(result).__name__}" + normalize_color)
            except Exception as inner_e:
                print(f" ➤ {red_color}[CRITICAL LOGGING ERROR]: {yellow_color}Improvised print failed -> {inner_e}" + normalize_color)

        print("~" * 100)


def debug(title_or_msg=None, *msg, func=None):
    """ Bulletproof drop-in debug function. """
    if callable(title_or_msg) and not msg and func is None:
        func = title_or_msg
        title_or_msg = None

    if func is None:
        caller_frame = inspect.currentframe().f_back
        is_decorator = False
        if caller_frame:
            try:
                filename = caller_frame.f_globals.get("__file__")
                lineno = caller_frame.f_lineno
                if filename and os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        if 0 <= lineno - 1 < len(lines):
                            if lines[lineno - 1].strip().startswith('@'):
                                is_decorator = True
            except Exception:
                pass
                
        if is_decorator:
            def decorator(actual_func):
                return debug(title_or_msg, *msg, func=actual_func)
            return decorator

        if not DEBUG:
            return
            
        _execute_log_print(caller_frame, title_or_msg, msg)
        return

    if not DEBUG:
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        caller_frame = inspect.currentframe().f_back
        result_error = None
        
        red_color = "\033[31m"
        yellow_color = "\033[33m"
        blue_color = "\033[34m"
        green_color = "\033[32m"
        normalize_color = "\033[0m"

        try:
            str_args = ", ".join(repr(arg) for arg in args)
            str_kwargs = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
            all_params = ", ".join(filter(None, [str_args, str_kwargs]))
        except Exception as e:
            all_params = f"{red_color}[REPR ERROR]: {yellow_color}Could not parse arguments -> {repr(e)}"

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            result = f"None \n{red_color}[FUNCTION ERROR]: \n{blue_color}{func.__name__}({green_color}{all_params or ''}{blue_color}): \n   {yellow_color}Error: {e or 'Unknown'}" + normalize_color
            result_error = e
            
        _execute_log_print(caller_frame, title_or_msg, msg, func, all_params, result)
        return result if not result_error else None
    return wrapper


# --- Robustness Edge-Case Tests ---
class UnprintableObject:
    def __str__(self): raise ValueError("Print is not allowed here!!")
    def __repr__(self): raise SystemError("Cannot represent me!!")

@debug("Testing broken __str__ handling")
def process_data(bad_obj):
    debug(bad_obj, bad_obj)
    
    return bad_obj

if __name__ == "__main__":
    broken = UnprintableObject()
    process_data(broken)
