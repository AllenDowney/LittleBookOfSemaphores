# deadlock example

aArrived = Semaphore(0)
bArrived = Semaphore(0)

## Thread A

# statement a1
bArrived.wait()
aArrived.signal()
# statement a2


##Thread B

# statement b1
aArrived.wait()
bArrived.signal()
# statement b2


