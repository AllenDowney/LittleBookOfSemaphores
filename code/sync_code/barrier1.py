# barrier non-solution

## initalization
count = 0
mutex = Semaphore(1)
barrier = Semaphore(0)


## Thread code
# rendezvous

mutex.wait()
    count = count + 1
mutex.signal()

if count == num_threads(): barrier.signal()

barrier.wait()

# critical point



