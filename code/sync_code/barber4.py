# FIFO barbershop
customers = 0
mutex = Semaphore(1)
mutex2 = Semaphore(1)
mutex3 = Semaphore(1)
sofa = Semaphore(4)
customer1 = Semaphore(0)
customer2 = Semaphore(0)
barber = Semaphore(0)
payment = Semaphore(0)
receipt = Semaphore(0)
queue1 = []
queue2 = []

## Thread
# customers
self.sem1 = Semaphore(0)
self.sem2 = Semaphore(0)

mutex.wait()
    if customers == 20:
        mutex.signal()
        balk()
    customers += 1
    queue1.append(self.sem1)
mutex.signal()

# enterShop()
customer1.signal()
self.sem1.wait()

sofa.wait()
    # sitOnSofa()
    self.sem1.signal()
    mutex2.wait()
        queue2.append(self.sem2)
    mutex2.signal()
    customer2.signal()
    self.sem2.wait()
sofa.signal()

# getHairCut()

mutex3.wait()
    # pay()
    payment.signal()
    receipt.wait()
mutex3.signal()

mutex.wait()
    customers -= 1
mutex.signal()

## Thread
# usher
customer1.wait()
mutex.wait()
    sem = queue1.pop(0)
    sem.signal()
    sem.wait()
mutex.signal()

## Thread
# barber
customer2.wait()
mutex2.wait()
    sem2 = queue2.pop(0)
    sem2.signal()
mutex2.signal()

# cutHair()
payment.wait()
# acceptPayment()
receipt.signal()
