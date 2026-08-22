# mutual exclusion
mutex = Semaphore(1)
counter = 0

## Thread code

mutex.wait()
# critical section
counter += 1
mutex.signal()

