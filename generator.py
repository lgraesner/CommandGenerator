import random
import re
import warnings
import qrcode
from PIL import Image, ImageDraw, ImageFont
from gpsr_commands import CommandGenerator
from egpsr_commands import EgpsrCommandGenerator
import yaml


def read_data(file_path):
    with open(file_path, 'r') as file:
        data = file.read()
    return data


def parse_names(data):
    parsed_names = re.findall(r'\|\s*([A-Za-z]+)\s*\|', data, re.DOTALL)
    parsed_names = [name.strip() for name in parsed_names]

    if parsed_names:
        return parsed_names[1:]
    else:
        warnings.warn("List of names is empty. Check content of names markdown file")
        return []


def parse_locations(data):
    parsed_locations = re.findall(r'\|\s*([0-9]+)\s*\|\s*([A-Za-z,\s, \(,\)]+)\|', data, re.DOTALL)
    parsed_locations = [b for (a, b) in parsed_locations]
    parsed_locations = [location.strip() for location in parsed_locations]

    parsed_placement_locations = [location for location in parsed_locations if location.endswith('(p)')]
    parsed_locations = [location.replace('(p)', '') for location in parsed_locations]
    parsed_placement_locations = [location.replace('(p)', '') for location in parsed_placement_locations]
    parsed_placement_locations = [location.strip() for location in parsed_placement_locations]
    parsed_locations = [location.strip() for location in parsed_locations]

    if parsed_locations:
        return parsed_locations, parsed_placement_locations
    else:
        warnings.warn("List of locations is empty. Check content of location markdown file")
        return []


def parse_rooms(data):
    parsed_rooms = re.findall(r'\|\s*(\w+ \w*)\s*\|', data, re.DOTALL)
    parsed_rooms = [rooms.strip() for rooms in parsed_rooms]

    if parsed_rooms:
        return parsed_rooms[1:]
    else:
        warnings.warn("List of rooms is empty. Check content of room markdown file")
        return []


def parse_objects(data):
    parsed_objects = re.findall(r'\|\s*(\w+)\s*\|', data, re.DOTALL)
    parsed_objects = [objects for objects in parsed_objects if objects != 'Objectname']
    parsed_objects = [objects.replace("_", " ") for objects in parsed_objects]
    parsed_objects = [objects.strip() for objects in parsed_objects]

    parsed_categories = re.findall(r'# Class \s*([\w,\s, \(,\)]+)\s*', data, re.DOTALL)
    parsed_categories = [category.strip() for category in parsed_categories]
    parsed_categories = [category.replace('(', '').replace(')', '').split() for category in parsed_categories]
    parsed_categories_plural = [category[0] for category in parsed_categories]
    parsed_categories_plural = [category.replace("_", " ") for category in parsed_categories_plural]
    parsed_categories_singular = [category[1] for category in parsed_categories]
    parsed_categories_singular = [category.replace("_", " ") for category in parsed_categories_singular]

    if parsed_objects or parsed_categories:
        return parsed_objects, parsed_categories_plural, parsed_categories_singular
    else:
        warnings.warn("List of objects or object categories is empty. Check content of object markdown file")
        return []


if __name__ == "__main__":
    names_file_path = '../names/names.md'
    locations_file_path = '../maps/location_names.md'
    rooms_file_path = '../maps/room_names.md'
    objects_file_path = '../objects/test.md'
    yaml_file = open("NLA_YAML.yaml", "w")

    examples = {}
    examples["nlu"] = []

    names_data = read_data(names_file_path)
    names = parse_names(names_data)

    locations_data = read_data(locations_file_path)
    location_names, placement_location_names = parse_locations(locations_data)

    rooms_data = read_data(rooms_file_path)
    room_names = parse_rooms(rooms_data)

    objects_data = read_data(objects_file_path)
    object_names, object_categories_plural, object_categories_singular = parse_objects(objects_data)

    generator = CommandGenerator(names, location_names, placement_location_names, room_names, object_names,
                                 object_categories_plural, object_categories_singular)
    egpsr_generator = EgpsrCommandGenerator(generator)
    user_prompt = "'1': Any command,\n" \
                  "'2': Command without manipulation,\n" \
                  "'3': Command with manipulation,\n" \
                  "'5': Generate EGPSR setup,\n" \
                  "'0': Generate QR code for the last command,\n" \
                  "'-n [number]': run command multiple times,\n" \
                  "'s': Save YAML file\n" \
                  "'q': Quit"
    print(user_prompt)
    command = ""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=30,
        border=4,
    )
    last_input = '?'
    try:
        while True:
            # Read user input
            user_input = input()
            
            #check optional arguments
            argument = re.search(r'-n\s+(\d+)', user_input)
            command_count = 1 if (argument is None) else int(argument.group(1))

            for i in range(command_count):
                command = ""
                intents = []
                # Check user input
                if user_input[0] == '1':
                    command, intents = generator.generate_command_start(cmd_category="")
                    last_input = "1"
                elif user_input[0] == '2':
                    command, intents = generator.generate_command_start(cmd_category="people")
                    last_input = "2"
                elif user_input[0] == '3':
                    command, intents = generator.generate_command_start(cmd_category="objects")
                    last_input = "3"
                elif user_input[0] == "5":
                    command, intents = egpsr_generator.generate_setup()
                    last_input = "5"
                elif user_input[0] == 'q':
                    quit()
                elif user_input[0] == '0':
                    commands = [command]
                    for c in commands:
                        qr.clear()
                        qr.add_data(c)
                        qr.make(fit=True)

                        img = qr.make_image(fill_color="black", back_color="white")
                        # Create a drawing object
                        draw = ImageDraw.Draw(img)

                        # Load a font
                        font = ImageFont.truetype("Arial.ttf", 30)

                        # Calculate text size and position
                        text_size = draw.textsize(c, font)
                        if text_size[0] > img.size[0]:
                            font = ImageFont.truetype("Arial.ttf", 15)
                            text_size = draw.textsize(c, font)
                        text_position = ((img.size[0] - text_size[0]) // 2, img.size[1] - text_size[1] - 10)

                        # Draw text on the image
                        draw.text(text_position, c, font=font, fill="black")
                        img.show()
                elif user_input[0] == 's':
                    print(examples)
                    for e in examples["nlu"]:
                        eSet = set(e["examples"])
                        count = len(e["examples"])
                        e["examples"] = list(eSet)[0:min(count, 15)]  #limit examples to 10 and remove duplicates
                    print(yaml.dump(examples, yaml_file, width=10000))
                    break

                    
                else:
                    print(user_prompt)
                    break
                intents = '+'.join(intents)

                entry = {}
                entry["intent"] = intents
                entry["examples"] = [command]
                
                present = False
                for e in examples["nlu"]:
                    if e["intent"] == entry["intent"]:
                        e["examples"].append(command)
                        present = True
                if not present:
                    examples["nlu"].append(entry)

                
    except KeyboardInterrupt:
        print("KeyboardInterrupt. Exiting the loop.")