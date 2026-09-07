"""Wrong use of a `@mut_method`-decorated method's return type; must be flagged.

If `mut_method` erased the method's signature (e.g. widened its return type
to `Any`), this assignment would type-check with zero complaints.
"""

from immutablepy import mut_method


class Box:
    def __init__(self, value: int) -> None:
        self.value = value

    @mut_method
    def add(self, amount: int) -> int:
        self.value += amount
        return self.value


result: str = Box(1).add(5)
