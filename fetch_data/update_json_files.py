import json


def update_file(p_file):
    with open(p_file, 'r', encoding='utf-8') as opened_file:
        loaded = json.load(opened_file)

    new_dict = {}
    for key in loaded:
        if "owner" in loaded[key].keys():
            new_key = f'{loaded[key]["owner"]}/{loaded[key]["repository"]}'
        else:
            new_key = key
        new_dict[new_key] = loaded[key]
        new_dict[new_key]["name"] = key

    with open(p_file, 'w', encoding='utf-8') as opened_file:
        json.dump(new_dict, opened_file, indent=4)


if __name__ == "__main__":
    files = [
        "outputs/actions_data_10_03_2022.json",
        "outputs/actions_data_13_04_2022.json",
        "outputs/actions_data_29_04_2022.json",
        "outputs/actions_data_16_05_2022.json",
        "outputs/actions_data_17_05_2022.json",
    ]

    for file in files:
        update_file(file)
