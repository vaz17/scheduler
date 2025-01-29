from ortools.sat.python import cp_model
from datetime import datetime


def generate_schedule(start_date, database):
    # Parse the start date from the input string into a datetime object
    start_date = datetime.strptime(start_date, "%Y-%m-%d")

    # Define the days of the week and time slots for shifts
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    time_slots = ["12am-6am", "6am-12pm", "9am-3pm", "12pm-6pm", "3pm-9pm", "6pm-12am", "9pm-3am"]

    # Fetch all employees from the database
    employees = database.get_all_employees()

    # Add a placeholder for "No Employee" to handle empty shifts
    no_employee = {
        "name": "No Employee",
        "availability": {day: time_slots for day in days_of_week},
        "min_shifts": 0,
        "max_shifts": len(time_slots) * len(days_of_week),  # Can fill all shifts if needed
    }
    employees.append(no_employee)

    # Create the CP-SAT model
    model = cp_model.CpModel()

    # Define variables for the number of employees, shifts, and days
    num_employees = len(employees)
    num_shifts = len(time_slots)
    num_days = len(days_of_week)
    
    # Create ranges for all employees, shifts, and days
    all_employees = range(num_employees)
    all_shifts = range(num_shifts)
    all_days = range(num_days)

    # Step 1: Create boolean variables for each employee-day-shift combination
    shifts = {}
    for e in all_employees:
        for d in all_days:
            for s in all_shifts:
                shifts[(e, d, s)] = model.NewBoolVar(f"shift_e{e}_d{d}_s{s}")

    # Step 2: Ensure exactly one employee is assigned to each shift per day
    for d in all_days:
        for s in all_shifts:
            model.AddExactlyOne(shifts[(e, d, s)] for e in all_employees)

    # Step 3: Ensure each employee is assigned at most one shift per day
    for e in range(num_employees - 1):  # Exclude "No Employee"
        for d in all_days:
            model.AddAtMostOne(shifts[(e, d, s)] for s in all_shifts)

    # Step 4: Define weight constants for the optimization objective
    preferred_shift_weight = 5  # Weight for preferred shifts
    not_available = -50        # Penalty for assigning unavailable shifts
    no_employee_penalty = -60   # Large negative penalty for using "No Employee"

    # Step 5: Define the penalties for unavailable and preferred shifts
    available_shifts = sum(
        not_available * shifts[(e, d, s)]
        for e in range(num_employees - 1)  # Exclude "No Employee"
        for d in all_days
        for s in all_shifts
        if (time_slots[s] not in employees[e]['availability'].get(days_of_week[d], []) 
            and f"{time_slots[s]} *" not in employees[e]['availability'].get(days_of_week[d], []))
    )

    preferred_shifts = sum(
        preferred_shift_weight * shifts[(e, d, s)]
        for e in range(num_employees - 1)  # Exclude "No Employee"
        for d in all_days
        for s in all_shifts
        if (f"{time_slots[s]} *" in employees[e]['availability'].get(days_of_week[d], []))
    )

    # Step 6: Define a penalty to minimize the use of "No Employee" placeholder
    no_employee_score = sum(
        no_employee_penalty * shifts[(num_employees - 1, d, s)]  # Index of "No Employee"
        for d in all_days
        for s in all_shifts
    )

    # Step 7: Add employee shift penalties to the objective
    for e in range(num_employees - 1):  # Exclude "No Employee"
        total_shifts_worked = sum(shifts[(e, d, s)] for d in all_days for s in all_shifts)
        
        # Compute how far the total shifts are from the minimum
        shift_diff = total_shifts_worked - employees[e]["min_shifts"]
        min_shifts = employees[e]["min_shifts"]
        
        # Apply a penalty based on how far shifts deviate from the minimum
        if min_shifts > 0:
            shift_penalty = shift_diff * (10 / min_shifts)  # Scaling factor can be adjusted
        else:
            shift_penalty = 0

        # Add the penalty to the objective function
        model.Maximize(
            no_employee_score + preferred_shifts + available_shifts + shift_penalty
        )
        
        # Ensure that the employee works within their min and max shifts
        model.Add(total_shifts_worked >= min(employees[e]["min_shifts"], 2))  # Example of a min shift
        model.Add(total_shifts_worked <= employees[e]["max_shifts"])

    # Step 8: Solve the model
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # Step 9: Calculate and print the shift difference for each employee
    for e in range(num_employees - 1):  # Exclude "No Employee"
        total_shifts_worked = sum(solver.Value(shifts[(e, d, s)]) for d in all_days for s in all_shifts)
        min_shifts = employees[e]["min_shifts"]
        shift_diff = total_shifts_worked - min_shifts
        print(f"Employee: {employees[e]['name']}, Minimum Shifts: {min_shifts}, "
              f"Shifts Worked: {total_shifts_worked}, Difference: {shift_diff}")

    # Step 10: Generate the final schedule in the desired format
    schedule = {day: {slot: "No Employees" for slot in time_slots} for day in days_of_week}

    # If a feasible or optimal solution is found, assign employees to shifts
    if status in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        for d in all_days:
            for s in all_shifts:
                for e in all_employees:
                    if solver.Value(shifts[(e, d, s)]) == 1:
                        day = days_of_week[d]
                        slot = time_slots[s]
                        # Assign employee to the time slot, appending if necessary
                        if schedule[day][slot] == "No Employees":
                            schedule[day][slot] = employees[e]['name']
                        else:
                            schedule[day][slot] += f", {employees[e]['name']}"

        print("Solution found!")
        # Print solver statistics
        print("\nStatistics")
        print(f"  - conflicts: {solver.NumConflicts()}")
        print(f"  - branches : {solver.NumBranches()}")
        print(f"  - wall time: {solver.WallTime()} s")
        print(f"Number of shift requests met = {solver.objective_value}")
        return schedule
    else:
        print("No feasible solution found!")
        return schedule
