# readers-writers
readers = 0
mutex = Semaphore(1)
roomEmpty = Semaphore(1)

## Thread
# writers
roomEmpty.wait()
#    go ahead and write
roomEmpty.signal()

## Thread
#readers
mutex.wait()
    readers += 1
    if readers == 1: roomEmpty.wait()
mutex.signal()
# critical section for readers
mutex.wait()
    readers -= 1
    if readers == 0: roomEmpty.signal()
mutex.signal()

