import Module

bridge = {}

for module in Module.__all__:
    bridge[module] = __import__(f"Module.{module}")