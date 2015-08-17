# simple barrier

## initalization
count = 0
mutex = Semaphore(1)
barrier = Semaphore(0)


## Thread code
# rendezvous

mutex.wait()
    count = count + 1
    if count == num_threads(): barrier.signal()
mutex.signal()

barrier.wait()
barrier.signal()

# critical point



