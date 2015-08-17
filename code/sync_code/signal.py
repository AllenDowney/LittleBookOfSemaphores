# signaling example
initComplete = Semaphore(0)

## Thread A                
# perform initialization
initComplete.signal()
# proceed

## Thread B
initComplete.wait()
initComplete.signal()
# proceed
