# multiplex

multiplex = Semaphore(3)

## Thread code

multiplex.wait()
    # critical section
multiplex.signal()

