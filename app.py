from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox,
    QGridLayout, QGroupBox, QHBoxLayout, QStackedLayout, QTableWidget, QTableWidgetItem, QPushButton, QDateEdit,
    QSpinBox, QListWidget
)
from PyQt5.QtCore import Qt, QEvent, QDate
from PyQt5.QtGui import QColor
from database import Database
from scheduler_logic import generate_schedule
import sys

class EmployeeDialog(QDialog):
    def __init__(self, title, name="", phone="", availability=None, max_shifts=0, min_shifts=0):
        super().__init__()
        self.setWindowTitle(title)

        # Default availability if none provided
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
        time_slots = ["12am-6am", "6am-12pm", "9am-3pm", "12pm-6pm", "3pm-9pm", "6pm-12am", "9pm-3am"]
        self.availability_checkboxes = {}
        self.preferred_shifts = {}

        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            group_box = QGroupBox(day)
            group_layout = QGridLayout()
            self.availability_checkboxes[day] = {}

            # Get the availability for the day, or empty list if no availability
            day_availability = availability.get(day, [])

            row, col = 0, 0
            for slot in time_slots:
                checkbox = QCheckBox(slot)
                # Check if the slot is part of the day's availability, including preferred shifts (indicated by *)
                if f"{slot} *" in day_availability:
                    checkbox.setChecked(True)
                    checkbox.setText(f"{slot} *")  # Mark as preferred shift
                elif slot in day_availability:
                    checkbox.setChecked(True)
                    checkbox.setText(slot)  # Regular shift
                
                self.availability_checkboxes[day][slot] = checkbox
                group_layout.addWidget(checkbox, row, col)

                # Attach double-click event to toggle preferred shift (add/remove *)
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
        
        # Create a dictionary for the availability, including preferred shifts
        availability = {
            day: [
                f"{slot} *" if f"{slot} *" in self.availability_checkboxes[day][slot].text() else slot
                for slot, checkbox in self.availability_checkboxes[day].items()
                if checkbox.isChecked()
            ]
            for day in self.availability_checkboxes
        }
        
        return {
            "name": self.name_input.text(),
            "phone": self.phone_input.text(),
            "availability": availability,
            "max_shifts": self.max_shifts_input.value(),
            "min_shifts": self.min_shifts_input.value(),
        }

    
    def make_preferred_shift(self, checkbox, day, slot):
        """Toggle preferred shift (add/remove '*') on double-click."""
        def on_double_click(event):
            if event.type() == QEvent.MouseButtonDblClick:
                # Check the current label of the checkbox
                current_text = checkbox.text()

                if "*" in current_text:
                    # Remove '*' if already present (un-preference)
                    checkbox.setText(slot)
                else:
                    # Add '*' to indicate preferred shift
                    checkbox.setText(f"{slot} *")
                    
                # Optionally, update the dictionary with preferred shifts
                if f"{slot} *" in checkbox.text():
                    # Add the preferred shift to the dictionary if it's marked with '*'
                    if day not in self.preferred_shifts:
                        self.preferred_shifts[day] = []
                    if slot not in self.preferred_shifts[day]:
                        self.preferred_shifts[day].append(f"{slot} *")
                else:
                    # Remove it from the dictionary if it's unmarked
                    if day in self.preferred_shifts and f"{slot} *" in self.preferred_shifts[day]:
                        self.preferred_shifts[day].remove(f"{slot} *")

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

        self.excluded_slots = []  # Store excluded (day, slot) pairs

        layout = QVBoxLayout(self)

        self.start_date_picker = QDateEdit(self)
        self.start_date_picker.setDate(QDate.currentDate())
        self.start_date_picker.setCalendarPopup(True)
        self.start_date_picker.setDisplayFormat("yyyy-MM-dd")
        layout.addWidget(self.start_date_picker)

        self.generate_schedule_button = QPushButton("Generate Schedule", self)
        self.generate_schedule_button.clicked.connect(self.generate_schedule)
        layout.addWidget(self.generate_schedule_button)

        self.schedule_table = QTableWidget(self)
        self.schedule_table.setColumnCount(7)
        self.schedule_table.setRowCount(7)
        self.schedule_table.setHorizontalHeaderLabels(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        )
        time_slots = ["12am-6am", "6am-12pm", "9am-3pm", "12pm-6pm", "3pm-9pm", "6pm-12am", "9pm-3am"]
        for row, slot in enumerate(time_slots):
            item = QTableWidgetItem(slot)
            self.schedule_table.setVerticalHeaderItem(row, item)

        self.schedule_table.cellDoubleClicked.connect(self.toggle_exclusion)

        self.load_empty_schedule()
        layout.addWidget(self.schedule_table)

    def load_empty_schedule(self):
        for row in range(self.schedule_table.rowCount()):
            for col in range(self.schedule_table.columnCount()):
                item = QTableWidgetItem("")
                self.schedule_table.setItem(row, col, item)

    def toggle_exclusion(self, row, col):
        day = self.schedule_table.horizontalHeaderItem(col).text()
        slot = self.schedule_table.verticalHeaderItem(row).text()
        item = self.schedule_table.item(row, col)

        key = (day, slot)

        if key in self.excluded_slots:
            self.excluded_slots.remove(key)
            item.setBackground(QTableWidgetItem().background())
        else:
            self.excluded_slots.append(key)
            item.setBackground(QColor("#fca5a5"))  # light red

    def generate_schedule(self):
        start_date = self.start_date_picker.date().toString("yyyy-MM-dd")
        schedule = generate_schedule(start_date, self.database, excluded=self.excluded_slots)

        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        time_slots = ["12am-6am", "6am-12pm", "9am-3pm", "12pm-6pm", "3pm-9pm", "6pm-12am", "9pm-3am"]

        self.schedule_table.setRowCount(len(time_slots))
        self.schedule_table.setColumnCount(len(days_of_week))
        self.schedule_table.setHorizontalHeaderLabels(days_of_week)
        self.schedule_table.setVerticalHeaderLabels(time_slots)

        for row, slot in enumerate(time_slots):
            for col, day in enumerate(days_of_week):
                employees = schedule[day][slot]
                item = self.schedule_table.item(row, col)
                if not item:
                    item = QTableWidgetItem()
                    self.schedule_table.setItem(row, col, item)
                item.setText(employees)
                if (day, slot) in self.excluded_slots:
                    item.setBackground(QColor("#fca5a5"))

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
        self.time_off_page = TimeOffPage(self.database)  # Time off page placeholder

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

