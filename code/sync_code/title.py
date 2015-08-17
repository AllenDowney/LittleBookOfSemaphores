# readers-writers
readers = 0
mutex = Semaphore(1)
roomEmpty = Semaphore(1)

## Thread
#readers
mutex.wait()
    readers += 1
    if readers == 1: roomEmpty.wait()
mutex.signal()
# Synchronization in Python
mutex.wait()
    readers -= 1
    if readers == 0: roomEmpty.signal()
mutex.signal()

## Thread
# writers
roomEmpty.wait()
# Allen Downey
# Olin College of Engineering
# for the Boston Python Interest Group
# July 14, 2005
roomEmpty.signal()

