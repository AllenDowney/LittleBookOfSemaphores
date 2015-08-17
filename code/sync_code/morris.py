## symmetric mutex solution

room1 = 0
room2 = 0
mutex = Semaphore(1)
t1 = Semaphore(1)
t2 = Semaphore(0)

## Thread code

mutex.wait()
    room1 += 1
mutex.signal()
                           
t1.wait()                 
    room2 += 1                
    mutex.wait()
    room1 -= 1

    if room1 == 0: 
        mutex.signal()
	t2.signal()
    else: 
        mutex.signal()
	t1.signal()

t2.wait()
    room2 -= 1

    // critical section

    if room2 == 0:
        t1.signal()
    else:
        t2.signal()
