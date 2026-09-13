"""A plain local's first assignment is always free; the second one, without
`Mut`, is a violation `mut_check._reassignment` catches (`ty` doesn't).
"""

x = 5
# noinspection redeclaration
x = 6
