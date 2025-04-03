from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from collections import defaultdict

def generate_schedule(start_date, database):
    # Only change to enter debug mode
    debug_mode = False
    # -------------------- Setup --------------------
    start_date = datetime.strptime(start_date, "%Y-%m-%d")

    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    time_slots = ["12am-6am", "6am-12pm", "9am-3pm", "12pm-6pm", "3pm-9pm", "6pm-12am", "9pm-3am"]

    employees = database.get_all_employees()

    # Add a placeholder employee to represent unfilled shifts
    no_employee = {
        "name": "No Employee",
        "availability": {day: time_slots for day in days_of_week},
        "min_shifts": 0,
        "max_shifts": len(time_slots) * len(days_of_week),
    }
    employees.append(no_employee)

    # -------------------- Time-Off Handling --------------------
    time_off_requests = database.get_all_time_off_requests()
    unavailable_dates = defaultdict(set)

    week_start = start_date
    week_end = week_start + timedelta(days=6)

    # Loops through time_off_requests and marks those days unavailable
    for entry in time_off_requests:
        name = entry["employee_name"]
        start = datetime.strptime(entry["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(entry["end_date"], "%Y-%m-%d").date()
        current = start
        while current <= end:
            if week_start.date() <= current <= week_end.date():
                unavailable_dates[name].add(current)
            current += timedelta(days=1)

    # -------------------- Constraint Model Setup --------------------
    model = cp_model.CpModel()

    num_employees = len(employees)
    num_shifts = len(time_slots)
    num_days = len(days_of_week)

    all_employees = range(num_employees)
    all_shifts = range(num_shifts)
    all_days = range(num_days)

    # -------------------- Shift Variables --------------------
    shifts = {}
    for e in all_employees:
        for d in all_days:
            for s in all_shifts:
                shifts[(e, d, s)] = model.NewBoolVar(f"shift_e{e}_d{d}_s{s}")

    # -------------------- Basic Constraints --------------------

    # Ensure each shift has exactly one assigned employee
    for d in all_days:
        for s in all_shifts:
            model.AddExactlyOne(shifts[(e, d, s)] for e in all_employees)

    # Ensure employees have at most one shift per day (excluding 'No Employee')
    for e in range(num_employees - 1):
        for d in all_days:
            model.AddAtMostOne(shifts[(e, d, s)] for s in all_shifts)

    # -------------------- Objective Weights --------------------
    preferred_shift_weight = 1
    not_available_penalty = -50
    no_employee_penalty = -40

    # Penalize assigning employees to shifts they're not available for
    available_shifts = sum(
        not_available_penalty * shifts[(e, d, s)]
        for e in range(num_employees - 1)
        for d in all_days
        for s in all_shifts
        if (time_slots[s] not in employees[e]['availability'].get(days_of_week[d], [])
            and f"{time_slots[s]} *" not in employees[e]['availability'].get(days_of_week[d], []))
    )

    # -------------------- Time-Off Constraint & Shift Adjustment --------------------
    employee_diff = defaultdict(int)

    # Restricts employee assigning on time off requests
    for d in all_days:
        date = week_start + timedelta(days=d)
        day_name = days_of_week[d]
        for e in range(num_employees - 1):
            name = employees[e]["name"]
            if date.date() in unavailable_dates[name]:
                for s in all_shifts:
                    model.Add(shifts[(e, d, s)] == 0)
                if employees[e]["availability"].get(day_name):
                    employee_diff[e] += 1  # Only count if they were otherwise available

    # Reward assigning employees to their preferred shifts
    preferred_shifts = sum(
        preferred_shift_weight * shifts[(e, d, s)]
        for e in range(num_employees - 1)
        for d in all_days
        for s in all_shifts
        if (f"{time_slots[s]} *" in employees[e]['availability'].get(days_of_week[d], []))
    )

    # Penalize using the 'No Employee' placeholder
    no_employee_score = sum(
        no_employee_penalty * shifts[(num_employees - 1, d, s)]
        for d in all_days
        for s in all_shifts
    )

    # -------------------- Shift Count Constraints --------------------
    total_shift_penalty = 0

    for e in range(num_employees - 1):
        total_shifts_worked = sum(shifts[(e, d, s)] for d in all_days for s in all_shifts)

        min_shifts = employees[e]["min_shifts"]
        max_shifts = employees[e]["max_shifts"]

        adjustment = employee_diff.get(e, 0)
        max_shifts = max(max_shifts - adjustment, 0)
        min_shifts = min(min(min_shifts, 2), max_shifts)

        if min_shifts > 0:
            shift_penalty = (total_shifts_worked - min_shifts) * (10 / min_shifts)
            total_shift_penalty += shift_penalty

        model.Add(total_shifts_worked >= min_shifts)
        model.Add(total_shifts_worked <= max_shifts)

    # -------------------- Objective Function --------------------
    model.Maximize(
        no_employee_score + preferred_shifts + available_shifts - total_shift_penalty
    )

    # -------------------- Solve Model --------------------
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # -------------------- Report Results --------------------
    for e in range(num_employees - 1):
        total_shifts_worked = sum(solver.Value(shifts[(e, d, s)]) for d in all_days for s in all_shifts)
        employee = employees[e]['name']
        if e not in employee_diff:
            min_shifts = employees[e]["min_shifts"]
        else:
            min_shifts = min(0, employees[e]["min_shifts"] - employee_diff[e])
        shift_diff = total_shifts_worked - min_shifts
        print(f"Employee: {employee}, Minimum Shifts: {min_shifts}, Shifts Worked: {total_shifts_worked}, Difference: {shift_diff}")

    # -------------------- Generate Final Schedule --------------------
    schedule = {day: {slot: "No Employees" for slot in time_slots} for day in days_of_week}

    if status in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        for d in all_days:
            for s in all_shifts:
                for e in all_employees:
                    if solver.Value(shifts[(e, d, s)]) == 1:
                        day = days_of_week[d]
                        slot = time_slots[s]
                        if schedule[day][slot] == "No Employees":
                            schedule[day][slot] = employees[e]['name']
                        else:
                            schedule[day][slot] += f", {employees[e]['name']}"

        print("Solution found!")
        print("\nStatistics")
        print(f"  - conflicts: {solver.NumConflicts()}")
        print(f"  - branches : {solver.NumBranches()}")
        print(f"  - wall time: {solver.WallTime()} s")
        print(f"Schedule Score = {solver.ObjectiveValue()}")


        if debug_mode:
            while True:
                print("\n--- DEBUG MODE: Check Availability ---")
                day_input = input("Enter a day to inspect (e.g., Monday), or 'exit' to quit: ").strip()
                if day_input.lower() == "exit":
                    break
                if day_input not in days_of_week:
                    print("Invalid day. Try again.")
                    continue

                print(f"Available time slots: {', '.join(time_slots)}")
                slot_input = input("Enter a time slot (e.g., 12pm-6pm): ").strip()
                if slot_input not in time_slots:
                    print("Invalid time slot. Try again.")
                    continue

                d = days_of_week.index(day_input)
                s = time_slots.index(slot_input)

                available = []
                for e in range(num_employees - 1):  # exclude 'No Employee'
                    availability = employees[e]['availability'].get(day_input, [])
                    if time_slots[s] in availability or f"{time_slots[s]} *" in availability:
                        available.append(employees[e]['name'])

                if available:
                    print(f"{day_input} - {slot_input}: Available Employees -> {', '.join(available)}")
                else:
                    print(f"No one is available for {day_input} - {slot_input}")

        return schedule

    else:
        print("No feasible solution found!")
        return schedule
    

