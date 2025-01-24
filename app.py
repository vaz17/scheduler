from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox, QGridLayout, 
    QGroupBox, QHBoxLayout, QStackedLayout, QTableWidget, QTableWidgetItem, QPushButton, QDateEdit, QSpinBox, QListWidget
)
from PyQt5.QtCore import Qt, QEvent, QDate
from database import Database
import sys
from scheduler_logic import generate_schedule

class EmployeeDialog(QDialog):
    def __init__(self, title, name="", phone="", availability=None, max_shifts=0, min_shifts=0):
        super().__init__()
        self.setWindowTitle(title)

        # Default availability i
        # if none provided
        if availability is None:
            availability = {day: [] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}

        layout = QFormLayout(self)

        # Input fields
        self.name_input = QLineEdit(self)
        self.name_input.setText(name)
        layout.addRow('Employee Name:', self.name_input)

        self.phone_input = QLineEdit(self)
        self.phone_input.setText(phone)
        layout.addRow('Phone Number:', self.phone_input)

        # Availability time slots
        time_slots = ["12am-6am", "6am-12pm", "9am-3pm", "12pm-6pm", "3pm-9pm", "6pm-12pm", "9pm-3am"]
        self.availability_checkboxes = {}
        self.preferred_shifts = {}

        for day in availability.keys():
            group_box = QGroupBox(day)
            group_layout = QGridLayout()
            self.availability_checkboxes[day] = {}

            row, col = 0, 0
            for slot in time_slots:
                checkbox = QCheckBox(slot)
                checkbox.setChecked(slot in availability[day])
                self.availability_checkboxes[day][slot] = checkbox
                group_layout.addWidget(checkbox, row, col)

                checkbox.mouseDoubleClickEvent = self.make_preferred_shift(checkbox, day, slot)

                col += 1
                if col > 3:  # 4 columns per row
                    col = 0
                    row += 1

            group_box.setLayout(group_layout)
            layout.addRow(group_box)

        # Add fields for max and min shifts
        self.max_shifts_input = QSpinBox(self)
        self.max_shifts_input.setRange(0, 7)  # Assume max 7 shifts per week
        self.max_shifts_input.setValue(max_shifts)
        layout.addRow("Maximum Shifts per Week:", self.max_shifts_input)

        self.min_shifts_input = QSpinBox(self)
        self.min_shifts_input.setRange(0, 7)  # Assume min 0 shifts per week
        self.min_shifts_input.setValue(min_shifts)
        layout.addRow("Minimum Shifts per Week:", self.min_shifts_input)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        layout.addWidget(button_box)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def get_employee_data(self):
        """Return the entered employee data as a dictionary."""
        return {
            "name": self.name_input.text(),
            "phone": self.phone_input.text(),
            "availability": {
                day: [slot for slot, checkbox in self.availability_checkboxes[day].items() if checkbox.isChecked()]
                for day in self.availability_checkboxes
            },
            "max_shifts": self.max_shifts_input.value(),
            "min_shifts": self.min_shifts_input.value(),
        }
    
    def make_preferred_shift(self, checkbox, day, slot):
        """Mark the shift as preferred on double-click."""
        def on_double_click(event):
            # Toggle the preferred status when the checkbox is double-clicked
            if event.type() == QEvent.MouseButtonDblClick:
                # Mark as preferred by changing the background color or some other indicator
                if checkbox.isChecked():
                    # If checked, mark it as preferred (e.g., background color change)
                    checkbox.setStyleSheet("background-color: lightgreen;")
                    if day not in self.preferred_shifts:
                        self.preferred_shifts[day] = []
                    if slot not in self.preferred_shifts[day]:
                        self.preferred_shifts[day].append(slot)
                else:
                    # Reset if unchecked
                    checkbox.setStyleSheet("")
                    if day in self.preferred_shifts and slot in self.preferred_shifts[day]:
                        self.preferred_shifts[day].remove(slot)

        return on_double_click

class EmployeeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Employee Scheduler")
        self.resize(800, 600)

        self.database = Database()

        # Main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        # Employee list
        self.employee_list = QListWidget()
        layout.addWidget(self.employee_list)

        # Buttons
        self.add_employee_button = QPushButton("Add Employee")
        self.edit_employee_button = QPushButton("Edit Employee")
        self.delete_employee_button = QPushButton("Delete Employee")
        layout.addWidget(self.add_employee_button)
        layout.addWidget(self.edit_employee_button)
        layout.addWidget(self.delete_employee_button)

        # Button connections
        self.add_employee_button.clicked.connect(self.show_new_employee_page)
        self.edit_employee_button.clicked.connect(self.show_edit_employee_page)
        self.delete_employee_button.clicked.connect(self.delete_employee)

        # Load employees
        self.load_employees()

    def load_employees(self):
        """Load employees from the database into the list."""
        employees = self.database.get_all_employees()
        for employee in employees:
            self.employee_list.addItem(employee["name"])

    def show_new_employee_page(self):
        new_employee_dialog = EmployeeDialog("New Employee")
        if new_employee_dialog.exec_():
            new_employee_data = new_employee_dialog.get_employee_data()
            self.database.add_employee(
                new_employee_data["name"],
                new_employee_data["phone"],
                new_employee_data["availability"],
                new_employee_data["max_shifts"],
                new_employee_data["min_shifts"]
            )
            self.employee_list.addItem(new_employee_data["name"])

    def show_edit_employee_page(self):
        selected_item = self.employee_list.currentItem()
        if selected_item:
            employee_name = selected_item.text()
            employee_data = self.database.get_employee_by_name(employee_name)
            if employee_data:
                edit_employee_dialog = EmployeeDialog(
                    "Edit Employee",
                    name=employee_data["name"],
                    phone=employee_data["phone"],
                    availability=employee_data["availability"],
                    max_shifts=employee_data["max_shifts"],
                    min_shifts=employee_data["min_shifts"]
                )
                if edit_employee_dialog.exec_():
                    updated_data = edit_employee_dialog.get_employee_data()
                    self.database.update_employee(
                        updated_data["name"],
                        updated_data["phone"],
                        updated_data["availability"],
                        updated_data["max_shifts"],
                        updated_data["min_shifts"]
                    )
                    selected_item.setText(updated_data["name"])

    def delete_employee(self):
        selected_item = self.employee_list.currentItem()
        if selected_item:
            employee_name = selected_item.text()
            self.database.delete_employee(employee_name)
            self.employee_list.takeItem(self.employee_list.row(selected_item))

