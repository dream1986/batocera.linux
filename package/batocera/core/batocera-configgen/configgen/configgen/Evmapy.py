#!/usr/bin/env python

import subprocess
import json
import re
import os
from utils.logger import eslog

class Evmapy():
    # evmapy is a process that map pads to keyboards (for pygame for example)
    __started = False

    @staticmethod
    def start(system, emulator, core, rom, playersControllers):
	if Evmapy.__prepare(system, emulator, core, rom, playersControllers):
            Evmapy.__started = True
	    subprocess.call(["batocera-evmapy", "start"])

    @staticmethod
    def stop():
        if Evmapy.__started:
            Evmapy.__started = False
	    subprocess.call(["batocera-evmapy", "stop"])

    @staticmethod
    def __prepare(system, emulator, core, rom, playersControllers):
        # consider files here in this order to get a configuration
        for keysfile in [
                "{}.keys" .format (rom),
                #"/userdata/system/config/evmapy/{}.{}.{}.keys" .format (system, emulator, core),
                #"/userdata/system/config/evmapy/{}.{}.keys" .format (system, emulator),
                "/userdata/system/config/evmapy/{}.keys" .format (system),
                #"/usr/share/evmapy/{}.{}.{}.keys" .format (system, emulator, core),
                #"/usr/share/evmapy/{}.{}.keys" .format (system, emulator),
                "/usr/share/evmapy/{}.keys" .format (system)
        ]:
            if os.path.exists(keysfile):
                eslog.log("evmapy on {}".format(keysfile))
                subprocess.call(["batocera-evmapy", "clear"])
    
                padActionConfig = json.load(open(keysfile))
    
                # configure each player
                nplayer = 1
                for playercontroller, pad in sorted(playersControllers.items()):
                    if "actions_player"+str(nplayer) in padActionConfig:
                        configfile = "/var/run/evmapy/{}.json" .format (re.sub(r'[^\w]', '.', pad.realName))
                        eslog.log("config file for keysfile is {} (from {})" .format (configfile, keysfile))
    
                        # create mapping
                        padConfig = {}
                        padConfig["axes"] = []
                        padConfig["buttons"] = []
                        padConfig["grab"] = False
    
                        # define buttons / axes
                        known_buttons = {}
                        for index in pad.inputs:
                            input = pad.inputs[index]
                            if input.type == "button":
                                known_buttons[input.name] = True
                                padConfig["buttons"].append({
                                    "name": input.name,
                                    "code": int(input.code)
                                })
                            elif input.type == "hat":
                                if int(input.value) in [1, 2]: # don't duplicate values
                                    if int(input.value) == 1:
                                        name = "X"
                                        isYAsInt = 0
                                    else:
                                        name = "Y"
                                        isYAsInt =  1 
                                    known_buttons["HAT" + input.id + name + ":min"] = True
                                    known_buttons["HAT" + input.id + name + ":max"] = True
                                    padConfig["axes"].append({
                                        "name": "HAT" + input.id + name,
                                        "code": int(input.id) + 16 + isYAsInt, # 16 = HAT0X in linux/input.h
                                        "min": -1,
                                        "max": 1
                                    })
                            elif input.type == "axis":
                                pass # to be implemented
    
                        # only add actions for which buttons are defined (otherwise, evmapy doesn't like it)
                        padActionsDefined = padActionConfig["actions_player"+str(nplayer)]
                        padActionsFiltered = []
                        for action in padActionsDefined:
                            if "trigger" in action:
                                trigger = Evmapy.__trigger_mapper(action["trigger"])
                                action["trigger"] = trigger
                                if isinstance(trigger, list):
                                    allfound = True
                                    for x in trigger:
                                        if x not in known_buttons:
                                            allfound = False
                                    if allfound:
                                        padActionsFiltered.append(action)
                                else:
                                    if trigger in known_buttons:
                                        padActionsFiltered.append(action)
                                padConfig["actions"] = padActionsFiltered
    
                        # save config file
                        with open(configfile, "w") as fd:
                            fd.write(json.dumps(padConfig, indent=4))
    
                    nplayer += 1
                return True
        # otherwise, preparation did nothing
        return False
    
    # remap evmapy trigger (aka up become HAT0Y:max)
    @staticmethod
    def __trigger_mapper(trigger):
        if isinstance(trigger, list):
            new_trigger = []
            for x in trigger:
                new_trigger.append(Evmapy.__trigger_mapper_string(x))
            return new_trigger
        return Evmapy.__trigger_mapper_string(trigger)

    @staticmethod
    def __trigger_mapper_string(trigger):
        # maybe this function is more complex if a pad has several hat. never see them.
        mapping = {
            "left": "HAT0X:min",
            "right": "HAT0X:max",
            "down": "HAT0Y:max",
            "up": "HAT0Y:min",
            "joystick1right": "ABS0X:min",
            "joystick1left": "ABS0X:max",
            "joystick1down": "ABS0Y:min",
            "joystick1up": "ABS0Y:max",
            "joystick2right": "ABS1X:min",
            "joystick2left": "ABS1X:max",
            "joystick2down": "ABS1Y:min",
            "joystick2up": "ABS1Y:max"
        }
        if trigger in mapping:
            return mapping[trigger]
        return trigger # no tranformation
