class Employee:
    def __init__(self, id, name):
        self.id = id
        self.name = name

class Availability:
    def __init__(self, employee, day, shift):
        self.employee = employee
        self.day = day
        self.shift = shift