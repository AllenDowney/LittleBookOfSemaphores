# mutual exclusion

mutex = Semaphore(1)
x = 0

## Thread A

mutex.wait()
    # critical section
    x = x + 1
mutex.signal()

## Thread B

mutex.wait()
    # critical section
    x = x + 1
mutex.signal()

