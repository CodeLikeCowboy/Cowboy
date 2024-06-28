def update_config_file(file_path):
    with open(file_path, "r") as file:
        content = file.read()

    # Use regex to replace the line
    updated_content = re.sub(
        r'^CLIENT_MODE = ".*"', 'CLIENT_MODE = "release"', content, flags=re.MULTILINE
    )

    with open(file_path, "w") as file:
        file.write(updated_content)


if __name__ == "__main__":
    config_file_path = "cowboy/config.py"
    update_config_file(config_file_path)
