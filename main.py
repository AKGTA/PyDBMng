import Module.hook as hook
import time

metatable = "databaseV1"
player_table = {}
item_toSave = []  # Kept exactly as your original global state variable

class Player():
    def __init__(self, id=None, name=None, age=None, male=None):
        if id:
            player_table[id] = self
        self.id = [id] if id is not None else None  # Preserved exact array nesting
        self.name = name
        self.age = age
        self.male = male

    def get_save_data(self):
        return [self.id, [(self.name, self.age, self.male)]]

    def set_info(self, rawData):
        id, data = rawData
        self.id = id
        self.name = data[-1][0]
        self.age = data[-1][1]
        self.male = data[-1][2]

    def save_info(self):
        global item_toSave
        item_toSave = self.get_save_data()  # Sets the global target to THIS player's exact array structure
        hook.save(metatable)                # Instantly triggers saver() via the hook system


def saver():
    global item_toSave
    return item_toSave  # Returns exactly the [ [id], [(name, age, male)] ] format expected by the hook

def loader(loadData):
    # Directly feeds the exact structure back into set_info without outer arrays breaking it
    id = loadData[0]
    if id and len(id) > 0:
        if not id[0] in player_table:
            player_table[id[0]] = Player()  # Create a new Player instance if it doesn't exist

        player_table.get(id[0], Player()).set_info(rawData=loadData)
        print(loadData)

def update_allPlayerSave():
    for _, player in enumerate(player_table):
        if isinstance(player, Player):
            player.save_info()

if __name__ == "__main__":
    try:
        hook.syncHook(metatable, loader, saver)
    except Exception as e:
        print(f"Error occurring {e}")
        hook.deleteSaveTable(metatable)

    # Added parentheses () to Alex's save call so it actually triggers
    Player(1, "Alice", 19, False).save_info()
    Player(2, "Alex", 20, True).save_info()

    while True:
        try:
            time.sleep(1)

        except KeyboardInterrupt:
            print(f"Stopping the loops")
            break
        except Exception as e:
            print(f"Error watch {e}")
