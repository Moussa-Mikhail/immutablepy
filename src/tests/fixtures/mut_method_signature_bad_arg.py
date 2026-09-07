"""Wrong argument type to a `@mut_method`-decorated method; must be flagged.

If `mut_method` erased the method's signature (e.g. widened it to
`Callable[..., Any]`), this call would type-check with zero complaints.
"""

from immutablepy import mut_method


class Box:
    def __init__(self, value: int) -> None:
        self.value = value

    @mut_method
    def add(self, amount: int) -> int:
        self.value += amount
        return self.value


Box(1).add("not an int")
