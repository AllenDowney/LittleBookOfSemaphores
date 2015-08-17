# Dance problem from Exam 1
leader1 = Semaphore(0)
follower1 = Semaphore(0)
leader2 = Semaphore(0)
follower2 = Semaphore(0)
multiplex = Semaphore(4)

## Thread A
follower1.signal()
leader1.wait()
multiplex.wait()
    #dance
multiplex.signal()
follower2.signal()
leader2.wait()

## Thread B
leader1.signal()
follower1.wait()
multiplex.wait()
    #dance
multiplex.signal()
leader2.signal()
follower2.wait()

