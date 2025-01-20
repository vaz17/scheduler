import sqlite3

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('employee_scheduler.db')
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Create necessary tables if they don't exist."""
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            max_shifts INTEGER,
            min_shifts INTEGER
        )""")
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS availability (
            employee_id INTEGER,
            day TEXT,
            time_slot TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        )""")
        self.conn.commit()

    def add_employee(self, name, phone, availability, max_shifts, min_shifts):
        """Add a new employee with availability."""
        self.cursor.execute("""
        INSERT INTO employees (name, phone, max_shifts, min_shifts)
        VALUES (?, ?, ?, ?)""", (name, phone, max_shifts, min_shifts))
        employee_id = self.cursor.lastrowid

        for day, time_slots in availability.items():
            for slot in time_slots:
                self.cursor.execute("""
                INSERT INTO availability (employee_id, day, time_slot)
                VALUES (?, ?, ?)""", (employee_id, day, slot))
        
        self.conn.commit()

    def get_all_employees(self):
        """Retrieve all employees with their availability."""
        self.cursor.execute("""
        SELECT id, name, phone, max_shifts, min_shifts FROM employees""")
        employees = []
        
        for row in self.cursor.fetchall():
            employee_id, name, phone, max_shifts, min_shifts = row
            self.cursor.execute("""
            SELECT day, time_slot FROM availability WHERE employee_id = ?""", (employee_id,))
            availability = {}
            for day, slot in self.cursor.fetchall():
                if day not in availability:
                    availability[day] = []
                availability[day].append(slot)
            employees.append({
                "name": name,
                "phone": phone,
                "max_shifts": max_shifts,
                "min_shifts": min_shifts,
                "availability": availability
            })
        
        return employees

    def get_employee_by_name(self, name):
        """Retrieve an employee's details by name."""
        self.cursor.execute("""
        SELECT id, name, phone, max_shifts, min_shifts FROM employees WHERE name = ?""", (name,))
        employee = self.cursor.fetchone()
        if employee:
            employee_id, name, phone, max_shifts, min_shifts = employee
            self.cursor.execute("""
            SELECT day, time_slot FROM availability WHERE employee_id = ?""", (employee_id,))
            availability = {}
            for day, slot in self.cursor.fetchall():
                if day not in availability:
                    availability[day] = []
                availability[day].append(slot)
            return {
                "name": name,
                "phone": phone,
                "max_shifts": max_shifts,
                "min_shifts": min_shifts,
                "availability": availability
            }
        return None

    def update_employee(self, name, phone, availability, max_shifts, min_shifts):
        """Update an existing employee's details."""
        self.cursor.execute("""
        UPDATE employees SET name = ?, phone = ?, max_shifts = ?, min_shifts = ?
        WHERE name = ?""", (name, phone, max_shifts, min_shifts, name))
        
        self.cursor.execute("""
        DELETE FROM availability WHERE employee_id IN (SELECT id FROM employees WHERE name = ?)""", (name,))
        self.conn.commit()

        self.cursor.execute("""
        SELECT id FROM employees WHERE name = ?""", (name,))
        employee_id = self.cursor.fetchone()[0]

        for day, time_slots in availability.items():
            for slot in time_slots:
                self.cursor.execute("""
                INSERT INTO availability (employee_id, day, time_slot)
                VALUES (?, ?, ?)""", (employee_id, day, slot))

        self.conn.commit()

    def delete_employee(self, name):
        """Delete an employee by name."""
        self.cursor.execute("""
        DELETE FROM availability WHERE employee_id IN (SELECT id FROM employees WHERE name = ?)""", (name,))
        self.cursor.execute("""
        DELETE FROM employees WHERE name = ?""", (name,))
        self.conn.commit()