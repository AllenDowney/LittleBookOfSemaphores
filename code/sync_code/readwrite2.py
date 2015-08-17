# readers-writers
readSwitch = Lightswitch()
roomEmpty = Semaphore(1)

## Thread
# writers
roomEmpty.wait()
#    go ahead and write
roomEmpty.signal()

## Thread
#readers
readSwitch.lock(roomEmpty)
# critical section for readers
readSwitch.unlock(roomEmpty)

