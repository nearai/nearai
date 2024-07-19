import fire

from .cli import CLI


def main() -> None:
    fire.Fire(CLI)


if __name__ == "__main__":
    main()
