"""Correct usage of a `@mut_method`-decorated method; must type-check clean."""

from immutablepy import mut_method


class Box:
    def __init__(self, value: int) -> None:
        self.value = value

    @mut_method
    def add(self, amount: int) -> int:
        self.value += amount
        return self.value


total: int = Box(1).add(5)
