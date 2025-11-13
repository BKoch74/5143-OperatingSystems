"""
Priority-Based Scheduling (PB)
-----------------------------
This scheduling algorithm chooses jobs to execute based on their priority values.

- Each job has a priority number (lower value = higher priority).
- The scheduler always selects the job with the highest priority to run next.
- If two jobs have the same priority, they are executed in First-Come, First-Served (FCFS) order.
- This is a **preemptive** algorithm: a new higher-priority job can interrupt a running lower-priority job.
- Advantage: Improves response time for important jobs.
- Disadvantage: Can cause starvation for low-priority jobs.
"""

# Priority-Based Scheduling
if sched == "PB" or sched == "ALL":

    # ---------------------------------------------------------
    # 1️⃣ Move jobs from Ready Queue → Running (CPU), if CPU available or preemption occurs
    # ---------------------------------------------------------
    if len(PB_ReadyQueue) > 0:
        for job in PB_ReadyQueue:

            # --- Case 1: CPU available, assign job directly ---
            if len(PB_Running) < Num_CPUs:
                PB_Running.append(job)
                with beat(5):
                    update_row(table2, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} "
                                f"P: {job.get_priority()}",
                                " ", " ", " ", " "])
                PB_ReadyQueue.remove(job)

            # --- Case 2: CPU full, check if preemption is needed ---
            else:
                for PB_job in PB_Running:
                    # If the new job has a higher priority (lower number)
                    if PB_job.get_priority() > job.get_priority():

                        # Preempt the lower-priority job
                        PB_Running.append(job)
                        with beat(5):
                            update_row(table2, (job.get_id() - 1),
                                       [str(job.get_arrival_time()), " ", " ",
                                        f"J{job.get_id()} {job.get_burst_type()} "
                                        f"{job.get_burst_time()} P: {job.get_priority()}",
                                        " ", " ", " ", " "])
                        PB_ReadyQueue.remove(job)

                        # Move preempted job to Waiting Queue
                        PB_WaitingQueue.append(PB_job)
                        with beat(5):
                            update_row(table2, (PB_job.get_id() - 1),
                                       [str(PB_job.get_arrival_time()), " ", " ", "",
                                        f"J{PB_job.get_id()}, BT: {PB_job.get_burst_type()}",
                                        " ", " ", " "])
                        PB_Running.remove(PB_job)
                        break

                    # Otherwise, if the new job is lower or equal in priority, it must wait
                    else:
                        job.increment_ready_wait_time()

    # ---------------------------------------------------------
    # 2️⃣ Process jobs currently running on the CPU
    # ---------------------------------------------------------
    for job in PB_Running:

        # --- Handle I/O bursts ---
        if job.get_burst_type() == "IO":
            PB_WaitingQueue.append(job)
            with beat(5):
                update_row(table2, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ", " ", " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} "
                            f"P: {job.get_priority()}",
                            " ", " ", " "])
            PB_Running.remove(job)
            continue

        # --- Handle CPU bursts ---
        if job.get_burst_type() == "CPU":

            # If the CPU burst has completed
            if job.get_burst_time() == 0:
                job.get_next_burst()             # Move to next burst (IO/EXIT)
                PB_WaitingQueue.append(job)
                with beat(5):
                    update_row(table2, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} "
                                f"P: {job.get_priority()}",
                                " ", " ", " "])
                PB_Running.remove(job)
                continue

            # If still running CPU burst
            else:
                job.decrement_burst_time()        # Decrease CPU burst time
                job.increment_running_time()      # Track how long it’s been running
                with beat(5):
                    update_row(table2, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} "
                                f"P: {job.get_priority()}",
                                " ", " ", " ", " "])

                # If burst finishes after decrement
                if job.get_burst_time() == 0:
                    job.get_next_burst()
                    PB_WaitingQueue.append(job)
                    with beat(5):
                        update_row(table2, (job.get_id() - 1),
                                   [str(job.get_arrival_time()), " ", " ", " ",
                                    f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} "
                                    f"P: {job.get_priority()}",
                                    " ", " ", " "])
                    PB_Running.remove(job)
                    continue

        # --- Handle jobs that have completed all bursts (EXIT) ---
        if job.get_burst_type() == "EXIT":
            job.set_exit_time(clock)
            PB_FinishedQueue.append(job)
            with beat(5):
                update_row(table2, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ", " ", " ", " ", " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} "
                            f"P: {job.get_priority()}",
                            str(job.get_exit_time())])
            PB_Running.remove(job)

    # ---------------------------------------------------------
    # 3️⃣ Move jobs from Waiting Queue → I/O Queue or Ready Queue
    # ---------------------------------------------------------
    for job in PB_WaitingQueue:

        # --- Handle I/O bursts ---
        if job.get_burst_type() == "IO":
            # If an I/O device is free, start I/O
            if len(PB_IO_Queue) < ios:
                PB_IO_Queue.append(job)
                with beat(5):
                    update_row(table2, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ", " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} "
                                f"P: {job.get_priority()}",
                                " ", " "])
                PB_WaitingQueue.remove(job)

            # Otherwise, wait for I/O availability
            else:
                job.increment_io_wait_time()

        # --- Handle CPU-ready jobs ---
        else:
            PB_ReadyQueue.append(job)
            with beat(5):
                update_row(table2, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} "
                            f"P: {job.get_priority()}",
                            " ", " ", " ", " ", " "])
            PB_WaitingQueue.remove(job)

    # ---------------------------------------------------------
    # 4️⃣ Process jobs currently in the I/O Queue
    # ---------------------------------------------------------
    for job in PB_IO_Queue:

        # --- If I/O burst is finished ---
        if job.get_burst_time() == 0:
            job.get_next_burst()
            PB_ReadyQueue.append(job)
            with beat(5):
                update_row(table2, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} "
                            f"P: {job.get_priority()}",
                            " ", " ", " ", " ", " "])
            PB_IO_Queue.remove(job)

        # --- If I/O burst still in progress ---
        else:
            job.decrement_burst_time()
            with beat(5):
                update_row(table2, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ", " ", " ", " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} "
                            f"P: {job.get_priority()}",
                            " ", " "])

            # Once I/O completes after decrement
            if job.get_burst_time() == 0:
                job.get_next_burst()
                PB_ReadyQueue.append(job)
                with beat(5):
                    update_row(table2, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} "
                                f"P: {job.get_priority()}",
                                " ", " ", " ", " ", " "])
                PB_IO_Queue.remove(job)
