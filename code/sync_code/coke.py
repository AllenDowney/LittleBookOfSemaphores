# producer-consumer
mutex = Semaphore(1)
cokes = Semaphore(0)
spaces = Semaphore(3)

## Thread
cokes.wait()
mutex.wait()
    # get a coke
mutex.signal()
spaces.signal()
# drink the coke

## Thread
# bring a coke
spaces.wait()
mutex.wait()
    # put a coke
mutex.signal()
cokes.signal()
