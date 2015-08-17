# Rendezvous
Aarrived = Semaphore(0)
Barrived = Semaphore(0)

## Thread A
Aarrived.signal()			 
Barrived.wait()
# proceed

## Thread B
Barrived.signal()
Aarrived.wait()
# proceed
