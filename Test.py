import Module.hook as hook
import time

data = 0
id = [0]
newdata = "String Data"
id2 = [0]

def loader(item):
    global data, id
    if item and isinstance(item, list) and len(item) > 0:
        newid, syncData = item
        val = syncData[-1][0]
        # Safety Cast: If SQLite returned it as a string, force it back to an int
        try:
            data = int(val)
            id = newid
        except (ValueError, TypeError):
            data = 0 # Default fallback if it's a completely broken string
    print(f"id: {id} Loaded!! New state: {data}")

def saver():
    global data, id
    print(f"Saving Data... State is: {data}")
    return [id, [(data,)]]

def second_loader(item):
    global newdata, id2
    if item and isinstance(item, list) and len(item) > 0:
        # Extracts data from SQLite tuple array safely
        id, syncData = item
        newdata = syncData[-1][0]
        id2 = id
    print(f"id: {id2} Second Loader!! New state: {newdata}")

def second_saver():
    global newdata, id2
    print(f"Saving Second Data... State is: {newdata}")
    return [id2, [(newdata,)]]

hook.deleteSaveTable("Test")
hook.deleteSaveTable("Test2")

# Register the hook. It immediately triggers your original sync flow.
hook.syncHook("Test", loader, saver)
hook.syncHook("Test2", second_loader, second_saver)
print(f"Initial printed data: {data}")
print(f"Initial printed newdata: {newdata}")

# Modify data
data += 2
print(f"Data manually bumped to: {data}")
print(f"Newdata manually updated to: {newdata}")

# Target updates cleanly without breaking the companion hooks
hook.syncHook("Test", savecall=saver)
hook.syncHook("Test", loadcall=loader)


data = 1

# Keep main script alive to watch your self-contained module loops automatically run
print("\nMonitoring internal module background loops (Ctrl+C to exit)...")
try:
    while True:
        time.sleep(1)
        data += 1
        newdata += "!"
except KeyboardInterrupt:
    print("Exiting...")