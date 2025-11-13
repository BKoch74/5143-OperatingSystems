"""
Round Robin Scheduling (RR) is a scheduling algorithm that assigns a fixed number of CPU time slots to each job.
Each process gets a small unit of CPU time (called a time slice or quantum) and then is moved to the back of the queue.
"""

# Round Robin scheduling
if sched == "RR" or sched == "ALL":

    # -----------------------------
    # 1️⃣ Assign jobs from Ready Queue to Running (CPU) if CPU is available
    # -----------------------------
    if len(RR_ReadyQueue) > 0:
        for job in RR_ReadyQueue:
            if len(RR_Running) < Num_CPUs:  # If CPU slot is free
                RR_Running.append(job)  # Move job to running state
                with beat(5):
                    update_row(table3, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                " ", " ", " ", " "])
                RR_ReadyQueue.remove(job)  # Remove job from ready queue
            else:
                # If all CPUs are busy, increase the job's waiting time
                job.increment_ready_wait_time()

    # -----------------------------
    # 2️⃣ Process jobs currently running on CPU
    # -----------------------------
    for job in RR_Running:

        # --- Handle I/O Bursts ---
        if job.get_burst_type() == "IO":
            RR_WaitingQueue.append(job)  # Move job to waiting queue for I/O
            with beat(5):
                update_row(table3, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ", " ", " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                            " ", " ", " "])
            RR_Running.remove(job)
            continue

        # --- Handle CPU Bursts ---
        if job.get_burst_type() == "CPU":

            # Case 1: Job has not exceeded its time slice
            if job.get_cpu_time() <= time_slice:

                # If current CPU burst finished
                if job.get_burst_time() == 0:
                    job.get_next_burst()        # Move to next burst (could be IO or EXIT)
                    job.reset_cpu_time()        # Reset CPU time for next burst
                    RR_WaitingQueue.append(job) # Move to waiting queue
                    with beat(5):
                        update_row(table3, (job.get_id() - 1),
                                   [str(job.get_arrival_time()), " ", " ", " ",
                                    f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                    " ", " ", " "])
                    RR_Running.remove(job)
                    continue
                else:
                    # Decrement burst time and increment counters
                    job.decrement_burst_time()
                    job.increment_running_time()
                    job.increment_cpu_time()

                    # Update display
                    with beat(5):
                        update_row(table3, (job.get_id() - 1),
                                   [str(job.get_arrival_time()), " ", " ",
                                    f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()} P: {job.get_priority()}",
                                    " ", " ", " ", " "])

                    # If job finished CPU burst after decrementing
                    if job.get_burst_time() == 0:
                        job.get_next_burst()
                        job.reset_cpu_time()
                        RR_WaitingQueue.append(job)
                        with beat(5):
                            update_row(table3, (job.get_id() - 1),
                                       [str(job.get_arrival_time()), " ", " ", " ",
                                        f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                        " ", " ", " "])
                        RR_Running.remove(job)
                        continue

            # Case 2: Job has exceeded its time slice → preempted
            else:
                job.reset_cpu_time()
                RR_WaitingQueue.append(job)  # Move back to waiting queue
                with beat(5):
                    update_row(table3, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                " ", " ", " "])
                RR_Running.remove(job)

        # --- Handle Job Completion ---
        if job.get_burst_type() == "EXIT":
            job.set_exit_time(clock)  # Record exit time
            RR_FinishedQueue.append(job)
            with beat(5):
                update_row(table3, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ", " ", " ", " ", " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                            str(job.get_exit_time())])
            RR_Running.remove(job)

    # -----------------------------
    # 3️⃣ Move jobs from Waiting Queue → I/O Queue or Ready Queue
    # -----------------------------
    for job in RR_WaitingQueue:
        if job.get_burst_type() == "IO":
            # If I/O device available
            if len(RR_IO_Queue) < ios:
                RR_IO_Queue.append(job)
                with beat(5):
                    update_row(table3, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ", " ", " ", " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                " ", " "])
                RR_WaitingQueue.remove(job)
            else:
                # Waiting for I/O device
                job.increment_io_wait_time()
        else:
            # Move CPU-ready jobs back to ready queue
            RR_ReadyQueue.append(job)
            with beat(5):
                update_row(table3, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                            " ", " ", " ", " ", " "])
            RR_WaitingQueue.remove(job)

    # -----------------------------
    # 4️⃣ Process jobs in I/O Queue
    # -----------------------------
    for job in RR_IO_Queue:

        # I/O burst completed → move back to ready queue
        if job.get_burst_time() == 0:
            job.get_next_burst()
            RR_ReadyQueue.append(job)
            with beat(5):
                update_row(table3, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                            " ", " ", " ", " ", " "])
            RR_IO_Queue.remove(job)
        else:
            # Continue I/O burst
            job.decrement_burst_time()
            with beat(5):
                update_row(table3, (job.get_id() - 1),
                           [str(job.get_arrival_time()), " ", " ", " ", " ",
                            f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                            " ", " "])

            # If I/O burst finishes after decrement
            if job.get_burst_time() == 0:
                job.get_next_burst()
                RR_ReadyQueue.append(job)
                with beat(5):
                    update_row(table3, (job.get_id() - 1),
                               [str(job.get_arrival_time()), " ",
                                f"J{job.get_id()} {job.get_burst_type()} {job.get_burst_time()}",
                                " ", " ", " ", " ", " "])
                RR_IO_Queue.remove(job)
