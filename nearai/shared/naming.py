import re

from nearai.shared.client_config import DEFAULT_NAMESPACE


def get_canonical_name(name: str) -> str:
    """Returns a name that can be used for matching entities.

    Applies such transformations:
    1. All letters lowercase.
    2. Strips '.near' extensions.
    3. Convert '.' between digits to 'p'.
    4. Convert '<not letter>v<digit>' -> '<not letter><digit>'
    5. Remove all non-alphanumeric characters except between digits.
        Use '_' between digits.
    6. Convert 'metallama' -> 'llama'.

    e.g. "llama-3.1-70b-instruct" -> "llama3p1_70binstruct"
    """
    # Convert to lowercase
    name = name.lower()
    # Strip .near extension if present
    if name.endswith(".near"):
        name = name[:-5]  # Remove last 5 characters ('.near')
    # Convert '.' between digits to 'p'
    name = re.sub(r"(\d)\.(\d)", r"\1p\2", name)
    # Convert '<digit>v<digit>' -> '<digit>_<digit>'
    name = re.sub(r"(\d)v(\d)", r"\1_\2", name)
    # Convert '<not letter>v<digit>' -> '<not letter><digit>'
    name = re.sub(r"(^|[^a-z])v(\d)", r"\1\2", name)
    # Replace non-alphanumeric characters between digits with '_'
    name = re.sub(r"(\d)[^a-z0-9]+(\d)", r"\1_\2", name)
    # Remove remaining non-alphanumeric characters, except '_'
    name = re.sub(r"[^a-z0-9_]", "", name)
    # Remove any remaining underscores that are not between digits
    name = re.sub(r"(?<!\d)_|_(?!\d)", "", name)
    # Convert 'metallama' to 'llama'
    name = name.replace("metallama", "llama")
    # Convert 'qwenq' to 'q'
    name = name.replace("qwenq", "q")
    return name


def create_registry_name(name: str) -> str:
    """Formats `name` for a suitable registry name."""
    # Convert to lowercase
    name = name.lower()
    # Convert '.' between digits to 'p'
    name = re.sub(r"(\d)\.(\d)", r"\1p\2", name)
    # Convert '<digit>v<digit>' -> '<digit>-<digit>'
    name = re.sub(r"(\d)v(\d)", r"\1-\2", name)
    # Convert '<not letter>v<digit>' -> '<not letter><digit>'
    name = re.sub(r"(^|[^a-z])v(\d)", r"\1\2", name)
    # Replace non-alphanumeric characters between digits with '-'
    name = re.sub(r"(\d)[^a-z0-9]+(\d)", r"\1-\2", name)
    # Remove remaining non-alphanumeric characters, except '-'
    name = re.sub(r"[^a-z0-9-]", "", name)
    # Convert 'metallama' or 'meta-llama' to 'llama'
    name = name.replace("metallama", "llama")
    name = name.replace("meta-llama", "llama")
    # Convert 'qwenq' or 'qwen-q' to 'q'
    name = name.replace("qwenq", "q")
    name = name.replace("qwen-q", "q")
    return name


class NamespacedName:
    def __init__(self, name: str, namespace: str = ""):  # noqa: D107
        self.name = name
        self.namespace = namespace

    def __eq__(self, other):  # noqa: D105
        if not isinstance(other, NamespacedName):
            return NotImplemented
        return self.name == other.name and self.namespace == other.namespace

    def __hash__(self):  # noqa: D105
        return hash((self.name, self.namespace))

    def __str__(self):  # noqa: D105
        if self.namespace:
            return f"{self.namespace}/{self.name}"
        return self.name

    def __repr__(self):  # noqa: D105
        return f"NamespacedName(name='{self.name}', namespace='{self.namespace}')"

    def canonical(self) -> "NamespacedName":  # noqa: D105
        """Returns canonical NamespacedName."""
        return NamespacedName(
            name=get_canonical_name(self.name),
            namespace=get_canonical_name(self.namespace) if self.namespace != DEFAULT_NAMESPACE else "",
        )
