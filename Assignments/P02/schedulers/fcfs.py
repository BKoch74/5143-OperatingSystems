"""
FCFS (First Come First Served) - This scheduling algorithm runs processes in the order they arrive.
It is non-preemptive, meaning once a job starts executing on the CPU, it runs until it either finishes
or performs an I/O operation. Jobs are executed sequentially based on their arrival order.
"""

# FCFS Scheduling
if sched == "FCFS" or sched == "ALL":

    # ---------------------------------------------------------
    # 1️⃣ Move jobs from Ready Queue → Running (CPU), if CPU available
    # ---------------------------------------------------------
    if len(FCFS_ReadyQueue) > 0:
        for job in FCFS_ReadyQueue:
            # If there’s an available CPU slot, assign the job to it
            if len(FCFS_Running) < Num_CPUs:
                FCFS_Running.append(job)
                with beat(5):
                    update_row(table1, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                " ", " ", " ", " "])
                # Once a job is assigned to CPU, remove it from Ready Queue
                FCFS_ReadyQueue.remove(job)

            # If no CPU is available, job must wait
            else:
                job.increment_ready_wait_time()
                with beat(5):
                    update_row(table1, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                " ", " ", " ", " ", " "])

    # ---------------------------------------------------------
    # 2️⃣ Process jobs currently in the Running (CPU) state
    # ---------------------------------------------------------
    for job in FCFS_Running:

        # --- Handle I/O Bursts ---
        if job.get_burst_type() == "IO":
            # Move job to Waiting Queue to perform I/O
            FCFS_WaitingQueue.append(job)
            with beat(5):
                update_row(table1, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ", " ", " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                            " ", " ", " "])
            FCFS_Running.remove(job)
            continue

        # --- Handle CPU Bursts ---
        if job.get_burst_type() == "CPU":
            # If current CPU burst has finished
            if job.get_burst_time() == 0:
                job.get_next_burst()              # Move to next burst (I/O or EXIT)
                FCFS_WaitingQueue.append(job)     # Move to waiting queue
                with beat(5):
                    update_row(table1, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                " ", " ", " "])
                FCFS_Running.remove(job)
                continue

            # If CPU burst still ongoing
            else:
                job.decrement_burst_time()    # Decrease remaining CPU burst time
                job.increment_running_time()  # Track how long it has run

                with beat(5):
                    update_row(table1, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                " ", " ", " ", " "])

                # If job completes CPU burst after decrementing
                if job.get_burst_time() == 0:
                    job.get_next_burst()
                    FCFS_WaitingQueue.append(job)
                    with beat(5):
                        update_row(table1, (job.get_id() - 1),
                                   [str(job.get_arrival_time()), " ", " ", " ",
                                    f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                    " ", " ", " "])
                    FCFS_Running.remove(job)
                    continue

        # --- Handle Job Completion (Exit) ---
        if job.get_burst_type() == "EXIT":
            job.set_exit_time(clock)           # Mark completion time
            FCFS_FinishedQueue.append(job)     # Move job to finished queue
            with beat(5):
                update_row(table1, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ", " ", " ", " ", " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                            str(job.get_exit_time())])
            FCFS_Running.remove(job)

    # ---------------------------------------------------------
    # 3️⃣ Move jobs from Waiting Queue → I/O Queue or Ready Queue
    # ---------------------------------------------------------
    for job in FCFS_WaitingQueue:

        # --- Handle I/O Bursts ---
        if job.get_burst_type() == "IO":
            # If an I/O device is available, move job to I/O queue
            if len(FCFS_IO_Queue) < ios:
                FCFS_IO_Queue.append(job)
                with beat(5):
                    update_row(table1, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ", " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                " ", " "])
                FCFS_WaitingQueue.remove(job)

            # Otherwise, job must wait for I/O to become free
            else:
                job.increment_io_wait_time()
                with beat(5):
                    update_row(table1, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                " ", " ", " "])

        # --- Handle CPU-Ready Jobs (post-I/O or new arrivals) ---
        else:
            FCFS_ReadyQueue.append(job)
            with beat(5):
                update_row(table1, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                            " ", " ", " ", " ", " "])
            FCFS_WaitingQueue.remove(job)

    # ---------------------------------------------------------
    # 4️⃣ Process jobs currently in the I/O Queue
    # ---------------------------------------------------------
    for job in FCFS_IO_Queue:

        # --- If I/O burst finished ---
        if job.get_burst_time() == 0:
            job.get_next_burst()
            FCFS_ReadyQueue.append(job)
            with beat(5):
                update_row(table1, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                            " ", " ", " ", " ", " "])
            FCFS_IO_Queue.remove(job)

        # --- If still performing I/O ---
        else:
            job.decrement_burst_time()  # Continue processing I/O burst
            with beat(5):
                update_row(table1, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ", " ", " ", " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                            " ", " "])

            # When I/O burst completes after decrement
            if job.get_burst_time() == 0:
                job.get_next_burst()
                FCFS_ReadyQueue.append(job)
                with beat(5):
                    update_row(table1, job.get_id() - 1,
                               [str(job.get_arrival_time()), " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                " ", " ", " ", " ", " "])
                FCFS_IO_Queue.remove(job)