class TimeOffPage(QWidget):
    def __init__(self, database):
        super().__init__()
        self.database = database
        layout = QVBoxLayout(self)

        self.request_button = QPushButton("Add Time Off Request")
        self.request_button.clicked.connect(self.show_time_off_dialog)
        layout.addWidget(self.request_button)

        self.delete_button = QPushButton("Delete Selected Request")
        self.delete_button.clicked.connect(self.delete_selected_request)
        layout.addWidget(self.delete_button)

        self.timeoff_list = QListWidget()
        layout.addWidget(self.timeoff_list)

        self.load_time_off_requests()

    def show_time_off_dialog(self):
        dialog = TimeOffDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
            self.database.add_time_off_request(
                data["employee_name"],
                data["start_date"],
                data["end_date"],
                data["reason"]
            )
            self.load_time_off_requests()

    def load_time_off_requests(self):
        self.timeoff_list.clear()
        self.time_off_data = self.database.get_all_time_off_requests()
        for r in self.time_off_data:
            self.timeoff_list.addItem(
                f"{r['employee_name']} | {r['start_date']} to {r['end_date']} | {r['reason']}"
            )

    def delete_selected_request(self):
        selected_item = self.timeoff_list.currentRow()
        if selected_item >= 0:
            request = self.time_off_data[selected_item]
            self.database.delete_time_off_request(
                request["employee_name"],
                request["start_date"]
            )
            self.load_time_off_requests()

class TimeOffDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Request Time Off")

        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        layout.addRow("Employee Name:", self.name_input)

        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDate(QDate.currentDate())
        layout.addRow("Start Date:", self.start_date_input)

        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDate(QDate.currentDate())
        layout.addRow("End Date:", self.end_date_input)

        self.reason_input = QLineEdit()
        layout.addRow("Reason:", self.reason_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def get_data(self):
        return {
            "employee_name": self.name_input.text(),
            "start_date": self.start_date_input.date().toString("yyyy-MM-dd"),
            "end_date": self.end_date_input.date().toString("yyyy-MM-dd"),
            "reason": self.reason_input.text()
        }



def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()
