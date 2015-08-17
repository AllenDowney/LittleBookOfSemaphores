# fox, goose and corn problem

fc = Lightswitch()
goose = Lightswitch()
fc_turn = Semaphore(1)
goose_turn = Semaphore(1)

## Thread 
#Fox code
fc_turn.wait()
    fc.lock(goose_turn)
fc_turn.signal()

# critical section

fc.unlock(goose_turn)



##  Thread 
#Goose code
goose_turn.wait()
    goose.lock(fc_turn)
goose_turn.signal()

# critical section

goose.unlock(fc_turn)



##  Thread 
#Corn code
fc_turn.wait()
    fc.lock(goose_turn)
fc_turn.signal()

# critical section

fc.unlock(goose_turn)