class SchedulerWindow(QWidget):
    def __init__(self, database):
        super().__init__()

        self.database = database
        self.setWindowTitle("Schedule Generator")
        self.resize(800, 600)

        # Main layout for the scheduler
        layout = QVBoxLayout(self)

        # Create a date picker for the start date
        self.start_date_picker = QDateEdit(self)
        self.start_date_picker.setDate(QDate.currentDate())  # Default to today's date
        self.start_date_picker.setCalendarPopup(True)
        self.start_date_picker.setDisplayFormat("yyyy-MM-dd")  # Format for the date (optional)
        layout.addWidget(self.start_date_picker)

        # Create a button to generate the schedule
        self.generate_schedule_button = QPushButton("Generate Schedule", self)
        self.generate_schedule_button.clicked.connect(self.generate_schedule)
        layout.addWidget(self.generate_schedule_button)

        # Create a table for the schedule
        self.schedule_table = QTableWidget(self)
        self.schedule_table.setColumnCount(7)  # 7 days of the week
        self.schedule_table.setRowCount(7)  # 7 time slots (example)

        # Set column headers (days of the week)
        self.schedule_table.setHorizontalHeaderLabels(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        )

        # Set row headers (time slots)
        time_slots = ["12am-6am", "6am-12pm", "9am-3pm", "12pm-6pm", "3pm-9pm", "6pm-12pm", "9pm-3am"]
        for row, slot in enumerate(time_slots):
            item = QTableWidgetItem(slot)
            self.schedule_table.setVerticalHeaderItem(row, item)

        # Load empty schedule by default
        self.load_empty_schedule()

        # Add the table to the layout
        layout.addWidget(self.schedule_table)

    def load_empty_schedule(self):
        """Load an empty schedule with no employee names."""
        for row in range(self.schedule_table.rowCount()):
            for col in range(self.schedule_table.columnCount()):
                item = QTableWidgetItem("")  # Empty cell by default
                self.schedule_table.setItem(row, col, item)

    def generate_schedule(self):
        """Generate the schedule based on the selected start date and populate the schedule table."""
        # Retrieve the selected start date
        start_date = self.start_date_picker.date().toString("yyyy-MM-dd")
        print(f"Generating schedule starting from: {start_date}")

        # Call the scheduling logic to generate the schedule
        schedule = generate_schedule(start_date, self.database)

        # Define days of the week and time slots
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        time_slots = ["12am-6am", "6am-12pm", "9am-3pm", "12pm-6pm", "3pm-9pm", "6pm-12pm", "9pm-3am"]

        # Ensure the table has the correct dimensions
        self.schedule_table.setRowCount(len(time_slots))
        self.schedule_table.setColumnCount(len(days_of_week))
        self.schedule_table.setHorizontalHeaderLabels(days_of_week)
        self.schedule_table.setVerticalHeaderLabels(time_slots)

        # Populate the table with the generated schedule
        for row, slot in enumerate(time_slots):
            for col, day in enumerate(days_of_week):
                # Get the list of employees assigned to this day and time slot
                employees = schedule[day][slot]
                # Format the employees' names into a string
                cell_text = ", ".join(employees) if employees else "No Employees"
                # Populate the table cell
                item = self.schedule_table.item(row, col)
                if not item:
                    # If no QTableWidgetItem exists, create one
                    item = QTableWidgetItem()
                    self.schedule_table.setItem(row, col, item)
                item.setText(cell_text)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")

        # Layouts
        pagelayout = QVBoxLayout()
        button_layout = QHBoxLayout()
        self.stacklayout = QStackedLayout()

        # Database connection
        self.database = Database()

        # Buttons to navigate between pages
        btn_schedule = QPushButton("Schedule")
        btn_schedule.pressed.connect(self.activate_tab_1)
        button_layout.addWidget(btn_schedule)

        btn_employees = QPushButton("Employees")
        btn_employees.pressed.connect(self.activate_tab_2)
        button_layout.addWidget(btn_employees)

        btn_timeoff = QPushButton("Time Off")
        btn_timeoff.pressed.connect(self.activate_tab_3)
        button_layout.addWidget(btn_timeoff)

        # Add the pages (widgets) to the stacked layout
        self.scheduler_page = SchedulerWindow(self.database)  # Scheduler page (to be filled later)
        self.employee_page = EmployeeWindow()  # Employee window
        self.time_off_page = QWidget()  # Time off page placeholder

        self.stacklayout.addWidget(self.scheduler_page)
        self.stacklayout.addWidget(self.employee_page)
        self.stacklayout.addWidget(self.time_off_page)

        # Add the button layout and stack layout to the main layout
        pagelayout.addLayout(button_layout)
        pagelayout.addLayout(self.stacklayout)

        # Set the central widget of the window
        widget = QWidget()
        widget.setLayout(pagelayout)
        self.setCentralWidget(widget)

    def activate_tab_1(self):
        """Switch to the scheduler page"""
        self.stacklayout.setCurrentIndex(0)

    def activate_tab_2(self):
        """Switch to the employee page"""
        self.stacklayout.setCurrentIndex(1)

    def activate_tab_3(self):
        """Switch to the time off page"""
        self.stacklayout.setCurrentIndex(2)



def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()
