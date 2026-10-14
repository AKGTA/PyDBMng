import sqlite3
import time
import threading

if __name__ == "__main__":
    from debugger import debug, debug_state

else:
    from Module.debugger import debug, debug_state

db_lock = threading.Lock()

conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()
callhook = {}
saves = {}

#Helper function to determine the SQLite column type based on Python data type
def ensureTable(target_table, rows):
    def sqlType(v):
        if isinstance(v, bool): return "NUMERIC"
        if isinstance(v, int): return "INTEGER"
        if isinstance(v, float): return "REAL"
        return "TEXT"

    first = rows[0]
    items = first.items() if isinstance(first, dict) else ((f"col_{i}", v) for i, v in enumerate(first))
    items = [(k, v) for k, v in items if k != "id"]

    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info([{target_table}])")
    existing = {info[1] for info in cur.fetchall()}

    if not existing:
        cols = ", ".join(f"[{k}] {sqlType(v)}" for k, v in items)
        cur.execute(f"CREATE TABLE [{target_table}] (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})")
    else:
        for k, v in items:
            if k not in existing:
                cur.execute(f"ALTER TABLE [{target_table}] ADD COLUMN [{k}] {sqlType(v)}")

    cur.close()

@debug(
    "Delete existing table", 
    "This drops every single item in the table", 
    "The function needed the table name to be able to know which table to drop"
)
def deleteSaveTable(table):
    global conn, cursor, saves, callhook
    
    # Ensure the cursor is open and active
    try:
        cursor.execute("SELECT 1")
    except (sqlite3.ProgrammingError, sqlite3.InterfaceError, AttributeError):
        cursor = conn.cursor()
        
    try:
        # Drop the table entirely from the database file
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        # Clear its tracking history out of the auto-increment sequence registry
        cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
        
        # Wipe it out of active runtime memory so background loops ignore it
        saves.pop(table, None)
        callhook.pop(table, None)
        
        conn.commit()
        debug(f"Table '{table}' and all of its save states have been completely deleted.")
    except sqlite3.OperationalError as e:
        debug(f"Error while deleting table '{table}': {e}")

@debug("Load data from the database", 
    "This loaded every table in the database by default",
    "Input table name to load only specific table",
    "Input row number and column number to pinpoint the exact data"
)
def loadSave(table=None, row=None, column=None):
    global conn, saves
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT 1")
    except (sqlite3.ProgrammingError, sqlite3.InterfaceError, AttributeError):
        cursor = conn.cursor()

    def loader(target_table):
        selection = ", ".join(column) if isinstance(column, list) else (column if column else "*")
        query = f"SELECT {selection} FROM {target_table}"
        parameters = ()

        if row and isinstance(row, dict):
            where_clauses = [f"{key} = ?" for key in row.keys()]
            query += " WHERE " + " AND ".join(where_clauses)
            parameters = tuple(row.values())

        try:
            cursor.execute(query, parameters)
            results = cursor.fetchall()
            
            # If we selected everything (*), strip out the 'id' column (index 0) from every row
            if not column or column == "*":
                saves[target_table] = [[row[0] for row in results], [row[1:] for row in results]]
            else:
                saves[target_table] = results
                
            return results
        
        except sqlite3.OperationalError as e:
            debug(f"Error loading table '{target_table}': {e}")
            return None

    if table is not None:
        final_results = loader(table)
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        all_tables = [r[0] for r in cursor.fetchall()]
        final_results = {}
        for t_name in all_tables:
            table_data = loader(t_name)
            if table_data is not None:
                final_results[t_name] = table_data

    cursor.close()
    return final_results

