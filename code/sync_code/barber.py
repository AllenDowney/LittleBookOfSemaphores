# The barbershop problem
n = 4
customers = 0
mutex = Semaphore(1)
customer = Semaphore(0)
barber = Semaphore(0)
customerDone = Semaphore(0)
barberDone = Semaphore(0)

## Thread
# customers
mutex.wait()
    if customers == n:
        mutex.signal()
        balk()
    customers += 1
mutex.signal()

customer.signal()
barber.wait()        

# getHairCut()

customerDone.signal()
barberDone.wait()        

mutex.wait()
    customers -= 1
mutex.signal()


## Thread
# barber
customer.wait()
barber.signal()

# cutHair()

customerDone.wait()
barberDone.signal()