@debug(
    "Save table to the database",
    "Input table of column type and input unexisted table will create new table with the column type specified",
    "If tablee already existed it will do a normal saves"
)
def insertSave(table=None, id=None):
    global conn, cursor, saves
    cursor = conn.cursor()

    if table is not None and table not in saves:
        return

    try:
        cursor.execute("SELECT 1")
    except (sqlite3.ProgrammingError, sqlite3.InterfaceError, AttributeError, sqlite3.OperationalError):
        cursor = conn.cursor()

    def inserter(target_table, data_package):
        # Safely split your custom hook format [ids, info] if it exists
        if isinstance(data_package, list) and len(data_package) == 2 and isinstance(data_package[0], list):
            ids_list, rows = data_package
        else:
            ids_list = []
            rows = data_package

        if not rows:
            return

        if isinstance(rows, dict):
            rows = [rows]
        elif isinstance(rows, (list, tuple)) and not (rows and isinstance(rows[0], (list, tuple, dict))):
            rows = [rows]

        ensureTable(target_table, rows)   # <-- add this

        if id is not None:
            if isinstance(rows[0], dict):
                for i, row in enumerate(rows):
                    row['id'] = id
                columns = list(rows[0].keys())
                safe_cols = ", ".join(f"[{c}]" for c in columns)
                placeholders = ", ".join(["?"] * len(columns))
                query = f"INSERT OR REPLACE INTO [{target_table}] ({safe_cols}) VALUES ({placeholders})"
                data_tuples = [tuple(row[col] for col in columns) for row in rows]
                # Add this check right before your query executions to catch the raw text:
                cursor.executemany(query, data_tuples)
            
            elif isinstance(rows[0], (list, tuple)):
                cursor.execute(f"PRAGMA table_info([{target_table}])")
                # FIX: Extract the column name (info[1]) but EXCLUDE the 'id' column 
                # because your loop manually attaches active_id at the front!
                columns = [info[1] for info in cursor.fetchall() if info[1] != 'id']
                
                # SAFETY FALLBACK: If thread collisions clear out columns, match them to your data length
                if not columns and rows[0]:
                    columns = [f"col_{x}" for x in range(len(rows[0]))]
                
                # Now include the explicit ID column at the start of your text keys
                safe_cols = ", ".join(f"[{c}]" for c in ["id"] + columns)
                placeholders = ", ".join(["?"] * (len(columns) + 1))
                query = f"INSERT OR REPLACE INTO [{target_table}] ({safe_cols}) VALUES ({placeholders})"
                
                # Check if we have an ID list from your hook, otherwise fallback to the passed id
                data_tuples = []
                for i, row in enumerate(rows):
                    active_id = ids_list[i] if (ids_list and i < len(ids_list)) else id
                    data_tuples.append(tuple([active_id] + list(row)))

                # Add this check right before your query executions to catch the raw text:
                cursor.executemany(query, data_tuples)

    # Execution Router passes the entire package payload safely
    if table is not None:
        inserter(table, saves[table])
    else:
        for t_name, data_package in list(saves.items()):
            inserter(t_name, data_package)

    conn.commit()

def load(name=None):
    global saves, callhook
    if not saves:
        loadSave()

    elif name and not name in saves:
        loadSave(name)

    if name: 
        hooks = callhook.get(name) 
        if hooks and hooks[0] and name in saves: 
            hooks[0](saves[name]) 
    else: 
        for hookName, hooks in callhook.items(): 
            if hooks[0] and hookName in saves: 
                hooks[0](saves[hookName]) 

def save(name=None): 
    global saves, callhook

    if name: 
        hooks = callhook.get(name) 
        if hooks and hooks[1]: 
            saves[name] = hooks[1]() 
            
        if name in saves and saves[name]:
            # Safely unpack the IDs list and the info rows list
            ids_list, rows = saves[name]
            
            # Extract a concrete singular ID integer/string for condition routing
            single_id = ids_list if not (isinstance(ids_list, list) and ids_list) else ids_list[0]
            
            if isinstance(rows, dict): 
                rows = [rows]
            elif isinstance(rows, (list, tuple)) and not (rows and isinstance(rows[0], (list, tuple, dict))): 
                rows = [rows]

            insertSave(name, id=single_id)

    else: 
        for hookName, hooks in list(callhook.items()): 
            if hooks[1]: 
                save(name=hookName)

@debug(
    "Syncing custom load and save function to be called once save and load runs",
    "The output will out put the data based on the table name in the data base"
)
def syncHook(name, loadcall=None, savecall=None): 
    global callhook, saves
    if name not in callhook:
        callhook[name] = [None, None]

    if loadcall: 
        callhook[name][0] = loadcall 
    if savecall: 
        callhook[name][1] = savecall 

    if name in saves and loadcall:
        load(name)
    elif savecall:
        save(name)

@debug(
    "Background worker loop for automatic save and load",
    "This function runs in a separate thread to periodically save and load data.",
    "It checks the elapsed time since the last save/load and triggers the respective functions."
)
def _background_worker():
    last_save_time = time.time()
    last_load_time = time.time()

    while True:
        try:
            current_time = time.time()

            # Wrap loop actions inside the lock so manual saves wait their turn
            if current_time - last_load_time > 10:  
                with db_lock:
                    load()      
                last_load_time = current_time

            if current_time - last_save_time > 5:  
                with db_lock:
                    save()
                last_save_time = current_time

            time.sleep(1)  
        except Exception as e:
            print(f"Error in engine loop: {e}")
            time.sleep(1)


# Initial execution pull on module boot up so your runtime doesn't start empty
loadSave()

# Launch loop worker
threading.Thread(target=_background_worker, daemon=True).start()
